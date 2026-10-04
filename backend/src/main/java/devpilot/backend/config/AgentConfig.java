package devpilot.backend.config;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.JdkClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;

import devpilot.backend.security.InternalApiKeyFilter;
import lombok.RequiredArgsConstructor;

/**
 * Wiring for the Issue Resolution Agent's connection to the Python {@code agent-service}:
 * the outbound WebClient (used to call the agent and stream its SSE progress back), and the
 * inbound filter that protects the callback endpoints the agent uses for tool calls.
 */
@Configuration
@RequiredArgsConstructor
public class AgentConfig {

    private final InternalApiKeyFilter internalApiKeyFilter;

    @Bean
    WebClient agentServiceWebClient(
            org.springframework.core.env.Environment env) {
        String baseUrl = env.getProperty("app.agent.service-url", "http://localhost:8000");
        return WebClient.builder()
                .baseUrl(baseUrl)
                // JDK HttpClient connector avoids pulling in a full reactor-netty dependency.
                .clientConnector(new JdkClientHttpConnector())
                .build();
    }

    @Bean
    FilterRegistrationBean<InternalApiKeyFilter> internalApiKeyFilterRegistration() {
        FilterRegistrationBean<InternalApiKeyFilter> registration = new FilterRegistrationBean<>(internalApiKeyFilter);
        registration.addUrlPatterns("/api/internal/*");
        return registration;
    }
}
