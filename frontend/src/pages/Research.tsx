// 綜述：把一批文獻整理成可以帶走的成果。
// 流程：選一種整理方式 → 指定主題與文獻來源 → 產出 → 存成文件接續編修。
import { BookText, Check, GitCompareArrows, Layers, Loader2, Microscope, Play, ScrollText, type LucideIcon } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { Citations } from "../components/Citations";
import { Markdown } from "../components/Markdown";
import { PaperDrawer } from "../components/Paper";
import { SaveDocumentButton } from "../components/SaveDocument";
import { ScopePicker } from "../components/ScopePicker";
import { api } from "../lib/api";
import { streamSSE, type Citation } from "../lib/sse";
import { scopeBody, type DocumentKind, type Scope } from "../lib/types";
import { Button, Empty, Input, Notice, PageHead } from "../ui";

type Tool = "deep" | "litreview" | "compare" | "report";

const TOOLS: { key: Tool; icon: LucideIcon; kind: DocumentKind }[] = [
  { key: "litreview", icon: BookText, kind: "review" },
  { key: "deep", icon: Microscope, kind: "deep_research" },
  { key: "compare", icon: GitCompareArrows, kind: "comparison" },
  { key: "report", icon: ScrollText, kind: "report" },
];

interface DeepEvent {
  type: string;
  questions?: string[];
  question?: string;
  content?: string;
  message?: string;
  papers?: string[];
  citations?: Citation[];
}

interface Section {
  question: string;
  content: string;
}

export function Research() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const [tool, setTool] = useState<Tool>((params.get("tool") as Tool) || "litreview");
  const [topic, setTopic] = useState("");
  const [scope, setScope] = useState<Scope>(
    params.get("project") ? { kind: "project", projectId: Number(params.get("project")) } : { kind: "library" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState("");
  const [paperIds, setPaperIds] = useState<string[]>([]);
  const [ranTopic, setRanTopic] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [synthesis, setSynthesis] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [openPaper, setOpenPaper] = useState<string | null>(null);

  const reset = () => {
    setError(null); setResult(""); setPaperIds([]); setQuestions([]); setSections([]);
    setSynthesis(""); setCitations([]);
  };
  useEffect(reset, [tool]);

  // 比較表可以只靠來源文獻（例如整個專案），不一定要主題
  const topicOptional = tool === "compare" && scope.kind !== "library";
  const canRun = !busy && (topic.trim().length > 0 || topicOptional);

  const run = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!canRun) return;
    const q = topic.trim();
    reset();
    setBusy(true);
    setRanTopic(q);
    try {
      if (tool === "deep") {
        await streamSSE<DeepEvent>("/api/deepresearch", { topic: q, ...scopeBody(scope) }, (ev) => {
          if (ev.type === "decompose") setQuestions(ev.questions ?? []);
          else if (ev.type === "section") setSections((s) => [...s, { question: ev.question ?? "", content: ev.content ?? "" }]);
          else if (ev.type === "synthesis") setSynthesis(ev.content ?? "");
          else if (ev.type === "citations") {
            setCitations(ev.citations ?? []);
            setPaperIds((ev.citations ?? []).map((c) => c.id));
          } else if (ev.type === "error") setError(ev.message ?? t("common.error"));
        });
      } else {
        const resp = await api<{ content: string; papers: string[] }>(`/api/${tool}`, {
          method: "POST",
          body: { ...(q ? { topic: q } : {}), ...scopeBody(scope) },
        });
        setResult(resp.content);
        setPaperIds(resp.papers ?? []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  const deepMarkdown = sections.length
    ? [...sections.map((s) => `## ${s.question}\n\n${s.content}`),
       synthesis ? `## ${t("research.synthesis")}\n\n${synthesis}` : ""].filter(Boolean).join("\n\n")
    : "";
  const output = tool === "deep" ? deepMarkdown : result;
  const done = !busy && output.length > 0;
  const meta = TOOLS.find((x) => x.key === tool)!;
  const toolName = t(`research.tool.${tool}.name`);
  const title = ranTopic ? t("research.titled", { tool: toolName, topic: ranTopic }) : toolName;

  return (
    <div className="stack-lg">
      <PageHead title={t("nav.synthesize")}>{t("research.intro")}</PageHead>

      <div className="grid-3" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        {TOOLS.map(({ key, icon: Icon }) => (
          <button key={key} type="button" className="panel" aria-pressed={tool === key}
                  onClick={() => setTool(key)}
                  style={{ padding: 16, textAlign: "left", cursor: "pointer", color: "inherit",
                           borderColor: tool === key ? "var(--pencil)" : undefined,
                           background: tool === key ? "var(--pencil-wash)" : undefined }}>
            <Icon size={18} strokeWidth={1.7} style={{ color: tool === key ? "var(--pencil)" : "var(--ink-3)" }} />
            <div className="t-strong" style={{ marginTop: 8 }}>{t(`research.tool.${key}.name`)}</div>
            <div className="t-meta" style={{ marginTop: 2 }}>{t(`research.tool.${key}.body`)}</div>
          </button>
        ))}
      </div>

      <form className="composer composer-wide" onSubmit={run}>
        <div style={{ padding: "8px 8px 0 14px" }}>
          <Input value={topic} onChange={(e) => setTopic(e.target.value)} maxLength={500}
                 placeholder={topicOptional ? t("research.topicOptional") : t(`research.tool.${tool}.placeholder`)}
                 aria-label={t("research.topic")}
                 style={{ border: 0, background: "none", height: 40, fontSize: 15, padding: 0, outline: "none" }} />
        </div>
        <div className="composer-bar">
          <span className="t-meta">{t("research.source")}</span>
          <ScopePicker scope={scope} onChange={setScope} />
          <span className="grow" />
          <Button type="submit" variant="primary" icon={Play} loading={busy} disabled={!canRun}>{t("research.run")}</Button>
        </div>
      </form>

      {error && <Notice tone="danger">{error}</Notice>}

      {!busy && !output && !error && (
        <div className="panel"><Empty icon={Layers} title={t("research.emptyTitle")}>{t("research.emptyBody")}</Empty></div>
      )}

      {(busy || output) && (
        <section className="panel">
          <div className="panel-head">
            <span className="panel-title">{title}</span>
            {done && <SaveDocumentButton size="sm" title={title} content={output} kind={meta.kind} paperIds={paperIds}
                                         projectId={scope.kind === "project" ? scope.projectId : null} />}
          </div>
          <div className="panel-pad stack-lg">
            {tool === "deep" && questions.length > 0 && (
              <div className="col" role="list" aria-label={t("research.plan")}>
                <span className="t-label">{t("research.plan")}</span>
                {questions.map((q, i) => {
                  const finished = i < sections.length;
                  const active = busy && i === sections.length;
                  return (
                    <div key={q} className="row" role="listitem" style={{ color: finished ? "var(--ink)" : "var(--ink-3)" }}>
                      {finished ? <Check size={14} style={{ color: "var(--ok)" }} />
                        : active ? <Loader2 size={14} className="spin-icon" style={{ color: "var(--pencil)" }} />
                          : <span style={{ width: 14 }} />}
                      <span>{q}</span>
                    </div>
                  );
                })}
              </div>
            )}
            {busy && !output && tool !== "deep" && (
              <div className="col">
                <div className="skeleton" style={{ height: 14, width: "60%" }} />
                <div className="skeleton" style={{ height: 14, width: "92%" }} />
                <div className="skeleton" style={{ height: 14, width: "78%" }} />
              </div>
            )}
            {output && <Markdown>{output}</Markdown>}
            {tool === "deep" && busy && sections.length === questions.length && questions.length > 0 && !synthesis && (
              <span className="t-meta">{t("research.synthesizing")}</span>
            )}
            {citations.length > 0 && <Citations items={citations} onOpen={setOpenPaper} />}
            {done && tool !== "deep" && paperIds.length > 0 && (
              <span className="t-meta">{t("research.basedOn", { count: paperIds.length })}</span>
            )}
          </div>
        </section>
      )}
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </div>
  );
}
