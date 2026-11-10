// 研究軌跡：蒐集 → 閱讀 → 提問 → 綜述 → 寫作。
// 整個產品的招牌元素：一條有站點的線，走過的站點塗滿墨色，下一站是紅筆圈起來的那個。
import { useTranslation } from "react-i18next";

import { STAGES, type StageInfo, type StageKey } from "../lib/types";

interface Props {
  stages: Record<StageKey, StageInfo>;
  next: StageKey | "export";
  onSelect?: (stage: StageKey) => void;
  compact?: boolean;
}

export function ResearchTrail({ stages, next, onSelect, compact }: Props) {
  const { t } = useTranslation();
  return (
    <div className={compact ? "trail trail-compact" : "trail"} role="list" aria-label={t("trail.label")}>
      {STAGES.map((key) => {
        const stage = stages[key];
        const figure = key === "read" ? `${stage.count}/${stage.total ?? 0}` : String(stage.count);
        const content = (
          <>
            <span className="trail-name">{t(`trail.${key}`)}</span>
            <span className="trail-figure">{figure}</span>
            <span className="trail-unit">{t(`trail.unit.${key}`)}</span>
          </>
        );
        const common = {
          className: "trail-step",
          "data-done": stage.done,
          "data-next": next === key,
          role: "listitem" as const,
        };
        return onSelect && !compact ? (
          <button key={key} type="button" {...common} onClick={() => onSelect(key)}
                  aria-label={`${t(`trail.${key}`)} ${figure} ${t(`trail.unit.${key}`)}`}>
            {content}
          </button>
        ) : (
          <div key={key} {...common}>{content}</div>
        );
      })}
    </div>
  );
}
