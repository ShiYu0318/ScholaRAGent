"""多 agent 協作管線，純編排、離線。"""
from src.agent.multi_agent import MultiAgentPipeline


def test_revises_when_critic_rejects_then_accepts():
    calls = {"writer": 0}

    def planner(q):
        return ["s1", "s2"]

    def retrieve(sub):
        return [{"id": sub}]

    def writer(q, ctx, issues=None):
        calls["writer"] += 1
        return "revised" if issues else "draft"

    def critic(q, draft, ctx):
        return (draft == "revised", ["需補充實驗"])   # 初稿被打回

    pipe = MultiAgentPipeline(planner, retrieve, writer, critic, max_revisions=1)
    assert pipe.run("q") == "revised"
    assert calls["writer"] == 2                        # 初稿 + 修訂各一次


def test_accepts_good_draft_without_revision():
    calls = {"writer": 0}

    def writer(q, ctx, issues=None):
        calls["writer"] += 1
        return "draft"

    pipe = MultiAgentPipeline(
        planner=lambda q: ["s"],
        retrieve=lambda s: [{"id": s}],
        writer=writer,
        critic=lambda q, d, c: (True, []),
        max_revisions=2,
    )
    assert pipe.run("q") == "draft"
    assert calls["writer"] == 1


def test_stops_at_max_revisions():
    calls = {"writer": 0}

    def writer(q, ctx, issues=None):
        calls["writer"] += 1
        return "draft"

    pipe = MultiAgentPipeline(
        planner=lambda q: ["s"],
        retrieve=lambda s: [],
        writer=writer,
        critic=lambda q, d, c: (False, ["never happy"]),
        max_revisions=2,
    )
    pipe.run("q")
    assert calls["writer"] == 3                         # 初稿 + 2 次修訂上限
