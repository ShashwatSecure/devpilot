package devpilot.backend.services.ai;

import java.util.List;

import devpilot.backend.dto.CitationDto;

public record RetrievedContext(
        List<CitationDto> citations,
        String contextText) {
}
