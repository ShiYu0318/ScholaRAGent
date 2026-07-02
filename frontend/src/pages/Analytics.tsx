// 分析頁：近期活動長條圖、互動行為統計、閱讀看板管線、熱門主題、文庫總量。
import { Box, Heading, Label, SegmentedControl, Text } from "@primer/react";
import { BookIcon, DatabaseIcon, PulseIcon, TagIcon, ThumbsupIcon } from "@primer/octicons-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import { BarChart } from "../components/BarChart";
import { Card, CardState } from "../components/Card";

interface AnalyticsResponse {
  actions: Record<string, number>;
  reading: Record<string, number>;
  activity: { date: string; count: number }[];
  topics: { keyword: string; count: number }[];
  library: Record<string, number | string | null>;
}

const READING_STATES = ["to-read", "reading", "done"] as const;

function fillDays(activity: { date: string; count: number }[], days: number) {
  const byDate = new Map(activity.map((a) => [a.date, a.count]));
  const out = [];
  const today = new Date();
  for (let i = days - 1; i >= 0; i -= 1) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    out.push({ label: iso.slice(5), value: byDate.get(iso) ?? 0 });
  }
  return out;
}

export function Analytics() {
  const { t } = useTranslation();
  const [days, setDays] = useState(14);
  const analytics = useQuery({
    queryKey: ["analytics", "full", days],
    queryFn: () => api<AnalyticsResponse>(`/api/analytics?days=${days}`),
  });
  const data = analytics.data;

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", mb: 3, gap: 3 }}>
        <Heading as="h2" sx={{ fontSize: 3, flex: 1 }}>
          {t("nav.analytics")}
        </Heading>
        <SegmentedControl aria-label={t("analytics.range")} size="small">
          {[14, 30].map((d) => (
            <SegmentedControl.Button key={d} selected={days === d} onClick={() => setDays(d)}>
              {t("analytics.days", { count: d })}
            </SegmentedControl.Button>
          ))}
        </SegmentedControl>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
          gap: 3,
        }}
      >
        <Box sx={{ gridColumn: ["auto", "auto", "1 / -1"] }}>
          <Card title={t("analytics.activity", { days })} icon={PulseIcon}>
            <CardState loading={analytics.isPending} error={analytics.isError} />
            {data && <BarChart data={fillDays(data.activity, days)} height={180} />}
          </Card>
        </Box>

        <Card title={t("analytics.actions")} icon={ThumbsupIcon}>
          <CardState
            loading={analytics.isPending}
            error={analytics.isError}
            empty={data ? Object.keys(data.actions).length === 0 : false}
          />
          {data && (
            <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
              {Object.entries(data.actions).map(([action, n]) => (
                <Label key={action} variant="accent">
                  {action}: {n}
                </Label>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("analytics.readingPipeline")} icon={BookIcon}>
          <CardState loading={analytics.isPending} error={analytics.isError} />
          {data && (
            <Box sx={{ display: "grid", gap: 2 }}>
              {READING_STATES.map((state) => (
                <Box key={state} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                  <Text sx={{ fontSize: 1, flex: 1 }}>{t(`library.state.${state}`)}</Text>
                  <Text sx={{ fontFamily: "mono", fontSize: 1 }}>
                    {data.reading[state] ?? 0}
                  </Text>
                </Box>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("analytics.topics")} icon={TagIcon}>
          <CardState
            loading={analytics.isPending}
            error={analytics.isError}
            empty={data?.topics.length === 0}
          />
          {data && data.topics.length > 0 && (
            <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
              {data.topics.map((k) => (
                <Label key={k.keyword} variant="secondary">
                  {k.keyword} · {k.count}
                </Label>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("analytics.library")} icon={DatabaseIcon}>
          <CardState loading={analytics.isPending} error={analytics.isError} />
          {data && (
            <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
              {Object.entries(data.library)
                .filter(([, v]) => typeof v === "number")
                .map(([k, v]) => (
                  <Text key={k} sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted" }}>
                    {k}={String(v)}
                  </Text>
                ))}
            </Box>
          )}
        </Card>
      </Box>
    </Box>
  );
}
