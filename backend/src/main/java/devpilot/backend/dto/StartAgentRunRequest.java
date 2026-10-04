package devpilot.backend.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/** Kicks off an Issue Resolution Agent run for a specific already-fetched GitHub issue. */
public record StartAgentRunRequest(
        @NotNull @Positive Integer issueNumber) {
}
