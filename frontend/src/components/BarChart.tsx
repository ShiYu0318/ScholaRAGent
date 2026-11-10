// 極簡長條圖（SVG）：單一序列，顏色取自主題的墨色，數值直接標在長條上。
export interface BarDatum {
  label: string;
  value: number;
}

export function BarChart({ data, height = 160, accent }: { data: BarDatum[]; height?: number; accent?: boolean }) {
  if (data.length === 0) return null;
  const step = 34;
  const width = Math.max(data.length * step, 120);
  const chartH = height - 22;
  const max = Math.max(...data.map((d) => d.value), 1);
  const labelEvery = Math.max(1, Math.ceil(data.length / 8));

  return (
    <div style={{ overflowX: "auto" }}>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}
           preserveAspectRatio="xMinYMid meet" role="img"
           aria-label={data.map((d) => `${d.label}: ${d.value}`).join(", ")}>
        {data.map((d, i) => {
          const h = Math.max((d.value / max) * (chartH - 14), d.value > 0 ? 3 : 1);
          const x = i * step + 5;
          return (
            <g key={d.label}>
              <rect x={x} y={chartH - h} width={step - 12} height={h} rx={2}
                    fill={d.value > 0 ? (accent ? "var(--pencil)" : "var(--ink-2)") : "var(--rule-strong)"}>
                <title>{`${d.label}: ${d.value}`}</title>
              </rect>
              <text x={x + (step - 12) / 2} y={chartH - h - 4} textAnchor="middle" fontSize={10}
                    fill="var(--ink-3)" style={{ fontVariantNumeric: "tabular-nums" }}>
                {d.value > 0 ? d.value : ""}
              </text>
              {i % labelEvery === 0 && (
                <text x={x + (step - 12) / 2} y={height - 6} textAnchor="middle" fontSize={10} fill="var(--ink-3)">
                  {d.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
