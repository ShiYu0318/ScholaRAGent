// 文庫頁：論文清單（搜尋/來源/個人化/抓取/匯出）、閱讀看板（拖拉）、RSS feeds。
import {
  ActionMenu,
  ActionList,
  Box,
  Button,
  Flash,
  Heading,
  IconButton,
  Label,
  SegmentedControl,
  Spinner,
  Text,
  TextInput,
  ToggleSwitch,
} from "@primer/react";
import {
  CodeIcon,
  DownloadIcon,
  HeartIcon,
  PlusIcon,
  SearchIcon,
  SyncIcon,
  TrashIcon,
} from "@primer/octicons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import { CardState } from "../components/Card";

interface Paper {
  id: string;
  title: string;
  link: string;
  published: string;
  source: string;
  reproducibility?: { has_code: boolean };
}

interface ReadingItem {
  id: string;
  title: string;
  state: "to-read" | "reading" | "done";
}

interface Feed {
  id: number;
  url: string;
  title: string | null;
  enabled: boolean;
}

type View = "papers" | "kanban" | "feeds";
const STATES: ReadingItem["state"][] = ["to-read", "reading", "done"];

async function download(path: string, filename: string) {
  const resp = await fetch(path, {
    headers: { Authorization: `Bearer ${localStorage.getItem("ragency.token") ?? ""}` },
  });
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function Library() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>("papers");
  const [query, setQuery] = useState("");
  const [personalized, setPersonalized] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const invalidate = (key: string) => void queryClient.invalidateQueries({ queryKey: [key] });

  // ---- 論文 ----
  const papers = useQuery({
    queryKey: ["papers", query],
    queryFn: () =>
      api<{ items: Paper[]; total: number }>(
        `/api/papers?limit=100${query ? `&query=${encodeURIComponent(query)}` : ""}`,
      ),
    enabled: view === "papers" && !personalized,
  });
  const recommended = useQuery({
    queryKey: ["personalized"],
    queryFn: () => api<{ items: Paper[] }>("/api/daily/personalized?top_n=10"),
    enabled: view === "papers" && personalized,
  });

  const fetchDaily = useMutation({
    mutationFn: () => api<{ fetched: number; added: number }>("/api/daily", { method: "POST", body: {} }),
    onSuccess: (d) => {
      setFlash(t("library.fetched", { fetched: d.fetched, added: d.added }));
      invalidate("papers");
    },
  });

  const like = useMutation({
    mutationFn: (paperId: string) =>
      api("/api/interactions", { method: "POST", body: { action: "like", paper_id: paperId } }),
  });

  const addToKanban = useMutation({
    mutationFn: (p: Paper) =>
      api("/api/reading", { method: "POST", body: { paper_id: p.id, title: p.title } }),
    onSuccess: () => {
      setFlash(t("library.addedToKanban"));
      invalidate("reading");
    },
  });

  // ---- 看板 ----
  const reading = useQuery({
    queryKey: ["reading"],
    queryFn: () => api<{ items: ReadingItem[] }>("/api/reading"),
    enabled: view === "kanban",
  });

  const moveCard = useMutation({
    mutationFn: ({ id, state }: { id: string; state: string }) =>
      api(`/api/reading/${id}`, { method: "PATCH", body: { state } }),
    onSuccess: () => invalidate("reading"),
  });

  const removeCard = useMutation({
    mutationFn: (id: string) => api(`/api/reading/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate("reading"),
  });

  // ---- Feeds ----
  const feeds = useQuery({
    queryKey: ["feeds"],
    queryFn: () => api<{ items: Feed[] }>("/api/feeds"),
    enabled: view === "feeds",
  });
  const [feedUrl, setFeedUrl] = useState("");

  const addFeed = useMutation({
    mutationFn: (url: string) => api("/api/feeds", { method: "POST", body: { url } }),
    onSuccess: () => {
      setFeedUrl("");
      invalidate("feeds");
    },
    onError: (e) => setFlash(e.message),
  });
  const toggleFeed = useMutation({
    mutationFn: (f: Feed) =>
      api(`/api/feeds/${f.id}`, { method: "PATCH", body: { enabled: !f.enabled } }),
    onSuccess: () => invalidate("feeds"),
  });
  const deleteFeed = useMutation({
    mutationFn: (id: number) => api(`/api/feeds/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidate("feeds"),
  });
  const refreshFeeds = useMutation({
    mutationFn: () => api<{ feeds: number; fetched: number; added: number }>("/api/feeds/refresh", { method: "POST" }),
    onSuccess: (d) => {
      setFlash(t("library.feedsRefreshed", { fetched: d.fetched, added: d.added }));
      invalidate("papers");
    },
  });

  const onDrop = (state: ReadingItem["state"]) => (e: DragEvent) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/paper-id");
    if (id) moveCard.mutate({ id, state });
  };

  const paperList = personalized ? recommended.data?.items : papers.data?.items;
  const activePapersQuery = personalized ? recommended : papers;

  return (
    <Box>
      <Box display="flex" sx={{ gap: 3, alignItems: "center", mb: 3, flexWrap: "wrap" }}>
        <Heading as="h2" sx={{ fontSize: 3, flex: 1 }}>
          {t("nav.library")}
        </Heading>
        <SegmentedControl aria-label="library view"
                          onChange={(i) => setView(["papers", "kanban", "feeds"][i] as View)}>
          <SegmentedControl.Button selected={view === "papers"}>{t("library.papers")}</SegmentedControl.Button>
          <SegmentedControl.Button selected={view === "kanban"}>{t("library.kanban")}</SegmentedControl.Button>
          <SegmentedControl.Button selected={view === "feeds"}>{t("library.feeds")}</SegmentedControl.Button>
        </SegmentedControl>
      </Box>

      {flash && (
        <Flash sx={{ mb: 3 }} onClick={() => setFlash(null)}>
          {flash}
        </Flash>
      )}

      {view === "papers" && (
        <>
          <Box display="flex" sx={{ gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
            <Box flex={1} minWidth={240}>
              <TextInput
                block
                leadingVisual={SearchIcon}
                placeholder={t("library.searchPlaceholder")}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </Box>
            <Button
              variant={personalized ? "primary" : "default"}
              onClick={() => setPersonalized(!personalized)}
            >
              {t("library.forYou")}
            </Button>
            <Button
              leadingVisual={SyncIcon}
              disabled={fetchDaily.isPending}
              onClick={() => fetchDaily.mutate()}
            >
              {t("library.fetchToday")}
            </Button>
            <ActionMenu>
              <ActionMenu.Button leadingVisual={DownloadIcon}>
                {t("library.export")}
              </ActionMenu.Button>
              <ActionMenu.Overlay>
                <ActionList>
                  <ActionList.Item onSelect={() => void download("/api/export/csv", "papers.csv")}>
                    CSV
                  </ActionList.Item>
                  <ActionList.Item onSelect={() => void download("/api/export/bibtex", "papers.bib")}>
                    BibTeX
                  </ActionList.Item>
                  <ActionList.Item onSelect={() => void download("/api/export/obsidian", "obsidian-vault.zip")}>
                    Obsidian
                  </ActionList.Item>
                </ActionList>
              </ActionMenu.Overlay>
            </ActionMenu>
          </Box>

          <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2 }}>
            <CardState
              loading={activePapersQuery.isPending}
              error={activePapersQuery.isError}
              empty={paperList?.length === 0}
            />
            {(paperList ?? []).map((p) => (
              <Box
                key={p.id}
                sx={{
                  display: "flex", alignItems: "center", gap: 2, px: 3, py: 2,
                  borderBottom: "1px solid", borderColor: "border.muted",
                  ":last-child": { borderBottom: 0 },
                }}
              >
                <Box flex={1} minWidth={0}>
                  <a href={p.link} target="_blank" rel="noreferrer">
                    <Text sx={{ fontSize: 1 }}>{p.title}</Text>
                  </a>
                  <Box display="flex" sx={{ gap: 2, mt: 1, alignItems: "center" }}>
                    <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.subtle" }}>
                      {p.id} · {p.published?.slice(0, 10)}
                    </Text>
                    <Label size="small">{p.source}</Label>
                    {p.reproducibility?.has_code && (
                      <Label size="small" variant="success">
                        <CodeIcon size={12} /> code
                      </Label>
                    )}
                  </Box>
                </Box>
                <IconButton
                  aria-label={t("library.like")}
                  icon={HeartIcon}
                  size="small"
                  variant="invisible"
                  onClick={() => like.mutate(p.id)}
                />
                <IconButton
                  aria-label={t("library.addToKanban")}
                  icon={PlusIcon}
                  size="small"
                  variant="invisible"
                  onClick={() => addToKanban.mutate(p)}
                />
              </Box>
            ))}
          </Box>
        </>
      )}

      {view === "kanban" && (
        <Box display="grid" sx={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 3 }}>
          {STATES.map((state) => (
            <Box
              key={state}
              onDragOver={(e: DragEvent) => e.preventDefault()}
              onDrop={onDrop(state)}
              sx={{
                border: "1px solid", borderColor: "border.default", borderRadius: 2,
                bg: "canvas.subtle", minHeight: 320, display: "flex", flexDirection: "column",
              }}
            >
              <Box sx={{ px: 3, py: 2, borderBottom: "1px solid", borderColor: "border.muted" }}>
                <Text sx={{ fontSize: 1, fontWeight: "bold" }}>
                  {t(`library.state.${state}`)}
                </Text>
                <Text sx={{ fontSize: 0, color: "fg.muted", ml: 2 }}>
                  {reading.data?.items.filter((i) => i.state === state).length ?? 0}
                </Text>
              </Box>
              <Box p={2} flex={1}>
                {reading.isPending && (
                  <Box display="flex" justifyContent="center" p={3}>
                    <Spinner size="small" />
                  </Box>
                )}
                {(reading.data?.items ?? [])
                  .filter((i) => i.state === state)
                  .map((item) => (
                    <Box
                      key={item.id}
                      draggable
                      onDragStart={(e: DragEvent) =>
                        e.dataTransfer.setData("text/paper-id", item.id)
                      }
                      sx={{
                        border: "1px solid", borderColor: "border.default", borderRadius: 2,
                        bg: "canvas.default", p: 2, mb: 2, cursor: "grab",
                        display: "flex", alignItems: "flex-start", gap: 2,
                      }}
                    >
                      <Text sx={{ fontSize: 1, flex: 1 }}>{item.title}</Text>
                      <IconButton
                        aria-label={t("common.delete")}
                        icon={TrashIcon}
                        size="small"
                        variant="invisible"
                        onClick={() => removeCard.mutate(item.id)}
                      />
                    </Box>
                  ))}
              </Box>
            </Box>
          ))}
        </Box>
      )}

      {view === "feeds" && (
        <Box>
          <Box display="flex" sx={{ gap: 2, mb: 3 }}>
            <TextInput
              block
              placeholder="https://example.com/feed.xml"
              value={feedUrl}
              onChange={(e) => setFeedUrl(e.target.value)}
            />
            <Button
              variant="primary"
              leadingVisual={PlusIcon}
              disabled={!feedUrl.trim() || addFeed.isPending}
              onClick={() => addFeed.mutate(feedUrl.trim())}
            >
              {t("library.addFeed")}
            </Button>
            <Button
              leadingVisual={SyncIcon}
              disabled={refreshFeeds.isPending}
              onClick={() => refreshFeeds.mutate()}
            >
              {t("library.refreshFeeds")}
            </Button>
          </Box>
          <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2 }}>
            <CardState
              loading={feeds.isPending}
              error={feeds.isError}
              empty={feeds.data?.items.length === 0}
            />
            {(feeds.data?.items ?? []).map((f) => (
              <Box
                key={f.id}
                sx={{
                  display: "flex", alignItems: "center", gap: 3, px: 3, py: 2,
                  borderBottom: "1px solid", borderColor: "border.muted",
                  ":last-child": { borderBottom: 0 },
                }}
              >
                <Box flex={1} minWidth={0}>
                  <Text id={`feed-label-${f.id}`} sx={{ fontSize: 1 }}>
                    {f.title || f.url}
                  </Text>
                  <Text as="div" sx={{ fontFamily: "mono", fontSize: 0, color: "fg.subtle" }}>
                    {f.url}
                  </Text>
                </Box>
                <ToggleSwitch
                  aria-labelledby={`feed-label-${f.id}`}
                  size="small"
                  checked={f.enabled}
                  onClick={() => toggleFeed.mutate(f)}
                />
                <IconButton
                  aria-label={t("common.delete")}
                  icon={TrashIcon}
                  size="small"
                  variant="invisible"
                  onClick={() => deleteFeed.mutate(f.id)}
                />
              </Box>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}
