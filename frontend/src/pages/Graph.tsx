// 圖譜：從結構看一個領域。引用網路找關鍵論文、概念圖看方法與資料集的關係、
// 全域問答回答「這個領域整體在做什麼」這類跨文獻的問題。
import { useMutation, useQuery } from "@tanstack/react-query";
import { Network, RefreshCw, Search, Table2 } from "lucide-react";
import { useCallback, useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { communityColor, ForceGraph, type GraphEdge, type GraphNode } from "../components/ForceGraph";
import { Markdown } from "../components/Markdown";
import { SaveDocumentButton } from "../components/SaveDocument";
import { api } from "../lib/api";
import { Button, Empty, Input, Notice, PageHead, Spinner, Tabs } from "../ui";

type Mode = "concept" | "citation" | "global";

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  influential?: { id: string; label: string; pagerank: number }[];
  communities?: { nodes: string[]; summary: string }[];
}

interface GlobalAnswer {
  answer: string;
  communities: { nodes: string[]; summary: string }[];
}

function Dot({ index }: { index: number }) {
  return <span style={{ width: 9, height: 9, borderRadius: "50%", background: communityColor(index), flex: "none", display: "inline-block" }} />;
}

export function Graph() {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>("concept");
  const [seedInput, setSeedInput] = useState("");
  const [seed, setSeed] = useState<{ seed: string; title?: string } | null>(null);
  const [query, setQuery] = useState("");
  const [showTable, setShowTable] = useState(false);

  const concept = useQuery({
    queryKey: ["graph", "concept"],
    queryFn: () => api<GraphData>("/api/graph/concept?summarize=true"),
    enabled: mode === "concept",
    staleTime: 5 * 60_000,
  });
  const citation = useQuery({
    queryKey: ["graph", "citation", seed],
    queryFn: () => {
      const params = new URLSearchParams({ seed: seed!.seed });
      if (seed!.title) params.set("title", seed!.title);
      return api<GraphData>(`/api/graph/citation?${params}`);
    },
    enabled: mode === "citation" && seed !== null,
    retry: false,
  });
  const globalSearch = useMutation({
    mutationFn: (q: string) => api<GlobalAnswer>(`/api/graph/global?query=${encodeURIComponent(q)}`),
  });

  const active = mode === "concept" ? concept : citation;
  const data = mode === "global" ? null : active.data;

  // 引用圖：點節點就以該論文為新種子展開
  const onNodeClick = useCallback((node: GraphNode) => {
    if (mode !== "citation") return;
    setSeedInput(node.label);
    setSeed({ seed: node.id, title: node.label });
  }, [mode]);

  const communityIds = useMemo(
    () => (data ? [...new Set(data.nodes.map((n) => n.community))].sort((a, b) => a - b) : []),
    [data]);

  const submitSeed = (e: FormEvent) => { e.preventDefault(); if (seedInput.trim()) setSeed({ seed: seedInput.trim() }); };
  const submitGlobal = (e: FormEvent) => { e.preventDefault(); if (query.trim()) globalSearch.mutate(query.trim()); };

  return (
    <div className="stack-lg">
      <PageHead title={t("nav.graph")}>{t(`graph.intro.${mode}`)}</PageHead>
      <Tabs<Mode> label={t("nav.graph")} value={mode} onChange={setMode}
                  items={[
                    { key: "concept", label: t("graph.concept") },
                    { key: "citation", label: t("graph.citation") },
                    { key: "global", label: t("graph.global") },
                  ]} />

      {mode === "citation" && (
        <form className="row" onSubmit={submitSeed}>
          <div className="grow">
            <Input icon={Search} value={seedInput} onChange={(e) => setSeedInput(e.target.value)}
                   placeholder={t("graph.seedPlaceholder")} aria-label={t("graph.seedPlaceholder")} maxLength={300} />
          </div>
          <Button type="submit" variant="primary" disabled={!seedInput.trim()} loading={citation.isFetching}>{t("graph.load")}</Button>
        </form>
      )}

      {mode === "global" && (
        <>
          <form className="row" onSubmit={submitGlobal}>
            <div className="grow">
              <Input icon={Search} value={query} onChange={(e) => setQuery(e.target.value)}
                     placeholder={t("graph.globalPlaceholder")} aria-label={t("graph.globalPlaceholder")} maxLength={500} />
            </div>
            <Button type="submit" variant="primary" disabled={!query.trim()} loading={globalSearch.isPending}>{t("graph.ask")}</Button>
          </form>
          {globalSearch.isError && <Notice tone="danger">{t("graph.loadFailed")}</Notice>}
          {!globalSearch.data && !globalSearch.isPending && (
            <div className="panel"><Empty icon={Network} title={t("graph.globalEmpty")}>{t("graph.globalEmptyBody")}</Empty></div>
          )}
          {globalSearch.data && (
            <div className="grid-main">
              <section className="panel">
                <div className="panel-head">
                  <span className="panel-title">{query}</span>
                  <SaveDocumentButton size="sm" title={query} content={globalSearch.data.answer} kind="report" />
                </div>
                <div className="panel-pad"><Markdown>{globalSearch.data.answer}</Markdown></div>
              </section>
              <aside className="stack">
                <span className="t-label">{t("graph.communities")}</span>
                {globalSearch.data.communities.map((c, i) => (
                  <div key={i} className="row" style={{ alignItems: "flex-start" }}>
                    <span style={{ paddingTop: 6 }}><Dot index={i} /></span>
                    <span className="t-meta">{c.summary || c.nodes.slice(0, 5).join("、")}</span>
                  </div>
                ))}
              </aside>
            </div>
          )}
        </>
      )}

      {mode !== "global" && (
        <>
          <div className="row-wrap">
            {communityIds.length > 1 && communityIds.map((c) => (
              <span key={c} className="row t-meta" style={{ gap: 5 }}><Dot index={c} />C{c + 1}</span>
            ))}
            <span className="grow" />
            {mode === "concept" && (
              <Button size="sm" icon={RefreshCw} loading={concept.isFetching} onClick={() => void concept.refetch()}>{t("graph.rebuild")}</Button>
            )}
            {data && data.nodes.length > 0 && (
              <Button size="sm" icon={showTable ? Network : Table2} onClick={() => setShowTable(!showTable)}>
                {showTable ? t("graph.showGraph") : t("graph.showTable")}
              </Button>
            )}
          </div>

          <div className="panel" style={{ overflow: "hidden", minHeight: 320 }}>
            {active.isPending && active.fetchStatus !== "idle" && <div className="empty" style={{ padding: 80 }}><Spinner /></div>}
            {mode === "citation" && seed === null && <Empty icon={Network} title={t("graph.seedTitle")}>{t("graph.seedHint")}</Empty>}
            {active.isError && <div style={{ padding: 16 }}><Notice tone="danger">{t("graph.loadFailed")}</Notice></div>}
            {data && data.nodes.length === 0 && <Empty icon={Network} title={t("graph.emptyConcept")} />}
            {data && data.nodes.length > 0 && !showTable && (
              <ForceGraph nodes={data.nodes} edges={data.edges} onNodeClick={onNodeClick} />
            )}
            {data && data.nodes.length > 0 && showTable && (
              <div className="prose" style={{ maxWidth: "none", padding: 16 }}>
                <table style={{ display: "table", width: "100%" }}>
                  <thead>
                    <tr><th>{t("graph.colLabel")}</th><th>{t("graph.colKind")}</th><th>{t("graph.colCommunity")}</th><th>PageRank</th></tr>
                  </thead>
                  <tbody>
                    {[...data.nodes].sort((a, b) => b.pagerank - a.pagerank).map((n) => (
                      <tr key={n.id}>
                        <td>{n.label}</td><td>{n.kind}</td>
                        <td><span className="row" style={{ gap: 5 }}><Dot index={n.community} />C{n.community + 1}</span></td>
                        <td className="num mono">{n.pagerank}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {mode === "citation" && data?.influential && data.influential.length > 0 && (
            <section className="panel">
              <div className="panel-head"><span className="panel-title">{t("graph.influential")}</span></div>
              <div className="list">
                {data.influential.map((n, i) => (
                  <div key={n.id} className="list-row list-row-click" style={{ alignItems: "baseline" }}
                       onClick={() => { setSeedInput(n.label); setSeed({ seed: n.id, title: n.label }); }}>
                    <span className="mono t-meta num" style={{ width: 20 }}>{i + 1}</span>
                    <span className="grow">{n.label}</span>
                    <span className="mono t-meta num">{n.pagerank}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
          {mode === "concept" && data?.communities && data.communities.length > 0 && (
            <section className="panel">
              <div className="panel-head"><span className="panel-title">{t("graph.communities")}</span></div>
              <div className="list">
                {data.communities.map((c, i) => (
                  <div key={i} className="list-row">
                    <span style={{ paddingTop: 6 }}><Dot index={i} /></span>
                    <div className="grow">
                      <div>{c.summary || t("graph.noSummary")}</div>
                      <div className="t-meta" style={{ marginTop: 2 }}>{c.nodes.slice(0, 8).join(" · ")}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
