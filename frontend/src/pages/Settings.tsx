// 設定：帳號與安全、外觀、通知、提醒、系統狀態。一欄到底，每區一個主題。
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { setLocale } from "../i18n";
import { api, setToken, type User } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { Badge, Button, Field, IconButton, Input, Notice, PageHead, Segmented, Select, Switch } from "../ui";
import { useToast } from "../ui/toast";

interface Preferences {
  frequency: "daily" | "weekly" | "off";
  hour: number;
  minute: number;
  timezone: string;
  quiet_start: number | null;
  quiet_end: number | null;
  min_score: number;
  dedupe: boolean;
  channels: string[];
}

interface Reminder {
  id: number;
  text: string;
  due_at: string;
  done: boolean;
}

interface HealthInfo {
  status: string;
  store_backend?: string;
  scheduler?: { running: boolean };
  providers?: Record<string, boolean>;
}

const CHANNELS = ["web", "telegram", "email", "line"] as const;

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section style={{ display: "grid", gridTemplateColumns: "220px minmax(0, 1fr)", gap: 32, padding: "28px 0", borderTop: "1px solid var(--rule)" }}
             className="settings-section">
      <div>
        <h3 style={{ fontSize: 16 }}>{title}</h3>
        {hint && <p className="t-meta" style={{ marginTop: 4 }}>{hint}</p>}
      </div>
      <div className="stack" style={{ maxWidth: 520 }}>{children}</div>
    </section>
  );
}

export function Settings() {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user, refresh, logout } = useAuth();
  const { mode, setMode } = useTheme();

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [reminderText, setReminderText] = useState("");
  const [reminderDue, setReminderDue] = useState("");

  const prefsQuery = useQuery({ queryKey: ["prefs"], queryFn: () => api<Preferences>("/api/notifications/preferences") });
  useEffect(() => { if (prefsQuery.data) setPrefs(prefsQuery.data); }, [prefsQuery.data]);
  const reminders = useQuery({ queryKey: ["reminders"], queryFn: () => api<{ items: Reminder[] }>("/api/reminders") });
  const health = useQuery({ queryKey: ["health"], queryFn: () => api<HealthInfo>("/api/health") });
  const providers = useQuery({ queryKey: ["auth", "providers"], queryFn: () => api<Record<string, boolean>>("/auth/providers") });

  const saveProfile = useMutation({
    mutationFn: () => api<User>("/auth/me", { method: "PATCH", body: { display_name: displayName.trim() } }),
    onSuccess: async () => { await refresh(); toast.show(t("settings.saved")); },
    onError: toast.error,
  });

  // 改密碼後舊 token 全部失效，後端會回一個新 token 讓這個裝置維持登入
  const changePassword = useMutation({
    mutationFn: () =>
      api<User & { token?: string }>("/auth/me", {
        method: "PATCH",
        body: { password: newPassword, current_password: currentPassword || undefined },
      }),
    onSuccess: async (data) => {
      if (data.token) setToken(data.token);
      setCurrentPassword("");
      setNewPassword("");
      await refresh();
      toast.show(t("settings.passwordChanged"));
    },
    onError: toast.error,
  });
  const logoutAll = useMutation({
    mutationFn: () => api("/auth/logout-all", { method: "POST" }),
    onSuccess: logout,
    onError: toast.error,
  });

  const savePrefs = useMutation({
    mutationFn: (body: Preferences) => api<Preferences>("/api/notifications/preferences", { method: "PUT", body }),
    onSuccess: () => toast.show(t("settings.saved")),
    onError: toast.error,
  });
  const refreshReminders = () => void queryClient.invalidateQueries({ queryKey: ["reminders"] });
  const addReminder = useMutation({
    mutationFn: () => api<Reminder>("/api/reminders", { method: "POST", body: { text: reminderText.trim(), due_at: reminderDue } }),
    onSuccess: () => { setReminderText(""); setReminderDue(""); refreshReminders(); },
    onError: toast.error,
  });
  const completeReminder = useMutation({
    mutationFn: (id: number) => api(`/api/reminders/${id}/complete`, { method: "POST" }),
    onSuccess: refreshReminders, onError: toast.error,
  });
  const deleteReminder = useMutation({
    mutationFn: (id: number) => api<void>(`/api/reminders/${id}`, { method: "DELETE" }),
    onSuccess: refreshReminders, onError: toast.error,
  });
  const linkDiscord = useMutation({
    mutationFn: () => api<{ url: string }>("/auth/discord/link", { method: "POST" }),
    onSuccess: (d) => { window.location.href = d.url; },
    onError: toast.error,
  });
  const unlinkDiscord = useMutation({
    mutationFn: () => api<void>("/auth/discord/link", { method: "DELETE" }),
    onSuccess: () => void refresh(),
    onError: toast.error,
  });

  const submitPassword = (e: FormEvent) => { e.preventDefault(); if (newPassword.length >= 8) changePassword.mutate(); };
  const submitReminder = (e: FormEvent) => { e.preventDefault(); if (reminderText.trim() && reminderDue) addReminder.mutate(); };
  const toggleChannel = (channel: string, on: boolean) => {
    if (!prefs) return;
    setPrefs({ ...prefs, channels: on ? [...new Set([...prefs.channels, channel])] : prefs.channels.filter((c) => c !== channel) });
  };

  return (
    <div className="page-narrow" style={{ margin: "0 auto", maxWidth: 820 }}>
      <PageHead title={t("nav.settings")} />

      <Section title={t("settings.profile")} hint={user?.email}>
        <form className="row" style={{ alignItems: "flex-end" }} onSubmit={(e) => { e.preventDefault(); saveProfile.mutate(); }}>
          <div className="grow">
            <Field label={t("settings.displayName")}>
              {(id) => <Input id={id} value={displayName} maxLength={80} onChange={(e) => setDisplayName(e.target.value)} />}
            </Field>
          </div>
          <Button type="submit" loading={saveProfile.isPending} disabled={!displayName.trim() || displayName === user?.display_name}>
            {t("common.save")}
          </Button>
        </form>
      </Section>

      <Section title={t("settings.security")} hint={t("settings.securityHint")}>
        <form className="stack" onSubmit={submitPassword}>
          {user?.has_password && (
            <Field label={t("settings.currentPassword")}>
              {(id) => <Input id={id} type="password" autoComplete="current-password" value={currentPassword}
                              onChange={(e) => setCurrentPassword(e.target.value)} />}
            </Field>
          )}
          <Field label={user?.has_password ? t("settings.newPassword") : t("settings.setPassword")} hint={t("settings.passwordHint")}>
            {(id) => <Input id={id} type="password" autoComplete="new-password" minLength={8} maxLength={128}
                            value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />}
          </Field>
          <div>
            <Button type="submit" loading={changePassword.isPending}
                    disabled={newPassword.length < 8 || (!!user?.has_password && !currentPassword)}>
              {t("settings.changePassword")}
            </Button>
          </div>
        </form>
        <div className="spread" style={{ paddingTop: 16, borderTop: "1px solid var(--rule-soft)" }}>
          <div>
            <div className="t-strong">{t("settings.logoutAll")}</div>
            <div className="t-meta">{t("settings.logoutAllHint")}</div>
          </div>
          <Button variant="danger" loading={logoutAll.isPending} onClick={() => logoutAll.mutate()}>{t("settings.logoutAllAction")}</Button>
        </div>
      </Section>

      <Section title={t("settings.linked")} hint={t("settings.linkedHint")}>
        {(["google", "github"] as const).map((p) => (
          <div key={p} className="spread">
            <span className="t-strong" style={{ textTransform: "capitalize" }}>{p}</span>
            {user?.[p] ? <Badge tone="ok"><Check size={11} />{t("settings.connected")}</Badge> : <Badge>{t("settings.notConnected")}</Badge>}
          </div>
        ))}
        <div className="spread">
          <span className="t-strong">Discord</span>
          {user?.discord
            ? <Button size="sm" loading={unlinkDiscord.isPending} onClick={() => unlinkDiscord.mutate()}>{t("settings.unlink")}</Button>
            : providers.data?.discord
              ? <Button size="sm" loading={linkDiscord.isPending} onClick={() => linkDiscord.mutate()}>{t("settings.link")}</Button>
              : <Badge>{t("settings.unavailable")}</Badge>}
        </div>
      </Section>

      <Section title={t("settings.appearance")}>
        <div className="spread">
          <span>{t("settings.theme")}</span>
          <Segmented label={t("settings.theme")} value={mode} onChange={setMode}
                     items={[{ key: "light", label: t("common.lightTheme") }, { key: "dark", label: t("common.darkTheme") }]} />
        </div>
        <div className="spread">
          <span>{t("settings.language")}</span>
          <Segmented label={t("settings.language")} value={i18n.language === "zh" ? "zh" : "en"} onChange={setLocale}
                     items={[{ key: "zh", label: "繁體中文" }, { key: "en", label: "English" }]} />
        </div>
      </Section>

      <Section title={t("settings.notifications")} hint={t("settings.notificationsHint")}>
        {prefs && (
          <>
            <div className="row" style={{ alignItems: "flex-end" }}>
              <div className="grow">
                <Field label={t("settings.frequency")}>
                  {(id) => (
                    <Select id={id} value={prefs.frequency}
                            onChange={(e) => setPrefs({ ...prefs, frequency: e.target.value as Preferences["frequency"] })}>
                      <option value="daily">{t("settings.daily")}</option>
                      <option value="weekly">{t("settings.weekly")}</option>
                      <option value="off">{t("settings.off")}</option>
                    </Select>
                  )}
                </Field>
              </div>
              <div style={{ width: 120 }}>
                <Field label={t("settings.time")}>
                  {(id) => (
                    <Input id={id} type="time" value={`${String(prefs.hour).padStart(2, "0")}:${String(prefs.minute).padStart(2, "0")}`}
                           onChange={(e) => {
                             const [h, m] = e.target.value.split(":").map(Number);
                             if (!Number.isNaN(h) && !Number.isNaN(m)) setPrefs({ ...prefs, hour: h, minute: m });
                           }} />
                  )}
                </Field>
              </div>
            </div>
            <Field label={t("settings.timezone")} hint={t("settings.timezoneHint")}>
              {(id) => <Input id={id} value={prefs.timezone} maxLength={64} onChange={(e) => setPrefs({ ...prefs, timezone: e.target.value })} />}
            </Field>
            <div className="col">
              <span className="field-label">{t("settings.channels")}</span>
              <div className="row-wrap" style={{ gap: 16 }}>
                {CHANNELS.map((c) => (
                  <label key={c} className="check">
                    <input type="checkbox" checked={prefs.channels.includes(c)} onChange={(e) => toggleChannel(c, e.target.checked)} />
                    {t(`settings.channel.${c}`)}
                  </label>
                ))}
              </div>
            </div>
            <div className="spread">
              <span>{t("settings.dedupe")}</span>
              <Switch checked={prefs.dedupe} onChange={(v) => setPrefs({ ...prefs, dedupe: v })} label={t("settings.dedupe")} />
            </div>
            <div><Button variant="primary" loading={savePrefs.isPending} onClick={() => savePrefs.mutate(prefs)}>{t("common.save")}</Button></div>
          </>
        )}
      </Section>

      <Section title={t("settings.reminders")} hint={t("settings.remindersHint")}>
        <form className="row" onSubmit={submitReminder}>
          <div className="grow">
            <Input value={reminderText} maxLength={500} onChange={(e) => setReminderText(e.target.value)}
                   placeholder={t("settings.reminderPlaceholder")} aria-label={t("settings.reminderPlaceholder")} />
          </div>
          <div style={{ width: 200 }}>
            <Input type="datetime-local" value={reminderDue} aria-label={t("settings.reminderDue")}
                   onChange={(e) => setReminderDue(e.target.value)} />
          </div>
          <Button type="submit" loading={addReminder.isPending} disabled={!reminderText.trim() || !reminderDue}>{t("common.add")}</Button>
        </form>
        {(reminders.data?.items ?? []).map((r) => (
          <div key={r.id} className="row">
            <IconButton icon={Check} label={t("settings.completeReminder")} onClick={() => completeReminder.mutate(r.id)} />
            <span className="grow">{r.text}</span>
            <span className="t-meta num">{r.due_at.replace("T", " ").slice(0, 16)}</span>
            <IconButton icon={Trash2} label={t("common.delete")} onClick={() => deleteReminder.mutate(r.id)} />
          </div>
        ))}
        {reminders.data?.items.length === 0 && <span className="t-meta">{t("settings.noReminders")}</span>}
      </Section>

      <Section title={t("settings.system")} hint={t("settings.systemHint")}>
        {health.isError && <Notice tone="danger">{t("common.error")}</Notice>}
        {health.data && (
          <>
            <div className="row-wrap">
              <Badge tone={health.data.status === "ok" ? "ok" : "danger"}>{health.data.status}</Badge>
              {health.data.store_backend && <span className="mono t-meta">{health.data.store_backend}</span>}
              {health.data.scheduler && (
                <Badge tone={health.data.scheduler.running ? "ok" : undefined}>
                  {health.data.scheduler.running ? t("settings.schedulerOn") : t("settings.schedulerOff")}
                </Badge>
              )}
            </div>
            <div className="row-wrap">
              {Object.entries(health.data.providers ?? {}).map(([name, ok]) => (
                <Badge key={name} tone={ok ? "ok" : undefined}>{name}</Badge>
              ))}
            </div>
          </>
        )}
      </Section>
    </div>
  );
}
