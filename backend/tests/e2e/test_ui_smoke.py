"""End-to-end UI test: one researcher's journey from sign-up to export.

Self-contained: starts tests/e2e/demo_server.py (real API, stubbed LLM and paper
sources, throwaway data) and drives the built frontend with Playwright.

    cd frontend && npm run build
    cd ../backend && uv run playwright install chromium
    E2E=1 uv run pytest tests/e2e -q

Skipped unless E2E=1, because it needs the frontend build and a browser.

Assertions target durable outcomes (a paper is in the library, the text survives a
reload) rather than transient ones (a toast that lasts four seconds, an "unsaved"
indicator that lasts one), and use Playwright's auto-retrying `expect`, so the test
does not depend on how busy the machine is.
"""
import io
import os
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pytest

try:
    from playwright.sync_api import expect
except ImportError:        # collected without the dev group installed
    expect = None

pytestmark = pytest.mark.skipif(not os.getenv("E2E"), reason="set E2E=1 to run the UI test")

BACKEND = Path(__file__).resolve().parents[2]
EMAIL, PASSWORD, NEW_PASSWORD = "researcher@example.com", "password123", "a-better-password"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    assert (BACKEND.parent / "frontend" / "dist" / "index.html").exists(), \
        "build the frontend first: cd frontend && npm run build"
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "tests.e2e.demo_server", "--port", str(port),
         "--data-dir", str(tmp_path_factory.mktemp("demo"))],
        cwd=BACKEND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(url + "/api/health", timeout=1)
                break
            except OSError:
                if proc.poll() is not None:
                    raise RuntimeError(proc.stdout.read().decode(errors="replace"))
                time.sleep(0.5)
        else:
            raise RuntimeError("demo server did not start")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="module")
def page(base_url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1360, "height": 900},
                                      accept_downloads=True)
        # English UI and light theme make selectors stable regardless of the machine
        context.add_init_script(
            "localStorage.setItem('scholaragent.locale','en');"
            "localStorage.setItem('scholaragent.theme','light');")
        pg = context.new_page()
        pg.set_default_timeout(15_000)
        expect.set_options(timeout=15_000)      # CI runners are slower than a laptop
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.base = base_url
        pg.errors = errors
        yield pg
        if os.getenv("E2E_SHOT"):
            pg.screenshot(path=os.environ["E2E_SHOT"])
        browser.close()


def go(pg, path):
    pg.goto(f"{pg.base}/#{path}")


def test_sign_up_lands_on_today_with_a_clear_start(page):
    go(page, "/login")
    page.get_by_role("button", name="Sign up").click()
    page.get_by_label("Display name").fill("Ada")
    page.get_by_label("Email").fill(EMAIL)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Create account").click()
    page.get_by_text("Start with a research question").wait_for()


def test_create_a_project(page):
    page.get_by_role("button", name="New project").first.click()
    page.get_by_label("Project name").fill("Evaluating RAG")
    page.get_by_label("Research question").fill("How should RAG faithfulness be measured?")
    page.get_by_role("button", name="Create", exact=True).click()
    page.get_by_role("heading", name="Evaluating RAG").wait_for()
    # an empty project points at collecting papers first
    page.get_by_text("Start by finding a few papers").wait_for()
    page.project_url = page.url


def test_find_and_import_papers_into_the_project(page):
    page.get_by_role("link", name="Find papers").first.click()
    page.get_by_role("textbox", name="Search", exact=True).fill("retrieval augmented generation evaluation")
    page.get_by_role("button", name="Search", exact=True).click()
    page.get_by_text("4 results").wait_for()
    # the project is preselected as the import target
    assert page.get_by_label("Import into").input_value() != ""
    for title in ("RAGAS: Automated Evaluation of Retrieval Augmented Generation",
                  "ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems"):
        page.get_by_role("checkbox", name=title).check()
    page.get_by_role("button", name="Import 2 selected").click()
    expect(page.get_by_text("In library")).to_have_count(2)


def test_read_a_paper_and_take_notes(page):
    page.goto(page.project_url.split("?")[0] + "?tab=papers")
    page.get_by_role("button", name="RAGAS: Automated Evaluation of Retrieval Augmented Generation").click()
    drawer = page.get_by_role("dialog", name="Paper details")
    drawer.get_by_text("Cited 412 times").wait_for()
    drawer.get_by_role("button", name="Done", exact=True).click()
    note = drawer.get_by_label("Notes")
    note.fill("Reference-free metrics; good baseline.")
    note.blur()
    drawer.get_by_role("button", name="Close").click()
    page.get_by_text("Reference-free metrics; good baseline.").wait_for()
    page.get_by_text("1/2").wait_for()          # trail: one of two papers finished


def test_ask_within_the_project_and_save_the_answer(page):
    page.get_by_role("link", name="Ask this project's papers").or_(
        page.get_by_role("link", name="Ask a question")).first.click()
    box = page.get_by_label("Ask a question…")
    box.fill("How is RAG evaluated?")
    box.press("Enter")
    page.get_by_text("Citation accuracy").wait_for()
    # answers cite only the project's two papers
    expect(page.locator(".cite")).to_have_count(2)
    page.get_by_role("button", name="Save as note").click()
    dialog = page.get_by_role("dialog", name="Save as document")
    dialog.get_by_role("button", name="Save").click()
    expect(dialog).to_be_hidden()            # the dialog closes once the save succeeded


def test_synthesize_a_review_and_keep_it(page):
    go(page, "/research?project=1")
    page.get_by_label("Topic").fill("RAG evaluation")
    page.get_by_role("button", name="Run").click()
    page.get_by_role("heading", name="Themes").wait_for()
    page.get_by_text("Based on 2 papers").wait_for()
    page.get_by_role("button", name="Save as document").click()
    dialog = page.get_by_role("dialog", name="Save as document")
    dialog.get_by_role("button", name="Save").click()
    expect(dialog).to_be_hidden()
    # the saved review is now in the document list; open it from there
    go(page, "/write")
    page.get_by_role("button", name="Literature review: RAG evaluation").click()
    page.wait_for_url("**/write/*")


def test_edit_the_document_with_autosave(page):
    page.get_by_role("heading", name="Themes").wait_for()      # opens in preview
    page.get_by_role("button", name="Edit", exact=True).click()
    editor = page.get_by_label("Content")
    editor.press("End")
    with page.expect_response(lambda r: "/api/documents/" in r.url
                              and r.request.method == "PATCH" and r.ok):
        editor.type("\n\nMy own conclusion.")              # autosave fires after a pause
    page.reload()
    page.get_by_text("My own conclusion.").wait_for()
    page.get_by_text("References (2)").wait_for()


def test_project_shows_progress_and_exports_everything(page):
    page.goto(page.project_url.split("?")[0])
    # collected, read, asked and synthesized: writing a draft is what's left
    page.get_by_text("Start a draft").wait_for()
    page.get_by_role("tab", name="Export").click()
    with page.expect_download() as info:
        page.get_by_role("button", name="Download project").click()
    with zipfile.ZipFile(io.BytesIO(Path(info.value.path()).read_bytes())) as zf:
        names = zf.namelist()
        assert {"README.md", "references.bib", "notes.md"} <= set(names)
        assert len([n for n in names if n.startswith("documents/")]) == 2
        assert zf.read("references.bib").decode().count("@misc{") == 2
        assert "Reference-free metrics" in zf.read("notes.md").decode()


def test_command_palette_jumps_between_pages(page):
    page.keyboard.press("ControlOrMeta+k")
    palette = page.get_by_role("dialog", name="Command palette")
    palette.get_by_role("textbox").fill("libr")
    page.keyboard.press("Enter")
    page.get_by_role("heading", name="Library", exact=True).wait_for()
    expect(page.get_by_role("tab", name="Papers")).to_contain_text("2")


def test_changing_the_password_and_signing_out_everywhere(page):
    go(page, "/settings")
    page.get_by_label("Current password").fill(PASSWORD)
    page.get_by_label("New password").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Change password").click()
    expect(page.get_by_label("New password")).to_have_value("")   # cleared on success
    # this device stays signed in with the reissued token
    page.reload()
    page.get_by_role("heading", name="Settings").wait_for()

    page.get_by_role("button", name="Sign out all").click()
    page.get_by_role("heading", name="Sign in").wait_for()
    page.get_by_label("Email").fill(EMAIL)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("alert").wait_for()                       # old password rejected
    page.get_by_label("Password").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("heading", name="Evaluating RAG").wait_for()


def test_no_console_errors(page):
    # the one expected error is the 401 from the rejected old password
    unexpected = [e for e in page.errors if "401" not in e]
    assert not unexpected, unexpected
