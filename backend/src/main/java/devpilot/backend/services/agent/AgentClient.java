package devpilot.backend.services.agent;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import lombok.RequiredArgsConstructor;
import reactor.core.publisher.Flux;

/** Thin HTTP client for the Python LangGraph agent-service. */
@Component
@RequiredArgsConstructor
public class AgentClient {

    private final WebClient agentServiceWebClient;

    @Value("${app.agent.service-api-key:}")
    private String agentServiceApiKey;

    public Flux<ServerSentEvent<String>> streamIssueResolution(AgentRunRequestPayload payload) {
        return agentServiceWebClient
                .post()
                .uri("/agent/issue-resolution/run")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .headers(headers -> {
                    if (agentServiceApiKey != null && !agentServiceApiKey.isBlank()) {
                        headers.set("X-Agent-Service-Key", agentServiceApiKey);
                    }
                })
                .bodyValue(payload)
                .retrieve()
                .bodyToFlux(new org.springframework.core.ParameterizedTypeReference<ServerSentEvent<String>>() {
                });
    }
}
