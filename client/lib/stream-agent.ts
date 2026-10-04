import { ensureCsrfToken, getApiBaseUrl, type AgentRun } from "@/lib/api";
import { consumeSseStream } from "@/lib/sse";

export type AgentProgressEvent = { node: string; message: string };

export type StreamAgentRunHandlers = {
  onProgress?: (event: AgentProgressEvent) => void;
  onResult?: (run: AgentRun) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
  signal?: AbortSignal;
};

/** Consumes the SSE stream from POST /api/repos/{repoId}/agent/runs/{runId}/stream. */
export async function streamAgentRun(
  repoId: string,
  runId: string,
  handlers: StreamAgentRunHandlers = {}
): Promise<void> {
  const csrfToken = await ensureCsrfToken();

  await consumeSseStream(
    `${getApiBaseUrl()}/api/repos/${repoId}/agent/runs/${runId}/stream`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-XSRF-TOKEN": csrfToken } : {}),
      },
      signal: handlers.signal,
    },
    {
      progress: (data) =>
        handlers.onProgress?.(JSON.parse(data) as AgentProgressEvent),
      result: (data) => handlers.onResult?.(JSON.parse(data) as AgentRun),
      error: (data) => {
        const parsed = JSON.parse(data) as { message?: string };
        handlers.onError?.(new Error(parsed.message ?? "Agent run failed"));
      },
      done: () => handlers.onDone?.(),
    },
    handlers.onError
  );

  handlers.onDone?.();
}
