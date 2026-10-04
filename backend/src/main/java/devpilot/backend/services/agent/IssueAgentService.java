package devpilot.backend.services.agent;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import devpilot.backend.dto.AgentRunResponse;
import devpilot.backend.dto.GithubIssueDto;
import devpilot.backend.entity.AgentRun;
import devpilot.backend.entity.AgentRunStatus;
import devpilot.backend.entity.IndexStatus;
import devpilot.backend.entity.Repository;
import devpilot.backend.exceptions.BadRequestException;
import devpilot.backend.exceptions.NotFoundException;
import devpilot.backend.repository.AgentRunRepository;
import devpilot.backend.services.RepoService;
import devpilot.backend.services.UserService;
import devpilot.backend.services.github.GithubApiClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/**
 * Orchestrates the "Issue Resolution Agent": fetches the GitHub issue, delegates the actual
 * multi-step reasoning to the Python LangGraph {@code agent-service}, relays its progress over
 * SSE, and persists the final proposal. Never commits, pushes, or executes generated code; posting
 * a comment back to GitHub is a separate, explicit, human-triggered action ({@link #postComment}).
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class IssueAgentService {

    private static final long AGENT_STREAM_TIMEOUT_MS = 300_000L;

    private final AgentRunRepository agentRunRepository;
    private final RepoService repoService;
    private final UserService userService;
    private final GithubApiClient githubApiClient;
    private final AgentClient agentClient;
    private final JsonMapper jsonMapper;

    // @Value("${app.agent.internal-api-key}")
    private String internalApiKey = "";

    @Value("${app.agent.max-review-iterations:2}")
    private int maxReviewIterations;

    @Value("${app.agent.backend-internal-base-url:http://localhost:8080/api/internal}")
    private String backendInternalBaseUrl;

    @Transactional(readOnly = true)
    public List<GithubIssueDto> listOpenIssues(UUID repoId, UUID userId) {
        Repository repo = repoService.requireOwned(repoId, userId);
        String token = userService.decryptAccessToken(userService.requiredById(userId));
        return githubApiClient.listOpenIssues(token, repo.getOwner(), repo.getName()).stream()
                .map(IssueAgentService::toIssueDto)
                .toList();
    }

    @Transactional
    public AgentRunResponse createRun(UUID repoId, UUID userId, int issueNumber) {
        Repository repo = repoService.requireOwned(repoId, userId);
        if (repo.getIndexStatus() != IndexStatus.READY) {
            throw new BadRequestException("Repository must be indexed before the agent can run");
        }
        String token = userService.decryptAccessToken(userService.requiredById(userId));
        Map<String, Object> issue = githubApiClient.getIssue(token, repo.getOwner(), repo.getName(), issueNumber);
        if (issue == null) {
            throw new NotFoundException("Issue #" + issueNumber + " not found");
        }

        AgentRun run = AgentRun.builder()
                .userId(userId)
                .repositoryId(repo.getId())
                .issueNumber(issueNumber)
                .issueTitle(String.valueOf(issue.get("title")))
                .issueUrl(issue.get("html_url") != null ? String.valueOf(issue.get("html_url")) : null)
                .status(AgentRunStatus.PENDING)
                .build();
        return toResponse(agentRunRepository.save(run));
    }

    @Transactional(readOnly = true)
    public List<AgentRunResponse> listRuns(UUID repoId, UUID userId) {
        repoService.requireOwned(repoId, userId);
        return agentRunRepository.findByUserIdAndRepositoryIdOrderByCreatedAtDesc(userId, repoId).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public AgentRunResponse getRun(UUID userId, UUID runId) {
        return toResponse(requireOwned(runId, userId));
    }

    /** Starts the LangGraph execution and streams its progress + final result over SSE. */
    public SseEmitter streamRun(UUID userId, UUID runId) {
        AgentRun run = requireOwned(runId, userId);
        if (run.getStatus() != AgentRunStatus.PENDING) {
            throw new BadRequestException("Agent run has already been started");
        }
        Repository repo = repoService.requireOwned(run.getRepositoryId(), userId);
        String token = userService.decryptAccessToken(userService.requiredById(userId));
        Map<String, Object> issue = githubApiClient.getIssue(
                token, repo.getOwner(), repo.getName(), run.getIssueNumber());
        String issueBody = issue != null && issue.get("body") != null ? String.valueOf(issue.get("body")) : "";

        run.setStatus(AgentRunStatus.RUNNING);
        agentRunRepository.save(run);

        var payload = new AgentRunRequestPayload(
                repo.getId().toString(),
                repo.getFullName(),
                new AgentRunRequestPayload.IssuePayload(run.getIssueNumber(), run.getIssueTitle(), issueBody),
                backendInternalBaseUrl,
                internalApiKey,
                maxReviewIterations);

        SseEmitter emitter = new SseEmitter(AGENT_STREAM_TIMEOUT_MS);
        AtomicBoolean finished = new AtomicBoolean(false);

        agentClient.streamIssueResolution(payload)
                .doOnNext(event -> handleEvent(emitter, run, event, finished))
                .doOnError(err -> handleFailure(emitter, run, err, finished))
                .doOnComplete(() -> handleStreamComplete(emitter, run, finished))
                .subscribe();

        return emitter;
    }

    @Transactional
    public AgentRunResponse postComment(UUID userId, UUID runId, String customBody) {
        AgentRun run = requireOwned(runId, userId);
        if (run.getStatus() != AgentRunStatus.COMPLETED) {
            throw new BadRequestException("Agent run has not completed successfully yet");
        }
        Repository repo = repoService.requireOwned(run.getRepositoryId(), userId);
        String token = userService.decryptAccessToken(userService.requiredById(userId));
        String body = (customBody != null && !customBody.isBlank()) ? customBody : buildDefaultComment(run);

        Map<String, Object> result = githubApiClient.postIssueComment(
                token, repo.getOwner(), repo.getName(), run.getIssueNumber(), body);

        run.setGithubCommentPosted(true);
        run.setGithubCommentUrl(result != null && result.get("html_url") != null
                ? String.valueOf(result.get("html_url"))
                : null);
        return toResponse(agentRunRepository.save(run));
    }

    private void handleEvent(SseEmitter emitter, AgentRun run, ServerSentEvent<String> event, AtomicBoolean finished) {
        if (finished.get()) {
            return;
        }
        String name = event.event() != null ? event.event() : "progress";
        String data = event.data();
        try {
            switch (name) {
                case "result" -> completeWithResult(emitter, run, data, finished);
                case "error" -> completeWithError(emitter, run, extractErrorMessage(data), finished);
                default -> emitter.send(SseEmitter.event().name("progress").data(data));
            }
        } catch (Exception ex) {
            log.error("Failed to relay agent event '{}' for run {}", name, run.getId(), ex);
            completeWithError(emitter, run, "Failed to process agent progress: " + ex.getMessage(), finished);
        }
    }

    private void completeWithResult(SseEmitter emitter, AgentRun run, String data, AtomicBoolean finished) {
        try {
            AgentResultPayload result = jsonMapper.readValue(data, AgentResultPayload.class);
            run.setIssueType(result.issueType());
            run.setSummary(result.summary());
            run.setRootCause(result.rootCause());
            run.setPlanJson(jsonMapper.writeValueAsString(result.plan() != null ? result.plan() : List.of()));
            run.setProposedDiff(result.proposedDiff());
            run.setPrDescription(result.prDescription());
            run.setTestSuggestions(result.testSuggestions());
            run.setReviewFeedback(result.reviewFeedback());
            run.setConfidence(result.confidence());
            run.setIterations(result.iterations());
            run.setStatus(AgentRunStatus.COMPLETED);
            agentRunRepository.save(run);

            emitter.send(SseEmitter.event().name("result").data(toResponse(run)));
            emitter.send(SseEmitter.event().name("done").data("[DONE]"));
            emitter.complete();
        } catch (Exception ex) {
            log.error("Failed to persist agent result for run {}", run.getId(), ex);
            completeWithError(emitter, run, "Failed to parse agent result: " + ex.getMessage(), finished);
            return;
        }
        finished.set(true);
    }

    private void completeWithError(SseEmitter emitter, AgentRun run, String message, AtomicBoolean finished) {
        if (!finished.compareAndSet(false, true)) {
            return;
        }
        run.setStatus(AgentRunStatus.FAILED);
        run.setErrorMessage(message);
        agentRunRepository.save(run);
        try {
            emitter.send(SseEmitter.event().name("error").data(Map.of("message", message)));
            emitter.send(SseEmitter.event().name("done").data("[DONE]"));
            emitter.complete();
        } catch (Exception ex) {
            emitter.completeWithError(ex);
        }
    }

    private void handleFailure(SseEmitter emitter, AgentRun run, Throwable err, AtomicBoolean finished) {
        log.error("Agent-service call failed for run {}", run.getId(), err);
        completeWithError(emitter, run, "Agent service unavailable: " + err.getMessage(), finished);
    }

    private void handleStreamComplete(SseEmitter emitter, AgentRun run, AtomicBoolean finished) {
        // No-op if a "result"/"error" event already finished the stream; otherwise the connection
        // closed unexpectedly and completeWithError's own compareAndSet guards against double-completion.
        completeWithError(emitter, run, "Agent service closed the connection unexpectedly", finished);
    }

    private String extractErrorMessage(String data) {
        try {
            AgentErrorPayload payload = jsonMapper.readValue(data, AgentErrorPayload.class);
            return payload.message();
        } catch (Exception ex) {
            return data;
        }
    }

    private String buildDefaultComment(AgentRun run) {
        return """
                🤖 **AI-generated analysis (DevPilot Issue Resolution Agent)**

                %s

                **Root cause**
                %s

                **Proposed fix**
                ```diff
                %s
                ```

                %s

                _This comment was generated automatically by an AI agent and has been reviewed by a maintainer before posting. Please verify before merging._
                """.formatted(
                run.getSummary(),
                run.getRootCause(),
                run.getProposedDiff(),
                run.getPrDescription());
    }

    private AgentRun requireOwned(UUID runId, UUID userId) {
        return agentRunRepository.findByIdAndUserId(runId, userId)
                .orElseThrow(() -> new NotFoundException("Agent run not found"));
    }

    private AgentRunResponse toResponse(AgentRun run) {
        return new AgentRunResponse(
                run.getId(),
                run.getRepositoryId(),
                run.getIssueNumber(),
                run.getIssueTitle(),
                run.getIssueUrl(),
                run.getStatus(),
                run.getIssueType(),
                run.getSummary(),
                run.getRootCause(),
                parsePlan(run.getPlanJson()),
                run.getProposedDiff(),
                run.getPrDescription(),
                run.getTestSuggestions(),
                run.getReviewFeedback(),
                run.getConfidence(),
                run.getIterations(),
                run.isGithubCommentPosted(),
                run.getGithubCommentUrl(),
                run.getErrorMessage(),
                run.getCreatedAt(),
                run.getUpdatedAt());
    }

    private List<String> parsePlan(String planJson) {
        if (planJson == null || planJson.isBlank()) {
            return List.of();
        }
        try {
            return jsonMapper.readValue(planJson, new TypeReference<>() {
            });
        } catch (Exception ex) {
            return List.of();
        }
    }

    @SuppressWarnings("unchecked")
    private static GithubIssueDto toIssueDto(Map<String, Object> issue) {
        String authorLogin = null;
        Object user = issue.get("user");
        if (user instanceof Map<?, ?> userMap && userMap.get("login") != null) {
            authorLogin = String.valueOf(userMap.get("login"));
        }
        return new GithubIssueDto(
                ((Number) issue.get("number")).intValue(),
                String.valueOf(issue.get("title")),
                issue.get("body") != null ? String.valueOf(issue.get("body")) : "",
                String.valueOf(issue.get("state")),
                issue.get("html_url") != null ? String.valueOf(issue.get("html_url")) : null,
                authorLogin,
                issue.get("comments") instanceof Number n ? n.intValue() : 0,
                issue.get("created_at") != null ? String.valueOf(issue.get("created_at")) : null);
    }
}
