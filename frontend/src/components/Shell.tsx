// 應用外框：依研究流程分組的側邊欄 + 內容區。
// 導覽順序就是研究的順序：蒐集 → 研究 → 寫作；進行中的專案直接列在側邊。
import {
  BarChart3, BookOpen, Compass, FileText, FolderOpen, GraduationCap, Layers, LogOut, Menu as MenuIcon,
  MessageSquareText, Moon, Network, Search, Settings as SettingsIcon, Sun, Sunrise, Languages,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { setLocale } from "../i18n";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { useProjects } from "../lib/types";
import { IconButton, Menu } from "../ui";
import { CommandPalette } from "./CommandPalette";

export interface NavItem {
  path: string;
  key: string;
  icon: LucideIcon;
}

export const NAV_GROUPS: { key: string | null; items: NavItem[] }[] = [
  { key: null, items: [{ path: "/", key: "nav.today", icon: Sunrise }] },
  {
    key: "nav.group.collect",
    items: [
      { path: "/discover", key: "nav.discover", icon: Compass },
      { path: "/library", key: "nav.library", icon: BookOpen },
    ],
  },
  {
    key: "nav.group.research",
    items: [
      { path: "/ask", key: "nav.ask", icon: MessageSquareText },
      { path: "/research", key: "nav.synthesize", icon: Layers },
      { path: "/graph", key: "nav.graph", icon: Network },
    ],
  },
  { key: "nav.group.write", items: [{ path: "/write", key: "nav.write", icon: FileText }] },
];

export const NAV_MORE: NavItem[] = [
  { path: "/learning", key: "nav.learning", icon: GraduationCap },
  { path: "/analytics", key: "nav.analytics", icon: BarChart3 },
];

export const ALL_NAV: NavItem[] = [
  ...NAV_GROUPS.flatMap((g) => g.items),
  { path: "/projects", key: "nav.projects", icon: FolderOpen },
  ...NAV_MORE,
  { path: "/settings", key: "nav.settings", icon: SettingsIcon },
];

function NavEntry({ item, onNavigate }: { item: NavItem; onNavigate: () => void }) {
  const { t } = useTranslation();
  return (
    <NavLink to={item.path} end={item.path === "/"} className="nav-link" onClick={onNavigate}>
      <item.icon size={16} strokeWidth={1.8} />
      {t(item.key)}
    </NavLink>
  );
}

export function Shell() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { mode, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const projects = useProjects();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // 換頁後收起行動版側邊欄
  useEffect(() => setNavOpen(false), [location.pathname]);

  const close = () => setNavOpen(false);
  const activeProjects = (projects.data?.items ?? []).slice(0, 6);
  // 全高版面（對話、編輯器）自己管理捲動
  const fullHeight = ["/ask", "/write"].some((p) => location.pathname.startsWith(p));

  return (
    <div className="shell">
      {navOpen && <button type="button" className="scrim" aria-label={t("common.close")} onClick={close} />}
      <aside className="sidebar" data-open={navOpen}>
        <Link to="/" className="brand" onClick={close}>
          <BookOpen size={20} className="brand-mark" strokeWidth={2} />
          ScholaRAGent
        </Link>

        <div style={{ padding: "0 8px 4px" }}>
          <button type="button" className="nav-link" style={{ width: "100%", border: 0, background: "none", cursor: "pointer" }}
                  onClick={() => setPaletteOpen(true)}>
            <Search size={16} strokeWidth={1.8} />
            {t("common.search")}
            <span className="kbd" style={{ marginLeft: "auto" }}>⌘K</span>
          </button>
        </div>

        <nav className="nav" aria-label={t("nav.label")}>
          {NAV_GROUPS.map((group) => (
            <div key={group.key ?? "top"} className="col" style={{ gap: 1 }}>
              {group.key && <div className="nav-group">{t(group.key)}</div>}
              {group.items.map((item) => <NavEntry key={item.path} item={item} onNavigate={close} />)}
            </div>
          ))}

          <div className="nav-group">{t("nav.group.projects")}</div>
          {activeProjects.map((p) => (
            <NavLink key={p.id} to={`/projects/${p.id}`} className="nav-link nav-project" onClick={close}>
              <span className="truncate">{p.name}</span>
              <span className="nav-count">{p.paper_count}</span>
            </NavLink>
          ))}
          <NavLink to="/projects" end className="nav-link" onClick={close}>
            <FolderOpen size={16} strokeWidth={1.8} />
            {activeProjects.length > 0 ? t("nav.allProjects") : t("nav.newProject")}
          </NavLink>

          <div className="nav-group">{t("nav.group.more")}</div>
          {NAV_MORE.map((item) => <NavEntry key={item.path} item={item} onNavigate={close} />)}
        </nav>

        <div className="sidebar-foot">
          <Menu
            align="left"
            header={<div className="menu-label truncate">{user?.email}</div>}
            trigger={(props) => (
              <button type="button" className="nav-link" style={{ width: "100%", border: 0, background: "none", cursor: "pointer" }} {...props}>
                <span className="avatar">{(user?.display_name ?? "?").slice(0, 1).toUpperCase()}</span>
                <span className="truncate">{user?.display_name}</span>
              </button>
            )}
            items={[
              { label: t("nav.settings"), icon: SettingsIcon, onSelect: () => navigate("/settings") },
              { label: mode === "dark" ? t("common.lightTheme") : t("common.darkTheme"),
                icon: mode === "dark" ? Sun : Moon, onSelect: toggle },
              { label: i18n.language === "zh" ? "English" : "繁體中文", icon: Languages,
                onSelect: () => setLocale(i18n.language === "zh" ? "en" : "zh") },
              { label: t("auth.signOut"), icon: LogOut, onSelect: logout, danger: true, separatorBefore: true },
            ]}
          />
        </div>
      </aside>

      <div className="main">
        <div className="topbar">
          <IconButton icon={MenuIcon} label={t("nav.label")} onClick={() => setNavOpen(true)} />
          <Link to="/" className="brand" style={{ padding: 0, fontSize: 15 }}>ScholaRAGent</Link>
          <span className="grow" />
          <IconButton icon={Search} label={t("common.search")} onClick={() => setPaletteOpen(true)} />
        </div>
        <main className={fullHeight ? "page page-full" : "page"}>
          <Outlet />
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
