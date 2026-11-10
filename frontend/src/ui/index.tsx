// 基礎元件：薄薄一層，樣式都在 styles/components.css。
// 原則：能用原生元素就用原生（button / dialog / select），鍵盤與語意不必自己重做。
import { Loader2, X, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  forwardRef,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ---------- 按鈕 ----------
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "primary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  loading?: boolean;
  block?: boolean;
}

export function Button({
  variant = "default", size = "md", icon: Icon, loading, block, className, children,
  disabled, type = "button", ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx("btn", variant !== "default" && `btn-${variant}`,
                    size !== "md" && `btn-${size}`, block && "btn-block", className)}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 size={14} className="spin-icon" /> : Icon && <Icon size={14} />}
      {children}
    </button>
  );
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  label: string;
  pressed?: boolean;
}

export function IconButton({ icon: Icon, label, pressed, className, ...rest }: IconButtonProps) {
  return (
    <button
      type="button"
      className={cx("icon-btn", className)}
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      {...rest}
    >
      <Icon size={16} />
    </button>
  );
}

// ---------- 表單 ----------
export function Field({ label, hint, children }: { label: string; hint?: string; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id)}
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  );
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon?: LucideIcon;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { icon: Icon, className, ...rest }, ref,
) {
  const input = <input ref={ref} className={cx("input", className)} {...rest} />;
  if (!Icon) return input;
  return (
    <div className="input-wrap">
      <Icon size={14} />
      {input}
    </div>
  );
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...rest }, ref) {
    return <textarea ref={ref} className={cx("textarea", className)} {...rest} />;
  },
);

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cx("select", className)} {...rest}>
      {children}
    </select>
  );
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="switch">
      <input type="checkbox" role="switch" checked={checked} aria-label={label}
             onChange={(e) => onChange(e.target.checked)} />
      <span className="switch-track" />
    </label>
  );
}

// ---------- 顯示 ----------
export function Badge({ tone, children }: { tone?: "accent" | "ok" | "warn" | "danger"; children: ReactNode }) {
  return <span className={cx("badge", tone && `badge-${tone}`)}>{children}</span>;
}

export function Spinner() {
  return <span className="spinner" role="status" aria-label="loading" />;
}

export function Notice({ tone, children }: { tone?: "danger" | "ok" | "warn"; children: ReactNode }) {
  return <div className={cx("notice", tone && `notice-${tone}`)} role={tone === "danger" ? "alert" : "status"}>{children}</div>;
}

export function Empty({ icon: Icon, title, children, action }: { icon?: LucideIcon; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      {Icon && <Icon size={28} strokeWidth={1.4} className="empty-icon" />}
      <div className="empty-title">{title}</div>
      {children && <div style={{ maxWidth: "44ch" }}>{children}</div>}
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
}

/** 資料區塊的三種狀態：載入中 / 失敗 / 無資料。都不是時不渲染任何東西。 */
export function QueryState({ loading, error, empty, emptyState }: { loading?: boolean; error?: boolean; empty?: boolean; emptyState?: ReactNode }) {
  const { t } = useTranslation();
  if (loading) {
    return (
      <div className="empty" style={{ padding: "24px" }}>
        <Spinner />
      </div>
    );
  }
  if (error) return <div style={{ padding: 16 }}><Notice tone="danger">{t("common.loadFailed")}</Notice></div>;
  if (empty) return <>{emptyState ?? <Empty title={t("common.nothingHere")} />}</>;
  return null;
}

export function PageHead({ kicker, title, children, actions }: { kicker?: ReactNode; title: ReactNode; children?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="page-head">
      {kicker && <div className="page-kicker">{kicker}</div>}
      <div className="spread" style={{ alignItems: "flex-start" }}>
        <div className="grow">
          <h1>{title}</h1>
          {children && <p>{children}</p>}
        </div>
        {actions && <div className="row-wrap" style={{ flex: "none" }}>{actions}</div>}
      </div>
    </header>
  );
}

export function Panel({ title, action, children, pad }: { title?: ReactNode; action?: ReactNode; children: ReactNode; pad?: boolean }) {
  return (
    <section className="panel">
      {(title || action) && (
        <div className="panel-head">
          <span className="panel-title">{title}</span>
          {action}
        </div>
      )}
      <div className={pad ? "panel-pad" : undefined}>{children}</div>
    </section>
  );
}

// ---------- 分頁 ----------
export interface TabItem<T extends string> {
  key: T;
  label: string;
  count?: number;
}

export function Tabs<T extends string>({ items, value, onChange, label }: { items: TabItem<T>[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map((it) => (
        <button key={it.key} role="tab" type="button" className="tab"
                aria-selected={value === it.key} onClick={() => onChange(it.key)}>
          {it.label}
          {it.count !== undefined && <span className="tab-count">{it.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Segmented<T extends string>({ items, value, onChange, label }: { items: { key: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {items.map((it) => (
        <button key={it.key} type="button" aria-pressed={value === it.key} onClick={() => onChange(it.key)}>
          {it.label}
        </button>
      ))}
    </div>
  );
}

// ---------- 浮層 ----------
/** 原生 <dialog>：焦點鎖定、Esc 關閉、背景不可互動都由瀏覽器處理。 */
function useDialog(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);
  const props = {
    ref,
    onClose,
    // 點到 backdrop（事件目標是 dialog 本身）就關閉
    onMouseDown: (e: React.MouseEvent<HTMLDialogElement>) => {
      if (e.target === ref.current) onClose();
    },
  };
  return props;
}

export function Dialog({ open, onClose, title, children, footer, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  const props = useDialog(open, onClose);
  const closeLabel = useTranslation().t("common.close");
  return (
    <dialog className={cx("dialog", wide && "dialog-wide")} aria-label={title} {...props}>
      {open && (
        <>
          <div className="dialog-head spread">
            <h3>{title}</h3>
            <IconButton icon={X} label={closeLabel} onClick={onClose} />
          </div>
          <div className="dialog-body">{children}</div>
          {footer && <div className="dialog-foot">{footer}</div>}
        </>
      )}
    </dialog>
  );
}

export function Drawer({ open, onClose, label, header, children }: { open: boolean; onClose: () => void; label: string; header: ReactNode; children: ReactNode }) {
  const props = useDialog(open, onClose);
  const closeLabel = useTranslation().t("common.close");
  return (
    <dialog className="drawer" aria-label={label} {...props}>
      {open && (
        <>
          <div className="drawer-head">
            <div className="grow">{header}</div>
            <IconButton icon={X} label={closeLabel} onClick={onClose} />
          </div>
          <div className="drawer-body">{children}</div>
        </>
      )}
    </dialog>
  );
}

export interface MenuItem {
  label: string;
  icon?: LucideIcon;
  onSelect: () => void;
  danger?: boolean;
  separatorBefore?: boolean;
}

/** 下拉選單：點外面或 Esc 關閉，上下鍵移動焦點。 */
export function Menu({ trigger, items, align = "right", header }: { trigger: (props: { onClick: () => void; "aria-expanded": boolean; "aria-haspopup": "menu" }) => ReactNode; items: MenuItem[]; align?: "left" | "right"; header?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        ref.current?.querySelector<HTMLElement>("[aria-haspopup]")?.focus();
      }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const els = Array.from(ref.current?.querySelectorAll<HTMLElement>("[role=menuitem]") ?? []);
        const i = els.indexOf(document.activeElement as HTMLElement);
        const next = e.key === "ArrowDown" ? (i + 1) % els.length : (i - 1 + els.length) % els.length;
        els[next]?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLElement>("[role=menuitem]")?.focus();
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="menu" ref={ref}>
      {trigger({ onClick: () => setOpen((o) => !o), "aria-expanded": open, "aria-haspopup": "menu" })}
      {open && (
        <div className={cx("menu-pop", align === "left" && "menu-pop-left")} role="menu">
          {header}
          {items.map((it) => (
            <div key={it.label}>
              {it.separatorBefore && <div className="menu-sep" />}
              <button type="button" role="menuitem"
                      className={cx("menu-item", it.danger && "menu-item-danger")}
                      onClick={() => { setOpen(false); it.onSelect(); }}>
                {it.icon && <it.icon size={14} />}
                {it.label}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
