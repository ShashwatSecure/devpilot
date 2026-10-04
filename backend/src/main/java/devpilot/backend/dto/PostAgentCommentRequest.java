package devpilot.backend.dto;

/** Optional override for the comment body; defaults to the agent's PR description when blank. */
public record PostAgentCommentRequest(String commentBody) {
}
