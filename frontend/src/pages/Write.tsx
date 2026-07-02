// 寫作面板：潤稿、貢獻抽取、審稿清單、LaTeX 草稿、簡報大綱、審閱建議。
import {
  Box,
  Button,
  Flash,
  Heading,
  SegmentedControl,
  Spinner,
  Text,
  Textarea,
  TextInput,
} from "@primer/react";
import { CopyIcon } from "@primer/octicons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import { Markdown } from "../components/Markdown";

type Tool = "polish" | "contributions" | "review" | "checklist" | "latex" | "slides";
const TOOLS: Tool[] = ["polish", "contributions", "review", "checklist", "latex", "slides"];
// 前三個吃長文字，後三個吃主題
const TEXT_TOOLS = new Set<Tool>(["polish", "contributions", "review"]);

export function Write() {
  const { t } = useTranslation();
  const [tool, setTool] = useState<Tool>("polish");
  const [text, setText] = useState("");
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState("");

  const isTextTool = TEXT_TOOLS.has(tool);
  const canRun = isTextTool ? text.trim() : topic.trim();

  const run = async () => {
    if (!canRun || busy) return;
    setBusy(true);
    setError(null);
    setResult("");
    try {
      const resp = await api<{ content: string }>(`/api/write/${tool}`, {
        method: "POST",
        body: { text: isTextTool ? text : "", topic: isTextTool ? "" : topic },
      });
      setResult(resp.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box>
      <Box display="flex" sx={{ gap: 3, alignItems: "center", mb: 3, flexWrap: "wrap" }}>
        <Heading as="h2" sx={{ fontSize: 3, flex: 1 }}>
          {t("nav.write")}
        </Heading>
        <SegmentedControl aria-label="write tool"
                          onChange={(i) => { setTool(TOOLS[i]); setResult(""); setError(null); }}>
          {TOOLS.map((tl) => (
            <SegmentedControl.Button key={tl} selected={tool === tl}>
              {t(`write.${tl}`)}
            </SegmentedControl.Button>
          ))}
        </SegmentedControl>
      </Box>

      {isTextTool ? (
        <Textarea
          block
          rows={8}
          placeholder={t("write.textPlaceholder")}
          value={text}
          onChange={(e) => setText(e.target.value)}
          sx={{ mb: 2 }}
        />
      ) : (
        <TextInput
          block
          placeholder={t("write.topicPlaceholder")}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void run()}
          sx={{ mb: 2 }}
        />
      )}

      <Box display="flex" sx={{ justifyContent: "flex-end", mb: 3 }}>
        <Button variant="primary" disabled={busy || !canRun} onClick={() => void run()}>
          {busy ? <Spinner size="small" /> : t("write.run")}
        </Button>
      </Box>

      {error && <Flash variant="danger" sx={{ mb: 3 }}>{error}</Flash>}

      {result && (
        <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2, p: 3 }}>
          <Box display="flex" sx={{ justifyContent: "flex-end", mb: 1 }}>
            <Button size="small" leadingVisual={CopyIcon}
                    onClick={() => void navigator.clipboard.writeText(result)}>
              {t("research.copy")}
            </Button>
          </Box>
          {tool === "latex" ? (
            <Box as="pre" sx={{ fontFamily: "mono", fontSize: 0, whiteSpace: "pre-wrap", m: 0 }}>
              {result}
            </Box>
          ) : (
            <Markdown>{result}</Markdown>
          )}
        </Box>
      )}

      {!result && !error && (
        <Box sx={{ border: "1px dashed", borderColor: "border.default", borderRadius: 2,
                   p: 5, textAlign: "center" }}>
          <Text sx={{ color: "fg.muted" }}>{t(`write.hint.${tool}`)}</Text>
        </Box>
      )}
    </Box>
  );
}
