// 與後端 API 對應的資料型別與共用查詢。
import { useQuery } from "@tanstack/react-query";

import { api } from "./api";

export type ReadingState = "to-read" | "reading" | "done";
export const READING_STATES: ReadingState[] = ["to-read", "reading", "done"];

export interface Paper {
  id: string;
  title: string;
  abstract?: string;
  authors?: string;
  link?: string;
  published?: string;
  source?: string;
  summary?: string | null;
  in_library?: boolean;
  reproducibility?: { has_code: boolean; repos?: string[] } | null;
  credibility?: { cited_by_count: number; tier: "high" | "medium" | "low" } | null;
  reading?: { state: ReadingState; tags: string[]; note: string } | null;
}

export interface ReadingItem {
  id: string;
  title: string;
  state: ReadingState;
  tags: string[];
  note: string;
}

export interface Project {
  id: number;
  name: string;
  question: string;
  status: "active" | "archived";
  paper_count: number;
  document_count: number;
  conversation_count: number;
  updated_at: string;
}

export type StageKey = "collect" | "read" | "ask" | "synthesize" | "write";
export const STAGES: StageKey[] = ["collect", "read", "ask", "synthesize", "write"];

export interface StageInfo {
  count: number;
  done: boolean;
  total?: number;
  to_read?: number;
  reading?: number;
}

export type DocumentKind = "note" | "review" | "report" | "comparison" | "deep_research" | "outline" | "draft";

export interface DocumentSummary {
  id: number;
  title: string;
  kind: DocumentKind;
  project_id: number | null;
  paper_ids: string[];
  excerpt?: string;
  updated_at: string;
}

export interface DocumentFull extends DocumentSummary {
  content: string;
  papers?: Paper[];
}

export interface ProjectOverview {
  project: Project;
  stages: Record<StageKey, StageInfo>;
  next_step: StageKey | "export";
  recent_documents: DocumentSummary[];
  recent_conversations: { id: number; title: string; updated_at: string }[];
}

export interface Conversation {
  id: number;
  title: string;
  share_token: string | null;
  project_id: number | null;
  updated_at: string;
}

/** 檢索範圍：整個文庫、某個專案，或指定的幾篇論文。 */
export type Scope =
  | { kind: "library" }
  | { kind: "project"; projectId: number }
  | { kind: "papers"; paperIds: string[]; label: string };

export function scopeBody(scope: Scope): { project_id?: number; paper_ids?: string[] } {
  if (scope.kind === "project") return { project_id: scope.projectId };
  if (scope.kind === "papers") return { paper_ids: scope.paperIds };
  return {};
}

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api<{ items: Project[] }>("/api/projects"),
    staleTime: 30_000,
  });
}

export function useReading() {
  return useQuery({
    queryKey: ["reading"],
    queryFn: () => api<{ items: ReadingItem[] }>("/api/reading"),
  });
}

export function shortDate(iso?: string): string {
  return iso ? iso.slice(0, 10) : "";
}
