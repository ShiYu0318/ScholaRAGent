// ⌘K 指令面板：跳頁、開專案，或把輸入的字直接拿去提問 / 搜尋文獻。
// 高頻操作：不做進場動畫以外的任何動效。
import { CornerDownLeft, FolderOpen, MessageSquareText, Compass, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useProjects } from "../lib/types";
import { ALL_NAV } from "./Shell";

interface Command {
  id: string;
  label: string;
  icon: LucideIcon;
  to: string;
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const projects = useProjects();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (open && !el.open) {
      setQuery("");
      setActive(0);
      el.showModal();
    }
    if (!open && el.open) el.close();
  }, [open]);

  const commands = useMemo<Command[]>(() => {
    const q = query.trim();
    const needle = q.toLowerCase();
    const pages = ALL_NAV.map((n) => ({ id: n.path, label: t(n.key), icon: n.icon, to: n.path }));
    const projs = (projects.data?.items ?? []).map((p) => ({
      id: `p${p.id}`, label: p.name, icon: FolderOpen, to: `/projects/${p.id}`,
    }));
    const matches = [...pages, ...projs].filter((c) => !needle || c.label.toLowerCase().includes(needle));
    if (q.length < 2) return matches;
    return [
      ...matches,
      { id: "ask", label: t("palette.ask", { q }), icon: MessageSquareText, to: `/ask?q=${encodeURIComponent(q)}` },
      { id: "find", label: t("palette.discover", { q }), icon: Compass, to: `/discover?q=${encodeURIComponent(q)}` },
    ];
  }, [query, projects.data, t]);

  const run = (cmd: Command | undefined) => {
    if (!cmd) return;
    navigate(cmd.to);
    onClose();
  };

  return (
    <dialog ref={dialogRef} className="palette" aria-label={t("common.commandPalette")} onClose={onClose}
            onMouseDown={(e) => { if (e.target === dialogRef.current) onClose(); }}>
      {open && (
        <>
          <input
            autoFocus
            value={query}
            placeholder={t("palette.placeholder")}
            aria-label={t("palette.placeholder")}
            onChange={(e) => { setQuery(e.target.value); setActive(0); }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => Math.min(i + 1, commands.length - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
              if (e.key === "Enter") { e.preventDefault(); run(commands[active]); }
            }}
          />
          <div className="palette-list" role="listbox">
            {commands.length === 0 && <div className="empty" style={{ padding: 20 }}>{t("palette.empty")}</div>}
            {commands.map((cmd, i) => (
              <button key={cmd.id} type="button" role="option" aria-selected={i === active}
                      className="menu-item palette-item"
                      onMouseEnter={() => setActive(i)} onClick={() => run(cmd)}>
                <cmd.icon size={15} />
                <span className="grow truncate">{cmd.label}</span>
                {i === active && <CornerDownLeft size={13} style={{ color: "var(--ink-faint)" }} />}
              </button>
            ))}
          </div>
        </>
      )}
    </dialog>
  );
}
