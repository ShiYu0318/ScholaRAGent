// 建立專案的對話框：名稱 + 研究問題。研究問題會顯示在專案頁首，提醒自己在找什麼。
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import type { Project } from "../lib/types";
import { Button, Dialog, Field, Input, Textarea } from "../ui";
import { useToast } from "../ui/toast";

export function ProjectDialog({ open, onClose, project }: { open: boolean; onClose: () => void; project?: Project }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("");

  useEffect(() => {
    if (open) {
      setName(project?.name ?? "");
      setQuestion(project?.question ?? "");
    }
  }, [open, project]);

  const save = useMutation({
    mutationFn: () =>
      project
        ? api<Project>(`/api/projects/${project.id}`, { method: "PATCH", body: { name: name.trim(), question: question.trim() } })
        : api<Project>("/api/projects", { method: "POST", body: { name: name.trim(), question: question.trim() } }),
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      void queryClient.invalidateQueries({ queryKey: ["project", saved.id] });
      onClose();
      if (!project) navigate(`/projects/${saved.id}`);
    },
    onError: toast.error,
  });

  return (
    <Dialog open={open} onClose={onClose} title={project ? t("project.edit") : t("project.new")}
            footer={
              <>
                <Button variant="ghost" onClick={onClose}>{t("common.cancel")}</Button>
                <Button variant="primary" loading={save.isPending} disabled={!name.trim()} onClick={() => save.mutate()}>
                  {project ? t("common.save") : t("project.create")}
                </Button>
              </>
            }>
      <form className="stack" onSubmit={(e) => { e.preventDefault(); if (name.trim()) save.mutate(); }}>
        <Field label={t("project.name")}>
          {(id) => <Input id={id} value={name} maxLength={120} autoFocus
                          placeholder={t("project.namePlaceholder")} onChange={(e) => setName(e.target.value)} />}
        </Field>
        <Field label={t("project.question")} hint={t("project.questionHint")}>
          {(id) => <Textarea id={id} rows={3} value={question} maxLength={1000}
                             placeholder={t("project.questionPlaceholder")} onChange={(e) => setQuestion(e.target.value)} />}
        </Field>
      </form>
    </Dialog>
  );
}
