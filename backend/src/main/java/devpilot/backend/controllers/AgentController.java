package devpilot.backend.controllers;

import java.util.List;
import java.util.UUID;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import devpilot.backend.dto.AgentRunResponse;
import devpilot.backend.dto.GithubIssueDto;
import devpilot.backend.dto.PostAgentCommentRequest;
import devpilot.backend.dto.StartAgentRunRequest;
import devpilot.backend.security.CurrentUser;
import devpilot.backend.services.agent.IssueAgentService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

/**
 * User-facing endpoints for the Issue Resolution Agent. All GitHub writes (posting a comment)
 * require an explicit call to {@code /post-comment} after the run has completed — nothing here
 * happens automatically.
 */
@RestController
@RequestMapping("/api/repos/{repoId}/agent")
@RequiredArgsConstructor
public class AgentController {

    private final CurrentUser currentUser;
    private final IssueAgentService issueAgentService;

    @GetMapping("/issues")
    public List<GithubIssueDto> listIssues(@PathVariable UUID repoId) {
        return issueAgentService.listOpenIssues(repoId, currentUser.id());
    }

    @PostMapping("/runs")
    public ResponseEntity<AgentRunResponse> createRun(
            @PathVariable UUID repoId, @Valid @RequestBody StartAgentRunRequest request) {
        return ResponseEntity.ok(issueAgentService.createRun(repoId, currentUser.id(), request.issueNumber()));
    }

    @GetMapping("/runs")
    public List<AgentRunResponse> listRuns(@PathVariable UUID repoId) {
        return issueAgentService.listRuns(repoId, currentUser.id());
    }

    @GetMapping("/runs/{runId}")
    public AgentRunResponse getRun(@PathVariable UUID repoId, @PathVariable UUID runId) {
        return issueAgentService.getRun(currentUser.id(), runId);
    }

    @PostMapping(value = "/runs/{runId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamRun(@PathVariable UUID repoId, @PathVariable UUID runId) {
        return issueAgentService.streamRun(currentUser.id(), runId);
    }

    @PostMapping("/runs/{runId}/post-comment")
    public AgentRunResponse postComment(
            @PathVariable UUID repoId,
            @PathVariable UUID runId,
            @RequestBody(required = false) PostAgentCommentRequest request) {
        String customBody = request != null ? request.commentBody() : null;
        return issueAgentService.postComment(currentUser.id(), runId, customBody);
    }
}
