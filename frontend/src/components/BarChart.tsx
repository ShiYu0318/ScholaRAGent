// 輕量長條圖：純 SVG，night 主題配色，hover 顯示數值（<title>）。
// 給 Trends 時序與 Analytics 活動圖共用，避免為簡單圖表引入繪圖庫。
import { Box } from "@primer/react";

export interface BarDatum {
  label: string;
  value: number;
}

interface BarChartProps {
  data: BarDatum[];
  height?: number;
  color?: string;
}

export function BarChart({ data, height = 160, color = "#2f81f7" }: BarChartProps) {
  if (data.length === 0) return null;
  const step = 34;
  const width = Math.max(data.length * step, 120);
  const chartH = height - 22;
  const max = Math.max(...data.map((d) => d.value), 1);
  const labelEvery = Math.max(1, Math.ceil(data.length / 8));

  return (
    <Box sx={{ overflowX: "auto" }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMinYMid meet"
        role="img"
      >
        {data.map((d, i) => {
          const h = Math.max((d.value / max) * (chartH - 14), d.value > 0 ? 3 : 1);
          const x = i * step + 5;
          return (
            <g key={d.label}>
              <rect
                x={x}
                y={chartH - h}
                width={step - 12}
                height={h}
                rx={2}
                fill={d.value > 0 ? color : "#30363d"}
              >
                <title>{`${d.label}: ${d.value}`}</title>
              </rect>
              <text
                x={x + (step - 12) / 2}
                y={chartH - h - 4}
                textAnchor="middle"
                fontSize={10}
                fill="#8b949e"
              >
                {d.value > 0 ? d.value : ""}
              </text>
              {i % labelEvery === 0 && (
                <text
                  x={x + (step - 12) / 2}
                  y={height - 6}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#8b949e"
                >
                  {d.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </Box>
  );
}
