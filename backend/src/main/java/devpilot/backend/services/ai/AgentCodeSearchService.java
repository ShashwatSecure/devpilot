package devpilot.backend.services.ai;

import java.util.List;
import java.util.UUID;

import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import devpilot.backend.dto.CodeSearchResultDto;
import devpilot.backend.util.ConversionUtils;
import lombok.RequiredArgsConstructor;

/**
 * Raw (uncollapsed) vector search used by the internal agent-service API. Unlike
 * {@link CodeContextRetriever} (which flattens results into one prompt string for the chat RAG
 * flow), this returns individual chunks so the LangGraph agent can reason over them as discrete
 * tool results.
 */
@Service
@RequiredArgsConstructor
public class AgentCodeSearchService {

    private final VectorStore vectorStore;

    public List<CodeSearchResultDto> search(UUID repositoryId, String query, int topK) {
        var search = SearchRequest.builder()
                .query(query)
                .topK(Math.max(1, Math.min(topK, 20)))
                .filterExpression(RagSettings.repoIdFilter(repositoryId))
                .build();

        return vectorStore.similaritySearch(search).stream()
                .map(this::toResult)
                .toList();
    }

    private CodeSearchResultDto toResult(Document document) {
        var meta = document.getMetadata();
        return new CodeSearchResultDto(
                ConversionUtils.stringVal(meta.get("filePath")),
                ConversionUtils.stringVal(meta.get("language")),
                document.getText(),
                ConversionUtils.intVal(meta.get("chunkIndex")),
                document.getScore());
    }
}
