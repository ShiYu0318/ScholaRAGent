// 應用外框：Header app bar + UnderlineNav 分頁 + 指令面板 + 語言/主題切換。
import {
  ActionList,
  ActionMenu,
  Box,
  Header,
  Text,
  UnderlineNav,
} from "@primer/react";
import {
  BeakerIcon,
  BookIcon,
  CommentDiscussionIcon,
  GearIcon,
  GraphIcon,
  HistoryIcon,
  HomeIcon,
  MoonIcon,
  MortarBoardIcon,
  PencilIcon,
  PulseIcon,
  SearchIcon,
  ShareAndroidIcon,
  SunIcon,
  TelescopeIcon,
} from "@primer/octicons-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { setLocale } from "../i18n";
import { useAuth } from "../lib/auth";
import { useThemeMode } from "../theme";
import { CommandPalette } from "./CommandPalette";

export const NAV_ITEMS = [
  { path: "/", key: "nav.home", icon: HomeIcon },
  { path: "/ask", key: "nav.ask", icon: CommentDiscussionIcon },
  { path: "/conversations", key: "nav.conversations", icon: HistoryIcon },
  { path: "/research", key: "nav.research", icon: BeakerIcon },
  { path: "/write", key: "nav.write", icon: PencilIcon },
  { path: "/graph", key: "nav.graph", icon: ShareAndroidIcon },
  { path: "/library", key: "nav.library", icon: BookIcon },
  { path: "/trends", key: "nav.trends", icon: GraphIcon },
  { path: "/learning", key: "nav.learning", icon: MortarBoardIcon },
  { path: "/analytics", key: "nav.analytics", icon: PulseIcon },
  { path: "/settings", key: "nav.settings", icon: GearIcon },
] as const;

export function Shell() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const { mode, toggle } = useThemeMode();
  const navigate = useNavigate();
  const location = useLocation();
  const [paletteOpen, setPaletteOpen] = useState(false);

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

  return (
    <Box display="flex" flexDirection="column" minHeight="100vh" bg="canvas.default">
      <Header>
        <Header.Item>
          <Header.Link
            onClick={() => navigate("/")}
            sx={{ fontSize: 2, display: "flex", alignItems: "center", gap: 2 }}
          >
            <TelescopeIcon size={24} />
            <span>{t("app.name")}</span>
          </Header.Link>
        </Header.Item>
        <Header.Item full>
          <Text sx={{ fontSize: 0, color: "header.text", opacity: 0.7 }}>
            {t("app.tagline")}
          </Text>
        </Header.Item>
        <Header.Item sx={{ mr: 2 }}>
          <Box
            as="button"
            onClick={() => setPaletteOpen(true)}
            aria-label={t("common.commandPalette")}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              px: 2,
              py: 1,
              fontSize: 0,
              color: "header.text",
              bg: "transparent",
              border: "1px solid",
              borderColor: "header.divider",
              borderRadius: 2,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <SearchIcon size={14} />
            <Text as="span" sx={{ opacity: 0.8 }}>{t("common.search")}</Text>
            <Text as="span" sx={{ fontFamily: "mono", fontSize: 0, opacity: 0.6 }}>
              ⌘K
            </Text>
          </Box>
        </Header.Item>
        <Header.Item sx={{ mr: 2 }}>
          <ActionMenu>
            <ActionMenu.Button variant="invisible" sx={{ color: "header.text" }}>
              {i18n.language === "zh" ? "中文" : "EN"}
            </ActionMenu.Button>
            <ActionMenu.Overlay>
              <ActionList selectionVariant="single">
                <ActionList.Item selected={i18n.language === "en"} onSelect={() => setLocale("en")}>
                  English
                </ActionList.Item>
                <ActionList.Item selected={i18n.language === "zh"} onSelect={() => setLocale("zh")}>
                  繁體中文
                </ActionList.Item>
              </ActionList>
            </ActionMenu.Overlay>
          </ActionMenu>
        </Header.Item>
        <Header.Item sx={{ mr: 2 }}>
          <Box
            as="button"
            onClick={toggle}
            aria-label={t("common.theme")}
            sx={{
              display: "flex",
              alignItems: "center",
              color: "header.text",
              bg: "transparent",
              border: 0,
              cursor: "pointer",
              p: 1,
            }}
          >
            {mode === "night" ? <SunIcon size={16} /> : <MoonIcon size={16} />}
          </Box>
        </Header.Item>
        <Header.Item sx={{ mr: 0 }}>
          <ActionMenu>
            <ActionMenu.Anchor>
              <Box as="button" aria-label={user?.display_name} sx={{ bg: "transparent", border: 0, cursor: "pointer", p: 0, display: "flex" }}>
                <Box
                  sx={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    bg: "accent.emphasis",
                    color: "fg.onEmphasis",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 0,
                    fontWeight: "bold",
                  }}
                >
                  {(user?.display_name ?? "?").slice(0, 1).toUpperCase()}
                </Box>
              </Box>
            </ActionMenu.Anchor>
            <ActionMenu.Overlay>
              <ActionList>
                <ActionList.Item disabled>
                  <ActionList.LeadingVisual>
                    <Box
                      sx={{
                        width: 16, height: 16, borderRadius: "50%",
                        bg: "accent.emphasis",
                      }}
                    />
                  </ActionList.LeadingVisual>
                  {user?.email}
                </ActionList.Item>
                <ActionList.Divider />
                <ActionList.Item onSelect={() => navigate("/settings")}>
                  <ActionList.LeadingVisual>
                    <GearIcon />
                  </ActionList.LeadingVisual>
                  {t("nav.settings")}
                </ActionList.Item>
                <ActionList.Item variant="danger" onSelect={logout}>
                  {t("auth.signOut")}
                </ActionList.Item>
              </ActionList>
            </ActionMenu.Overlay>
          </ActionMenu>
        </Header.Item>
      </Header>

      <UnderlineNav aria-label="Main" sx={{ bg: "canvas.default", px: 3 }}>
        {NAV_ITEMS.map((item) => (
          <UnderlineNav.Item
            key={item.path}
            icon={item.icon}
            aria-current={location.pathname === item.path ? "page" : undefined}
            onSelect={(e) => {
              e.preventDefault();
              navigate(item.path);
            }}
          >
            {t(item.key)}
          </UnderlineNav.Item>
        ))}
      </UnderlineNav>

      <Box as="main" flex={1} p={4} maxWidth={1280} width="100%" mx="auto">
        <Outlet />
      </Box>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </Box>
  );
}
