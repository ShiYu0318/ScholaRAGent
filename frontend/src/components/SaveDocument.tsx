// 把一段產出（綜述、回答、比較表…）存成文件。存完給一個「開啟」的捷徑，接續去寫作頁編修。
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FilePlus2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { useProjects, type DocumentFull, type DocumentKind } from "../lib/types";
import { Button, Dialog, Field, Input, Select } from "../ui";
import { useToast } from "../ui/toast";

interface Props {
  title: string;
  content: string;
  kind: DocumentKind;
  paperIds?: string[];
  projectId?: number | null;
  size?: "sm" | "md";
  label?: string;
}

export function SaveDocumentButton({ title, content, kind, paperIds = [], projectId = null, size = "md", label }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useProjects();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(title);
  const [project, setProject] = useState<string>(projectId ? String(projectId) : "");

  useEffect(() => {
    if (open) {
      setName(title);
      setProject(projectId ? String(projectId) : "");
    }
  }, [open, title, projectId]);

  const save = useMutation({
    mutationFn: () =>
      api<DocumentFull>("/api/documents", {
        method: "POST",
        body: { title: name.trim(), content, kind, paper_ids: paperIds.slice(0, 100),
                project_id: project ? Number(project) : null },
      }),
    onSuccess: (doc) => {
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      void queryClient.invalidateQueries({ queryKey: ["project"] });
      toast.show(t("doc.saved"), { action: { label: t("doc.open"), onClick: () => navigate(`/write/${doc.id}`) } });
    },
    onError: toast.error,
  });

  return (
    <>
      <Button icon={FilePlus2} size={size} onClick={() => setOpen(true)} disabled={!content.trim()}>
        {label ?? t("doc.saveAs")}
      </Button>
      <Dialog open={open} onClose={() => setOpen(false)} title={t("doc.saveAs")}
              footer={
                <>
                  <Button variant="ghost" onClick={() => setOpen(false)}>{t("common.cancel")}</Button>
                  <Button variant="primary" loading={save.isPending} disabled={!name.trim()}
                          onClick={() => save.mutate()}>
                    {t("common.save")}
                  </Button>
                </>
              }>
        <div className="stack">
          <Field label={t("doc.title")}>
            {(id) => <Input id={id} value={name} maxLength={200} autoFocus
                            onChange={(e) => setName(e.target.value)} />}
          </Field>
          <Field label={t("doc.project")} hint={t("doc.projectHint")}>
            {(id) => (
              <Select id={id} value={project} onChange={(e) => setProject(e.target.value)}>
                <option value="">{t("doc.noProject")}</option>
                {(projects.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </Select>
            )}
          </Field>
        </div>
      </Dialog>
    </>
  );
}
