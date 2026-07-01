"""每日個人化過濾，離線 FakeEmbedder。"""
from src.recommend.personalize import personalize_daily


def _p(pid, title):
    return {"id": pid, "title": title, "abstract": title}


def test_ranks_papers_by_profile_similarity(fake_embedder):
    papers = [_p("1", "quantum error correction"),
              _p("2", "graph neural networks molecules")]
    profile = ["graph neural networks for molecules"]
    out = personalize_daily(papers, profile, fake_embedder, top_n=2)
    assert out[0]["id"] == "2"          # 與興趣最相似者排前


def test_top_n_limits_results(fake_embedder):
    papers = [_p("1", "a b"), _p("2", "c d"), _p("3", "e f")]
    out = personalize_daily(papers, ["a b"], fake_embedder, top_n=1)
    assert len(out) == 1


def test_no_profile_returns_prefix_unchanged(fake_embedder):
    papers = [_p("1", "x"), _p("2", "y")]
    assert personalize_daily(papers, [], fake_embedder, top_n=1) == papers[:1]


def test_empty_papers(fake_embedder):
    assert personalize_daily([], ["interest"], fake_embedder) == []
