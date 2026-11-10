// 專案工作區：整個研究流程在同一頁完成。
// 頁首是研究軌跡與下一步；下面的分頁對應軌跡上的站點。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive, ArchiveRestore, Compass, Download, FilePlus2, Layers, MessageSquareText, MoreHorizontal,
  Pencil, Plus, Search, Trash2, X,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { NextStep } from "../components/NextStep";
import { PaperDrawer, PaperRow, paperPath } from "../components/Paper";
import { ProjectDialog } from "../components/ProjectForm";
import { ResearchTrail } from "../components/ResearchTrail";
import { api, download } from "../lib/api";
import {
  shortDate, type Conversation, type DocumentSummary, type Paper, type ProjectOverview, type StageKey,
} from "../lib/types";
import { Badge, Button, Dialog, Empty, IconButton, Input, Menu, Notice, QueryState, Tabs } from "../ui";
import { useToast } from "../ui/toast";

type Tab = "overview" | "papers" | "questions" | "documents" | "export";
const STAGE_TAB: Record<StageKey, Tab> = {
  collect: "papers", read: "papers", ask: "questions", synthesize: "documents", write: "documents",
};

function AddFromLibrary({ projectId, existing, open, onClose }: { projectId: number; existing: Set<string>; open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());

  const papers = useQuery({
    queryKey: ["papers", query, "picker"],
    queryFn: () => api<{ items: Paper[] }>(`/api/papers?limit=50${query ? `&query=${encodeURIComponent(query)}` : ""}`),
    enabled: open,
  });
  const add = useMutation({
    mutationFn: () => api<{ added: number }>(`/api/projects/${projectId}/papers`, { method: "POST", body: { paper_ids: [...picked] } }),
    onSuccess: (d) => {
      toast.show(t("paper.addedToProject", { count: d.added }));
      void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      setPicked(new Set());
      onClose();
    },
    onError: toast.error,
  });
  const toggle = (id: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  const candidates = (papers.data?.items ?? []).filter((p) => !existing.has(p.id));

  return (
    <Dialog open={open} onClose={onClose} title={t("project.addFromLibrary")} wide
            footer={
              <>
                <Button variant="ghost" onClick={onClose}>{t("common.cancel")}</Button>
                <Button variant="primary" disabled={picked.size === 0} loading={add.isPending} onClick={() => add.mutate()}>
                  {t("project.addSelected", { count: picked.size })}
                </Button>
              </>
            }>
      <div className="stack">
        <Input icon={Search} value={query} placeholder={t("library.searchPlaceholder")}
               onChange={(e) => setQuery(e.target.value)} autoFocus />
        <div className="panel" style={{ maxHeight: 380, overflowY: "auto" }}>
          <QueryState loading={papers.isPending} error={papers.isError} empty={candidates.length === 0}
                      emptyState={<Empty title={t("project.noCandidates")} />} />
          {candidates.map((p) => (
            <label key={p.id} className="list-row list-row-click" style={{ alignItems: "center" }}>
              <span className="check"><input type="checkbox" checked={picked.has(p.id)} onChange={() => toggle(p.id)} /></span>
              <span className="grow">
                <span className="paper-title" style={{ fontSize: 14 }}>{p.title}</span>
                <span className="paper-meta"><span className="num">{shortDate(p.published)}</span><span className="mono">{p.id}</span></span>
              </span>
            </label>
          ))}
        </div>
      </div>
    </Dialog>
  );
}

export function ProjectPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const projectId = Number(id);
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "overview";
  const setTab = (next: Tab) => setParams(next === "overview" ? {} : { tab: next }, { replace: true });

  const [editing, setEditing] = useState(false);
  const [adding, setAdding] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [openPaper, setOpenPaper] = useState<string | null>(null);

  const overview = useQuery({
    queryKey: ["project", projectId, "overview"],
    queryFn: () => api<ProjectOverview>(`/api/projects/${projectId}/overview`),
    retry: false,
  });
  const papers = useQuery({
    queryKey: ["project", projectId, "papers"],
    queryFn: () => api<{ items: Paper[] }>(`/api/projects/${projectId}/papers`),
    enabled: tab === "papers" || tab === "export",
  });
  const conversations = useQuery({
    queryKey: ["project", projectId, "conversations"],
    queryFn: () => api<{ items: Conversation[] }>(`/api/conversations?project_id=${projectId}`),
    enabled: tab === "questions",
  });
  const documents = useQuery({
    queryKey: ["project", projectId, "documents"],
    queryFn: () => api<{ items: DocumentSummary[] }>(`/api/documents?project_id=${projectId}`),
    enabled: tab === "documents",
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["projects"] });
  };
  const removePaper = useMutation({
    mutationFn: (paperId: string) => api(`/api/projects/${projectId}/papers/${paperPath(paperId)}`, { method: "DELETE" }),
    onSuccess: invalidate,
    onError: toast.error,
  });
  const setStatus = useMutation({
    mutationFn: (status: "active" | "archived") => api(`/api/projects/${projectId}`, { method: "PATCH", body: { status } }),
    onSuccess: invalidate,
    onError: toast.error,
  });
  const remove = useMutation({
    mutationFn: () => api(`/api/projects/${projectId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate("/projects");
    },
    onError: toast.error,
  });
  const exportZip = useMutation({
    mutationFn: () => download(`/api/projects/${projectId}/export`, `${overview.data?.project.name ?? "project"}.zip`),
    onError: toast.error,
  });

  if (overview.isPending) return <div className="skeleton" style={{ height: 240 }} />;
  if (overview.isError || !overview.data) {
    return <Empty title={t("project.notFound")} action={<Link className="btn" to="/projects">{t("nav.allProjects")}</Link>} />;
  }

  const { project, stages, next_step: nextStep } = overview.data;
  const paperIds = new Set((papers.data?.items ?? []).map((p) => p.id));

  return (
    <div className="stack-lg">
      <header>
        <div className="page-kicker"><Link to="/projects">{t("nav.projects")}</Link><span>/</span></div>
        <div className="spread" style={{ alignItems: "flex-start" }}>
          <div className="grow">
            <div className="row">
              <h1>{project.name}</h1>
              {project.status === "archived" && <Badge>{t("project.archived")}</Badge>}
            </div>
            {project.question
              ? <p className="t-serif t-muted" style={{ marginTop: 6, fontSize: 16, fontStyle: "italic", maxWidth: "68ch" }}>{project.question}</p>
              : <button type="button" className="btn btn-ghost btn-sm" style={{ marginTop: 6, marginLeft: -8 }} onClick={() => setEditing(true)}>{t("project.addQuestion")}</button>}
          </div>
          <Menu
            trigger={(props) => <IconButton icon={MoreHorizontal} label={t("common.more")} {...props} />}
            items={[
              { label: t("project.edit"), icon: Pencil, onSelect: () => setEditing(true) },
              project.status === "active"
                ? { label: t("project.archive"), icon: Archive, onSelect: () => setStatus.mutate("archived") }
                : { label: t("project.unarchive"), icon: ArchiveRestore, onSelect: () => setStatus.mutate("active") },
              { label: t("common.delete"), icon: Trash2, danger: true, separatorBefore: true, onSelect: () => setConfirmDelete(true) },
            ]}
          />
        </div>
      </header>

      <section className="stack">
        <ResearchTrail stages={stages} next={nextStep} onSelect={(stage) => setTab(STAGE_TAB[stage])} />
        <NextStep projectId={projectId} step={nextStep} />
      </section>

      <Tabs<Tab>
        label={project.name}
        value={tab}
        onChange={setTab}
        items={[
          { key: "overview", label: t("project.tab.overview") },
          { key: "papers", label: t("project.tab.papers"), count: project.paper_count },
          { key: "questions", label: t("project.tab.questions"), count: project.conversation_count },
          { key: "documents", label: t("project.tab.documents"), count: project.document_count },
          { key: "export", label: t("project.tab.export") },
        ]}
      />

      {tab === "overview" && (
        <div className="grid-2">
          <section>
            <div className="section-head"><h3>{t("home.recentDocuments")}</h3></div>
            <div className="panel">
              {overview.data.recent_documents.length === 0 && (
                <Empty title={t("project.noDocuments")}
                       action={<Link className="btn" to={`/research?project=${projectId}`}><Layers size={14} />{t("nav.synthesize")}</Link>} />
              )}
              {overview.data.recent_documents.map((d) => (
                <Link key={d.id} to={`/write/${d.id}`} className="list-row list-row-click" style={{ color: "inherit", textDecoration: "none" }}>
                  <div className="grow">
                    <div className="paper-title" style={{ fontSize: 14 }}>{d.title}</div>
                    <div className="paper-meta"><Badge>{t(`doc.kind.${d.kind}`)}</Badge><span className="num">{shortDate(d.updated_at)}</span></div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
          <section>
            <div className="section-head"><h3>{t("home.recentConversations")}</h3></div>
            <div className="panel">
              {overview.data.recent_conversations.length === 0 && (
                <Empty title={t("project.noQuestions")}
                       action={<Link className="btn" to={`/ask?project=${projectId}`}><MessageSquareText size={14} />{t("nav.ask")}</Link>} />
              )}
              {overview.data.recent_conversations.map((c) => (
                <Link key={c.id} to={`/ask?c=${c.id}`} className="list-row list-row-click" style={{ color: "inherit", textDecoration: "none" }}>
                  <div className="grow">
                    <div className="paper-title" style={{ fontSize: 14 }}>{c.title || `#${c.id}`}</div>
                    <div className="paper-meta"><span className="num">{shortDate(c.updated_at)}</span></div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        </div>
      )}

      {tab === "papers" && (
        <section className="stack">
          <div className="row-wrap">
            <Link className="btn btn-primary" to={`/discover?project=${projectId}`}><Compass size={14} />{t("project.findPapers")}</Link>
            <Button icon={Plus} onClick={() => setAdding(true)}>{t("project.addFromLibrary")}</Button>
            <span className="grow" />
            {project.paper_count >= 2 && (
              <Link className="btn btn-ghost" to={`/research?project=${projectId}&tool=compare`}>{t("project.compareAll")}</Link>
            )}
          </div>
          <div className="panel">
            <QueryState loading={papers.isPending} error={papers.isError} empty={papers.data?.items.length === 0}
                        emptyState={<Empty icon={Compass} title={t("project.noPapers")}>{t("project.noPapersBody")}</Empty>} />
            <div className="list">
              {(papers.data?.items ?? []).map((p) => (
                <PaperRow key={p.id} paper={p} onOpen={setOpenPaper}
                          actions={<IconButton icon={X} label={t("project.removePaper")} onClick={() => removePaper.mutate(p.id)} />} />
              ))}
            </div>
          </div>
        </section>
      )}

      {tab === "questions" && (
        <section className="stack">
          <div><Link className="btn btn-primary" to={`/ask?project=${projectId}`}><MessageSquareText size={14} />{t("project.askProject")}</Link></div>
          <div className="panel">
            <QueryState loading={conversations.isPending} error={conversations.isError}
                        empty={conversations.data?.items.length === 0}
                        emptyState={<Empty icon={MessageSquareText} title={t("project.noQuestions")}>{t("project.noQuestionsBody")}</Empty>} />
            <div className="list">
              {(conversations.data?.items ?? []).map((c) => (
                <Link key={c.id} to={`/ask?c=${c.id}`} className="list-row list-row-click" style={{ color: "inherit", textDecoration: "none" }}>
                  <div className="grow">
                    <div className="paper-title" style={{ fontSize: 15 }}>{c.title || `#${c.id}`}</div>
                    <div className="paper-meta"><span className="num">{shortDate(c.updated_at)}</span></div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {tab === "documents" && (
        <section className="stack">
          <div className="row-wrap">
            <Link className="btn btn-primary" to={`/research?project=${projectId}`}><Layers size={14} />{t("project.synthesize")}</Link>
            <Link className="btn" to={`/write?project=${projectId}&new=1`}><FilePlus2 size={14} />{t("doc.new")}</Link>
          </div>
          <div className="panel">
            <QueryState loading={documents.isPending} error={documents.isError}
                        empty={documents.data?.items.length === 0}
                        emptyState={<Empty icon={Layers} title={t("project.noDocuments")}>{t("project.noDocumentsBody")}</Empty>} />
            <div className="list">
              {(documents.data?.items ?? []).map((d) => (
                <Link key={d.id} to={`/write/${d.id}`} className="list-row list-row-click" style={{ color: "inherit", textDecoration: "none" }}>
                  <div className="grow">
                    <div className="paper-title" style={{ fontSize: 15 }}>{d.title}</div>
                    <div className="paper-meta">
                      <Badge>{t(`doc.kind.${d.kind}`)}</Badge>
                      <span className="num">{shortDate(d.updated_at)}</span>
                      <span>{t("doc.cites", { count: d.paper_ids.length })}</span>
                    </div>
                    {d.excerpt && <p className="paper-abstract clamp-2">{d.excerpt}</p>}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {tab === "export" && (
        <section className="panel panel-pad stack" style={{ maxWidth: 640 }}>
          <h3>{t("project.exportTitle")}</h3>
          <p className="t-muted">{t("project.exportBody")}</p>
          <ul className="prose prose-sm" style={{ margin: 0 }}>
            <li><span className="mono">references.bib</span> — {t("project.exportBib", { count: project.paper_count })}</li>
            <li><span className="mono">notes.md</span> — {t("project.exportNotes")}</li>
            <li><span className="mono">documents/</span> — {t("project.exportDocs", { count: project.document_count })}</li>
          </ul>
          {project.paper_count === 0 && <Notice tone="warn">{t("project.exportEmpty")}</Notice>}
          <div>
            <Button variant="primary" size="lg" icon={Download} loading={exportZip.isPending} onClick={() => exportZip.mutate()}>
              {t("project.exportAction")}
            </Button>
          </div>
        </section>
      )}

      <ProjectDialog open={editing} onClose={() => setEditing(false)} project={project} />
      <AddFromLibrary projectId={projectId} existing={paperIds} open={adding} onClose={() => setAdding(false)} />
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)} title={t("project.deleteTitle")}
              footer={
                <>
                  <Button variant="ghost" onClick={() => setConfirmDelete(false)}>{t("common.cancel")}</Button>
                  <Button variant="danger" loading={remove.isPending} onClick={() => remove.mutate()}>{t("common.delete")}</Button>
                </>
              }>
        <p>{t("project.deleteBody")}</p>
      </Dialog>
    </div>
  );
}
