// 對話管理頁：搜尋、開啟續聊、分享（複製連結）、刪除。
import {
  ActionList,
  Box,
  Flash,
  Heading,
  IconButton,
  Text,
  TextInput,
} from "@primer/react";
import { LinkIcon, SearchIcon, TrashIcon } from "@primer/octicons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { CardState } from "../components/Card";

interface Conversation {
  id: number;
  title: string;
  updated_at: string;
  share_token: string | null;
}

export function Conversations() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [flash, setFlash] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ["conversations", query],
    queryFn: () =>
      api<{ items: Conversation[] }>(
        `/api/conversations${query ? `?query=${encodeURIComponent(query)}` : ""}`,
      ),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["conversations"] });

  const share = useMutation({
    mutationFn: (id: number) =>
      api<{ url: string }>(`/api/conversations/${id}/share`, { method: "POST" }),
    onSuccess: async (data) => {
      await navigator.clipboard.writeText(data.url);
      setFlash(t("conv.linkCopied"));
      void invalidate();
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api(`/api/conversations/${id}`, { method: "DELETE" }),
    onSuccess: () => void invalidate(),
  });

  return (
    <Box>
      <Heading as="h2" sx={{ fontSize: 3, mb: 3 }}>
        {t("nav.conversations")}
      </Heading>

      {flash && (
        <Flash variant="success" sx={{ mb: 3 }} onClick={() => setFlash(null)}>
          {flash}
        </Flash>
      )}

      <TextInput
        block
        leadingVisual={SearchIcon}
        placeholder={t("conv.searchPlaceholder")}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 3 }}
      />

      <Box
        sx={{
          border: "1px solid",
          borderColor: "border.default",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <CardState
          loading={list.isPending}
          error={list.isError}
          empty={list.data?.items.length === 0}
        />
        <ActionList>
          {(list.data?.items ?? []).map((c) => (
            <ActionList.Item key={c.id} onSelect={() => navigate(`/ask?c=${c.id}`)}>
              {c.title || `#${c.id}`}
              <ActionList.Description variant="block">
                <Text sx={{ fontFamily: "mono", fontSize: 0 }}>
                  {new Date(c.updated_at).toLocaleString()}
                  {c.share_token ? "  ·  shared" : ""}
                </Text>
              </ActionList.Description>
              <ActionList.TrailingVisual>
                <Box display="flex" sx={{ gap: 1 }}>
                  <IconButton
                    aria-label={t("conv.share")}
                    icon={LinkIcon}
                    size="small"
                    variant="invisible"
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      share.mutate(c.id);
                    }}
                  />
                  <IconButton
                    aria-label={t("common.delete")}
                    icon={TrashIcon}
                    size="small"
                    variant="invisible"
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      remove.mutate(c.id);
                    }}
                  />
                </Box>
              </ActionList.TrailingVisual>
            </ActionList.Item>
          ))}
        </ActionList>
      </Box>
    </Box>
  );
}
