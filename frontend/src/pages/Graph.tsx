// 圖譜頁：引用網路（seed 展開）、概念圖（社群/摘要）、全域搜尋。
// 圖 + 圖例 + 表格視圖（無障礙替代），hover tooltip 由 ForceGraph 提供。
import {
  Box,
  Button,
  Flash,
  Heading,
  Label,
  SegmentedControl,
  Spinner,
  Text,
  TextInput,
} from "@primer/react";
import { SearchIcon, SyncIcon } from "@primer/octicons-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import {
  communityColor,
  ForceGraph,
  type GraphEdge,
  type GraphNode,
} from "../components/ForceGraph";

type Mode = "citation" | "concept" | "global";

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
    staleTime: 5 * 60 * 1000,
  });

  const citation = useQuery({
    queryKey: ["graph", "citation", seed],
    queryFn: () => {
      const params = new URLSearchParams({ seed: seed!.seed });
      if (seed!.title) params.set("title", seed!.title);
      return api<GraphData>(`/api/graph/citation?${params}`);
    },
    enabled: mode === "citation" && seed !== null,
  });

  const globalSearch = useMutation({
    mutationFn: (q: string) =>
      api<GlobalAnswer>(`/api/graph/global?query=${encodeURIComponent(q)}`),
  });

  const active = mode === "concept" ? concept : citation;
  const data = mode === "global" ? null : active.data;

  // 引用圖點節點 = 以該論文為新種子展開（標題檢索 fallback）
  const onNodeClick = useCallback(
    (node: GraphNode) => {
      if (mode !== "citation") return;
      setSeedInput(node.label);
      setSeed({ seed: node.id, title: node.label });
    },
    [mode],
  );

  const communityIds = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.nodes.map((n) => n.community))].sort((a, b) => a - b);
  }, [data]);

  return (
    <Box>
      <Box display="flex" sx={{ gap: 3, alignItems: "center", mb: 3, flexWrap: "wrap" }}>
        <Heading as="h2" sx={{ fontSize: 3, flex: 1 }}>
          {t("nav.graph")}
        </Heading>
        <SegmentedControl aria-label="graph mode" onChange={(i) => setMode(["citation", "concept", "global"][i] as Mode)}>
          <SegmentedControl.Button selected={mode === "citation"}>
            {t("graph.citation")}
          </SegmentedControl.Button>
          <SegmentedControl.Button selected={mode === "concept"}>
            {t("graph.concept")}
          </SegmentedControl.Button>
          <SegmentedControl.Button selected={mode === "global"}>
            {t("graph.global")}
          </SegmentedControl.Button>
        </SegmentedControl>
      </Box>

      {mode === "citation" && (
        <Box display="flex" sx={{ gap: 2, mb: 3 }}>
          <TextInput
            block
            leadingVisual={SearchIcon}
            placeholder={t("graph.seedPlaceholder")}
            value={seedInput}
            onChange={(e) => setSeedInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && seedInput.trim()) {
                setSeed({ seed: seedInput.trim() });
              }
            }}
          />
          <Button
            variant="primary"
            disabled={!seedInput.trim()}
            onClick={() => setSeed({ seed: seedInput.trim() })}
          >
            {t("graph.load")}
          </Button>
        </Box>
      )}

      {mode === "global" && (
        <Box display="flex" sx={{ gap: 2, mb: 3 }}>
          <TextInput
            block
            leadingVisual={SearchIcon}
            placeholder={t("graph.globalPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && query.trim()) globalSearch.mutate(query.trim());
            }}
          />
          <Button
            variant="primary"
            disabled={!query.trim() || globalSearch.isPending}
            onClick={() => globalSearch.mutate(query.trim())}
          >
            {t("graph.ask")}
          </Button>
        </Box>
      )}

      {mode !== "global" && (
        <>
          <Box display="flex" sx={{ gap: 2, mb: 2, alignItems: "center", flexWrap: "wrap" }}>
            {communityIds.length > 1 &&
              communityIds.map((c) => (
                <Box key={c} display="flex" sx={{ gap: 1, alignItems: "center" }}>
                  <Box
                    sx={{
                      width: 10, height: 10, borderRadius: "50%",
                      bg: communityColor(c),
                    }}
                  />
                  <Text sx={{ fontSize: 0, color: "fg.muted" }}>C{c + 1}</Text>
                </Box>
              ))}
            <Box flex={1} />
            {mode === "concept" && (
              <Button
                size="small"
                leadingVisual={SyncIcon}
                onClick={() => void concept.refetch()}
              >
                {t("graph.rebuild")}
              </Button>
            )}
            <Button size="small" onClick={() => setShowTable(!showTable)}>
              {showTable ? t("graph.showGraph") : t("graph.showTable")}
            </Button>
          </Box>

          <Box
            sx={{
              border: "1px solid", borderColor: "border.default", borderRadius: 2,
              bg: "canvas.default", overflow: "hidden", minHeight: 300,
            }}
          >
            {active.isPending && mode === "concept" && (
              <Box display="flex" justifyContent="center" p={6}>
                <Spinner />
              </Box>
            )}
            {mode === "citation" && seed === null && (
              <Box p={5} textAlign="center">
                <Text sx={{ color: "fg.muted" }}>{t("graph.seedHint")}</Text>
              </Box>
            )}
            {active.isError && (
              <Box p={4}>
                <Flash variant="danger">{t("graph.loadFailed")}</Flash>
              </Box>
            )}
            {data && data.nodes.length === 0 && (
              <Box p={5} textAlign="center">
                <Text sx={{ color: "fg.muted" }}>{t("graph.emptyConcept")}</Text>
              </Box>
            )}
            {data && data.nodes.length > 0 && !showTable && (
              <ForceGraph nodes={data.nodes} edges={data.edges} onNodeClick={onNodeClick} />
            )}
            {data && data.nodes.length > 0 && showTable && (
              <Box as="table" sx={{ width: "100%", fontSize: 1, borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[t("graph.colLabel"), "kind", "community", "pagerank"].map((h) => (
                      <Box
                        as="th" key={h}
                        sx={{ textAlign: "left", p: 2, borderBottom: "1px solid", borderColor: "border.default", color: "fg.muted" }}
                      >
                        {h}
                      </Box>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...data.nodes]
                    .sort((a, b) => b.pagerank - a.pagerank)
                    .map((n) => (
                      <tr key={n.id}>
                        <Box as="td" sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.muted" }}>{n.label}</Box>
                        <Box as="td" sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.muted" }}>{n.kind}</Box>
                        <Box as="td" sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.muted" }}>C{n.community + 1}</Box>
                        <Box as="td" sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.muted", fontFamily: "mono" }}>{n.pagerank}</Box>
                      </tr>
                    ))}
                </tbody>
              </Box>
            )}
          </Box>

          <Box display="grid" sx={{ gridTemplateColumns: "1fr 1fr", gap: 3, mt: 3 }}>
            {mode === "citation" && data?.influential && data.influential.length > 0 && (
              <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2, p: 3 }}>
                <Heading as="h3" sx={{ fontSize: 1, mb: 2 }}>
                  {t("graph.influential")}
                </Heading>
                {data.influential.map((n, i) => (
                  <Box key={n.id} display="flex" sx={{ gap: 2, mb: 1, alignItems: "baseline" }}>
                    <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.subtle" }}>{i + 1}.</Text>
                    <Text sx={{ fontSize: 1, flex: 1 }}>{n.label}</Text>
                    <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted" }}>{n.pagerank}</Text>
                  </Box>
                ))}
              </Box>
            )}
            {mode === "concept" && data?.communities && data.communities.length > 0 && (
              <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2, p: 3, gridColumn: "1 / -1" }}>
                <Heading as="h3" sx={{ fontSize: 1, mb: 2 }}>
                  {t("graph.communities")}
                </Heading>
                {data.communities.map((c, i) => (
                  <Box key={i} display="flex" sx={{ gap: 2, mb: 2, alignItems: "flex-start" }}>
                    <Box sx={{ width: 10, height: 10, borderRadius: "50%", bg: communityColor(i), mt: 1, flexShrink: 0 }} />
                    <Box>
                      <Text sx={{ fontSize: 1 }}>{c.summary || t("common.empty")}</Text>
                      <Box display="flex" flexWrap="wrap" sx={{ gap: 1, mt: 1 }}>
                        {c.nodes.slice(0, 8).map((n) => (
                          <Label key={n}>{n}</Label>
                        ))}
                      </Box>
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </>
      )}

      {mode === "global" && (
        <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2, p: 4, minHeight: 200 }}>
          {globalSearch.isPending && (
            <Box display="flex" justifyContent="center" p={4}>
              <Spinner />
            </Box>
          )}
          {globalSearch.isError && <Flash variant="danger">{t("graph.loadFailed")}</Flash>}
          {globalSearch.data && (
            <Text sx={{ whiteSpace: "pre-wrap", fontSize: 1 }}>{globalSearch.data.answer}</Text>
          )}
          {!globalSearch.data && !globalSearch.isPending && (
            <Text sx={{ color: "fg.muted" }}>{t("graph.globalHint")}</Text>
          )}
        </Box>
      )}
    </Box>
  );
}
