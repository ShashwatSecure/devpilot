import { ApiError } from "@/lib/api";

async function readErrorMessage(res: Response): Promise<string> {
  let message = res.statusText;
  try {
    const data = await res.json();
    message = data.message ?? data.error ?? message;
  } catch {
    // ignore, fall back to statusText
  }
  return message;
}

/** Dispatch table mapping SSE `event:` names to a handler for the raw `data:` payload. */
export type SseEventHandlers = Record<string, (data: string) => void>;

/**
 * Fetches `url` and parses the response body as a `text/event-stream`, invoking the matching
 * handler in `handlers` for each `event:`/`data:` pair. Parse errors within a handler are
 * forwarded to `onParseError` without interrupting the stream.
 */
export async function consumeSseStream(
  url: string,
  init: RequestInit,
  handlers: SseEventHandlers,
  onParseError?: (error: Error) => void
): Promise<void> {
  const res = await fetch(url, init);

  if (!res.ok) {
    throw new ApiError(res.status, await readErrorMessage(res));
  }
  if (!res.body) {
    throw new Error("No response body for SSE stream");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.trim()) continue;

      let event = "message";
      const dataLines: string[] = [];
      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trimStart());
        }
      }

      const data = dataLines.join("\n");
      if (!data) continue;

      try {
        handlers[event]?.(data);
      } catch (err) {
        onParseError?.(
          err instanceof Error ? err : new Error("Failed to parse SSE event")
        );
      }
    }
  }
}
