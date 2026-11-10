// 「下一步」：依專案目前走到的階段，給一個明確的動作。
import { ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { StageKey } from "../lib/types";

export function nextStepLink(projectId: number, step: StageKey | "export"): string {
  switch (step) {
    case "collect": return `/discover?project=${projectId}`;
    case "read": return `/projects/${projectId}?tab=papers`;
    case "ask": return `/ask?project=${projectId}`;
    case "synthesize": return `/research?project=${projectId}`;
    case "write": return `/write?project=${projectId}&new=1`;
    default: return `/projects/${projectId}?tab=export`;
  }
}

export function NextStep({ projectId, step }: { projectId: number; step: StageKey | "export" }) {
  const { t } = useTranslation();
  return (
    <div className="next-step">
      <div className="next-step-body">
        <div className="t-label" style={{ color: "var(--pencil)" }}>{t("next.label")}</div>
        <div className="next-step-title">{t(`next.${step}.title`)}</div>
        <div className="t-meta" style={{ marginTop: 2 }}>{t(`next.${step}.body`)}</div>
      </div>
      <Link className="btn btn-primary" to={nextStepLink(projectId, step)}>
        {t(`next.${step}.action`)}
        <ArrowRight size={14} />
      </Link>
    </div>
  );
}
