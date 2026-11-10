// 今日：一打開就知道「我的研究走到哪、接下來做什麼」。
// 焦點是進行中專案的研究軌跡與下一步；其餘資訊退到第二層。
import { useQuery } from "@tanstack/react-query";
import { ArrowUp, BookOpen, FolderPlus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { NextStep } from "../components/NextStep";
import { PaperDrawer } from "../components/Paper";
import { ProjectDialog } from "../components/ProjectForm";
import { ResearchTrail } from "../components/ResearchTrail";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import {
  shortDate, useProjects, useReading, type Conversation, type DocumentSummary, type Paper, type ProjectOverview,
} from "../lib/types";
import { Button, Empty, IconButton, QueryState } from "../ui";

function greetingKey(): string {
  const h = new Date().getHours();
  return h < 5 ? "home.night" : h < 12 ? "home.morning" : h < 18 ? "home.afternoon" : "home.evening";
}

export function Home() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const projects = useProjects();
  const reading = useReading();
  const [question, setQuestion] = useState("");
  const [creating, setCreating] = useState(false);
  const [openPaper, setOpenPaper] = useState<string | null>(null);

  const current = projects.data?.items[0];
  const overview = useQuery({
    queryKey: ["project", current?.id, "overview"],
    queryFn: () => api<ProjectOverview>(`/api/projects/${current!.id}/overview`),
    enabled: !!current,
  });
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<{ items: DocumentSummary[] }>("/api/documents"),
  });
  const conversations = useQuery({
    queryKey: ["conversations", "recent"],
    queryFn: () => api<{ items: Conversation[] }>("/api/conversations?limit=5"),
  });
  const recommended = useQuery({
    queryKey: ["personalized", 4],
    queryFn: () => api<{ items: Paper[] }>("/api/daily/personalized?top_n=4"),
  });

  const ask = (e: FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    navigate(`/ask?q=${encodeURIComponent(q)}${current ? `&project=${current.id}` : ""}`);
  };

  const toRead = (reading.data?.items ?? []).filter((r) => r.state !== "done").slice(0, 5);
  const today = new Date().toLocaleDateString(i18n.language === "zh" ? "zh-TW" : "en-US",
                                              { weekday: "long", month: "long", day: "numeric" });

  return (
    <div className="stack-lg">
      <header>
        <div className="t-meta">{today}</div>
        <h1 style={{ marginTop: 4 }}>{t(greetingKey(), { name: user?.display_name ?? "" })}</h1>
      </header>

      {/* 焦點：進行中的專案 */}
      {projects.isPending ? (
        <div className="skeleton" style={{ height: 180 }} />
      ) : current && overview.data ? (
        <section className="panel panel-pad stack">
          <div className="spread" style={{ alignItems: "flex-start" }}>
            <div className="grow">
              <div className="t-label">{t("home.currentProject")}</div>
              <h2 style={{ marginTop: 4 }}>
                <Link to={`/projects/${current.id}`} style={{ color: "inherit" }}>{current.name}</Link>
              </h2>
              {current.question && <p className="t-serif t-muted" style={{ marginTop: 4, fontStyle: "italic" }}>{current.question}</p>}
            </div>
            <Link className="btn btn-ghost btn-sm" to="/projects">{t("nav.allProjects")}</Link>
          </div>
          <ResearchTrail stages={overview.data.stages} next={overview.data.next_step}
                         onSelect={() => navigate(`/projects/${current.id}`)} />
          <NextStep projectId={current.id} step={overview.data.next_step} />
        </section>
      ) : current ? (
        <div className="skeleton" style={{ height: 180 }} />
      ) : (
        <section className="panel">
          <Empty icon={BookOpen} title={t("home.startTitle")}
                 action={<Button variant="primary" size="lg" icon={FolderPlus} onClick={() => setCreating(true)}>{t("project.new")}</Button>}>
            {t("home.startBody")}
          </Empty>
        </section>
      )}

      {/* 快速提問 */}
      <form className="composer composer-wide" onSubmit={ask}>
        <div className="row" style={{ padding: "6px 8px 6px 14px" }}>
          <input className="grow" style={{ border: 0, background: "none", outline: "none", height: 36, fontSize: 15 }}
                 value={question} onChange={(e) => setQuestion(e.target.value)}
                 placeholder={current ? t("home.askInProject", { name: current.name }) : t("home.askPlaceholder")}
                 aria-label={t("nav.ask")} />
          <IconButton icon={ArrowUp} label={t("ask.send")} type="submit" disabled={!question.trim()} />
        </div>
      </form>

      <div className="grid-main">
        <div className="stack-lg">
          <section>
            <div className="section-head">
              <h3>{t("home.readingQueue")}</h3>
              <Link to="/library?view=board" className="t-meta">{t("common.viewAll")}</Link>
            </div>
            <div className="panel">
              <QueryState loading={reading.isPending} error={reading.isError} empty={toRead.length === 0}
                          emptyState={<Empty title={t("home.readingEmpty")}
                                             action={<Link className="btn" to="/discover">{t("nav.discover")}</Link>} />} />
              <div className="list">
                {toRead.map((r) => (
                  <div key={r.id} className="list-row list-row-click" onClick={() => setOpenPaper(r.id)}>
                    <div className="grow">
                      <div className="paper-title">{r.title}</div>
                      <div className="paper-meta">
                        <span>{t(`reading.${r.state}`)}</span>
                        {r.tags.map((tag) => <span key={tag}>#{tag}</span>)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section>
            <div className="section-head">
              <h3>{t("home.forYou")}</h3>
              <Link to="/discover?tab=foryou" className="t-meta">{t("common.viewAll")}</Link>
            </div>
            <div className="panel">
              <QueryState loading={recommended.isPending} error={recommended.isError}
                          empty={recommended.data?.items.length === 0}
                          emptyState={<Empty title={t("home.forYouEmpty")}
                                             action={<Link className="btn" to="/discover">{t("discover.searchTab")}</Link>} />} />
              <div className="list">
                {(recommended.data?.items ?? []).map((p) => (
                  <div key={p.id} className="list-row list-row-click" onClick={() => setOpenPaper(p.id)}>
                    <div className="grow">
                      <div className="paper-title">{p.title}</div>
                      <div className="paper-meta"><span className="num">{shortDate(p.published)}</span><span className="mono">{p.id}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        <aside className="stack-lg">
          <section>
            <div className="section-head">
              <span className="t-label">{t("home.recentDocuments")}</span>
              <Link to="/write" className="t-meta">{t("common.viewAll")}</Link>
            </div>
            <div className="col">
              {(documents.data?.items ?? []).slice(0, 5).map((d) => (
                <Link key={d.id} to={`/write/${d.id}`} className="nav-link" style={{ height: "auto", padding: "6px 8px" }}>
                  <span className="grow truncate">{d.title}</span>
                  <span className="t-meta num">{shortDate(d.updated_at).slice(5)}</span>
                </Link>
              ))}
              {documents.data?.items.length === 0 && <span className="t-meta">{t("home.noDocuments")}</span>}
            </div>
          </section>
          <section>
            <div className="section-head">
              <span className="t-label">{t("home.recentConversations")}</span>
              <Link to="/ask" className="t-meta">{t("common.viewAll")}</Link>
            </div>
            <div className="col">
              {(conversations.data?.items ?? []).map((c) => (
                <Link key={c.id} to={`/ask?c=${c.id}`} className="nav-link" style={{ height: "auto", padding: "6px 8px" }}>
                  <span className="grow truncate">{c.title || `#${c.id}`}</span>
                </Link>
              ))}
              {conversations.data?.items.length === 0 && <span className="t-meta">{t("home.noConversations")}</span>}
            </div>
          </section>
        </aside>
      </div>

      <ProjectDialog open={creating} onClose={() => setCreating(false)} />
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </div>
  );
}
