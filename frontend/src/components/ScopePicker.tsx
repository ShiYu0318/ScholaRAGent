// 檢索範圍選擇：整個文庫 / 某個專案 /（由其他頁帶入的）指定論文。
import { BookOpen, ChevronDown, FolderOpen, FileText } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useProjects, type Scope } from "../lib/types";
import { Menu, type MenuItem } from "../ui";

export function ScopePicker({ scope, onChange }: { scope: Scope; onChange: (s: Scope) => void }) {
  const { t } = useTranslation();
  const projects = useProjects();
  const list = projects.data?.items ?? [];

  const label =
    scope.kind === "library" ? t("scope.library")
      : scope.kind === "papers" ? scope.label
        : list.find((p) => p.id === scope.projectId)?.name ?? t("scope.project");
  const Icon = scope.kind === "library" ? BookOpen : scope.kind === "papers" ? FileText : FolderOpen;

  const items: MenuItem[] = [
    { label: t("scope.library"), icon: BookOpen, onSelect: () => onChange({ kind: "library" }) },
    ...list.map((p, i) => ({
      label: `${p.name}（${p.paper_count}）`,
      icon: FolderOpen,
      separatorBefore: i === 0,
      onSelect: () => onChange({ kind: "project", projectId: p.id }),
    })),
  ];

  return (
    <Menu
      align="left"
      header={<div className="menu-label">{t("scope.title")}</div>}
      items={items}
      trigger={(props) => (
        <button type="button" className="scope-chip" data-scoped={scope.kind !== "library"}
                title={t("scope.title")} {...props}>
          <Icon size={13} />
          <span className="truncate">{label}</span>
          <ChevronDown size={12} />
        </button>
      )}
    />
  );
}
