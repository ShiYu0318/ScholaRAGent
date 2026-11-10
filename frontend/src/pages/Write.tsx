// 寫作：文件清單 + Markdown 編輯器。
// 綜述、提問存下來的結果都在這裡接續編修；寫作工具直接作用在目前的文件上。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Download, FilePlus2, FileText, List, MoreHorizontal, PenLine, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Markdown } from "../components/Markdown";
import { PaperDrawer } from "../components/Paper";
import { api, download } from "../lib/api";
import { shortDate, useProjects, type DocumentFull, type DocumentKind, type DocumentSummary } from "../lib/types";
import { Badge, Button, Dialog, Empty, IconButton, Menu, Segmented, Select, Spinner } from "../ui";
import { useToast } from "../ui/toast";

const KINDS: DocumentKind[] = ["draft", "outline", "note", "review", "report", "comparison", "deep_research"];
type AiTool = "polish" | "review" | "contributions" | "checklist" | "latex" | "slides";
// 前三個處理既有文字，後三個依主題產生新內容
const TEXT_TOOLS: AiTool[] = ["polish", "review", "contributions"];
const TOPIC_TOOLS: AiTool[] = ["latex", "slides", "checklist"];

function Editor({ docId }: { docId: number }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useProjects();
  const area = useRef<HTMLTextAreaElement>(null);

  const doc = useQuery({
    queryKey: ["document", docId],
    queryFn: () => api<DocumentFull>(`/api/documents/${docId}`),
    retry: false,
  });
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [dirty, setDirty] = useState(false);
  const [ai, setAi] = useState<{ tool: AiTool; result: string; selection: [number, number] | null } | null>(null);
  const [openPaper, setOpenPaper] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const hydrated = useRef<number | null>(null);

  useEffect(() => {
    if (doc.data && hydrated.current !== doc.data.id) {
      hydrated.current = doc.data.id;
      setTitle(doc.data.title);
      setContent(doc.data.content);
      setDirty(false);
      // 從研究工具存下來的成果先看排版結果；空白的新文件直接進編輯
      setMode(doc.data.content.trim() ? "preview" : "edit");
    }
  }, [doc.data]);

  const refreshLists = () => {
    void queryClient.invalidateQueries({ queryKey: ["documents"] });
    void queryClient.invalidateQueries({ queryKey: ["project"] });
  };
  const save = useMutation({
    mutationFn: (patch: Partial<Pick<DocumentFull, "title" | "content" | "kind" | "project_id">>) =>
      api<DocumentFull>(`/api/documents/${docId}`, { method: "PATCH", body: patch }),
    onSuccess: (saved) => {
      queryClient.setQueryData<DocumentFull>(["document", docId], (old) => (old ? { ...old, ...saved } : old));
      setDirty(false);
      refreshLists();
    },
    onError: toast.error,
  });

  // 自動儲存：停止輸入 1.2 秒後送出
  useEffect(() => {
    if (!dirty || !title.trim()) return;
    const timer = window.setTimeout(() => save.mutate({ title: title.trim(), content }), 1200);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, content, dirty]);

  // 離開前還有未儲存的內容時提醒
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const remove = useMutation({
    mutationFn: () => api(`/api/documents/${docId}`, { method: "DELETE" }),
    onSuccess: () => { refreshLists(); navigate("/write"); },
    onError: toast.error,
  });

  const runAi = useMutation({
    mutationFn: async (tool: AiTool) => {
      const el = area.current;
      const hasSelection = !!el && el.selectionEnd > el.selectionStart;
      const selection: [number, number] | null = hasSelection ? [el!.selectionStart, el!.selectionEnd] : null;
      const text = selection ? content.slice(selection[0], selection[1]) : content;
      const body = TEXT_TOOLS.includes(tool)
        ? { text: text.slice(0, 20000) }
        : { topic: title.slice(0, 500), paper_ids: doc.data?.paper_ids.length ? doc.data.paper_ids.slice(0, 50) : undefined };
      const resp = await api<{ content: string }>(`/api/write/${tool}`, { method: "POST", body });
      return { tool, result: resp.content, selection };
    },
    onSuccess: setAi,
    onError: toast.error,
  });

  const apply = (how: "replace" | "append") => {
    if (!ai) return;
    const next = how === "replace" && ai.selection
      ? content.slice(0, ai.selection[0]) + ai.result + content.slice(ai.selection[1])
      : how === "replace" ? ai.result : `${content.trimEnd()}\n\n${ai.result}\n`;
    setContent(next);
    setDirty(true);
    setAi(null);
    setMode("edit");
  };

  if (doc.isPending) return <div className="empty"><Spinner /></div>;
  if (doc.isError || !doc.data) return <Empty title={t("doc.notFound")} />;
  const d = doc.data;
  const exportName = d.title.replace(/[^\w一-鿿-]+/g, "-").slice(0, 60) || "document";

  return (
    <>
      <div className="editor-bar">
        <Segmented label={t("doc.mode")} value={mode} onChange={setMode}
                   items={[{ key: "edit", label: t("doc.edit") }, { key: "preview", label: t("doc.preview") }]} />
        <Select value={d.kind} aria-label={t("doc.kindLabel")} style={{ width: "auto" }}
                onChange={(e) => save.mutate({ kind: e.target.value as DocumentKind })}>
          {KINDS.map((k) => <option key={k} value={k}>{t(`doc.kind.${k}`)}</option>)}
        </Select>
        <Select value={d.project_id ?? ""} aria-label={t("doc.project")} style={{ width: "auto", maxWidth: 200 }}
                onChange={(e) => save.mutate({ project_id: e.target.value ? Number(e.target.value) : null })}>
          <option value="">{t("doc.noProject")}</option>
          {(projects.data?.items ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        <span className="grow" />
        <span className="t-meta row" aria-live="polite">
          {save.isPending ? <><Spinner />{t("doc.saving")}</> : dirty ? t("doc.unsaved") : <><Check size={13} />{t("doc.savedAt", { date: shortDate(d.updated_at) })}</>}
        </span>
        <Menu
          header={<div className="menu-label">{t("doc.aiHint")}</div>}
          trigger={(props) => <Button icon={Sparkles} loading={runAi.isPending} {...props}>{t("doc.ai")}</Button>}
          items={[
            ...TEXT_TOOLS.map((tool) => ({ label: t(`doc.tool.${tool}`), onSelect: () => runAi.mutate(tool) })),
            ...TOPIC_TOOLS.map((tool, i) => ({ label: t(`doc.tool.${tool}`), separatorBefore: i === 0, onSelect: () => runAi.mutate(tool) })),
          ]}
        />
        <Menu
          trigger={(props) => <IconButton icon={MoreHorizontal} label={t("common.more")} {...props} />}
          items={[
            { label: t("doc.exportMd"), icon: Download,
              onSelect: () => void download(`/api/documents/${docId}/export?format=md`, `${exportName}.md`).catch(toast.error) },
            { label: t("doc.exportBib"), icon: Download,
              onSelect: () => void download(`/api/documents/${docId}/export?format=bib`, `${exportName}.bib`).catch(toast.error) },
            { label: t("common.delete"), icon: Trash2, danger: true, separatorBefore: true, onSelect: () => setConfirmDelete(true) },
          ]}
        />
      </div>

      <div className="editor-body">
        <div className="editor-sheet">
          <input className="editor-title" value={title} maxLength={200} placeholder={t("doc.titlePlaceholder")}
                 aria-label={t("doc.title")} onChange={(e) => { setTitle(e.target.value); setDirty(true); }} />
          {mode === "edit" ? (
            <textarea ref={area} className="editor-text" value={content} maxLength={200000}
                      placeholder={t("doc.contentPlaceholder")} aria-label={t("doc.content")}
                      onChange={(e) => { setContent(e.target.value); setDirty(true); }} />
          ) : (
            <div style={{ marginTop: 16 }}>
              {content.trim() ? <Markdown>{content}</Markdown> : <span className="t-muted">{t("doc.empty")}</span>}
            </div>
          )}

          {(d.papers ?? []).length > 0 && (
            <section style={{ marginTop: 48 }}>
              <div className="t-label" style={{ marginBottom: 8 }}>{t("doc.references", { count: d.papers!.length })}</div>
              <ol className="prose prose-sm" style={{ margin: 0, maxWidth: "none" }}>
                {d.papers!.map((p) => (
                  <li key={p.id}>
                    <button type="button" className="paper-title" style={{ fontSize: 14, fontWeight: 500 }} onClick={() => setOpenPaper(p.id)}>
                      {p.title}
                    </button>
                    <span className="t-meta"> {p.authors ? `— ${p.authors.split(",")[0]}` : ""} {p.published ? `(${p.published.slice(0, 4)})` : ""}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      </div>

      <Dialog open={ai !== null} onClose={() => setAi(null)} wide
              title={ai ? t(`doc.tool.${ai.tool}`) : ""}
              footer={ai && (
                <>
                  <Button variant="ghost" onClick={() => void navigator.clipboard.writeText(ai.result).then(() => toast.show(t("common.copied")))}>{t("common.copy")}</Button>
                  <Button onClick={() => apply("append")}>{t("doc.append")}</Button>
                  {ai.tool === "polish" && (
                    <Button variant="primary" onClick={() => apply("replace")}>
                      {ai.selection ? t("doc.replaceSelection") : t("doc.replaceAll")}
                    </Button>
                  )}
                </>
              )}>
        {ai && <Markdown small>{ai.result}</Markdown>}
      </Dialog>
      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)} title={t("doc.deleteTitle")}
              footer={
                <>
                  <Button variant="ghost" onClick={() => setConfirmDelete(false)}>{t("common.cancel")}</Button>
                  <Button variant="danger" loading={remove.isPending} onClick={() => remove.mutate()}>{t("common.delete")}</Button>
                </>
              }>
        <p>{t("doc.deleteBody")}</p>
      </Dialog>
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </>
  );
}

export function Write() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const docId = id ? Number(id) : null;
  const [params] = useSearchParams();
  const [listOpen, setListOpen] = useState(false);
  const creating = useRef(false);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<{ items: DocumentSummary[] }>("/api/documents"),
  });

  const create = useMutation({
    mutationFn: (projectId: number | null) =>
      api<DocumentFull>("/api/documents", {
        method: "POST", body: { title: t("doc.untitled"), kind: "draft", project_id: projectId },
      }),
    onSuccess: (doc) => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["project"] });
      navigate(`/write/${doc.id}`, { replace: true });
    },
    onError: toast.error,
  });

  // 從專案頁「新增文件」進來：?new=1&project=<id>
  useEffect(() => {
    if (params.get("new") && !creating.current) {
      creating.current = true;
      create.mutate(params.get("project") ? Number(params.get("project")) : null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => setListOpen(false), [docId]);
  const items = documents.data?.items ?? [];

  return (
    <div className="editor">
      <aside className="editor-list" data-open={listOpen}>
        <div style={{ padding: 16 }}>
          <Button variant="primary" icon={FilePlus2} block loading={create.isPending} onClick={() => create.mutate(null)}>
            {t("doc.new")}
          </Button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 12px" }}>
          {documents.isPending && <div className="empty"><Spinner /></div>}
          {items.map((d) => (
            <button key={d.id} type="button" className="conv-item" aria-current={d.id === docId}
                    style={{ flexDirection: "column", alignItems: "flex-start", gap: 2 }}
                    onClick={() => navigate(`/write/${d.id}`)}>
              <span className="truncate" style={{ width: "100%" }}>{d.title}</span>
              <span className="row t-meta" style={{ fontWeight: 400 }}>
                <Badge>{t(`doc.kind.${d.kind}`)}</Badge><span className="num">{shortDate(d.updated_at)}</span>
              </span>
            </button>
          ))}
        </div>
      </aside>
      <section className="editor-main">
        <div className="topbar-only" style={{ padding: "8px 16px", borderBottom: "1px solid var(--rule-soft)" }}>
          <Button size="sm" variant="ghost" icon={List} onClick={() => setListOpen((o) => !o)}>{t("doc.all")}</Button>
        </div>
        {docId !== null ? <Editor key={docId} docId={docId} /> : (
          <div className="editor-body">
            <Empty icon={items.length ? PenLine : FileText} title={items.length ? t("doc.pickTitle") : t("doc.emptyTitle")}
                   action={<Button variant="primary" icon={FilePlus2} onClick={() => create.mutate(null)}>{t("doc.new")}</Button>}>
              {t("doc.emptyBody")}
            </Empty>
          </div>
        )}
      </section>
    </div>
  );
}

