// 研究面板：深度研究（SSE 進度）、文獻綜述、比較、主題報告、BibTeX、白話解讀。
import {
  Box,
  Button,
  Flash,
  Heading,
  Label,
  SegmentedControl,
  Spinner,
  Text,
  TextInput,
} from "@primer/react";
import { CopyIcon } from "@primer/octicons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../lib/api";
import { streamSSE } from "../lib/sse";
import { Markdown } from "../components/Markdown";

type Tool = "deep" | "litreview" | "compare" | "report" | "bibtex" | "explain";
const TOOLS: Tool[] = ["deep", "litreview", "compare", "report", "bibtex", "explain"];

interface Section {
  question: string;
  content: string;
}

export function Research() {
  const { t } = useTranslation();
  const [tool, setTool] = useState<Tool>("deep");
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string>("");
  // 深度研究的漸進狀態
  const [questions, setQuestions] = useState<string[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [synthesis, setSynthesis] = useState("");

  const reset = () => {
    setError(null);
    setResult("");
    setQuestions([]);
    setSections([]);
    setSynthesis("");
  };

  const run = async () => {
    const q = topic.trim();
    if (!q || busy) return;
    reset();
    setBusy(true);
    try {
      if (tool === "deep") {
        interface DeepEvent {
          type: string;
          questions?: string[];
          question?: string;
          content?: string;
          message?: string;
        }
        await streamSSE<DeepEvent>("/api/deepresearch", { topic: q }, (e) => {
          if (e.type === "decompose") setQuestions(e.questions ?? []);
          else if (e.type === "section") {
            setSections((s) => [...s, { question: e.question ?? "", content: e.content ?? "" }]);
          } else if (e.type === "synthesis") setSynthesis(e.content ?? "");
          else if (e.type === "error") setError(e.message ?? "");
        });
      } else if (tool === "explain") {
        const resp = await api<{ content: string }>("/api/explain", {
          method: "POST",
          body: { paper_id: q },
        });
        setResult(resp.content);
      } else {
        const path = { litreview: "/api/litreview", compare: "/api/compare",
                       report: "/api/report", bibtex: "/api/bibtex" }[tool];
        const resp = await api<{ content: string }>(path, {
          method: "POST",
          body: { topic: q },
        });
        setResult(resp.content);
      }
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
          {t("nav.research")}
        </Heading>
        <SegmentedControl aria-label="research tool"
                          onChange={(i) => { setTool(TOOLS[i]); reset(); }}>
          {TOOLS.map((tl) => (
            <SegmentedControl.Button key={tl} selected={tool === tl}>
              {t(`research.${tl}`)}
            </SegmentedControl.Button>
          ))}
        </SegmentedControl>
      </Box>

      <Box display="flex" sx={{ gap: 2, mb: 3 }}>
        <TextInput
          block
          placeholder={t(tool === "explain" ? "research.explainPlaceholder" : "research.topicPlaceholder")}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void run()}
        />
        <Button variant="primary" disabled={busy || !topic.trim()} onClick={() => void run()}>
          {busy ? <Spinner size="small" /> : t("research.run")}
        </Button>
      </Box>

      {error && <Flash variant="danger" sx={{ mb: 3 }}>{error}</Flash>}

      {tool === "deep" && (questions.length > 0 || busy) && (
        <Box sx={{ mb: 3 }}>
          <Box display="flex" flexWrap="wrap" sx={{ gap: 2, mb: 2 }}>
            {questions.map((q, i) => (
              <Label key={q} variant={i < sections.length ? "success" : "secondary"}>
                {q.slice(0, 40)}
              </Label>
            ))}
          </Box>
          {sections.map((s) => (
            <Box key={s.question}
                 sx={{ border: "1px solid", borderColor: "border.default",
                       borderRadius: 2, p: 3, mb: 2 }}>
              <Heading as="h3" sx={{ fontSize: 1, mb: 2 }}>{s.question}</Heading>
              <Markdown>{s.content}</Markdown>
            </Box>
          ))}
          {synthesis && (
            <Box sx={{ border: "1px solid", borderColor: "accent.muted",
                       borderRadius: 2, p: 3, bg: "canvas.subtle" }}>
              <Heading as="h3" sx={{ fontSize: 1, mb: 2 }}>{t("research.synthesis")}</Heading>
              <Markdown>{synthesis}</Markdown>
            </Box>
          )}
        </Box>
      )}

      {result && (
        <Box sx={{ border: "1px solid", borderColor: "border.default", borderRadius: 2, p: 3 }}>
          <Box display="flex" sx={{ justifyContent: "flex-end", mb: 1 }}>
            <Button size="small" leadingVisual={CopyIcon}
                    onClick={() => void navigator.clipboard.writeText(result)}>
              {t("research.copy")}
            </Button>
          </Box>
          {tool === "bibtex" ? (
            <Box as="pre" sx={{ fontFamily: "mono", fontSize: 0, whiteSpace: "pre-wrap", m: 0 }}>
              {result}
            </Box>
          ) : (
            <Markdown>{result}</Markdown>
          )}
        </Box>
      )}

      {!busy && !result && sections.length === 0 && !error && (
        <Box sx={{ border: "1px dashed", borderColor: "border.default", borderRadius: 2,
                   p: 5, textAlign: "center" }}>
          <Text sx={{ color: "fg.muted" }}>{t(`research.hint.${tool}`)}</Text>
        </Box>
      )}
    </Box>
  );
}
