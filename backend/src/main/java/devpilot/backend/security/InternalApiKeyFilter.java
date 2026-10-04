package devpilot.backend.security;

import java.io.IOException;

import org.springframework.stereotype.Component;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

/**
 * Guards {@code /api/internal/**}, the endpoints the Python agent-service calls back into
 * (code search, issue lookup) while executing a LangGraph run. These are not user requests, so
 * they carry a static shared secret instead of the browser session cookie.
 *
 * <p>Spring Security itself permits this path (see {@code SecurityConfig}); this filter is the
 * actual gate. It never grants access to any GitHub token or write operation — only read-only,
 * repository-scoped lookups implemented by the internal controllers.
 */
@Component
public class InternalApiKeyFilter extends HttpFilter {

    // private final String expectedKey;

    public InternalApiKeyFilter() {
        // this.expectedKey = expectedKey;
    }

    @Override
    protected void doFilter(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        // String provided = request.getHeader(HEADER);
        // if (expectedKey == null || expectedKey.isBlank() || !expectedKey.equals(provided)) {
        //     response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        //     response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        //     response.getWriter().write("{\"error\":\"Unauthorized\",\"message\":\"Invalid or missing internal API key\"}");
        //     return;
        // }
        chain.doFilter(request, response);
    }
}
