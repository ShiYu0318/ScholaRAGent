// 學習：進入新領域時的讀書計畫。輸入主題產生一條學習路徑，逐項打勾；旁邊記錄自己的技能程度。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GraduationCap, Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { Button, Empty, IconButton, Input, PageHead, QueryState } from "../ui";
import { useToast } from "../ui/toast";

interface PathItem {
  title: string;
  done: boolean;
}

interface LearningPath {
  id: number;
  topic: string;
  items: PathItem[];
}

interface Skill {
  skill: string;
  level: number;
}

export function Learning() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState("");
  const [skillName, setSkillName] = useState("");
  const [skillLevel, setSkillLevel] = useState(50);

  const paths = useQuery({ queryKey: ["learning-paths"], queryFn: () => api<{ items: LearningPath[] }>("/api/learning-paths") });
  const skills = useQuery({ queryKey: ["skills"], queryFn: () => api<{ items: Skill[] }>("/api/skills") });
  const refreshPaths = () => void queryClient.invalidateQueries({ queryKey: ["learning-paths"] });

  const createPath = useMutation({
    mutationFn: () => api<LearningPath>("/api/learning-paths", { method: "POST", body: { topic: topic.trim() } }),
    onSuccess: () => { setTopic(""); refreshPaths(); },
    onError: toast.error,
  });
  const updatePath = useMutation({
    mutationFn: ({ id, items }: { id: number; items: PathItem[] }) =>
      api<LearningPath>(`/api/learning-paths/${id}`, {
        method: "PATCH",
        body: { items, progress: { done: items.filter((i) => i.done).length, total: items.length } },
      }),
    onSuccess: refreshPaths, onError: toast.error,
  });
  const deletePath = useMutation({
    mutationFn: (id: number) => api<void>(`/api/learning-paths/${id}`, { method: "DELETE" }),
    onSuccess: refreshPaths, onError: toast.error,
  });
  const putSkill = useMutation({
    mutationFn: (body: Skill) => api<Skill>("/api/skills", { method: "PUT", body }),
    onSuccess: () => { setSkillName(""); void queryClient.invalidateQueries({ queryKey: ["skills"] }); },
    onError: toast.error,
  });

  const submitPath = (e: FormEvent) => { e.preventDefault(); if (topic.trim()) createPath.mutate(); };
  const submitSkill = (e: FormEvent) => {
    e.preventDefault();
    if (skillName.trim()) putSkill.mutate({ skill: skillName.trim(), level: skillLevel });
  };

  return (
    <div className="stack-lg">
      <PageHead title={t("nav.learning")}>{t("learning.intro")}</PageHead>
      <div className="grid-main">
        <section className="stack">
          <form className="row" onSubmit={submitPath}>
            <div className="grow">
              <Input value={topic} onChange={(e) => setTopic(e.target.value)} maxLength={200}
                     placeholder={t("learning.topicPlaceholder")} aria-label={t("learning.topicPlaceholder")} />
            </div>
            <Button type="submit" variant="primary" icon={Plus} loading={createPath.isPending} disabled={!topic.trim()}>
              {t("learning.generate")}
            </Button>
          </form>
          <QueryState loading={paths.isPending} error={paths.isError} empty={paths.data?.items.length === 0}
                      emptyState={<div className="panel"><Empty icon={GraduationCap} title={t("learning.emptyTitle")}>{t("learning.emptyBody")}</Empty></div>} />
          {(paths.data?.items ?? []).map((path) => {
            const done = path.items.filter((i) => i.done).length;
            return (
              <article key={path.id} className="panel">
                <div className="panel-head">
                  <div className="grow">
                    <h3 style={{ fontSize: 17 }}>{path.topic}</h3>
                    <div className="row" style={{ marginTop: 8 }}>
                      <div className="progress grow"><i style={{ width: `${(done / Math.max(path.items.length, 1)) * 100}%` }} /></div>
                      <span className="t-meta num">{done}/{path.items.length}</span>
                    </div>
                  </div>
                  <Link className="btn btn-ghost btn-sm" to={`/discover?q=${encodeURIComponent(path.topic)}`}>{t("learning.findPapers")}</Link>
                  <IconButton icon={Trash2} label={t("common.delete")} onClick={() => deletePath.mutate(path.id)} />
                </div>
                <div className="list">
                  {path.items.map((item, index) => (
                    <label key={index} className="list-row list-row-click" style={{ alignItems: "center" }}>
                      <span className="check">
                        <input type="checkbox" checked={item.done}
                               onChange={() => updatePath.mutate({
                                 id: path.id,
                                 items: path.items.map((it, i) => (i === index ? { ...it, done: !it.done } : it)),
                               })} />
                      </span>
                      <span className="grow" style={item.done ? { color: "var(--ink-faint)", textDecoration: "line-through" } : undefined}>
                        {item.title}
                      </span>
                    </label>
                  ))}
                </div>
              </article>
            );
          })}
        </section>

        <aside className="stack">
          <span className="t-label">{t("learning.skills")}</span>
          {(skills.data?.items ?? []).map((s) => (
            <div key={s.skill} className="col" style={{ gap: 4 }}>
              <div className="spread"><span>{s.skill}</span><span className="num t-meta">{Math.round(s.level)}</span></div>
              <div className="progress"><i style={{ width: `${s.level}%` }} /></div>
            </div>
          ))}
          {skills.data?.items.length === 0 && <span className="t-meta">{t("learning.noSkills")}</span>}
          <form className="col" onSubmit={submitSkill} style={{ marginTop: 8 }}>
            <Input value={skillName} onChange={(e) => setSkillName(e.target.value)} maxLength={80}
                   placeholder={t("learning.skillPlaceholder")} aria-label={t("learning.skillPlaceholder")} />
            <div className="row">
              <input type="range" min={0} max={100} step={5} value={skillLevel} className="grow"
                     style={{ accentColor: "var(--pencil)" }} aria-label={t("learning.level")}
                     onChange={(e) => setSkillLevel(Number(e.target.value))} />
              <span className="num t-meta" style={{ width: 28, textAlign: "right" }}>{skillLevel}</span>
              <Button type="submit" size="sm" disabled={!skillName.trim()} loading={putSkill.isPending}>{t("learning.setSkill")}</Button>
            </div>
          </form>
        </aside>
      </div>
    </div>
  );
}
