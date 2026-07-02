// OAuth 轉址落點：#/auth/callback?token=… | ?linked=discord | ?error=…
import { Box, Flash, Spinner } from "@primer/react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../lib/auth";

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
    const linked = params.get("linked");
    const err = params.get("error");

    if (token) {
      void acceptToken(token).then(() => navigate("/", { replace: true }));
    } else if (linked) {
      navigate("/settings", { replace: true });
    } else {
      setError(err === "already_linked" ? t("auth.alreadyLinked") : t("auth.oauthFailed"));
    }
  }, [location.search, acceptToken, navigate, t]);

  return (
    <Box minHeight="100vh" bg="canvas.default" display="flex" alignItems="center" justifyContent="center">
      {error ? (
        <Box>
          <Flash variant="danger">{error}</Flash>
          <Box mt={3} textAlign="center">
            <Link to="/login">{t("auth.signIn")}</Link>
          </Box>
        </Box>
      ) : (
        <Spinner />
      )}
    </Box>
  );
}
