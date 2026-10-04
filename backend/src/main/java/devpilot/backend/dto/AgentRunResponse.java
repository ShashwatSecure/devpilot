package devpilot.backend.dto;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import devpilot.backend.entity.AgentRunStatus;

public record AgentRunResponse(
        UUID id,
        UUID repositoryId,
        int issueNumber,
        String issueTitle,
        String issueUrl,
        AgentRunStatus status,
        String issueType,
        String summary,
        String rootCause,
        List<String> plan,
        String proposedDiff,
        String prDescription,
        String testSuggestions,
        String reviewFeedback,
        String confidence,
        int iterations,
        boolean githubCommentPosted,
        String githubCommentUrl,
        String errorMessage,
        Instant createdAt,
        Instant updatedAt) {
}
