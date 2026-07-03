// 設定頁：帳號資料、外觀語言、連結帳號（Discord 綁定）、通知偏好與排程、
// 提醒管理、系統/金鑰狀態。
import {
  Box,
  Button,
  Checkbox,
  Flash,
  Heading,
  IconButton,
  Label,
  SegmentedControl,
  Select,
  Text,
  TextInput,
} from "@primer/react";
import {
  BellIcon,
  CheckIcon,
  ClockIcon,
  LinkIcon,
  PaintbrushIcon,
  PersonIcon,
  ServerIcon,
  TrashIcon,
} from "@primer/octicons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type User } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useThemeMode } from "../theme";
import { Card, CardState } from "../components/Card";

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
  store_backend: string;
  scheduler: { running: boolean; jobs: { id: string; next_run: string | null }[] };
  providers: Record<string, boolean>;
}

const CHANNELS = ["web", "telegram", "email", "line"] as const;

export function Settings() {
  const { t, i18n } = useTranslation();
  const { user, refresh } = useAuth();
  const { mode, toggle } = useThemeMode();
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [saved, setSaved] = useState<string | null>(null);
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [reminderText, setReminderText] = useState("");
  const [reminderDue, setReminderDue] = useState("");

  const prefsQuery = useQuery({
    queryKey: ["notification-prefs"],
    queryFn: () => api<Preferences>("/api/notifications/preferences"),
  });
  useEffect(() => {
    if (prefsQuery.data) setPrefs(prefsQuery.data);
  }, [prefsQuery.data]);

  const reminders = useQuery({
    queryKey: ["reminders"],
    queryFn: () => api<{ items: Reminder[] }>("/api/reminders"),
  });
  const health = useQuery({
    queryKey: ["health", "full"],
    queryFn: () => api<HealthInfo>("/api/health"),
  });

  const flash = (msg: string) => {
    setSaved(msg);
    setTimeout(() => setSaved(null), 2500);
  };

  const saveAccount = useMutation({
    mutationFn: (body: Partial<User>) =>
      api<User>("/auth/me", { method: "PATCH", body }),
    onSuccess: async (updated) => {
      await refresh();
      if (updated.locale && updated.locale !== i18n.language) {
        i18n.changeLanguage(updated.locale);
        localStorage.setItem("ragency.locale", updated.locale);
      }
      flash(t("settings.saved"));
    },
  });

  const savePrefs = useMutation({
    mutationFn: (body: Preferences) =>
      api<Preferences>("/api/notifications/preferences", { method: "PUT", body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-prefs"] });
      flash(t("settings.saved"));
    },
  });

  const addReminder = useMutation({
    mutationFn: () =>
      api<Reminder>("/api/reminders", {
        method: "POST",
        body: { text: reminderText.trim(), due_at: reminderDue },
      }),
    onSuccess: () => {
      setReminderText("");
      setReminderDue("");
      queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });

  const completeReminder = useMutation({
    mutationFn: (id: number) =>
      api<{ ok: boolean }>(`/api/reminders/${id}/complete`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reminders"] }),
  });

  const deleteReminder = useMutation({
    mutationFn: (id: number) => api<void>(`/api/reminders/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reminders"] }),
  });

  const linkDiscord = useMutation({
    mutationFn: () => api<{ url: string }>("/auth/discord/link", { method: "POST" }),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
  });

  const unlinkDiscord = useMutation({
    mutationFn: () => api<void>("/auth/discord/link", { method: "DELETE" }),
    onSuccess: () => refresh(),
  });

  const setChannel = (channel: string, on: boolean) => {
    if (!prefs) return;
    const channels = on
      ? [...new Set([...prefs.channels, channel])]
      : prefs.channels.filter((c) => c !== channel);
    setPrefs({ ...prefs, channels });
  };

  return (
    <Box>
      <Heading as="h2" sx={{ fontSize: 3, mb: 3 }}>
        {t("nav.settings")}
      </Heading>
      {saved && (
        <Flash variant="success" sx={{ mb: 3 }}>
          {saved}
        </Flash>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 3,
          alignItems: "start",
        }}
      >
        <Card title={t("settings.account")} icon={PersonIcon}>
          <Box sx={{ display: "grid", gap: 3 }}>
            <Box>
              <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                Email
              </Text>
              <Text sx={{ fontSize: 1, fontFamily: "mono" }}>{user?.email}</Text>
            </Box>
            <Box>
              <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                {t("auth.displayName")}
              </Text>
              <TextInput
                block
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </Box>
            <Box>
              <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                {t("common.language")}
              </Text>
              <Select
                block
                value={user?.locale || i18n.language}
                onChange={(e) =>
                  saveAccount.mutate({ locale: e.target.value })
                }
              >
                <Select.Option value="en">English</Select.Option>
                <Select.Option value="zh">繁體中文</Select.Option>
              </Select>
            </Box>
            <Button
              variant="primary"
              disabled={saveAccount.isPending}
              onClick={() => saveAccount.mutate({ display_name: displayName })}
            >
              {t("common.save")}
            </Button>
          </Box>
        </Card>

        <Card title={t("settings.appearance")} icon={PaintbrushIcon}>
          <Box sx={{ display: "grid", gap: 2 }}>
            <Text sx={{ fontSize: 0, color: "fg.muted" }}>{t("common.theme")}</Text>
            <SegmentedControl aria-label={t("common.theme")}>
              <SegmentedControl.Button
                selected={mode === "night"}
                onClick={() => mode !== "night" && toggle()}
              >
                {t("common.themeNight")}
              </SegmentedControl.Button>
              <SegmentedControl.Button
                selected={mode === "day"}
                onClick={() => mode !== "day" && toggle()}
              >
                {t("common.themeDay")}
              </SegmentedControl.Button>
            </SegmentedControl>
          </Box>
        </Card>

        <Card title={t("settings.linked")} icon={LinkIcon}>
          <Box sx={{ display: "grid", gap: 2 }}>
            {(["google", "github"] as const).map((p) => (
              <Box key={p} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Text sx={{ fontSize: 1, flex: 1, textTransform: "capitalize" }}>{p}</Text>
                <Label variant={user?.[p] ? "success" : "secondary"}>
                  {user?.[p] ? t("settings.linkedYes") : t("settings.linkedNo")}
                </Label>
              </Box>
            ))}
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Text sx={{ fontSize: 1, flex: 1 }}>Discord</Text>
              {user?.discord ? (
                <Button
                  size="small"
                  variant="danger"
                  disabled={unlinkDiscord.isPending}
                  onClick={() => unlinkDiscord.mutate()}
                >
                  {t("settings.unlink")}
                </Button>
              ) : (
                <Button
                  size="small"
                  disabled={linkDiscord.isPending}
                  onClick={() => linkDiscord.mutate()}
                >
                  {t("settings.link")}
                </Button>
              )}
            </Box>
            {linkDiscord.isError && (
              <Text sx={{ fontSize: 0, color: "danger.fg" }}>
                {t("settings.linkUnavailable")}
              </Text>
            )}
          </Box>
        </Card>

        <Card title={t("settings.notifications")} icon={BellIcon}>
          <CardState loading={prefsQuery.isPending} error={prefsQuery.isError} />
          {prefs && (
            <Box sx={{ display: "grid", gap: 3 }}>
              <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}>
                <Box>
                  <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                    {t("settings.frequency")}
                  </Text>
                  <Select
                    block
                    value={prefs.frequency}
                    onChange={(e) =>
                      setPrefs({ ...prefs, frequency: e.target.value as Preferences["frequency"] })
                    }
                  >
                    <Select.Option value="daily">{t("settings.freqDaily")}</Select.Option>
                    <Select.Option value="weekly">{t("settings.freqWeekly")}</Select.Option>
                    <Select.Option value="off">{t("settings.freqOff")}</Select.Option>
                  </Select>
                </Box>
                <Box>
                  <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                    {t("settings.time")}
                  </Text>
                  <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                    <TextInput
                      type="number"
                      min={0}
                      max={23}
                      sx={{ width: 64 }}
                      aria-label={t("settings.hour")}
                      value={String(prefs.hour)}
                      onChange={(e) =>
                        setPrefs({ ...prefs, hour: Number(e.target.value) || 0 })
                      }
                    />
                    <Text>:</Text>
                    <TextInput
                      type="number"
                      min={0}
                      max={59}
                      sx={{ width: 64 }}
                      aria-label={t("settings.minute")}
                      value={String(prefs.minute)}
                      onChange={(e) =>
                        setPrefs({ ...prefs, minute: Number(e.target.value) || 0 })
                      }
                    />
                  </Box>
                </Box>
              </Box>
              <Box>
                <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                  {t("settings.timezone")}
                </Text>
                <TextInput
                  block
                  value={prefs.timezone}
                  onChange={(e) => setPrefs({ ...prefs, timezone: e.target.value })}
                />
              </Box>
              <Box>
                <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
                  {t("settings.channels")}
                </Text>
                <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap" }}>
                  {CHANNELS.map((c) => (
                    <Box key={c} as="label" sx={{ display: "flex", gap: 1, alignItems: "center", cursor: "pointer" }}>
                      <Checkbox
                        checked={prefs.channels.includes(c)}
                        onChange={(e) => setChannel(c, e.target.checked)}
                        aria-label={c}
                      />
                      <Text sx={{ fontSize: 1 }}>{c}</Text>
                    </Box>
                  ))}
                </Box>
              </Box>
              <Box as="label" sx={{ display: "flex", gap: 2, alignItems: "center", cursor: "pointer" }}>
                <Checkbox
                  checked={prefs.dedupe}
                  onChange={(e) => setPrefs({ ...prefs, dedupe: e.target.checked })}
                  aria-label={t("settings.dedupe")}
                />
                <Text sx={{ fontSize: 1 }}>{t("settings.dedupe")}</Text>
              </Box>
              <Button
                variant="primary"
                disabled={savePrefs.isPending}
                onClick={() => savePrefs.mutate(prefs)}
              >
                {t("common.save")}
              </Button>
            </Box>
          )}
        </Card>

        <Card title={t("settings.reminders")} icon={ClockIcon}>
          <CardState
            loading={reminders.isPending}
            error={reminders.isError}
            empty={reminders.data?.items.length === 0}
          />
          <Box sx={{ display: "grid", gap: 2 }}>
            {reminders.data?.items.map((r) => (
              <Box key={r.id} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <Text sx={{ fontSize: 1, display: "block" }}>{r.text}</Text>
                  <Text sx={{ fontSize: 0, color: "fg.muted", fontFamily: "mono" }}>
                    {r.due_at.replace("T", " ").slice(0, 16)}
                  </Text>
                </Box>
                <IconButton
                  aria-label={t("settings.completeReminder")}
                  icon={CheckIcon}
                  size="small"
                  variant="invisible"
                  onClick={() => completeReminder.mutate(r.id)}
                />
                <IconButton
                  aria-label={t("common.delete")}
                  icon={TrashIcon}
                  size="small"
                  variant="invisible"
                  onClick={() => deleteReminder.mutate(r.id)}
                />
              </Box>
            ))}
            <Box sx={{ display: "grid", gap: 2, mt: 2 }}>
              <TextInput
                placeholder={t("settings.reminderPlaceholder")}
                value={reminderText}
                onChange={(e) => setReminderText(e.target.value)}
              />
              <Box sx={{ display: "flex", gap: 2 }}>
                <TextInput
                  sx={{ flex: 1 }}
                  type="datetime-local"
                  aria-label={t("settings.reminderDue")}
                  value={reminderDue}
                  onChange={(e) => setReminderDue(e.target.value)}
                />
                <Button
                  disabled={!reminderText.trim() || !reminderDue || addReminder.isPending}
                  onClick={() => addReminder.mutate()}
                >
                  {t("settings.addReminder")}
                </Button>
              </Box>
            </Box>
          </Box>
        </Card>

        <Card title={t("settings.system")} icon={ServerIcon}>
          <CardState loading={health.isPending} error={health.isError} />
          {health.data && (
            <Box sx={{ display: "grid", gap: 2 }}>
              <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
                <Label variant={health.data.status === "ok" ? "success" : "danger"}>
                  {health.data.status}
                </Label>
                <Text sx={{ fontFamily: "mono", fontSize: 0, color: "fg.muted" }}>
                  {health.data.store_backend}
                </Text>
                <Label variant={health.data.scheduler.running ? "success" : "secondary"}>
                  {health.data.scheduler.running
                    ? t("settings.schedulerOn")
                    : t("settings.schedulerOff")}
                </Label>
              </Box>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                {Object.entries(health.data.providers).map(([name, ok]) => (
                  <Label key={name} variant={ok ? "success" : "secondary"}>
                    {name}
                  </Label>
                ))}
              </Box>
            </Box>
          )}
        </Card>
      </Box>
    </Box>
  );
}
