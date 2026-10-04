package devpilot.backend.dto;

/** A code chunk returned from the internal vector-search API used by the Python agent-service. */
public record CodeSearchResultDto(
        String filePath,
        String language,
        String content,
        Integer chunkIndex,
        Double score) {
}
