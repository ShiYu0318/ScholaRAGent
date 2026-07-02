"""認證端點：Email+密碼註冊/登入、OAuth（Google/GitHub）、Discord 帳號綁定。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from src import config
from src.api import auth as auth_lib
from src.api.deps import get_current_user, get_store, public_user
from src.store.base import Store

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None
    locale: str = "en"


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UpdateMeBody(BaseModel):
    display_name: str | None = None
    locale: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


def _token_response(user):
    return {"token": auth_lib.create_token(user["id"]), "user": public_user(user)}


@router.post("/register", status_code=201)
def register(body: RegisterBody, store: Store = Depends(get_store)):
    try:
        user = store.create_user(
            email=body.email,
            password_hash=auth_lib.hash_password(body.password),
            display_name=body.display_name,
            locale=body.locale,
        )
    except ValueError:
        raise HTTPException(status_code=409, detail="此 email 已註冊")
    return _token_response(user)


@router.post("/login")
def login(body: LoginBody, store: Store = Depends(get_store)):
    user = store.get_user_by_email(body.email)
    if not user or not auth_lib.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="email 或密碼錯誤")
    return _token_response(user)


@router.get("/me")
def me(user=Depends(get_current_user)):
    return public_user(user)


@router.patch("/me")
def update_me(body: UpdateMeBody, user=Depends(get_current_user),
              store: Store = Depends(get_store)):
    fields = {}
    if body.display_name is not None:
        fields["display_name"] = body.display_name
    if body.locale is not None:
        fields["locale"] = body.locale
    if body.password is not None:
        fields["password_hash"] = auth_lib.hash_password(body.password)
    updated = store.update_user(user["id"], **fields) if fields else user
    return public_user(updated)


@router.get("/providers")
def providers():
    """回報已設定金鑰的 OAuth 供應商，前端據此顯示登入按鈕。"""
    return {name: auth_lib.provider_enabled(name) for name in auth_lib.PROVIDERS}


def _require_provider(provider):
    if provider not in auth_lib.PROVIDERS:
        raise HTTPException(status_code=404, detail=f"未知供應商：{provider}")
    if not auth_lib.provider_enabled(provider):
        raise HTTPException(status_code=404, detail=f"{provider} 登入未啟用（缺金鑰）")


@router.get("/oauth/{provider}")
def oauth_start(provider: str):
    """導向供應商授權頁（登入模式）。"""
    _require_provider(provider)
    state = auth_lib.create_token(0, purpose="oauth_state", expires_minutes=10,
                                  provider=provider, mode="login")
    return RedirectResponse(auth_lib.authorize_url(provider, state))


@router.post("/discord/link")
def discord_link(user=Depends(get_current_user)):
    """回傳 Discord 綁定授權網址（前端自行導向）。"""
    _require_provider("discord")
    state = auth_lib.create_token(user["id"], purpose="oauth_state", expires_minutes=10,
                                  provider="discord", mode="link")
    return {"url": auth_lib.authorize_url("discord", state)}


@router.delete("/discord/link")
def discord_unlink(user=Depends(get_current_user), store: Store = Depends(get_store)):
    updated = store.update_user(user["id"], discord_id=None)
    return public_user(updated)


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, code: str = "", state: str = "",
                   store: Store = Depends(get_store)):
    _require_provider(provider)
    payload = auth_lib.decode_token(state, purpose="oauth_state")
    if not payload or payload.get("provider") != provider or not code:
        raise HTTPException(status_code=400, detail="OAuth state 無效或已過期")

    try:
        profile = auth_lib.exchange_code(provider, code)
    except Exception:
        return RedirectResponse(f"{config.FRONTEND_URL}/#/auth/callback?error=oauth_failed")

    id_field = auth_lib.PROVIDERS[provider]["id_field"]

    if payload.get("mode") == "link":
        owner = store.get_user_by_oauth(id_field, profile["sub"])
        uid = int(payload["sub"])
        if owner and owner["id"] != uid:
            return RedirectResponse(f"{config.FRONTEND_URL}/#/auth/callback?error=already_linked")
        store.update_user(uid, **{id_field: profile["sub"]})
        return RedirectResponse(f"{config.FRONTEND_URL}/#/auth/callback?linked={provider}")

    # 登入模式：先比對供應商 id，其次同 email 帳號自動綁定，否則新建
    user = store.get_user_by_oauth(id_field, profile["sub"])
    if not user and profile.get("email"):
        user = store.get_user_by_email(profile["email"])
        if user:
            store.update_user(user["id"], **{id_field: profile["sub"]})
    if not user:
        email = profile.get("email") or f"{provider}-{profile['sub']}@users.noreply.air-agent"
        try:
            user = store.create_user(email=email, display_name=profile.get("name"),
                                     **{id_field: profile["sub"]})
        except ValueError:
            raise HTTPException(status_code=409, detail="帳號建立衝突，請改用 email 登入")

    token = auth_lib.create_token(user["id"])
    return RedirectResponse(f"{config.FRONTEND_URL}/#/auth/callback?token={token}")
