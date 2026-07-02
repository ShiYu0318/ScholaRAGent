// ⌘K 指令面板：頁面導覽 + 之後可掛上動作（抓論文、切語言…）。
import { ActionList, Box, Text, TextInput } from "@primer/react";
import { SearchIcon } from "@primer/octicons-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { NAV_ITEMS } from "./Shell";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    return NAV_ITEMS.filter((item) => {
      const label = t(item.key).toLowerCase();
      return !q || label.includes(q) || item.path.includes(q);
    });
  }, [query, t]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Enter" && items.length > 0) {
        navigate(items[0].path);
        onClose();
      }
    };
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, items, navigate, onClose]);

  if (!open) return null;

  return (
    <Box
      onClick={onClose}
      sx={{
        position: "fixed",
        inset: 0,
        bg: "primer.canvas.backdrop",
        zIndex: 100,
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        pt: "12vh",
      }}
    >
      <Box
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
        sx={{
          width: 560,
          maxWidth: "90vw",
          bg: "canvas.overlay",
          border: "1px solid",
          borderColor: "border.default",
          borderRadius: 2,
          boxShadow: "shadow.large",
          overflow: "hidden",
        }}
      >
        <Box p={2} borderBottom="1px solid" borderColor="border.default">
          <TextInput
            ref={inputRef}
            block
            leadingVisual={SearchIcon}
            placeholder={t("common.typeToFilter")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </Box>
        <ActionList>
          {items.map((item) => (
            <ActionList.Item
              key={item.path}
              onSelect={() => {
                navigate(item.path);
                onClose();
              }}
            >
              <ActionList.LeadingVisual>
                <item.icon />
              </ActionList.LeadingVisual>
              {t(item.key)}
              <ActionList.TrailingVisual>
                <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.subtle" }}>
                  {item.path}
                </Text>
              </ActionList.TrailingVisual>
            </ActionList.Item>
          ))}
          {items.length === 0 && (
            <Box p={3}>
              <Text sx={{ color: "fg.muted", fontSize: 1 }}>{t("common.empty")}</Text>
            </Box>
          )}
        </ActionList>
      </Box>
    </Box>
  );
}
