// 探索：所有「找文獻」的入口集中在這裡。
// 搜尋與匯入是焦點；推薦、趨勢、訂閱來源是輔助的發現管道。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Compass, Download, Plus, RefreshCw, Rss, Search, Trash2, TrendingUp } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { BarChart } from "../components/BarChart";
import { AddToProject, PaperDrawer, PaperRow } from "../components/Paper";
import { api } from "../lib/api";
import { useProjects, type Paper } from "../lib/types";
import { Badge, Button, Empty, IconButton, Input, Notice, PageHead, QueryState, Segmented, Select, Switch, Tabs, Textarea } from "../ui";
import { useToast } from "../ui/toast";

type Tab = "search" | "foryou" | "trends" | "sources";

interface ImportResult {
  imported: Paper[];
  failed: string[];
}

interface Rising {
  keyword: string;
  slope: number;
  periods: string[];
  counts: number[];
  forecast: number;
}

interface Feed {
  id: number;
  url: string;
  title: string | null;
  enabled: boolean;
}

// ---------- 搜尋與匯入 ----------
function SearchTab({ initialQuery, initialProject }: { initialQuery: string; initialProject: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const projects = useProjects();
  const [input, setInput] = useState(initialQuery);
  const [query, setQuery] = useState(initialQuery);
  const [target, setTarget] = useState(initialProject);
  const [toReading, setToReading] = useState(true);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [imported, setImported] = useState<Set<string>>(new Set());
  const [refs, setRefs] = useState("");
  const [openPaper, setOpenPaper] = useState<string | null>(null);

  useEffect(() => { setInput(initialQuery); setQuery(initialQuery); }, [initialQuery]);

  const results = useQuery({
    queryKey: ["discover", query],
    queryFn: () => api<{ items: Paper[] }>(`/api/discover?query=${encodeURIComponent(query)}&limit=15`),
    enabled: query.length >= 2,
    staleTime: 5 * 60_000,
  });

  const doImport = useMutation({
    mutationFn: (list: string[]) =>
      api<ImportResult>("/api/papers/import", {
        method: "POST",
        body: { refs: list, project_id: target ? Number(target) : null, add_to_reading: toReading },
      }),
    onSuccess: (data) => {
      setImported((prev) => new Set([...prev, ...data.imported.map((p) => p.id)]));
      setPicked(new Set());
      for (const key of ["papers", "reading", "projects", "project", "personalized"]) {
        void queryClient.invalidateQueries({ queryKey: [key] });
      }
      if (data.imported.length > 0) toast.show(t("discover.imported", { count: data.imported.length }));
      if (data.failed.length > 0) toast.show(t("discover.importFailed", { refs: data.failed.slice(0, 3).join("、") }), { tone: "danger" });
      if (data.failed.length === 0) setRefs("");
    },
    onError: toast.error,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim().length >= 2) setQuery(input.trim());
  };
  const toggle = (id: string) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  const refList = refs.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean).slice(0, 25);
  const isIn = (p: Paper) => p.in_library || imported.has(p.id);

  return (
    <div className="grid-main">
      <div className="stack">
        <form className="row" onSubmit={submit}>
          <div className="grow">
            <Input icon={Search} value={input} onChange={(e) => setInput(e.target.value)}
                   placeholder={t("discover.searchPlaceholder")} aria-label={t("discover.searchTab")}
                   style={{ height: 40, fontSize: 15 }} autoFocus />
          </div>
          <Button variant="primary" size="lg" type="submit" disabled={input.trim().length < 2}>{t("common.search")}</Button>
        </form>

        {query.length < 2 ? (
          <div className="panel"><Empty icon={Compass} title={t("discover.startTitle")}>{t("discover.startBody")}</Empty></div>
        ) : (
          <>
            <div className="spread">
              <span className="t-meta">{results.data ? t("discover.resultCount", { count: results.data.items.length, query }) : " "}</span>
              <Button variant="primary" icon={Download} disabled={picked.size === 0} loading={doImport.isPending}
                      onClick={() => doImport.mutate([...picked])}>
                {t("discover.importSelected", { count: picked.size })}
              </Button>
            </div>
            <div className="panel">
              <QueryState loading={results.isPending} error={results.isError} empty={results.data?.items.length === 0}
                          emptyState={<Empty title={t("discover.noResults")}>{t("discover.noResultsBody")}</Empty>} />
              <div className="list">
                {(results.data?.items ?? []).map((p) => (
                  <PaperRow
                    key={p.id}
                    paper={{ ...p, in_library: isIn(p) }}
                    showAbstract
                    onOpen={isIn(p) ? setOpenPaper : undefined}
                    leading={
                      <span className="check" style={{ paddingTop: 3 }}>
                        <input type="checkbox" aria-label={p.title} disabled={isIn(p) && !target}
                               checked={picked.has(p.id)} onChange={() => toggle(p.id)} />
                      </span>
                    }
                    actions={isIn(p)
                      ? <AddToProject paperIds={[p.id]}>{(props) => <IconButton icon={Plus} label={t("paper.addToProject")} {...props} />}</AddToProject>
                      : <IconButton icon={Download} label={t("discover.import")} onClick={() => doImport.mutate([p.id])} />}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      <aside className="stack-lg">
        <section className="stack">
          <span className="t-label">{t("discover.importTo")}</span>
          <Select value={target} onChange={(e) => setTarget(e.target.value)} aria-label={t("discover.importTo")}>
            <option value="">{t("discover.libraryOnly")}</option>
            {(projects.data?.items ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          <div className="spread">
            <span>{t("discover.addToReading")}</span>
            <Switch checked={toReading} onChange={setToReading} label={t("discover.addToReading")} />
          </div>
        </section>
        <section className="stack">
          <span className="t-label">{t("discover.byId")}</span>
          <Textarea rows={4} value={refs} onChange={(e) => setRefs(e.target.value)}
                    placeholder={"2401.12345\nhttps://arxiv.org/abs/1706.03762\n10.1145/3292500.3330701"}
                    aria-label={t("discover.byId")} className="mono" />
          <span className="field-hint">{t("discover.byIdHint")}</span>
          <Button icon={Download} disabled={refList.length === 0} loading={doImport.isPending}
                  onClick={() => doImport.mutate(refList)}>
            {t("discover.importCount", { count: refList.length })}
          </Button>
        </section>
      </aside>
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </div>
  );
}

// ---------- 為你推薦 ----------
function ForYouTab() {
  const { t } = useTranslation();
  const [openPaper, setOpenPaper] = useState<string | null>(null);
  const recommended = useQuery({
    queryKey: ["personalized", 12],
    queryFn: () => api<{ items: Paper[] }>("/api/daily/personalized?top_n=12"),
  });
  return (
    <div className="stack">
      <p className="t-muted" style={{ maxWidth: "62ch" }}>{t("discover.forYouBody")}</p>
      <div className="panel">
        <QueryState loading={recommended.isPending} error={recommended.isError} empty={recommended.data?.items.length === 0}
                    emptyState={<Empty title={t("home.forYouEmpty")} />} />
        <div className="list">
          {(recommended.data?.items ?? []).map((p) => (
            <PaperRow key={p.id} paper={p} showAbstract onOpen={setOpenPaper}
                      actions={<AddToProject paperIds={[p.id]}>{(props) => <IconButton icon={Plus} label={t("paper.addToProject")} {...props} />}</AddToProject>} />
          ))}
        </div>
      </div>
      <PaperDrawer paperId={openPaper} onClose={() => setOpenPaper(null)} />
    </div>
  );
}

// ---------- 趨勢 ----------
function TrendsTab({ onSearch }: { onSearch: (q: string) => void }) {
  const { t } = useTranslation();
  const [granularity, setGranularity] = useState<"month" | "year">("month");
  const [picked, setPicked] = useState<string | null>(null);
  const trends = useQuery({
    queryKey: ["trends", granularity],
    queryFn: () => api<{ rising: Rising[]; top: { keyword: string; count: number }[]; total_papers: number }>(
      `/api/trends?granularity=${granularity}&top=15`),
  });
  const selected = picked ?? trends.data?.rising[0]?.keyword ?? trends.data?.top[0]?.keyword ?? null;
  const series = useQuery({
    queryKey: ["trend", selected, granularity],
    queryFn: () => api<Rising>(`/api/trends/${encodeURIComponent(selected!)}?granularity=${granularity}`),
    enabled: !!selected,
  });

  return (
    <div className="stack-lg">
      <div className="spread">
        <span className="t-meta">{trends.data ? t("discover.trendBasis", { count: trends.data.total_papers }) : " "}</span>
        <Segmented label={t("discover.granularity")} value={granularity} onChange={setGranularity}
                   items={[{ key: "month", label: t("discover.byMonth") }, { key: "year", label: t("discover.byYear") }]} />
      </div>
      <QueryState loading={trends.isPending} error={trends.isError}
                  empty={trends.data ? trends.data.top.length === 0 : false}
                  emptyState={<div className="panel"><Empty icon={TrendingUp} title={t("discover.trendEmpty")}>{t("discover.trendEmptyBody")}</Empty></div>} />
      {trends.data && trends.data.top.length > 0 && (
        <div className="grid-main">
          <section className="panel panel-pad stack">
            <div className="spread">
              <div>
                <div className="t-label">{t("discover.keyword")}</div>
                <h2 style={{ marginTop: 2 }}>{selected}</h2>
              </div>
              {selected && <Button icon={Search} onClick={() => onSearch(selected)}>{t("discover.searchKeyword")}</Button>}
            </div>
            {series.data && (
              <>
                <BarChart accent data={series.data.periods.map((p, i) => ({ label: p.slice(2), value: series.data!.counts[i] }))} />
                <span className="t-meta">{t("discover.forecast", { value: series.data.forecast })}</span>
              </>
            )}
          </section>
          <aside className="stack-lg">
            {trends.data.rising.length > 0 && (
              <section className="stack">
                <span className="t-label">{t("discover.rising")}</span>
                <div className="row-wrap">
                  {trends.data.rising.map((r) => (
                    <button key={r.keyword} type="button" className="keyword" aria-pressed={selected === r.keyword}
                            onClick={() => setPicked(r.keyword)}>
                      {r.keyword}<span className="num">↑{r.slope.toFixed(1)}</span>
                    </button>
                  ))}
                </div>
              </section>
            )}
            <section className="stack">
              <span className="t-label">{t("discover.frequent")}</span>
              <div className="row-wrap">
                {trends.data.top.map((k) => (
                  <button key={k.keyword} type="button" className="keyword" aria-pressed={selected === k.keyword}
                          onClick={() => setPicked(k.keyword)}>
                    {k.keyword}<span className="num">{k.count}</span>
                  </button>
                ))}
              </div>
            </section>
          </aside>
        </div>
      )}
    </div>
  );
}

// ---------- 訂閱來源 ----------
function SourcesTab() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");
  const feeds = useQuery({ queryKey: ["feeds"], queryFn: () => api<{ items: Feed[] }>("/api/feeds") });
  const sources = useQuery({
    queryKey: ["sources"],
    queryFn: () => api<{ items: { name: string; configured: boolean; detail: string | null }[] }>("/api/sources"),
  });
  const refreshAll = () => {
    void queryClient.invalidateQueries({ queryKey: ["feeds"] });
    void queryClient.invalidateQueries({ queryKey: ["papers"] });
    void queryClient.invalidateQueries({ queryKey: ["sources"] });
  };
  const addFeed = useMutation({
    mutationFn: () => api("/api/feeds", { method: "POST", body: { url: url.trim() } }),
    onSuccess: () => { setUrl(""); refreshAll(); },
    onError: toast.error,
  });
  const toggleFeed = useMutation({
    mutationFn: (f: Feed) => api(`/api/feeds/${f.id}`, { method: "PATCH", body: { enabled: !f.enabled } }),
    onSuccess: refreshAll, onError: toast.error,
  });
  const deleteFeed = useMutation({
    mutationFn: (id: number) => api(`/api/feeds/${id}`, { method: "DELETE" }),
    onSuccess: refreshAll, onError: toast.error,
  });
  const refreshFeeds = useMutation({
    mutationFn: () => api<{ fetched: number; added: number }>("/api/feeds/refresh", { method: "POST" }),
    onSuccess: (d) => { toast.show(t("discover.fetched", d)); refreshAll(); },
    onError: toast.error,
  });
  const fetchDaily = useMutation({
    mutationFn: () => api<{ fetched: number; added: number }>("/api/daily", { method: "POST", body: {} }),
    onSuccess: (d) => { toast.show(t("discover.fetched", d)); refreshAll(); },
    onError: toast.error,
  });

  return (
    <div className="grid-main">
      <section className="stack">
        <div className="section-head"><h3>{t("discover.feeds")}</h3>
          <Button icon={RefreshCw} loading={refreshFeeds.isPending} disabled={feeds.data?.items.length === 0}
                  onClick={() => refreshFeeds.mutate()}>{t("discover.refreshFeeds")}</Button>
        </div>
        <form className="row" onSubmit={(e) => { e.preventDefault(); if (url.trim()) addFeed.mutate(); }}>
          <div className="grow">
            <Input icon={Rss} type="url" value={url} onChange={(e) => setUrl(e.target.value)}
                   placeholder="https://example.com/feed.xml" aria-label={t("discover.feedUrl")} />
          </div>
          <Button type="submit" icon={Plus} loading={addFeed.isPending} disabled={!url.trim()}>{t("discover.addFeed")}</Button>
        </form>
        <div className="panel">
          <QueryState loading={feeds.isPending} error={feeds.isError} empty={feeds.data?.items.length === 0}
                      emptyState={<Empty icon={Rss} title={t("discover.noFeeds")}>{t("discover.noFeedsBody")}</Empty>} />
          <div className="list">
            {(feeds.data?.items ?? []).map((f) => (
              <div key={f.id} className="list-row" style={{ alignItems: "center" }}>
                <div className="grow">
                  <div className="t-strong truncate">{f.title || new URL(f.url).hostname}</div>
                  <div className="t-meta mono truncate">{f.url}</div>
                </div>
                <Switch checked={f.enabled} onChange={() => toggleFeed.mutate(f)} label={f.url} />
                <IconButton icon={Trash2} label={t("common.delete")} onClick={() => deleteFeed.mutate(f.id)} />
              </div>
            ))}
          </div>
        </div>
      </section>
      <aside className="stack-lg">
        <section className="stack">
          <span className="t-label">{t("discover.daily")}</span>
          <p className="t-meta">{t("discover.dailyBody")}</p>
          <Button icon={RefreshCw} loading={fetchDaily.isPending} onClick={() => fetchDaily.mutate()}>{t("discover.fetchNow")}</Button>
        </section>
        <section className="stack">
          <span className="t-label">{t("discover.sourceStatus")}</span>
          <div className="col">
            {(sources.data?.items ?? []).map((s) => (
              <div key={s.name} className="spread">
                <span className="row"><span className="t-strong">{s.name}</span>{s.detail && <span className="t-meta mono">{s.detail}</span>}</span>
                {s.configured ? <Badge tone="ok"><Check size={11} />{t("discover.on")}</Badge> : <Badge>{t("discover.off")}</Badge>}
              </div>
            ))}
          </div>
        </section>
        <Notice>{t("discover.sharedNotice")}</Notice>
      </aside>
    </div>
  );
}

export function Discover() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "search";
  const set = (next: Record<string, string>) => {
    const merged = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) {
      if (v) merged.set(k, v); else merged.delete(k);
    }
    setParams(merged, { replace: true });
  };

  return (
    <div className="stack-lg">
      <PageHead title={t("nav.discover")}>{t("discover.intro")}</PageHead>
      <Tabs<Tab> label={t("nav.discover")} value={tab} onChange={(next) => set({ tab: next === "search" ? "" : next })}
                 items={[
                   { key: "search", label: t("discover.searchTab") },
                   { key: "foryou", label: t("discover.forYouTab") },
                   { key: "trends", label: t("discover.trendsTab") },
                   { key: "sources", label: t("discover.sourcesTab") },
                 ]} />
      {tab === "search" && <SearchTab initialQuery={params.get("q") ?? ""} initialProject={params.get("project") ?? ""} />}
      {tab === "foryou" && <ForYouTab />}
      {tab === "trends" && <TrendsTab onSearch={(q) => set({ tab: "", q })} />}
      {tab === "sources" && <SourcesTab />}
    </div>
  );
}
