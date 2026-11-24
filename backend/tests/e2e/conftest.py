"""Save a screenshot of the page whenever an end-to-end step fails.

Screenshots go to $E2E_ARTIFACTS (default: backend/e2e-artifacts/), one per failing test,
so a failure in CI can be inspected without reproducing it locally. CI uploads the folder.
"""
import os
import re
from pathlib import Path

import pytest

ARTIFACTS = Path(os.getenv("E2E_ARTIFACTS", Path(__file__).resolve().parents[2] / "e2e-artifacts"))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page is not None:
            ARTIFACTS.mkdir(parents=True, exist_ok=True)
            name = re.sub(r"[^\w.-]+", "_", item.name)
            try:
                page.screenshot(path=str(ARTIFACTS / f"{name}.png"), full_page=True)
                (ARTIFACTS / f"{name}.url.txt").write_text(page.url + "\n", encoding="utf-8")
            except Exception as exc:  # noqa: BLE001 - never mask the real failure
                print(f"could not save e2e screenshot: {exc}")
    return report
