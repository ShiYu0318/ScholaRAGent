"""多金鑰輪替，注入時鐘，離線。"""
import pytest

from src.llm.key_rotator import KeyRotator


def test_round_robin_cycles_keys():
    r = KeyRotator(["a", "b", "c"], now=lambda: 0)
    assert [r.next() for _ in range(4)] == ["a", "b", "c", "a"]


def test_skips_rate_limited_key():
    clock = [0]
    r = KeyRotator(["a", "b"], cooldown=10, now=lambda: clock[0])
    r.mark_rate_limited("a")
    assert r.next() == "b"
    assert r.next() == "b"          # a 仍在冷卻，持續跳過


def test_recovers_after_cooldown():
    clock = [0]
    r = KeyRotator(["a", "b"], cooldown=10, now=lambda: clock[0])
    r.mark_rate_limited("a")
    clock[0] = 11                   # 冷卻結束
    assert "a" in {r.next() for _ in range(4)}


def test_all_blocked_does_not_crash():
    r = KeyRotator(["a", "b"], cooldown=10, now=lambda: 0)
    r.mark_rate_limited("a")
    r.mark_rate_limited("b")
    assert r.next() in ("a", "b")


def test_empty_keys_raises():
    with pytest.raises(ValueError):
        KeyRotator([])
