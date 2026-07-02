// 首頁總覽卡片牆：今日/週報、趨勢、待讀、近期對話、分析、健康狀態。
// 各卡片對應的端點分階段上線；尚未提供的顯示「尚未啟用」。
import { Box, Heading, Label, Text } from "@primer/react";
import {
  BookIcon,
  CalendarIcon,
  CommentDiscussionIcon,
  FlameIcon,
  GraphIcon,
  PulseIcon,
  ServerIcon,
} from "@primer/octicons-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { Card, CardState } from "../components/Card";

interface Paper {
  id: string;
  title: string;
  link?: string;
  published?: string;
  summary?: string | null;
}

interface HealthInfo {
  status: string;
  store: Record<string, number | string | null>;
}

function useCardQuery<T>(key: string[], path: string) {
  return useQuery({ queryKey: key, queryFn: () => api<T>(path) });
}

export function Home() {
  const { t } = useTranslation();
  const papers = useCardQuery<{ items: Paper[]; total: number }>(
    ["papers", "recent"], "/api/papers?limit=5",
  );
  const weekly = useCardQuery<{ summary: string }>(["digest", "weekly"], "/api/digest/weekly");
  const trends = useCardQuery<{ items: { term: string; count: number }[] }>(
    ["trends"], "/api/trends?limit=6",
  );
  const reading = useCardQuery<{ items: { id: string; title: string }[] }>(
    ["reading", "to-read"], "/api/reading?state=to-read",
  );
  const conversations = useCardQuery<{ items: { id: number; title: string }[] }>(
    ["conversations", "recent"], "/api/conversations?limit=5",
  );
  const analytics = useCardQuery<{ actions: Record<string, number> }>(
    ["analytics"], "/api/analytics",
  );
  const health = useCardQuery<HealthInfo>(["health"], "/api/health");

  return (
    <Box>
      <Heading as="h2" sx={{ fontSize: 3, mb: 3 }}>
        {t("home.title")}
      </Heading>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
          gap: 3,
        }}
      >
        <Card title={t("home.todayDigest")} icon={CalendarIcon}>
          <CardState
            loading={papers.isPending}
            error={papers.isError}
            empty={papers.data?.items.length === 0}
          />
          {papers.data && papers.data.items.length > 0 && (
            <Box display="grid" sx={{ gap: 2 }}>
              <Text sx={{ color: "fg.muted", fontSize: 0 }}>
                {t("home.papersInLibrary", { count: papers.data.total })}
              </Text>
              {papers.data.items.map((p) => (
                <Text key={p.id} sx={{ fontSize: 1 }} className="truncate">
                  <a href={p.link} target="_blank" rel="noreferrer">
                    {p.title}
                  </a>
                </Text>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("home.weeklyDigest")} icon={GraphIcon}>
          <CardState loading={weekly.isPending} error={weekly.isError} />
          {weekly.data && (
            <Text sx={{ fontSize: 1, whiteSpace: "pre-wrap" }}>
              {weekly.data.summary.slice(0, 400)}
            </Text>
          )}
        </Card>

        <Card title={t("home.trends")} icon={FlameIcon}>
          <CardState
            loading={trends.isPending}
            error={trends.isError}
            empty={trends.data?.items.length === 0}
          />
          {trends.data && trends.data.items.length > 0 && (
            <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
              {trends.data.items.map((it) => (
                <Label key={it.term} variant="accent">
                  {it.term} · {it.count}
                </Label>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("home.toRead")} icon={BookIcon}>
          <CardState
            loading={reading.isPending}
            error={reading.isError}
            empty={reading.data?.items.length === 0}
          />
          {reading.data && reading.data.items.length > 0 && (
            <Box display="grid" sx={{ gap: 2 }}>
              {reading.data.items.slice(0, 5).map((it) => (
                <Text key={it.id} sx={{ fontSize: 1 }}>
                  {it.title}
                </Text>
              ))}
            </Box>
          )}
        </Card>

        <Card
          title={t("home.recentConversations")}
          icon={CommentDiscussionIcon}
          action={
            <Link to="/conversations" style={{ fontSize: 12 }}>
              {t("common.viewAll")}
            </Link>
          }
        >
          <CardState
            loading={conversations.isPending}
            error={conversations.isError}
            empty={conversations.data?.items.length === 0}
          />
          {conversations.data && conversations.data.items.length > 0 && (
            <Box display="grid" sx={{ gap: 2 }}>
              {conversations.data.items.map((c) => (
                <Text key={c.id} sx={{ fontSize: 1 }}>
                  {c.title || `#${c.id}`}
                </Text>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("home.analytics")} icon={PulseIcon}>
          <CardState
            loading={analytics.isPending}
            error={analytics.isError}
            empty={analytics.data ? Object.keys(analytics.data.actions).length === 0 : false}
          />
          {analytics.data && Object.keys(analytics.data.actions).length > 0 && (
            <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
              {Object.entries(analytics.data.actions).map(([action, n]) => (
                <Label key={action}>
                  {action}: {n}
                </Label>
              ))}
            </Box>
          )}
        </Card>

        <Card title={t("home.health")} icon={ServerIcon}>
          <CardState loading={health.isPending} error={health.isError} />
          {health.data && (
            <Box display="grid" sx={{ gap: 2 }}>
              <Box display="flex" sx={{ gap: 2, alignItems: "center" }}>
                <Label variant={health.data.status === "ok" ? "success" : "danger"}>
                  {health.data.status}
                </Label>
                <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted" }}>
                  {String(health.data.store.backend ?? "")}
                </Text>
              </Box>
              <Box display="flex" flexWrap="wrap" sx={{ gap: 2 }}>
                {Object.entries(health.data.store)
                  .filter(([k, v]) => k !== "backend" && v !== null)
                  .map(([k, v]) => (
                    <Text key={k} sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted" }}>
                      {k}={String(v)}
                    </Text>
                  ))}
              </Box>
            </Box>
          )}
        </Card>
      </Box>
    </Box>
  );
}
