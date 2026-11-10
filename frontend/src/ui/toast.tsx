// 提示訊息：操作結果的短暫回饋，可帶一個動作（例如「前往專案」）。
import i18n from "../i18n";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface ToastItem {
  id: number;
  message: string;
  tone?: "danger";
  action?: ToastAction;
}

interface ToastApi {
  show: (message: string, opts?: { tone?: "danger"; action?: ToastAction }) => void;
  error: (err: unknown) => void;
}

const ToastContext = createContext<ToastApi>({ show: () => {}, error: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const show = useCallback<ToastApi["show"]>((message, opts) => {
    const id = nextId.current++;
    setItems((list) => [...list.slice(-2), { id, message, ...opts }]);
    window.setTimeout(() => setItems((list) => list.filter((t) => t.id !== id)),
                      opts?.action ? 7000 : 4000);
  }, []);

  const error = useCallback<ToastApi["error"]>((err) => {
    show(err instanceof Error && err.message ? err.message : i18n.t("common.error"), { tone: "danger" });
  }, [show]);

  const api = useMemo(() => ({ show, error }), [show, error]);

  // 原生 modal dialog 畫在瀏覽器的 top layer，z-index 再高也蓋不過它。
  // 提示訊息也放進 top layer（popover），而且每次有新訊息就重新開一次，
  // 讓它排到目前開著的對話框上面——否則對話框裡的操作失敗時使用者什麼都看不到。
  const layer = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = layer.current;
    if (!el || typeof el.showPopover !== "function") return;
    if (el.matches(":popover-open")) el.hidePopover();
    if (items.length > 0) el.showPopover();
  }, [items]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      {/* React 18 的型別還沒有 popover 屬性，用展開帶入 */}
      <div ref={layer} {...{ popover: "manual" }} className="toasts" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={t.tone === "danger" ? "toast toast-danger" : "toast"}>
            <span>{t.message}</span>
            {t.action && (
              <button type="button" onClick={() => {
                t.action!.onClick();
                setItems((list) => list.filter((x) => x.id !== t.id));
              }}>
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  return useContext(ToastContext);
}
