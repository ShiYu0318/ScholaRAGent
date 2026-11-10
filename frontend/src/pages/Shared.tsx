// 公開分享頁：不需登入的唯讀對話。版面與提問頁的閱讀欄一致。
import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";

import { Citations } from "../components/Citations";
import { Markdown } from "../components/Markdown";
import { api } from "../lib/api";
import type { Citation } from "../lib/sse";
import { Empty, Spinner } from "../ui";

interface SharedConv {
  title: string;
  created_at: string;
  messages: { role: string; content: string; citations: Citation[] | null }[];
}

export function Shared() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const conv = useQuery({
    queryKey: ["shared", token],
    queryFn: () => api<SharedConv>(`/api/shared/${encodeURIComponent(token ?? "")}`),
    retry: false,
  });

  return (
    <div style={{ minHeight: "100vh" }}>
      <header className="row" style={{ padding: "14px 24px", borderBottom: "1px solid var(--rule)" }}>
        <Link to="/" className="brand" style={{ padding: 0, fontSize: 15 }}><BookOpen size={18} className="brand-mark" />ScholaRAGent</Link>
        <span className="grow" />
        <span className="t-meta">{t("shared.readonly")}</span>
      </header>
      <main className="chat-column">
        {conv.isPending && <div className="empty"><Spinner /></div>}
        {conv.isError && <Empty title={t("shared.notFound")}>{t("shared.notFoundBody")}</Empty>}
        {conv.data && (
          <>
            <div>
              <h1>{conv.data.title}</h1>
              <div className="t-meta num" style={{ marginTop: 4 }}>{new Date(conv.data.created_at).toLocaleDateString()}</div>
            </div>
            {conv.data.messages.map((m, i) =>
              m.role === "user" ? (
                <h2 key={i} className="turn-q">{m.content}</h2>
              ) : (
                <div key={i} style={{ marginTop: -16 }}>
                  <Markdown>{m.content}</Markdown>
                  {m.citations && <Citations items={m.citations} />}
                </div>
              ),
            )}
          </>
        )}
      </main>
    </div>
  );
}
