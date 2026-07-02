// fetch 版 SSE 讀取器：POST + Authorization header（EventSource 做不到），
// 逐事件回呼；後端每個事件是一行 `data: {json}\n\n`。
import { ApiError, getToken } from "./api";

export interface AskEvent {
  type: "conversation" | "token" | "citations" | "done" | "error";
  conversation_id?: number;
  message_id?: number;
  text?: string;
  message?: string;
  citations?: Citation[];
}

export interface Citation {
  id: string;
  title: string;
  link: string;
  published: string;
  authors: string;
}

export async function streamSSE(
  path: string,
  body: unknown,
  onEvent: (event: AskEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(path, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      // 串流錯誤沒有 JSON body 時維持 statusText
    }
    throw new ApiError(resp.status, detail);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of frame.split("\n")) {
        if (line.startsWith("data: ")) onEvent(JSON.parse(line.slice(6)) as AskEvent);
      }
    }
  }
}
