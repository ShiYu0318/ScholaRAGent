// 問答頁：SSE 逐字串流 + 引用來源；?c=<id> 載入既有對話續聊。
import { Box, Button, Flash, Label, Spinner, Text, Textarea } from "@primer/react";
import { PaperAirplaneIcon } from "@primer/octicons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { api } from "../lib/api";
import { streamSSE, type Citation } from "../lib/sse";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[] | null;
}

export function Ask() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const convId = params.get("c") ? Number(params.get("c")) : null;
  const bottomRef = useRef<HTMLDivElement>(null);
  const loadedConv = useRef<number | null>(null);

  // 載入既有對話（從 Conversations 頁點進來）
  useEffect(() => {
    if (convId === null || loadedConv.current === convId) return;
    loadedConv.current = convId;
    api<{ messages: ChatMessage[] }>(`/api/conversations/${convId}`)
      .then((conv) => setMessages(conv.messages))
      .catch(() => setError(t("common.error")));
  }, [convId, t]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const question = input.trim();
    if (!question || streaming) return;
    setInput("");
    setError(null);
    setStreaming(true);
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);

    const appendToLast = (fn: (last: ChatMessage) => ChatMessage) =>
      setMessages((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);

    try {
      await streamSSE("/api/ask", { question, conversation_id: convId }, (ev) => {
        if (ev.type === "conversation" && ev.conversation_id) {
          loadedConv.current = ev.conversation_id;
          setParams({ c: String(ev.conversation_id) }, { replace: true });
        } else if (ev.type === "token" && ev.text) {
          appendToLast((last) => ({ ...last, content: last.content + ev.text }));
        } else if (ev.type === "citations" && ev.citations) {
          appendToLast((last) => ({ ...last, citations: ev.citations }));
        } else if (ev.type === "error" && ev.message) {
          setError(ev.message);
        } else if (ev.type === "done") {
          void queryClient.invalidateQueries({ queryKey: ["conversations"] });
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
      setMessages((m) => (m[m.length - 1]?.content === "" ? m.slice(0, -2) : m));
    } finally {
      setStreaming(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  return (
    <Box display="flex" flexDirection="column" sx={{ height: "calc(100vh - 180px)" }}>
      <Box flex={1} sx={{ overflowY: "auto", pr: 2 }}>
        {messages.length === 0 && (
          <Box
            sx={{
              border: "1px dashed", borderColor: "border.default", borderRadius: 2,
              p: 5, textAlign: "center", mt: 4,
            }}
          >
            <Text sx={{ color: "fg.muted" }}>{t("ask.placeholder")}</Text>
          </Box>
        )}
        {messages.map((m, i) => (
          <Box
            key={i}
            sx={{
              mb: 3,
              display: "flex",
              flexDirection: "column",
              alignItems: m.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <Box
              sx={{
                maxWidth: "85%",
                border: "1px solid",
                borderColor: m.role === "user" ? "accent.muted" : "border.default",
                bg: m.role === "user" ? "accent.subtle" : "canvas.subtle",
                borderRadius: 2,
                px: 3,
                py: 2,
              }}
            >
              <Text sx={{ whiteSpace: "pre-wrap", fontSize: 1 }}>
                {m.content}
                {streaming && i === messages.length - 1 && m.role === "assistant" && (
                  <Text as="span" sx={{ color: "accent.fg" }}>▍</Text>
                )}
              </Text>
              {m.citations && m.citations.length > 0 && (
                <Box mt={2} display="flex" flexWrap="wrap" sx={{ gap: 1 }}>
                  {m.citations.map((c, n) => (
                    <a key={c.id} href={c.link} target="_blank" rel="noreferrer">
                      <Label variant="accent" sx={{ cursor: "pointer" }}>
                        [{n + 1}] {c.title.slice(0, 40)}
                      </Label>
                    </a>
                  ))}
                </Box>
              )}
            </Box>
          </Box>
        ))}
        <div ref={bottomRef} />
      </Box>

      {error && (
        <Flash variant="danger" sx={{ mb: 2 }}>
          {error}
        </Flash>
      )}

      <Box display="flex" sx={{ gap: 2, alignItems: "flex-end" }}>
        <Textarea
          block
          resize="none"
          rows={2}
          placeholder={t("ask.inputPlaceholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={streaming}
        />
        <Button
          variant="primary"
          onClick={() => void send()}
          disabled={streaming || !input.trim()}
          leadingVisual={streaming ? () => <Spinner size="small" /> : PaperAirplaneIcon}
        >
          {t("ask.send")}
        </Button>
      </Box>
    </Box>
  );
}
