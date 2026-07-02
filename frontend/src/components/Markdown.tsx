// GitHub 風 Markdown 渲染：GFM 表格、細邊框、等寬碼體。
import { Box } from "@primer/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <Box
      sx={{
        fontSize: 1,
        lineHeight: 1.6,
        "& h1, & h2, & h3": {
          borderBottom: "1px solid",
          borderColor: "border.muted",
          pb: 1,
          mt: 3,
          mb: 2,
        },
        "& h1": { fontSize: 3 },
        "& h2": { fontSize: 2 },
        "& h3": { fontSize: 1 },
        "& p": { my: 2 },
        "& table": {
          borderCollapse: "collapse",
          my: 2,
          display: "block",
          overflowX: "auto",
        },
        "& th, & td": {
          border: "1px solid",
          borderColor: "border.default",
          px: 2,
          py: 1,
        },
        "& th": { bg: "canvas.subtle" },
        "& code": {
          fontFamily: "mono",
          fontSize: 0,
          bg: "canvas.subtle",
          px: 1,
          borderRadius: 1,
        },
        "& pre": {
          bg: "canvas.subtle",
          border: "1px solid",
          borderColor: "border.muted",
          borderRadius: 2,
          p: 3,
          overflowX: "auto",
        },
        "& pre code": { bg: "transparent", p: 0 },
        "& ul, & ol": { pl: 4, my: 2 },
        "& a": { color: "accent.fg" },
        "& blockquote": {
          borderLeft: "3px solid",
          borderColor: "border.default",
          pl: 3,
          color: "fg.muted",
          my: 2,
          ml: 0,
        },
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </Box>
  );
}
