// 分析：自己的研究節奏。焦點是「最近有沒有持續在讀」，其餘是輔助的分佈。
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { BarChart } from "../components/BarChart";
import { api } from "../lib/api";
import { READING_STATES } from "../lib/types";
import { Empty, PageHead, QueryState, Segmented } from "../ui";

interface AnalyticsResponse {
  actions: Record<string, number>;
  reading: Record<string, number>;
  activity: { date: string; count: number }[];
  topics: { keyword: string; count: number }[];
  library: Record<string, number | string | null>;
}

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
  const [days, setDays] = useState<"14" | "30">("14");
  const analytics = useQuery({
    queryKey: ["analytics", days],
    queryFn: () => api<AnalyticsResponse>(`/api/analytics?days=${days}`),
  });
  const data = analytics.data;
  const series = data ? fillDays(data.activity, Number(days)) : [];
  const total = series.reduce((sum, d) => sum + d.value, 0);
  const activeDays = series.filter((d) => d.value > 0).length;
  const readingTotal = data ? READING_STATES.reduce((sum, s) => sum + (data.reading[s] ?? 0), 0) : 0;

  return (
    <div className="stack-lg">
      <PageHead title={t("nav.analytics")}
                actions={<Segmented label={t("analytics.range")} value={days} onChange={setDays}
                                    items={[{ key: "14", label: t("analytics.days", { count: 14 }) },
                                            { key: "30", label: t("analytics.days", { count: 30 }) }]} />}>
        {t("analytics.intro")}
      </PageHead>
      <QueryState loading={analytics.isPending} error={analytics.isError} />
      {data && (
        <>
          <section className="panel panel-pad stack">
            <div className="row" style={{ gap: 40, alignItems: "flex-end" }}>
              <div>
                <div className="t-label">{t("analytics.interactions")}</div>
                <div className="stat-figure">{total}</div>
              </div>
              <div>
                <div className="t-label">{t("analytics.activeDays")}</div>
                <div className="stat-figure">{activeDays}<span className="t-meta" style={{ fontSize: 14, fontFamily: "var(--font-ui)", fontWeight: 400 }}> / {days}</span></div>
              </div>
            </div>
            {total > 0 ? <BarChart data={series} height={180} /> : <Empty title={t("analytics.noActivity")}>{t("analytics.noActivityBody")}</Empty>}
          </section>

          <div className="grid-3">
            <section className="stack">
              <span className="t-label">{t("analytics.reading")}</span>
              {READING_STATES.map((state) => {
                const n = data.reading[state] ?? 0;
                return (
                  <div key={state} className="col" style={{ gap: 4 }}>
                    <div className="spread"><span>{t(`reading.${state}`)}</span><span className="num t-strong">{n}</span></div>
                    <div className="progress"><i style={{ width: `${readingTotal ? (n / readingTotal) * 100 : 0}%` }} /></div>
                  </div>
                );
              })}
            </section>
            <section className="stack">
              <span className="t-label">{t("analytics.actions")}</span>
              {Object.keys(data.actions).length === 0 && <span className="t-meta">{t("analytics.none")}</span>}
              {Object.entries(data.actions).sort((a, b) => b[1] - a[1]).map(([action, n]) => (
                <div key={action} className="spread"><span>{t(`analytics.action.${action}`, { defaultValue: action })}</span><span className="num t-strong">{n}</span></div>
              ))}
            </section>
            <section className="stack">
              <span className="t-label">{t("analytics.topics")}</span>
              {data.topics.length === 0 && <span className="t-meta">{t("analytics.none")}</span>}
              <div className="row-wrap">
                {data.topics.map((k) => (
                  <span key={k.keyword} className="keyword" style={{ cursor: "default" }}>{k.keyword}<span className="num">{k.count}</span></span>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
