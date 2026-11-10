// 提問：左側是對話歷史，右側是一問一答的閱讀欄。
// 問題用襯線大字、回答用內文排版，像在讀一份自己提問寫成的筆記；
// 提問前可選檢索範圍（整個文庫 / 專案 / 指定論文）。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Copy, History, Link2, Link2Off, MessageSquarePlus, MessageSquareText, Search, Square, Trash2 } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { Citations } from "../components/Citations";
import { Markdown } from "../components/Markdown";
import { PaperDrawer } from "../components/Paper";
import { SaveDocumentButton } from "../components/SaveDocument";
import { ScopePicker } from "../components/ScopePicker";
import { api } from "../lib/api";
import { streamSSE, type Citation } from "../lib/sse";
import { scopeBody, type Conversation, type Paper, type Scope } from "../lib/types";
import { Button, Empty, IconButton, Input, Menu, Notice } from "../ui";
import { useToast } from "../ui/toast";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[] | null;
}

interface ConversationFull extends Conversation {
  messages: ChatMessage[];
}

export function Ask() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const convId = params.get("c") ? Number(params.get("c")) : null;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [current, setCurrent] = useState<Conversation | null>(null);
  const [input, setInput] = useState("");
  const [scope, setScope] = useState<Scope>({ kind: "library" });
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sideOpen, setSideOpen] = useState(false);
  const [openPaper, setOpenPaper] = useState<string | null>(null);

  const loaded = useRef<number | null>(null);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const autoAsked = useRef(false);

  const conversations = useQuery({
    queryKey: ["conversations", search],
    queryFn: () => api<{ items: Conversation[] }>(
      `/api/conversations?limit=100${search ? `&query=${encodeURIComponent(search)}` : ""}`),
  });

  // 載入既有對話
  useEffect(() => {
    if (convId === null) {
      if (loaded.current !== null) {
        loaded.current = null;
        setMessages([]);
        setCurrent(null);
      }
      return;
    }
    if (loaded.current === convId) return;
    loaded.current = convId;
    api<ConversationFull>(`/api/conversations/${convId}`)
      .then((conv) => {
        setMessages(conv.messages);
        setCurrent(conv);
        if (conv.project_id) setScope({ kind: "project", projectId: conv.project_id });
      })
      .catch(() => setError(t("ask.loadFailed")));
  }, [convId, t]);

  // 從其他頁帶入的範圍：?project= 或 ?paper=
  useEffect(() => {
    const project = params.get("project");
    const paper = params.get("paper");
    if (project) setScope({ kind: "project", projectId: Number(project) });
    else if (paper) {
      setScope({ kind: "papers", paperIds: [paper], label: paper });
      api<Paper>(`/api/paper/${encodeURI(paper)}`)
        .then((p) => setScope({ kind: "papers", paperIds: [paper], label: p.title }))
        .catch(() => undefined);
    }
    // 只在進頁時讀一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: streaming ? "auto" : "smooth", block: "end" });
  }, [messages, streaming]);

  const send = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || streaming) return;
    setInput("");
    setError(null);
    setStreaming(true);
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    const patchLast = (fn: (last: ChatMessage) => ChatMessage) =>
      setMessages((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);
    const controller = new AbortController();
    abort.current = controller;
    try {
      await streamSSE("/api/ask", { question, conversation_id: loaded.current, ...scopeBody(scope) }, (ev) => {
        if (ev.type === "conversation" && ev.conversation_id) {
          loaded.current = ev.conversation_id;
          setParams({ c: String(ev.conversation_id) }, { replace: true });
        } else if (ev.type === "token" && ev.text) {
          patchLast((last) => ({ ...last, content: last.content + ev.text }));
        } else if (ev.type === "citations" && ev.citations) {
          patchLast((last) => ({ ...last, citations: ev.citations }));
        } else if (ev.type === "error" && ev.message) {
          setError(ev.message);
        } else if (ev.type === "done") {
          void queryClient.invalidateQueries({ queryKey: ["conversations"] });
          void queryClient.invalidateQueries({ queryKey: ["project"] });
        }
      }, controller.signal);
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : t("common.error"));
        setMessages((m) => (m[m.length - 1]?.content === "" ? m.slice(0, -2) : m));
      }
    } finally {
      setStreaming(false);
      abort.current = null;
      textarea.current?.focus();
    }
  };

  // 從首頁或指令面板帶著問題進來：直接送出一次
  useEffect(() => {
    const q = params.get("q");
    if (q && !autoAsked.current) {
      autoAsked.current = true;
      void send(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const newChat = () => {
    abort.current?.abort();
    loaded.current = null;
    setMessages([]);
    setCurrent(null);
    setError(null);
    setParams({}, { replace: true });
    setSideOpen(false);
    textarea.current?.focus();
  };

  const refreshConversations = () => void queryClient.invalidateQueries({ queryKey: ["conversations"] });
  const share = useMutation({
    mutationFn: (id: number) => api<{ url: string; token: string }>(`/api/conversations/${id}/share`, { method: "POST" }),
    onSuccess: async (d) => {
      await navigator.clipboard.writeText(d.url).catch(() => undefined);
      setCurrent((c) => (c ? { ...c, share_token: d.token } : c));
      refreshConversations();
      toast.show(t("ask.shareCopied"));
    },
    onError: toast.error,
  });
  const unshare = useMutation({
    mutationFn: (id: number) => api(`/api/conversations/${id}/share`, { method: "DELETE" }),
    onSuccess: () => {
      setCurrent((c) => (c ? { ...c, share_token: null } : c));
      refreshConversations();
      toast.show(t("ask.shareRevoked"));
    },
    onError: toast.error,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/conversations/${id}`, { method: "DELETE" }),
    onSuccess: (_d, id) => {
      refreshConversations();
      if (id === loaded.current) newChat();
    },
    onError: toast.error,
  });

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 輸入法選字中的 Enter 不送出
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send();
    }
  };

  // 把訊息兩兩配成「一問一答」
  const turns: { q: ChatMessage; a?: ChatMessage }[] = [];
  for (const m of messages) {
    if (m.role === "user") turns.push({ q: m });
    else if (turns.length > 0) turns[turns.length - 1].a = m;
  }
  const suggestions = [t("ask.suggest1"), t("ask.suggest2"), t("ask.suggest3")];
  const convKey = loaded.current;

  return (
    <div className="chat">
      <aside className="chat-side" data-open={sideOpen}>
        <div className="chat-side-head">
          <Button variant="primary" icon={MessageSquarePlus} block onClick={newChat}>{t("ask.newChat")}</Button>
          <Input icon={Search} value={search} onChange={(e) => setSearch(e.target.value)}
                 placeholder={t("ask.searchHistory")} aria-label={t("ask.searchHistory")} />
        </div>
        <div className="chat-side-list">
          {conversations.data?.items.length === 0 && <div className="t-meta" style={{ padding: 8 }}>{t("ask.noHistory")}</div>}
          {(conversations.data?.items ?? []).map((c) => (
            <div key={c.id} className="row" style={{ gap: 0 }}>
              <button type="button" className="conv-item grow" aria-current={c.id === convKey}
                      onClick={() => { setParams({ c: String(c.id) }); setSideOpen(false); }}>
                <span className="truncate grow">{c.title || `#${c.id}`}</span>
                {c.share_token && <Link2 size={12} aria-label={t("ask.shared")} style={{ color: "var(--pencil)", flex: "none" }} />}
              </button>
              <IconButton icon={Trash2} label={t("common.delete")} onClick={() => remove.mutate(c.id)} />
            </div>
          ))}
        </div>
      </aside>

      <section className="chat-main">
        <div className="row" style={{ padding: "10px 20px", borderBottom: "1px solid var(--rule-soft)", minHeight: 49 }}>
          <span className="topbar-only"><IconButton icon={History} label={t("ask.history")} onClick={() => setSideOpen((o) => !o)} /></span>
          <span className="grow truncate t-strong">{current?.title ?? t("ask.newChat")}</span>
          {current && (
            <Menu
              trigger={(props) => (
                <Button size="sm" variant="ghost" icon={current.share_token ? Link2 : Link2Off} {...props}>
                  {current.share_token ? t("ask.shared") : t("ask.share")}
                </Button>
              )}
              items={current.share_token ? [
                { label: t("ask.copyLink"), icon: Copy, onSelect: () => share.mutate(current.id) },
                { label: t("ask.revokeLink"), icon: Link2Off, danger: true, onSelect: () => unshare.mutate(current.id) },
              ] : [
                { label: t("ask.createLink"), icon: Link2, onSelect: () => share.mutate(current.id) },
              ]}
            />
          )}
        </div>

        <div className="chat-scroll">
          <div className="chat-column">
            {turns.length === 0 && (
              <Empty icon={MessageSquareText} title={t("ask.emptyTitle")}>
                <p>{t("ask.emptyBody")}</p>
                <div className="col" style={{ marginTop: 16, alignItems: "center" }}>
                  {suggestions.map((s) => (
                    <button key={s} type="button" className="keyword" onClick={() => void send(s)}>{s}</button>
                  ))}
                </div>
              </Empty>
            )}
            {turns.map((turn, i) => {
              const last = i === turns.length - 1;
              const answering = streaming && last;
              return (
                <article key={i}>
                  <h2 className="turn-q">{turn.q.content}</h2>
                  <div className="turn-a">
                    {turn.a?.content
                      ? <Markdown>{turn.a.content}</Markdown>
                      : answering && <span className="t-meta">{t("ask.thinking")}</span>}
                    {answering && <span className="caret" aria-hidden />}
                  </div>
                  {turn.a?.citations && <Citations items={turn.a.citations} onOpen={setOpenPaper} />}
                  {turn.a?.content && !answering && (
                    <div className="turn-tools">
                      <SaveDocumentButton size="sm" label={t("ask.saveAsNote")} kind="note"
                                          title={turn.q.content.slice(0, 80)}
                                          content={`> ${turn.q.content}\n\n${turn.a.content}`}
                                          paperIds={(turn.a.citations ?? []).map((c) => c.id)}
                                          projectId={scope.kind === "project" ? scope.projectId : current?.project_id} />
                      <Button size="sm" variant="ghost" icon={Copy}
                              onClick={() => void navigator.clipboard.writeText(turn.a!.content).then(() => toast.show(t("common.copied")))}>
                        {t("common.copy")}
                      </Button>
                    </div>
                  )}
                </article>
              );
            })}
            {error && <Notice tone="danger">{error}</Notice>}
            <div ref={bottom} />
          </div>
        </div>

        <div className="composer-wrap">
          <div className="composer">
            <textarea ref={textarea} rows={1} value={input} maxLength={4000} autoFocus
                      placeholder={t("ask.inputPlaceholder")} aria-label={t("ask.inputPlaceholder")}
                      onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown} />
            <div className="composer-bar">
              <ScopePicker scope={scope} onChange={setScope} />
              <span className="grow" />
              <span className="t-meta">{t("ask.enterHint")}</span>
              {streaming
                ? <Button size="sm" icon={Square} onClick={() => abort.current?.abort()}>{t("ask.stop")}</Button>
                : <Button size="sm" variant="primary" icon={ArrowUp} disabled={!input.trim()} onClick={() => void send()}>{t("ask.send")}</Button>}
            </div>
          </div>
        </div>
      </section>
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </div>
  );
}
