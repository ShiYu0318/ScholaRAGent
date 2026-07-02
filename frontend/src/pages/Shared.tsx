// 公開分享頁：不需登入即可讀的唯讀對話。
import { Box, Flash, Heading, Label, Spinner, Text } from "@primer/react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { api } from "../lib/api";
import type { Citation } from "../lib/sse";

interface SharedConv {
  title: string;
  created_at: string;
  messages: { role: string; content: string; citations: Citation[] | null }[];
}

export function Shared() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const conv = useQuery({
    queryKey: ["shared", token],
    queryFn: () => api<SharedConv>(`/api/shared/${token}`),
  });

  return (
    <Box minHeight="100vh" bg="canvas.default" p={4}>
      <Box maxWidth={800} mx="auto">
        {conv.isPending && (
          <Box display="flex" justifyContent="center" p={6}>
            <Spinner />
          </Box>
        )}
        {conv.isError && <Flash variant="danger">{t("conv.sharedNotFound")}</Flash>}
        {conv.data && (
          <>
            <Heading as="h1" sx={{ fontSize: 3, mb: 1 }}>
              {conv.data.title}
            </Heading>
            <Text sx={{ color: "fg.muted", fontSize: 0, fontFamily: "mono" }}>
              {new Date(conv.data.created_at).toLocaleString()}
            </Text>
            <Box mt={4}>
              {conv.data.messages.map((m, i) => (
                <Box
                  key={i}
                  sx={{
                    mb: 3,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: m.role === "user" ? "flex-end" : "flex-start",
                  }}
                >
                  <Box
                    sx={{
                      maxWidth: "85%",
                      border: "1px solid",
                      borderColor: m.role === "user" ? "accent.muted" : "border.default",
                      bg: m.role === "user" ? "accent.subtle" : "canvas.subtle",
                      borderRadius: 2,
                      px: 3,
                      py: 2,
                    }}
                  >
                    <Text sx={{ whiteSpace: "pre-wrap", fontSize: 1 }}>{m.content}</Text>
                    {m.citations && m.citations.length > 0 && (
                      <Box mt={2} display="flex" flexWrap="wrap" sx={{ gap: 1 }}>
                        {m.citations.map((c, n) => (
                          <a key={c.id} href={c.link} target="_blank" rel="noreferrer">
                            <Label variant="accent">[{n + 1}] {c.title.slice(0, 40)}</Label>
                          </a>
                        ))}
                      </Box>
                    )}
                  </Box>
                </Box>
              ))}
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}
