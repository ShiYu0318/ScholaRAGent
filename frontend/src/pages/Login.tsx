// 登入 / 註冊頁：Email+密碼與 OAuth（依 /auth/providers 顯示可用按鈕）。
import { Box, Button, Flash, FormControl, Heading, Text, TextInput } from "@primer/react";
import { MarkGithubIcon, TelescopeIcon } from "@primer/octicons-react";
import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";

import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Providers {
  google: boolean;
  github: boolean;
  discord: boolean;
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

  const providers = useQuery({
    queryKey: ["auth", "providers"],
    queryFn: () => api<Providers>("/auth/providers"),
  });

  if (user) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "signin") await login(email, password);
      else await register(email, password, displayName);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box
      minHeight="100vh"
      bg="canvas.default"
      display="flex"
      alignItems="center"
      justifyContent="center"
      p={3}
    >
      <Box width={340}>
        <Box display="flex" flexDirection="column" alignItems="center" mb={4}>
          <TelescopeIcon size={40} />
          <Heading as="h1" sx={{ fontSize: 4, mt: 2 }}>
            {t("app.name")}
          </Heading>
          <Text sx={{ color: "fg.muted", fontSize: 1 }}>{t("app.tagline")}</Text>
        </Box>

        {error && (
          <Flash variant="danger" sx={{ mb: 3 }}>
            {error}
          </Flash>
        )}

        <Box
          as="form"
          onSubmit={submit}
          sx={{
            bg: "canvas.subtle",
            border: "1px solid",
            borderColor: "border.default",
            borderRadius: 2,
            p: 3,
            display: "grid",
            gap: 3,
          }}
        >
          <FormControl required>
            <FormControl.Label>{t("auth.email")}</FormControl.Label>
            <TextInput
              block
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormControl>
          <FormControl required>
            <FormControl.Label>{t("auth.password")}</FormControl.Label>
            <TextInput
              block
              type="password"
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </FormControl>
          {mode === "signup" && (
            <FormControl>
              <FormControl.Label>{t("auth.displayName")}</FormControl.Label>
              <TextInput
                block
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </FormControl>
          )}
          <Button type="submit" variant="primary" block disabled={busy}>
            {mode === "signin" ? t("auth.submitSignIn") : t("auth.submitSignUp")}
          </Button>
        </Box>

        {(providers.data?.google || providers.data?.github) && (
          <Box mt={3} display="grid" sx={{ gap: 2 }}>
            <Text sx={{ color: "fg.muted", fontSize: 0, textAlign: "center" }}>
              {t("auth.continueWith")}
            </Text>
            {providers.data?.google && (
              <Button block onClick={() => (window.location.href = "/auth/oauth/google")}>
                {t("auth.google")}
              </Button>
            )}
            {providers.data?.github && (
              <Button
                block
                leadingVisual={MarkGithubIcon}
                onClick={() => (window.location.href = "/auth/oauth/github")}
              >
                {t("auth.github")}
              </Button>
            )}
          </Box>
        )}

        <Box mt={3} textAlign="center">
          <Button
            variant="invisible"
            onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
          >
            {mode === "signin" ? t("auth.switchToSignUp") : t("auth.switchToSignIn")}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
