package devpilot.backend.dto;

/** A single GitHub issue, as shown in the "pick an issue" list before running the agent. */
public record GithubIssueDto(
        int number,
        String title,
        String body,
        String state,
        String htmlUrl,
        String authorLogin,
        int commentsCount,
        String createdAt) {
}
