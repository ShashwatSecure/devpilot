package devpilot.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.util.UUID;

/** Request body for the internal (agent-service -> backend) code search endpoint. */
public record InternalCodeSearchRequest(
        @NotNull UUID repositoryId,
        @NotBlank String query,
        @Positive Integer topK) {
}
