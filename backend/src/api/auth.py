"""認證基礎：bcrypt 密碼雜湊、JWT 簽發/驗證、OAuth 供應商設定。

Python 3.13 環境直接用 bcrypt 與 PyJWT（passlib/python-jose 相容性差）。
JWT_SECRET 未設定時以行程隨機值代替：重啟即失效，只適合本機開發。
"""
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt

from src import config
from src.utils.logger import get_logger

logger = get_logger("api.auth")

_ALGO = "HS256"
_EPHEMERAL_SECRET = secrets.token_urlsafe(32)


def _secret():
    return config.JWT_SECRET or _EPHEMERAL_SECRET


# ---- 密碼 ----
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


# ---- JWT ----
def create_token(user_id, purpose="auth", expires_minutes=None, **extra):
    now = datetime.now(timezone.utc)
    minutes = expires_minutes or config.JWT_EXPIRE_MINUTES
    payload = {
        "sub": str(user_id),
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        **extra,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def decode_token(token: str, purpose="auth"):
    """驗證並解碼 token；無效/過期/用途不符回傳 None。"""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != purpose:
        return None
    return payload


# ---- OAuth 供應商 ----
# 金鑰未設定的供應商視為停用（前端據 /auth/providers 隱藏按鈕）。
PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
        "id_field": "google_sub",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "id_field": "github_id",
    },
    "discord": {
        "authorize_url": "https://discord.com/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "userinfo_url": "https://discord.com/api/users/@me",
        "scope": "identify email",
        "id_field": "discord_id",
    },
}


def provider_credentials(name):
    creds = {
        "google": (config.GOOGLE_CLIENT_ID, config.GOOGLE_CLIENT_SECRET),
        "github": (config.GITHUB_CLIENT_ID, config.GITHUB_CLIENT_SECRET),
        "discord": (config.DISCORD_CLIENT_ID, config.DISCORD_CLIENT_SECRET),
    }.get(name, ("", ""))
    return creds


def provider_enabled(name):
    cid, csecret = provider_credentials(name)
    return bool(cid and csecret)


def redirect_uri(provider):
    return f"{config.API_PUBLIC_URL}/auth/oauth/{provider}/callback"


def authorize_url(provider, state):
    cid, _ = provider_credentials(provider)
    meta = PROVIDERS[provider]
    params = httpx.QueryParams(
        client_id=cid,
        redirect_uri=redirect_uri(provider),
        response_type="code",
        scope=meta["scope"],
        state=state,
    )
    return f"{meta['authorize_url']}?{params}"


def exchange_code(provider, code):
    """用授權碼換 access token 並抓使用者資料。

    回傳 {"sub": 供應商使用者 id, "email": ..., "name": ...}；失敗丟 RuntimeError。
    """
    cid, csecret = provider_credentials(provider)
    meta = PROVIDERS[provider]
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            meta["token_url"],
            data={
                "client_id": cid,
                "client_secret": csecret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri(provider),
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        access_token = resp.json().get("access_token")
        if not access_token:
            raise RuntimeError(f"{provider} 未回傳 access_token")

        prof = client.get(
            meta["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        prof.raise_for_status()
        data = prof.json()

        if provider == "google":
            return {"sub": data["sub"], "email": data.get("email"),
                    "name": data.get("name")}
        if provider == "github":
            email = data.get("email")
            if not email:
                emails = client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"},
                ).json()
                primary = next((e for e in emails if e.get("primary")), None)
                email = (primary or (emails[0] if emails else {})).get("email")
            return {"sub": str(data["id"]), "email": email,
                    "name": data.get("name") or data.get("login")}
        # discord
        return {"sub": str(data["id"]), "email": data.get("email"),
                "name": data.get("global_name") or data.get("username")}
