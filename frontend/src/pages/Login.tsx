// 登入 / 註冊。左側用研究軌跡說明這個產品在做什麼，右側是表單。
import { useQuery } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";

import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { STAGES } from "../lib/types";
import { Button, Field, Input, Notice } from "../ui";

interface Providers {
  google: boolean;
  github: boolean;
}

export function Login() {
  const { t } = useTranslation();
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const providers = useQuery({ queryKey: ["auth", "providers"], queryFn: () => api<Providers>("/auth/providers") });
  if (user) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "signin") await login(email, password);
      else await register(email, password, displayName);
    } catch (err) {
      setError(err instanceof ApiError
        ? (err.status === 429 ? t("auth.tooMany") : err.message)
        : t("common.error"));
    } finally {
      setBusy(false);
    }
  };
  const oauth = [providers.data?.google && "google", providers.data?.github && "github"].filter(Boolean) as string[];

  return (
    <div className="auth">
      <aside className="auth-aside">
        <div className="brand" style={{ padding: 0 }}><BookOpen size={20} className="brand-mark" />ScholaRAGent</div>
        <div>
          <h1 style={{ fontSize: 34, maxWidth: "16ch" }}>{t("auth.pitch")}</h1>
          <p className="t-muted" style={{ marginTop: 12, maxWidth: "44ch", fontSize: 15 }}>{t("auth.pitchBody")}</p>
          <div className="trail trail-compact" style={{ marginTop: 40, maxWidth: 460 }} aria-hidden>
            {STAGES.map((s, i) => (
              <div key={s} className="trail-step" data-done={i < 2} data-next={i === 2}>
                <span className="trail-name">{t(`trail.${s}`)}</span>
              </div>
            ))}
          </div>
        </div>
        <span className="t-meta">{t("auth.footer")}</span>
      </aside>

      <main className="auth-form">
        <div className="auth-card stack">
          <div>
            <h2>{mode === "signin" ? t("auth.signIn") : t("auth.signUp")}</h2>
            <p className="t-meta" style={{ marginTop: 4 }}>
              {mode === "signin" ? t("auth.noAccount") : t("auth.haveAccount")}{" "}
              <button type="button" onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(null); }}
                      style={{ border: 0, background: "none", padding: 0, color: "var(--pencil)", cursor: "pointer", fontWeight: 600 }}>
                {mode === "signin" ? t("auth.signUp") : t("auth.signIn")}
              </button>
            </p>
          </div>
          {error && <Notice tone="danger">{error}</Notice>}
          <form className="stack" onSubmit={submit}>
            {mode === "signup" && (
              <Field label={t("auth.displayName")}>
                {(id) => <Input id={id} value={displayName} maxLength={80} autoComplete="name" onChange={(e) => setDisplayName(e.target.value)} />}
              </Field>
            )}
            <Field label={t("auth.email")}>
              {(id) => <Input id={id} type="email" required autoComplete="email" value={email} autoFocus onChange={(e) => setEmail(e.target.value)} />}
            </Field>
            <Field label={t("auth.password")} hint={mode === "signup" ? t("settings.passwordHint") : undefined}>
              {(id) => <Input id={id} type="password" required minLength={mode === "signup" ? 8 : undefined} maxLength={128}
                              autoComplete={mode === "signin" ? "current-password" : "new-password"}
                              value={password} onChange={(e) => setPassword(e.target.value)} />}
            </Field>
            <Button type="submit" variant="primary" size="lg" block loading={busy}>
              {mode === "signin" ? t("auth.signIn") : t("auth.createAccount")}
            </Button>
          </form>
          {oauth.length > 0 && (
            <>
              <div className="row t-meta"><hr className="divider grow" />{t("auth.or")}<hr className="divider grow" /></div>
              {oauth.map((p) => (
                <a key={p} className="btn btn-lg btn-block" href={`/auth/oauth/${p}`}>
                  {t("auth.continueWith", { provider: p === "google" ? "Google" : "GitHub" })}
                </a>
              ))}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
