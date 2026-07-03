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
                                                "name": "GH"})
    state = auth_lib.create_token(0, purpose="oauth_state", expires_minutes=5,
                                  provider="github", mode="login")
    resp = api.get(f"/auth/oauth/github/callback?code=ok&state={state}",
                   follow_redirects=False)
    assert resp.status_code == 307
    assert "token=" in resp.headers["location"]

    store = store_module.get_store()
    user = store.get_user_by_oauth("github_id", "gh-1")
    assert user["email"] == "gh@example.com"

    # 再次登入：不重複建帳號
    resp2 = api.get(f"/auth/oauth/github/callback?code=ok&state={state}",
                    follow_redirects=False)
    assert resp2.status_code == 307
    assert store.stats()["users"] == 1
