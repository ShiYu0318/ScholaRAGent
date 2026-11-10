// OAuth 轉址落點：#/auth/callback?token=… | ?linked=discord | ?error=…
// token 一讀到就存起來並以 replace 導走，不留在瀏覽紀錄裡。
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../lib/auth";
import { Notice, Spinner } from "../ui";

const ERRORS: Record<string, string> = {
  already_linked: "auth.alreadyLinked",
  email_unverified: "auth.emailUnverified",
};

export function AuthCallback() {
  const { t } = useTranslation();
  const { acceptToken } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;
    const params = new URLSearchParams(location.search);
    const token = params.get("token");
    if (token) {
      void acceptToken(token).then(() => navigate("/", { replace: true }));
    } else if (params.get("linked")) {
      navigate("/settings", { replace: true });
    } else {
      setError(t(ERRORS[params.get("error") ?? ""] ?? "auth.oauthFailed"));
    }
  }, [location.search, acceptToken, navigate, t]);

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      {error ? (
        <div className="stack" style={{ maxWidth: 380, textAlign: "center" }}>
          <Notice tone="danger">{error}</Notice>
          <Link to="/login">{t("auth.backToSignIn")}</Link>
        </div>
      ) : <Spinner />}
    </div>
  );
}
