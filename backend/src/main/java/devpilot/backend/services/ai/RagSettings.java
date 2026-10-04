package devpilot.backend.services.ai;

import java.util.UUID;

import org.springframework.ai.vectorstore.filter.Filter.Expression;
import org.springframework.ai.vectorstore.filter.FilterExpressionBuilder;

public final class RagSettings {
    /** How many code chunks to fetch from the vector database per question. */
    public static final int TOP_K_CHUNKS = 8;

    /** Max time (ms) to keep an SSE stream open while the model is responding. */
    public static final long STREAM_TIMEOUT_MS = 180_000L;

    /** Metadata key stored on each embedded document (must match {@link devpilot.backend.service.indexing.CodeChunker}). */
    public static final String METADATA_REPO_ID = "repoId";

    private RagSettings() {
    }

    /** Vector-store filter restricting a similarity search to a single repository's chunks. */
    public static Expression repoIdFilter(String repoId) {
        return new FilterExpressionBuilder().eq(METADATA_REPO_ID, repoId).build();
    }

    public static Expression repoIdFilter(UUID repoId) {
        return repoIdFilter(repoId.toString());
    }
}
