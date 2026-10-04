package devpilot.backend.services.ai;

import java.util.List;

import org.springframework.ai.document.Document;
import org.springframework.stereotype.Component;

import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import devpilot.backend.dto.ChatMessageResponse;
import devpilot.backend.dto.CitationDto;
import devpilot.backend.entity.ChatMessage;
import devpilot.backend.util.ConversionUtils;
import lombok.RequiredArgsConstructor;

/**
 * Converts vector-store {@link Document}s into API citations and JSON for persistence.
 */
@Component
@RequiredArgsConstructor
public class CitationMapper {

    private final JsonMapper jsonMapper;

    public CitationDto fromDocument(Document document) {
        var meta = document.getMetadata();
        return new CitationDto(
                ConversionUtils.stringVal(meta.get("filePath")),
                ConversionUtils.intVal(meta.get("startLine")),
                ConversionUtils.intVal(meta.get("endLine")),
                ConversionUtils.stringVal(meta.get("language")));
    }

    public String toJson(List<CitationDto> citations) {
        try {
            return jsonMapper.writeValueAsString(citations);
        } catch (JacksonException e) {
            return "[]";
        }
    }

    public List<CitationDto> fromJson(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            return jsonMapper.readValue(json, new TypeReference<>() {});
        } catch (JacksonException e) {
            return List.of();
        }
    }

    /** Maps a persisted chat message to its API response, decoding stored citation JSON. */
    public ChatMessageResponse toResponse(ChatMessage message) {
        return new ChatMessageResponse(
                message.getId(),
                message.getRole(),
                message.getContent(),
                fromJson(message.getCitations()),
                message.getCreatedAt());
    }
}
