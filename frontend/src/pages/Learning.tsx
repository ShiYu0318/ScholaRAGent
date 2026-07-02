// 學習頁：依主題生成學習路徑（LLM/檢索式）、勾選步驟進度、技能等級管理。
import {
  Box,
  Button,
  Checkbox,
  Heading,
  IconButton,
  ProgressBar,
  Text,
  TextInput,
} from "@primer/react";
import { MortarBoardIcon, PlusIcon, TrashIcon } from "@primer/octicons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import { Card, CardState } from "../components/Card";

interface PathItem {
  title: string;
  done: boolean;
}

interface LearningPath {
  id: number;
  topic: string;
  items: PathItem[];
  progress: Record<string, number>;
}

interface Skill {
  skill: string;
  level: number;
}

export function Learning() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState("");
  const [skillName, setSkillName] = useState("");
  const [skillLevel, setSkillLevel] = useState("50");

  const paths = useQuery({
    queryKey: ["learning-paths"],
    queryFn: () => api<{ items: LearningPath[] }>("/api/learning-paths"),
  });
  const skills = useQuery({
    queryKey: ["skills"],
    queryFn: () => api<{ items: Skill[] }>("/api/skills"),
  });

  const createPath = useMutation({
    mutationFn: (newTopic: string) =>
      api<LearningPath>("/api/learning-paths", {
        method: "POST",
        body: { topic: newTopic },
      }),
    onSuccess: () => {
      setTopic("");
      queryClient.invalidateQueries({ queryKey: ["learning-paths"] });
    },
  });

  const updatePath = useMutation({
    mutationFn: ({ id, items }: { id: number; items: PathItem[] }) =>
      api<LearningPath>(`/api/learning-paths/${id}`, {
        method: "PATCH",
        body: {
          items,
          progress: { done: items.filter((i) => i.done).length, total: items.length },
        },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["learning-paths"] }),
  });

  const deletePath = useMutation({
    mutationFn: (id: number) =>
      api<void>(`/api/learning-paths/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["learning-paths"] }),
  });

  const putSkill = useMutation({
    mutationFn: (body: Skill) =>
      api<Skill>("/api/skills", { method: "PUT", body }),
    onSuccess: () => {
      setSkillName("");
      queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });

  const toggleItem = (path: LearningPath, index: number) => {
    const items = path.items.map((it, i) =>
      i === index ? { ...it, done: !it.done } : it,
    );
    updatePath.mutate({ id: path.id, items });
  };

  return (
    <Box>
      <Heading as="h2" sx={{ fontSize: 3, mb: 3 }}>
        {t("nav.learning")}
      </Heading>

      <Box sx={{ display: "flex", gap: 2, mb: 3, maxWidth: 560 }}>
        <TextInput
          sx={{ flex: 1 }}
          placeholder={t("learning.topicPlaceholder")}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && topic.trim()) createPath.mutate(topic.trim());
          }}
        />
        <Button
          variant="primary"
          leadingVisual={PlusIcon}
          disabled={!topic.trim() || createPath.isPending}
          onClick={() => createPath.mutate(topic.trim())}
        >
          {createPath.isPending ? t("common.loading") : t("learning.create")}
        </Button>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
          gap: 3,
        }}
      >
        {paths.isPending || paths.isError || paths.data?.items.length === 0 ? (
          <Card title={t("learning.pathsTitle")} icon={MortarBoardIcon}>
            <CardState
              loading={paths.isPending}
              error={paths.isError}
              empty={paths.data?.items.length === 0}
            />
            {paths.data?.items.length === 0 && (
              <Text sx={{ color: "fg.subtle", fontSize: 1 }}>{t("learning.emptyHint")}</Text>
            )}
          </Card>
        ) : (
          paths.data?.items.map((path) => {
            const done = path.items.filter((i) => i.done).length;
            return (
              <Card
                key={path.id}
                title={path.topic}
                icon={MortarBoardIcon}
                action={
                  <IconButton
                    aria-label={t("common.delete")}
                    icon={TrashIcon}
                    variant="invisible"
                    size="small"
                    onClick={() => deletePath.mutate(path.id)}
                  />
                }
              >
                <Box sx={{ display: "grid", gap: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <ProgressBar
                      progress={(done / Math.max(path.items.length, 1)) * 100}
                      sx={{ flex: 1 }}
                      aria-label={t("learning.progress", { done, total: path.items.length })}
                    />
                    <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted" }}>
                      {done}/{path.items.length}
                    </Text>
                  </Box>
                  {path.items.map((item, i) => (
                    <Box
                      key={`${path.id}-${i}`}
                      as="label"
                      sx={{ display: "flex", alignItems: "flex-start", gap: 2, cursor: "pointer" }}
                    >
                      <Checkbox
                        checked={item.done}
                        onChange={() => toggleItem(path, i)}
                        aria-label={item.title}
                      />
                      <Text
                        sx={{
                          fontSize: 1,
                          color: item.done ? "fg.subtle" : "fg.default",
                          textDecoration: item.done ? "line-through" : "none",
                        }}
                      >
                        {item.title}
                      </Text>
                    </Box>
                  ))}
                </Box>
              </Card>
            );
          })
        )}

        <Card title={t("learning.skillsTitle")} icon={MortarBoardIcon}>
          <CardState loading={skills.isPending} error={skills.isError} />
          <Box sx={{ display: "grid", gap: 2 }}>
            {skills.data?.items.map((s) => (
              <Box key={s.skill} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Text sx={{ fontSize: 1, width: 140 }} className="truncate">
                  {s.skill}
                </Text>
                <ProgressBar progress={s.level} sx={{ flex: 1 }} aria-label={s.skill} />
                <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted", width: 32 }}>
                  {s.level}
                </Text>
              </Box>
            ))}
            <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
              <TextInput
                sx={{ flex: 1 }}
                size="small"
                placeholder={t("learning.skillPlaceholder")}
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
              />
              <TextInput
                sx={{ width: 72 }}
                size="small"
                type="number"
                min={0}
                max={100}
                aria-label={t("learning.levelLabel")}
                value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value)}
              />
              <Button
                size="small"
                disabled={!skillName.trim() || putSkill.isPending}
                onClick={() =>
                  putSkill.mutate({
                    skill: skillName.trim(),
                    level: Math.max(0, Math.min(100, Number(skillLevel) || 0)),
                  })
                }
              >
                {t("common.save")}
              </Button>
            </Box>
          </Box>
        </Card>
      </Box>
    </Box>
  );
}
