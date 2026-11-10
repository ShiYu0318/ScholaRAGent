"""認證端點：註冊/登入/me、OAuth 降級、Discord 綁定。全離線。"""
import pytest
from fastapi.testclient import TestClient

from src import store as store_module
from src.store.sqlite_faiss import SqliteFaissStore


@pytest.fixture
def api(tmp_path, fake_embedder):
    """隔離 store 的 TestClient；不觸碰真正的 data/。"""
    from src.api.app import create_app

    store = SqliteFaissStore(db_path=tmp_path / "api.db", embedder=fake_embedder)
    prev = store_module.set_store(store)
    client = TestClient(create_app())
    yield client
    store_module.set_store(prev)
    store.close()


def _register(api, email="u@example.com", password="password123"):
    return api.post("/auth/register", json={"email": email, "password": password})


def _start_state(api, provider="github"):
    """走 /auth/oauth/{provider} 取得 state（TestClient 會保留 nonce cookie）。"""
    from urllib.parse import parse_qs, urlparse
    resp = api.get(f"/auth/oauth/{provider}", follow_redirects=False)
    assert resp.status_code == 307
    return parse_qs(urlparse(resp.headers["location"]).query)["state"][0]


def test_register_returns_token_and_user(api):
    resp = _register(api)
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"]
    assert data["user"]["email"] == "u@example.com"
    assert "password_hash" not in data["user"]


def test_register_duplicate_email_409(api):
    _register(api)
    assert _register(api).status_code == 409


def test_register_short_password_422(api):
    resp = api.post("/auth/register", json={"email": "x@y.z", "password": "short"})
    assert resp.status_code == 422


def test_login_and_me(api):
    _register(api)
    resp = api.post("/auth/login", json={"email": "u@example.com", "password": "password123"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    me = api.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "u@example.com"


def test_login_wrong_password_401(api):
    _register(api)
    resp = api.post("/auth/login", json={"email": "u@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_me_without_token_401(api):
    assert api.get("/auth/me").status_code == 401
    assert api.get("/auth/me", headers={"Authorization": "Bearer bogus"}).status_code == 401


def test_update_me(api):
    token = _register(api).json()["token"]
    resp = api.patch("/auth/me", json={"display_name": "小明", "locale": "zh"},
                     headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "小明"
    assert resp.json()["locale"] == "zh"


def test_providers_disabled_by_default(api, monkeypatch):
    from src import config
    for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GITHUB_CLIENT_ID",
                "GITHUB_CLIENT_SECRET", "DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET"):
        monkeypatch.setattr(config, key, "")
    resp = api.get("/auth/providers")
    assert resp.json() == {"google": False, "github": False, "discord": False}
    # 未設金鑰的供應商：登入端點降級為 404
    assert api.get("/auth/oauth/google", follow_redirects=False).status_code == 404
    assert api.get("/auth/oauth/unknown", follow_redirects=False).status_code == 404


def test_oauth_start_redirects_when_configured(api, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "sec")
    resp = api.get("/auth/oauth/github", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"].startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=cid" in resp.headers["location"]


def test_discord_link_requires_auth_and_provider(api, monkeypatch):
    from src import config
    assert api.post("/auth/discord/link").status_code == 401
    token = _register(api).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(config, "DISCORD_CLIENT_ID", "")
    monkeypatch.setattr(config, "DISCORD_CLIENT_SECRET", "")
    assert api.post("/auth/discord/link", headers=headers).status_code == 404
    monkeypatch.setattr(config, "DISCORD_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "DISCORD_CLIENT_SECRET", "sec")
    resp = api.post("/auth/discord/link", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("https://discord.com/oauth2/authorize?")


def test_oauth_callback_bad_state_400(api, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "sec")
    resp = api.get("/auth/oauth/github/callback?code=x&state=bogus",
                   follow_redirects=False)
    assert resp.status_code == 400


def test_oauth_callback_login_creates_user(api, monkeypatch):
    """stub 掉與供應商的 token 交換，驗證 callback 建立使用者並轉址帶 token。"""
    from src import config
    from src.api import auth as auth_lib

    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "sec")
    monkeypatch.setattr(auth_lib, "exchange_code",
                        lambda provider, code: {"sub": "gh-1", "email": "gh@example.com",
                                                "email_verified": True, "name": "GH"})
    state = _start_state(api)
    resp = api.get(f"/auth/oauth/github/callback?code=ok&state={state}",
                   follow_redirects=False)
    assert resp.status_code == 307
    assert "token=" in resp.headers["location"]

    store = store_module.get_store()
    user = store.get_user_by_oauth("github_id", "gh-1")
    assert user["email"] == "gh@example.com"

    # 再次登入：不重複建帳號（nonce 一次性，需重新發起）
    state = _start_state(api)
    resp2 = api.get(f"/auth/oauth/github/callback?code=ok&state={state}",
                    follow_redirects=False)
    assert resp2.status_code == 307
    assert store.stats()["users"] == 1


def _oauth_login(api, monkeypatch, profile):
    """以 stub 的供應商資料跑一次 GitHub 登入 callback。"""
    from src import config
    from src.api import auth as auth_lib

    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "sec")
    monkeypatch.setattr(auth_lib, "exchange_code", lambda provider, code: profile)
    state = _start_state(api)
    return api.get(f"/auth/oauth/github/callback?code=ok&state={state}",
                   follow_redirects=False)


def test_oauth_unverified_email_cannot_claim_existing_account(api, monkeypatch):
    _register(api, email="victim@example.com")
    resp = _oauth_login(api, monkeypatch, {
        "sub": "gh-evil", "email": "victim@example.com",
        "email_verified": False, "name": "Evil"})
    assert "error=email_unverified" in resp.headers["location"]
    store = store_module.get_store()
    assert store.get_user_by_email("victim@example.com")["github_id"] is None
    assert store.get_user_by_oauth("github_id", "gh-evil") is None


def test_oauth_verified_email_links_existing_account(api, monkeypatch):
    _register(api, email="me@example.com")
    resp = _oauth_login(api, monkeypatch, {
        "sub": "gh-me", "email": "me@example.com",
        "email_verified": True, "name": "Me"})
    assert "token=" in resp.headers["location"]
    store = store_module.get_store()
    assert store.get_user_by_email("me@example.com")["github_id"] == "gh-me"
    assert store.stats()["users"] == 1


def test_oauth_unverified_email_new_account_uses_placeholder(api, monkeypatch):
    resp = _oauth_login(api, monkeypatch, {
        "sub": "gh-new", "email": "someone@example.com",
        "email_verified": False, "name": "New"})
    assert "token=" in resp.headers["location"]
    store = store_module.get_store()
    assert store.get_user_by_email("someone@example.com") is None
    assert store.get_user_by_oauth("github_id", "gh-new")["email"].endswith(
        "@users.noreply.scholaragent")


def test_oauth_state_from_another_browser_is_rejected(api, monkeypatch):
    """login CSRF：攻擊者把自己的 callback 連結丟給受害者，受害者瀏覽器沒有對應 nonce。"""
    from src import config
    from src.api import auth as auth_lib

    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "sec")
    monkeypatch.setattr(auth_lib, "exchange_code",
                        lambda provider, code: {"sub": "gh-atk", "email": "a@example.com",
                                                "email_verified": True, "name": "A"})
    state = _start_state(api)
    api.cookies.clear()  # 換一個瀏覽器
    resp = api.get(f"/auth/oauth/github/callback?code=ok&state={state}",
                   follow_redirects=False)
    assert resp.status_code == 400
    assert store_module.get_store().stats()["users"] == 0


def test_oauth_start_sets_httponly_nonce_cookie(api, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "GITHUB_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GITHUB_CLIENT_SECRET", "sec")
    resp = api.get("/auth/oauth/github", follow_redirects=False)
    cookie = resp.headers["set-cookie"].lower()
    assert "oauth_nonce=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
