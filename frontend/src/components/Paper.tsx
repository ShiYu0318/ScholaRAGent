// 論文相關的共用元件：清單列、加入專案選單、詳情抽屜。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookmarkPlus, Code2, ExternalLink, FolderPlus, Lightbulb, MessageSquareText, Quote, ThumbsUp,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { api, ApiError } from "../lib/api";
import {
  READING_STATES, shortDate, useProjects, useReading, type Paper, type ReadingState,
} from "../lib/types";
import { Badge, Button, Drawer, Field, IconButton, Input, Menu, Notice, Segmented, Spinner, Textarea } from "../ui";
import { useToast } from "../ui/toast";
import { Markdown } from "./Markdown";

/** 論文 id 可能含斜線（舊式 arXiv id），路徑上只跳脫空白等字元。 */
export function paperPath(id: string): string {
  return encodeURI(id);
}

export function AddToProject({ paperIds, children }: { paperIds: string[]; children: (props: object) => ReactNode }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useProjects();

  const add = useMutation({
    mutationFn: (projectId: number) =>
      api<{ added: number }>(`/api/projects/${projectId}/papers`, { method: "POST", body: { paper_ids: paperIds } }),
    onSuccess: (data, projectId) => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      toast.show(t("paper.addedToProject", { count: data.added }),
                 { action: { label: t("common.open"), onClick: () => navigate(`/projects/${projectId}`) } });
    },
    onError: toast.error,
  });

  const list = projects.data?.items ?? [];
  return (
    <Menu
      header={<div className="menu-label">{t("paper.addToProject")}</div>}
      items={[
        ...list.map((p) => ({ label: p.name, onSelect: () => add.mutate(p.id) })),
        { label: t("nav.newProject"), icon: FolderPlus, separatorBefore: list.length > 0,
          onSelect: () => navigate("/projects?new=1") },
      ]}
      trigger={(props) => children(props)}
    />
  );
}

interface RowProps {
  paper: Paper;
  onOpen?: (id: string) => void;
  actions?: ReactNode;
  showAbstract?: boolean;
  leading?: ReactNode;
}

export function PaperRow({ paper, onOpen, actions, showAbstract, leading }: RowProps) {
  const { t } = useTranslation();
  return (
    <div className="list-row">
      {leading}
      <div className="grow">
        {onOpen ? (
          <button type="button" className="paper-title" onClick={() => onOpen(paper.id)}>{paper.title}</button>
        ) : (
          <a className="paper-title" href={paper.link} target="_blank" rel="noopener noreferrer">{paper.title}</a>
        )}
        <div className="paper-meta">
          {paper.authors && <span className="truncate" style={{ maxWidth: 320 }}>{paper.authors}</span>}
          {paper.published && <span className="num">{shortDate(paper.published)}</span>}
          <span className="mono">{paper.id}</span>
          {paper.reproducibility?.has_code && <Badge tone="ok"><Code2 size={11} />{t("paper.hasCode")}</Badge>}
          {paper.reading && <Badge tone={paper.reading.state === "done" ? "ok" : undefined}>{t(`reading.${paper.reading.state}`)}</Badge>}
          {paper.in_library && <Badge>{t("paper.inLibrary")}</Badge>}
        </div>
        {showAbstract && paper.abstract && <p className="paper-abstract clamp-3">{paper.abstract}</p>}
        {paper.reading?.note && <p className="paper-abstract clamp-2 t-serif" style={{ fontStyle: "italic" }}>“{paper.reading.note}”</p>}
      </div>
      {actions && <div className="row-actions">{actions}</div>}
    </div>
  );
}

/** 論文詳情：摘要、訊號、閱讀狀態與筆記，並能從這裡直接往下一步走（提問、加入專案）。 */
export function PaperDrawer({ paperId, onClose }: { paperId: string | null; onClose: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const reading = useReading();

  const paper = useQuery({
    queryKey: ["paper", paperId],
    queryFn: () => api<Paper>(`/api/paper/${paperPath(paperId!)}`),
    enabled: paperId !== null,
  });
  const entry = reading.data?.items.find((r) => r.id === paperId) ?? null;
  const [note, setNote] = useState("");
  const [tags, setTags] = useState("");
  const [explained, setExplained] = useState<string | null>(null);

  // 只在「換了一篇論文」或「伺服器上的值真的變了」時才把欄位同步成伺服器的值。
  // 依賴要用內容比較：閱讀清單每次重新載入都會給新的陣列，若拿陣列本身當依賴，
  // 使用者打到一半的筆記會在背景重新載入時被清空。
  const serverNote = entry?.note ?? "";
  const serverTags = (entry?.tags ?? []).join(", ");
  useEffect(() => {
    setNote(serverNote);
    setTags(serverTags);
  }, [paperId, serverNote, serverTags]);
  useEffect(() => setExplained(null), [paperId]);

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["reading"] });
    void queryClient.invalidateQueries({ queryKey: ["project"] });
  };

  // 先嘗試局部更新，項目不存在（404）才建立。
  // 不能用畫面上的 entry 來判斷：剛加入清單、快取還沒更新時它是舊的，
  // 那時若走「建立」會把剛設好的狀態蓋回預設值。
  const saveReading = useMutation({
    mutationFn: async (patch: { state?: ReadingState; note?: string; tags?: string[] }) => {
      try {
        return await api(`/api/reading/${paperPath(paperId!)}`, { method: "PATCH", body: patch });
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 404) throw err;
        return api("/api/reading", { method: "POST", body: {
          paper_id: paperId, title: paper.data?.title ?? "", state: patch.state ?? "to-read",
          note: patch.note ?? "", tags: patch.tags ?? [] } });
      }
    },
    onSuccess: refresh,
    onError: toast.error,
  });

  const explain = useMutation({
    mutationFn: () => api<{ content: string }>("/api/explain", { method: "POST", body: { paper_id: paperId } }),
    onSuccess: (d) => setExplained(d.content),
    onError: toast.error,
  });

  const like = useMutation({
    mutationFn: () => api("/api/interactions", { method: "POST", body: { action: "like", paper_id: paperId } }),
    onSuccess: () => toast.show(t("paper.liked")),
    onError: toast.error,
  });

  const p = paper.data;
  const parsedTags = tags.split(/[,，]/).map((s) => s.trim()).filter(Boolean).slice(0, 20);

  return (
    <Drawer
      open={paperId !== null}
      onClose={onClose}
      label={t("paper.details")}
      header={p ? (
        <>
          <h3 style={{ fontSize: 20 }}>{p.title}</h3>
          <div className="paper-meta">
            {p.authors && <span>{p.authors}</span>}
            {p.published && <span className="num">{shortDate(p.published)}</span>}
          </div>
        </>
      ) : <Spinner />}
    >
      {paper.isError && <Notice tone="danger">{t("common.error")}</Notice>}
      {p && (
        <div className="stack-lg">
          <div className="row-wrap">
            <Button variant="primary" icon={MessageSquareText}
                    onClick={() => { onClose(); navigate(`/ask?paper=${encodeURIComponent(p.id)}`); }}>
              {t("paper.ask")}
            </Button>
            <AddToProject paperIds={[p.id]}>
              {(props) => <Button icon={FolderPlus} {...props}>{t("paper.addToProject")}</Button>}
            </AddToProject>
            {p.link && (
              <a className="btn" href={p.link} target="_blank" rel="noopener noreferrer">
                <ExternalLink size={14} />{t("paper.source")}
              </a>
            )}
            <IconButton icon={ThumbsUp} label={t("paper.like")} onClick={() => like.mutate()} />
          </div>

          <div className="row-wrap">
            <span className="mono t-meta">{p.id}</span>
            {p.source && <Badge>{p.source}</Badge>}
            {p.credibility && (
              <Badge tone={p.credibility.tier === "high" ? "ok" : undefined}>
                <Quote size={11} />{t("paper.citedBy", { count: p.credibility.cited_by_count })}
              </Badge>
            )}
            {p.reproducibility?.has_code && (p.reproducibility.repos ?? []).slice(0, 2).map((repo) => (
              <a key={repo} className="badge badge-ok" href={repo} target="_blank" rel="noopener noreferrer">
                <Code2 size={11} />{repo.replace(/^https?:\/\/(www\.)?/, "").slice(0, 36)}
              </a>
            ))}
          </div>

          <section>
            <div className="t-label" style={{ marginBottom: 8 }}>{t("paper.abstract")}</div>
            <p className="t-serif" style={{ fontSize: 15, lineHeight: 1.7 }}>{p.abstract || t("paper.noAbstract")}</p>
          </section>

          <section className="stack">
            <div className="spread">
              <span className="t-label">{t("paper.myReading")}</span>
              <Segmented
                label={t("paper.myReading")}
                value={entry?.state ?? ("none" as ReadingState)}
                onChange={(state) => saveReading.mutate({ state })}
                items={READING_STATES.map((s) => ({ key: s, label: t(`reading.${s}`) }))}
              />
            </div>
            <Field label={t("paper.note")} hint={t("paper.noteHint")}>
              {(id) => (
                <Textarea id={id} rows={5} value={note} maxLength={5000}
                          placeholder={t("paper.notePlaceholder")}
                          onChange={(e) => setNote(e.target.value)}
                          onBlur={() => note !== serverNote && saveReading.mutate({ note })} />
              )}
            </Field>
            <Field label={t("paper.tags")} hint={t("paper.tagsHint")}>
              {(id) => (
                <Input id={id} value={tags} onChange={(e) => setTags(e.target.value)}
                       onBlur={() => parsedTags.join(", ") !== serverTags && saveReading.mutate({ tags: parsedTags })} />
              )}
            </Field>
            {!entry && (
              <div>
                <Button size="sm" icon={BookmarkPlus} onClick={() => saveReading.mutate({ state: "to-read" })}>
                  {t("paper.addToReading")}
                </Button>
              </div>
            )}
          </section>

          <section className="stack">
            <div className="spread">
              <span className="t-label">{t("paper.explainTitle")}</span>
              <Button size="sm" icon={Lightbulb} loading={explain.isPending} onClick={() => explain.mutate()}>
                {explained ? t("paper.explainAgain") : t("paper.explain")}
              </Button>
            </div>
            {explained && <Markdown small>{explained}</Markdown>}
          </section>
        </div>
      )}
    </Drawer>
  );
}
