import { ensureCsrfToken, getApiBaseUrl, type ChatMessage } from "@/lib/api";
import { consumeSseStream } from "@/lib/sse";

export type StreamChatHandlers = {
  onUserMessage?: (message: ChatMessage) => void;
  onToken?: (token: string) => void;
  onAssistantMessage?: (message: ChatMessage) => void;
  onDone?: () => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
};

export async function streamChatMessage(
  sessionId: string,
  content: string,
  handlers: StreamChatHandlers = {}
): Promise<void> {
  const csrfToken = await ensureCsrfToken();

  await consumeSseStream(
    `${getApiBaseUrl()}/api/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-XSRF-TOKEN": csrfToken } : {}),
      },
      body: JSON.stringify({ content }),
      signal: handlers.signal,
    },
    {
      token: (data) => handlers.onToken?.(JSON.parse(data) as string),
      user_message: (data) =>
        handlers.onUserMessage?.(JSON.parse(data) as ChatMessage),
      assistant_message: (data) =>
        handlers.onAssistantMessage?.(JSON.parse(data) as ChatMessage),
      done: () => handlers.onDone?.(),
    },
    handlers.onError
  );

  handlers.onDone?.();
}
