package devpilot.backend.controllers;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import devpilot.backend.dto.CodeSearchResultDto;
import devpilot.backend.dto.InternalCodeSearchRequest;
import devpilot.backend.services.ai.AgentCodeSearchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

/**
 * Callback API used only by the Python agent-service while it executes a LangGraph run
 * (see {@link devpilot.backend.security.InternalApiKeyFilter}). Deliberately read-only and
 * repository-scoped: no GitHub token, no write access, no arbitrary code execution is reachable
 * from here, which keeps a compromised or misled agent from doing anything destructive.
 */
@RestController
@RequestMapping("/api/internal/agent")
@RequiredArgsConstructor
public class AgentInternalController {

    private final AgentCodeSearchService agentCodeSearchService;

    @PostMapping("/search")
    public List<CodeSearchResultDto> search(@Valid @RequestBody InternalCodeSearchRequest request) {
        int topK = request.topK() != null ? request.topK() : 8;
        return agentCodeSearchService.search(request.repositoryId(), request.query(), topK);
    }
}
