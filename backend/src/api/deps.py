"""FastAPI 相依注入：儲存後端與目前使用者。"""
from fastapi import Depends, Header, HTTPException

from src import store as store_module
from src.api import auth as auth_lib
from src.store.base import Store


def get_store() -> Store:
    return store_module.get_store()


def _user_from_bearer(authorization, store):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    payload = auth_lib.decode_token(authorization.split(" ", 1)[1].strip())
    if not payload:
        return None
    return store.get_user(int(payload["sub"]))


def get_current_user(authorization: str = Header(default=None),
                     store: Store = Depends(get_store)):
    user = _user_from_bearer(authorization, store)
    if not user:
        raise HTTPException(status_code=401, detail="未登入或憑證無效")
    return user


def get_optional_user(authorization: str = Header(default=None),
                      store: Store = Depends(get_store)):
    """公開端點用：有帶 token 就解析，沒帶回傳 None。"""
    return _user_from_bearer(authorization, store)


def public_user(user):
    """去除敏感欄位的使用者外觀（API 回應用）。"""
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "locale": user["locale"],
        "has_password": bool(user["password_hash"]),
        "google": bool(user["google_sub"]),
        "github": bool(user["github_id"]),
        "discord": bool(user["discord_id"]),
        "created_at": user["created_at"],
    }
