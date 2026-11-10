// 專案列表：每個專案一列，附上精簡版的研究軌跡，一眼看出各自走到哪。
import { useQueries } from "@tanstack/react-query";
import { FolderOpen, FolderPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { ProjectDialog } from "../components/ProjectForm";
import { ResearchTrail } from "../components/ResearchTrail";
import { api } from "../lib/api";
import { shortDate, type Project, type ProjectOverview } from "../lib/types";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Empty, PageHead, QueryState, Switch } from "../ui";

export function Projects() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const [archived, setArchived] = useState(false);

  useEffect(() => {
    if (params.get("new")) {
      setCreating(true);
      setParams({}, { replace: true });
    }
  }, [params, setParams]);

  const projects = useQuery({
    queryKey: ["projects", { archived }],
    queryFn: () => api<{ items: Project[] }>(`/api/projects?include_archived=${archived}`),
  });
  const items = projects.data?.items ?? [];
  const overviews = useQueries({
    queries: items.map((p) => ({
      queryKey: ["project", p.id, "overview"],
      queryFn: () => api<ProjectOverview>(`/api/projects/${p.id}/overview`),
    })),
  });

  return (
    <div>
      <PageHead title={t("nav.projects")}
                actions={<Button variant="primary" icon={FolderPlus} onClick={() => setCreating(true)}>{t("project.new")}</Button>}>
        {t("project.intro")}
      </PageHead>

      <div className="row" style={{ marginBottom: 12, justifyContent: "flex-end" }}>
        <span className="t-meta">{t("project.showArchived")}</span>
        <Switch checked={archived} onChange={setArchived} label={t("project.showArchived")} />
      </div>

      <div className="panel">
        <QueryState loading={projects.isPending} error={projects.isError} empty={items.length === 0}
                    emptyState={
                      <Empty icon={FolderOpen} title={t("project.emptyTitle")}
                             action={<Button variant="primary" icon={FolderPlus} onClick={() => setCreating(true)}>{t("project.new")}</Button>}>
                        {t("project.emptyBody")}
                      </Empty>
                    } />
        <div className="list">
          {items.map((p, i) => {
            const o = overviews[i]?.data;
            return (
              <Link key={p.id} to={`/projects/${p.id}`} className="list-row list-row-click"
                    style={{ color: "inherit", textDecoration: "none", alignItems: "center", gap: 24, padding: "16px" }}>
                <div className="grow">
                  <div className="row">
                    <span className="paper-title" style={{ fontSize: 17 }}>{p.name}</span>
                    {p.status === "archived" && <Badge>{t("project.archived")}</Badge>}
                  </div>
                  {p.question && <div className="t-meta truncate" style={{ marginTop: 2 }}>{p.question}</div>}
                  <div className="paper-meta">
                    <span>{t("project.papers", { count: p.paper_count })}</span>
                    <span>{t("project.documents", { count: p.document_count })}</span>
                    <span className="num">{t("project.updated", { date: shortDate(p.updated_at) })}</span>
                  </div>
                </div>
                <div style={{ width: 300, flex: "none" }}>
                  {o && <ResearchTrail stages={o.stages} next={o.next_step} compact />}
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      <ProjectDialog open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
