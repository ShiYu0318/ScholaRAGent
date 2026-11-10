// D3 力導向網路圖：拖拉節點、滾輪縮放、hover tooltip、點擊回呼。
// 節點大小 = PageRank（sqrt 比例）；顏色 = 社群（固定順序的類別色盤）。
// 超過六個社群折進灰色；只有 PageRank 前 8 名畫直接標籤（選擇性標籤原則）。
import * as d3 from "d3";
import { useEffect, useRef } from "react";

export interface GraphNode {
  id: string;
  label: string;
  kind: string;
  year?: number | null;
  cited_by_count?: number | null;
  pagerank: number;
  community: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

// 低彩度的六色：在稿紙色與深色底上都讀得清楚，第一色是紅筆（強調色）
export const COMMUNITY_PALETTE = [
  "#b4472f", "#2f7391", "#7462ad", "#3f7a4d", "#b07a1c", "#a34d80",
];
const OTHER_COLOR = "#8a8275";

export function communityColor(index: number): string {
  return index < COMMUNITY_PALETTE.length ? COMMUNITY_PALETTE[index] : OTHER_COLOR;
}

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
}

type SimNode = GraphNode & d3.SimulationNodeDatum;
type SimLink = d3.SimulationLinkDatum<SimNode> & { relation: string };

export function ForceGraph({ nodes, edges, height = 560, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = "";
    if (nodes.length === 0) return;

    const width = container.clientWidth || 900;
    const simNodes: SimNode[] = nodes.map((n) => ({ ...n }));
    const simLinks: SimLink[] = edges.map((e) => ({ ...e }));

    const maxPr = Math.max(...nodes.map((n) => n.pagerank), 1e-9);
    const radius = (n: SimNode) => 5 + 14 * Math.sqrt(n.pagerank / maxPr);
    const labelled = new Set(
      [...simNodes].sort((a, b) => b.pagerank - a.pagerank).slice(0, 8).map((n) => n.id),
    );

    const svg = d3
      .select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .style("cursor", "grab");

    const root = svg.append("g");

    const tooltip = d3
      .select(container)
      .append("div")
      .style("position", "absolute")
      .style("pointer-events", "none")
      .style("background", "var(--paper-float)")
      .style("box-shadow", "var(--float-shadow)")
      .style("border-radius", "6px")
      .style("padding", "6px 10px")
      .style("font-size", "12px")
      .style("color", "var(--ink)")
      .style("max-width", "320px")
      .style("display", "none")
      .style("z-index", "10");

    const link = root
      .append("g")
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .style("stroke", "var(--rule-strong)")
      .attr("stroke-width", 1.2)
      .attr("stroke-opacity", 0.9);

    const node = root
      .append("g")
      .selectAll<SVGCircleElement, SimNode>("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", radius)
      .attr("fill", (n) => communityColor(n.community))
      // seed 節點以 2px 表面色外環強調（mark spec 的 surface ring）
      .style("stroke", (n) => (n.kind === "seed" ? "var(--ink)" : "var(--paper-raised)"))
      .attr("stroke-width", 2)
      .style("cursor", "pointer");

    const label = root
      .append("g")
      .selectAll("text")
      .data(simNodes.filter((n) => labelled.has(n.id)))
      .join("text")
      .text((n) => (n.label.length > 28 ? `${n.label.slice(0, 28)}…` : n.label))
      .attr("font-size", 11)
      .style("fill", "var(--ink-2)")
      .attr("pointer-events", "none");

    node
      .on("mouseover", (event: MouseEvent, n: SimNode) => {
        const parts = [
          `<strong>${n.label}</strong>`,
          `kind: ${n.kind} · community: C${n.community + 1}`,
        ];
        if (n.year) parts.push(`year: ${n.year}`);
        if (n.cited_by_count != null) parts.push(`cited by: ${n.cited_by_count}`);
        parts.push(`pagerank: ${n.pagerank}`);
        tooltip.html(parts.join("<br/>")).style("display", "block");
        const rect = container.getBoundingClientRect();
        tooltip
          .style("left", `${event.clientX - rect.left + 12}px`)
          .style("top", `${event.clientY - rect.top + 12}px`);
      })
      .on("mousemove", (event: MouseEvent) => {
        const rect = container.getBoundingClientRect();
        tooltip
          .style("left", `${event.clientX - rect.left + 12}px`)
          .style("top", `${event.clientY - rect.top + 12}px`);
      })
      .on("mouseout", () => tooltip.style("display", "none"))
      .on("click", (_event: MouseEvent, n: SimNode) => onNodeClick?.(n));

    const sim = d3
      .forceSimulation(simNodes)
      .force("link", d3.forceLink<SimNode, SimLink>(simLinks).id((n) => n.id).distance(95))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide<SimNode>().radius((n) => radius(n) + 4))
      .on("tick", () => {
        link
          .attr("x1", (l) => (l.source as SimNode).x!)
          .attr("y1", (l) => (l.source as SimNode).y!)
          .attr("x2", (l) => (l.target as SimNode).x!)
          .attr("y2", (l) => (l.target as SimNode).y!);
        node.attr("cx", (n) => n.x!).attr("cy", (n) => n.y!);
        label.attr("x", (n) => n.x! + radius(n) + 4).attr("y", (n) => n.y! + 4);
      });

    node.call(
      d3
        .drag<SVGCircleElement, SimNode>()
        .on("start", (event, n) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          n.fx = n.x;
          n.fy = n.y;
        })
        .on("drag", (event, n) => {
          n.fx = event.x;
          n.fy = event.y;
        })
        .on("end", (event, n) => {
          if (!event.active) sim.alphaTarget(0);
          n.fx = null;
          n.fy = null;
        }),
    );

    svg.call(
      d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.25, 4])
        .on("zoom", (event) => root.attr("transform", event.transform)),
    );

    return () => {
      sim.stop();
      container.innerHTML = "";
    };
  }, [nodes, edges, height, onNodeClick]);

  return <div ref={containerRef} style={{ position: "relative", width: "100%" }} />;
}
