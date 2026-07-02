// 趨勢頁：上升關鍵字（斜率排序）、關鍵字時序長條圖與下期預測、
// 熱門關鍵字、資料來源狀態。
import { ActionList, Box, Heading, Label, SegmentedControl, Text } from "@primer/react";
import { FlameIcon, GraphIcon, PlugIcon, TagIcon } from "@primer/octicons-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import { BarChart } from "../components/BarChart";
import { Card, CardState } from "../components/Card";

interface RisingKeyword {
  keyword: string;
  slope: number;
  periods: string[];
  counts: number[];
  forecast: number;
}

interface TrendsResponse {
  rising: RisingKeyword[];
  top: { keyword: string; count: number }[];
  total_papers: number;
}

interface SourceInfo {
  name: string;
  configured: boolean;
  detail: string | null;
}

type Granularity = "month" | "year";

export function Trends() {
  const { t } = useTranslation();
  const [granularity, setGranularity] = useState<Granularity>("month");
  const [picked, setPicked] = useState<string | null>(null);

  const trends = useQuery({
    queryKey: ["trends", "full", granularity],
    queryFn: () => api<TrendsResponse>(`/api/trends?granularity=${granularity}&top=15`),
  });
  const sources = useQuery({
    queryKey: ["sources"],
    queryFn: () => api<{ items: SourceInfo[] }>("/api/sources"),
  });

  const rising = trends.data?.rising ?? [];
  const selected = picked ?? rising[0]?.keyword ?? null;

  const series = useQuery({
    queryKey: ["trend", selected, granularity],
    enabled: selected !== null,
    queryFn: () =>
      api<RisingKeyword>(
        `/api/trends/${encodeURIComponent(selected!)}?granularity=${granularity}`,
      ),
  });

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", mb: 3, gap: 3 }}>
        <Heading as="h2" sx={{ fontSize: 3, flex: 1 }}>
          {t("nav.trends")}
        </Heading>
        <SegmentedControl aria-label={t("trends.granularity")} size="small">
          <SegmentedControl.Button
            selected={granularity === "month"}
            onClick={() => setGranularity("month")}
          >
            {t("trends.granMonth")}
          </SegmentedControl.Button>
          <SegmentedControl.Button
            selected={granularity === "year"}
            onClick={() => setGranularity("year")}
          >
            {t("trends.granYear")}
          </SegmentedControl.Button>
        </SegmentedControl>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: ["1fr", "1fr", "320px 1fr"],
          gap: 3,
          alignItems: "start",
        }}
      >
        <Box sx={{ display: "grid", gap: 3 }}>
          <Card title={t("trends.rising")} icon={FlameIcon}>
            <CardState
              loading={trends.isPending}
              error={trends.isError}
              empty={rising.length === 0}
            />
            {rising.length > 0 && (
              <ActionList sx={{ mx: -2 }}>
                {rising.map((r) => (
                  <ActionList.Item
                    key={r.keyword}
                    active={r.keyword === selected}
                    onSelect={() => setPicked(r.keyword)}
                  >
                    {r.keyword}
                    <ActionList.TrailingVisual>
                      <Text sx={{ fontFamily: "mono", fontSize: 0, color: "success.fg" }}>
                        +{r.slope.toFixed(2)}
                      </Text>
                    </ActionList.TrailingVisual>
                  </ActionList.Item>
                ))}
              </ActionList>
            )}
          </Card>

          <Card title={t("trends.top")} icon={TagIcon}>
            <CardState
              loading={trends.isPending}
              error={trends.isError}
              empty={trends.data?.top.length === 0}
            />
            <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
              {trends.data?.top.map((k) => (
                <Label
                  key={k.keyword}
                  variant={k.keyword === selected ? "accent" : "secondary"}
                  sx={{ cursor: "pointer" }}
                  onClick={() => setPicked(k.keyword)}
                >
                  {k.keyword} · {k.count}
                </Label>
              ))}
            </Box>
          </Card>
        </Box>

        <Box sx={{ display: "grid", gap: 3 }}>
          <Card
            title={selected ? `${t("trends.timeseries")} — ${selected}` : t("trends.timeseries")}
            icon={GraphIcon}
          >
            {selected === null && (
              <Text sx={{ color: "fg.subtle", fontSize: 1 }}>{t("trends.selectHint")}</Text>
            )}
            <CardState
              loading={selected !== null && series.isPending}
              error={series.isError}
              empty={series.data ? series.data.counts.length === 0 : false}
            />
            {series.data && series.data.counts.length > 0 && (
              <Box sx={{ display: "grid", gap: 2 }}>
                <BarChart
                  data={series.data.periods.map((p, i) => ({
                    label: p,
                    value: series.data!.counts[i],
                  }))}
                />
                <Text sx={{ fontSize: 1, color: "fg.muted" }}>
                  {t("trends.forecast", { value: series.data.forecast })}
                </Text>
              </Box>
            )}
          </Card>

          <Card title={t("trends.sources")} icon={PlugIcon}>
            <CardState loading={sources.isPending} error={sources.isError} />
            {sources.data && (
              <Box sx={{ display: "grid", gap: 2 }}>
                {sources.data.items.map((s) => (
                  <Box key={s.name} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <Label variant={s.configured ? "success" : "secondary"}>
                      {s.configured ? t("trends.configured") : t("trends.notConfigured")}
                    </Label>
                    <Text sx={{ fontSize: 1, fontFamily: "mono" }}>{s.name}</Text>
                    {s.detail && (
                      <Text sx={{ fontSize: 0, color: "fg.muted" }}>{s.detail}</Text>
                    )}
                  </Box>
                ))}
              </Box>
            )}
          </Card>
        </Box>
      </Box>
    </Box>
  );
}
