"""外部資料清理：連結 scheme 與 CSV 公式注入。"""
import csv
import io

import pytest

from src.api.services.library import LibraryService
from src.store.sqlite_faiss import SqliteFaissStore
from src.utils.text_safety import csv_safe, safe_link


@pytest.mark.parametrize("link", ["javascript:alert(1)", "JaVaScRiPt:alert(1)",
                                  "data:text/html,<script>", "vbscript:x", "file:///etc/passwd",
                                  " javascript:alert(1)", "", None, "//evil.example.com"])
def test_safe_link_drops_non_http(link):
    assert safe_link(link) == ""


def test_safe_link_keeps_http_and_https():
    assert safe_link(" https://arxiv.org/abs/1 ") == "https://arxiv.org/abs/1"
    assert safe_link("http://example.com") == "http://example.com"


@pytest.mark.parametrize("value", ["=1+1", "+cmd", "-2+3", "@SUM(A1)", "\tx", "\rx"])
def test_csv_safe_neutralises_formula_prefixes(value):
    assert csv_safe(value) == "'" + value


def test_csv_safe_leaves_normal_values():
    assert csv_safe("Attention Is All You Need") == "Attention Is All You Need"
    assert csv_safe(3) == 3


def test_store_drops_unsafe_links_and_export_escapes_formulas(tmp_path, fake_embedder):
    store = SqliteFaissStore(db_path=tmp_path / "t.db", embedder=fake_embedder)
    store.upsert_papers([{"id": "x1", "title": '=HYPERLINK("http://evil","click")',
                          "abstract": "a", "link": "javascript:alert(1)", "source": "rss"}])
    assert store.get_paper("x1")["link"] == ""
    rows = list(csv.DictReader(io.StringIO(LibraryService(store).export_csv())))
    assert rows[0]["title"].startswith("'=")
    store.close()
