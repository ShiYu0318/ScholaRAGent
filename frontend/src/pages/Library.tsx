// 文庫：已收錄的論文與自己的閱讀進度。
// 清單負責「找到那篇」，看板負責「讀到哪了」；點任何一篇都開同一個詳情面板。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookmarkPlus, BookOpen, Compass, Download, Plus, Search, StickyNote, Trash2 } from "lucide-react";
import { useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { AddToProject, PaperDrawer, PaperRow, paperPath } from "../components/Paper";
import { api, download } from "../lib/api";
import { READING_STATES, useReading, type Paper, type ReadingState } from "../lib/types";
import { Button, Empty, IconButton, Input, Menu, PageHead, QueryState, Tabs } from "../ui";
import { useToast } from "../ui/toast";

type View = "papers" | "board";

export function Library() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const view = (params.get("view") as View) || "papers";
  const [query, setQuery] = useState("");
  const [openPaper, setOpenPaper] = useState<string | null>(null);
  const [over, setOver] = useState<ReadingState | null>(null);

  const papers = useQuery({
    queryKey: ["papers", query],
    queryFn: () => api<{ items: Paper[]; total: number }>(
      `/api/papers?limit=100${query ? `&query=${encodeURIComponent(query)}` : ""}`),
    enabled: view === "papers",
    placeholderData: (prev) => prev,
  });
  const reading = useReading();
  const readingById = new Map((reading.data?.items ?? []).map((r) => [r.id, r]));

  const refreshReading = () => void queryClient.invalidateQueries({ queryKey: ["reading"] });
  const addToReading = useMutation({
    mutationFn: (p: Paper) => api("/api/reading", { method: "POST", body: { paper_id: p.id, title: p.title } }),
    onSuccess: () => { toast.show(t("library.addedToReading")); refreshReading(); },
    onError: toast.error,
  });
  const move = useMutation({
    mutationFn: ({ id, state }: { id: string; state: ReadingState }) =>
      api(`/api/reading/${paperPath(id)}`, { method: "PATCH", body: { state } }),
    onSuccess: refreshReading, onError: toast.error,
  });
  const removeCard = useMutation({
    mutationFn: (id: string) => api(`/api/reading/${paperPath(id)}`, { method: "DELETE" }),
    onSuccess: refreshReading, onError: toast.error,
  });
  const exportFile = (path: string, name: string) => void download(path, name).catch(toast.error);

  const onDrop = (state: ReadingState) => (e: DragEvent) => {
    e.preventDefault();
    setOver(null);
    const id = e.dataTransfer.getData("text/paper-id");
    if (id) move.mutate({ id, state });
  };

  return (
    <div className="stack-lg">
      <PageHead
        title={t("nav.library")}
        actions={
          <>
            <Menu
              trigger={(props) => <Button icon={Download} {...props}>{t("library.export")}</Button>}
              items={[
                { label: "BibTeX (.bib)", onSelect: () => exportFile("/api/export/bibtex", "papers.bib") },
                { label: "CSV", onSelect: () => exportFile("/api/export/csv", "papers.csv") },
                { label: "Obsidian (.zip)", onSelect: () => exportFile("/api/export/obsidian", "obsidian-vault.zip") },
              ]}
            />
            <Link className="btn btn-primary" to="/discover"><Compass size={14} />{t("library.findMore")}</Link>
          </>
        }
      >
        {t("library.intro")}
      </PageHead>

      <Tabs<View> label={t("nav.library")} value={view}
                  onChange={(next) => setParams(next === "papers" ? {} : { view: next }, { replace: true })}
                  items={[
                    { key: "papers", label: t("library.papers"), count: papers.data?.total },
                    { key: "board", label: t("library.board"), count: reading.data?.items.length },
                  ]} />

      {view === "papers" && (
        <section className="stack">
          <Input icon={Search} value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder={t("library.searchPlaceholder")} aria-label={t("library.searchPlaceholder")} />
          <div className="panel">
            <QueryState loading={papers.isPending} error={papers.isError} empty={papers.data?.items.length === 0}
                        emptyState={
                          <Empty icon={BookOpen} title={query ? t("library.noMatch") : t("library.emptyTitle")}
                                 action={!query && <Link className="btn btn-primary" to="/discover">{t("library.findMore")}</Link>}>
                            {!query && t("library.emptyBody")}
                          </Empty>
                        } />
            <div className="list">
              {(papers.data?.items ?? []).map((p) => {
                const r = readingById.get(p.id);
                return (
                  <PaperRow
                    key={p.id}
                    paper={{ ...p, reading: r ? { state: r.state, tags: r.tags, note: "" } : null }}
                    onOpen={setOpenPaper}
                    actions={
                      <>
                        {!r && <IconButton icon={BookmarkPlus} label={t("paper.addToReading")} onClick={() => addToReading.mutate(p)} />}
                        <AddToProject paperIds={[p.id]}>
                          {(props) => <IconButton icon={Plus} label={t("paper.addToProject")} {...props} />}
                        </AddToProject>
                      </>
                    }
                  />
                );
              })}
            </div>
          </div>
        </section>
      )}

      {view === "board" && (
        reading.data?.items.length === 0 ? (
          <div className="panel">
            <Empty icon={BookmarkPlus} title={t("library.boardEmpty")}
                   action={<Button onClick={() => setParams({}, { replace: true })}>{t("library.papers")}</Button>}>
              {t("library.boardEmptyBody")}
            </Empty>
          </div>
        ) : (
          <div className="board">
            {READING_STATES.map((state) => {
              const items = (reading.data?.items ?? []).filter((i) => i.state === state);
              return (
                <div key={state} className="board-col" data-over={over === state}
                     onDragOver={(e) => { e.preventDefault(); setOver(state); }}
                     onDragLeave={() => setOver(null)} onDrop={onDrop(state)}>
                  <div className="board-col-head">
                    <span className="t-strong">{t(`reading.${state}`)}</span>
                    <span className="t-meta num">{items.length}</span>
                  </div>
                  {items.map((item) => (
                    <div key={item.id} className="board-card" draggable
                         onDragStart={(e) => e.dataTransfer.setData("text/paper-id", item.id)}>
                      <button type="button" className="paper-title" style={{ fontSize: 14 }} onClick={() => setOpenPaper(item.id)}>
                        {item.title}
                      </button>
                      <div className="spread" style={{ marginTop: 8 }}>
                        <div className="paper-meta" style={{ marginTop: 0 }}>
                          {item.note && <StickyNote size={12} aria-label={t("paper.note")} />}
                          {item.tags.slice(0, 3).map((tag) => <span key={tag}>#{tag}</span>)}
                        </div>
                        <div className="row" style={{ gap: 2 }}>
                          {/* 不靠拖曳也能移動：鍵盤與觸控使用者用這個選單 */}
                          <select className="select" style={{ width: "auto", height: 24, fontSize: 11, padding: "0 4px" }}
                                  value={item.state} aria-label={t("library.moveTo")}
                                  onChange={(e) => move.mutate({ id: item.id, state: e.target.value as ReadingState })}>
                            {READING_STATES.map((s) => <option key={s} value={s}>{t(`reading.${s}`)}</option>)}
                          </select>
                          <IconButton icon={Trash2} label={t("common.remove")} onClick={() => removeCard.mutate(item.id)} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        )
      )}

      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </div>
  );
}
