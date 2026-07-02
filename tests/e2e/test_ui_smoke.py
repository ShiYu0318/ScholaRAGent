"""前端關鍵流程 smoke（Playwright，整合測試）。

需要本機 dev servers 與 E2E=1 才會執行（CI 與一般 pytest 自動 skip）：

    uv run uvicorn src.api.app:app --port 8000   # 後端（改過後端要重啟）
    cd frontend && npm run dev                    # 前端 :5173
    E2E=1 uv run pytest tests/e2e -q

流程走真實 API（含 Groq/arXiv 金鑰時的 LLM 生成）；帳號用固定
smoke e2e 使用者，重跑冪等。
"""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("E2E"), reason="設 E2E=1 才跑 UI smoke")

BASE = os.getenv("E2E_BASE_URL", "http://localhost:5173")
EMAIL = "e2e@example.com"
PASSWORD = "password123"


@pytest.fixture(scope="module")
def page():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1360, "height": 900})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.errors = errors
        _sign_in(pg)
        yield pg
        assert not errors, f"頁面 JS 錯誤：{errors}"
        browser.close()


def _sign_in(pg):
    pg.goto(BASE + "/")
    pg.wait_for_selector("text=Sign in", timeout=15000)
    pg.fill("input[type=email]", EMAIL)
    pg.fill("input[type=password]", PASSWORD)
    pg.click("button[type=submit]")
    try:
        pg.wait_for_selector("text=Overview", timeout=5000)
    except Exception:
        # 首跑：帳號不存在，切註冊
        pg.click("text=create an account")
        pg.fill("input[type=email]", EMAIL)
        pg.fill("input[type=password]", PASSWORD)
        pg.click("button[type=submit]")
        pg.wait_for_selector("text=Overview", timeout=10000)


def _nav(pg, label, marker):
    pg.click(f"nav >> text={label}")
    pg.wait_for_selector(f"text={marker}", timeout=15000)


def test_home_cards(page):
    _nav(page, "Overview", "System health")
    page.wait_for_selector("text=ok", timeout=10000)


def test_library_papers_and_kanban(page):
    _nav(page, "Library", "Fetch today")
    page.click("button:has-text('Kanban')")
    page.wait_for_selector("text=To read", timeout=5000)


def test_trends_page(page):
    _nav(page, "Trends", "Top keywords")
    page.wait_for_selector("text=Data sources", timeout=10000)
    page.wait_for_selector("span:has-text('arxiv')", timeout=10000)


def test_analytics_page(page):
    _nav(page, "Analytics", "Reading pipeline")
    page.wait_for_selector("svg[role=img]", timeout=10000)


def test_learning_page(page):
    _nav(page, "Learning", "Skills")


def test_settings_prefs_and_reminder(page):
    _nav(page, "Settings", "Notifications")
    page.wait_for_selector("text=System", timeout=5000)
    # 通知偏好儲存
    page.get_by_label("Hour").fill("8")
    page.locator("button:has-text('Save')").nth(1).click()
    page.wait_for_selector("text=Saved.", timeout=5000)
    # 提醒新增後刪除（冪等）
    page.fill("input[placeholder='What to be reminded of']", "e2e reminder")
    page.fill("input[type=datetime-local]", "2030-01-01T09:00")
    page.click("button:has-text('Add')")
    page.wait_for_selector("text=e2e reminder", timeout=5000)
    # Settings 頁只有提醒列有 Delete IconButton（accessible name 走 tooltip labelledby）
    page.get_by_role("button", name="Delete").last.click()
    page.wait_for_timeout(500)


def test_locale_switch_to_zh_and_back(page):
    _nav(page, "Settings", "Account")
    page.locator("select").first.select_option("zh")
    page.wait_for_selector("text=設定", timeout=5000)
    page.locator("select").first.select_option("en")
    page.wait_for_selector("text=Settings", timeout=5000)
