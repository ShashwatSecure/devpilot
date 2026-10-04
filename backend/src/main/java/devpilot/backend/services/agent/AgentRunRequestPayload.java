package devpilot.backend.services.agent;

import java.util.List;

/** Payload sent to the Python agent-service to start a LangGraph run. */
public record AgentRunRequestPayload(
        String repositoryId,
        String repositoryFullName,
        IssuePayload issue,
        String internalApiBaseUrl,
        String internalApiKey,
        int maxReviewIterations) {

    public record IssuePayload(int number, String title, String body) {
    }
}

/** Final structured output of the graph (event: result). */
record AgentResultPayload(
        String issueType,
        String summary,
        String rootCause,
        List<String> plan,
        String proposedDiff,
        String prDescription,
        String testSuggestions,
        String reviewFeedback,
        String confidence,
        int iterations) {
}

/** Error payload (event: error). */
record AgentErrorPayload(String message) {
}
