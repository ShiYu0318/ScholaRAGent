"""行程內滑動視窗限流：依 IP（未登入端點）或使用者（已登入端點）計數。

限流器掛在 app.state，每個 app 實例各自獨立（測試不互相干擾）。單一行程
部署足夠；多副本部署時應改由反向代理或共用儲存（如 Redis）限流。
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from src import config
from src.api.deps import get_current_user


class RateLimiter:
    def __init__(self, clock=time.monotonic, max_keys=50_000):
        self._clock = clock
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def hit(self, key, limit, window):
        """記一次請求；允許回傳 0，超量回傳需等待的秒數（>=1）。"""
        now = self._clock()
        with self._lock:
            if len(self._hits) > self._max_keys:
                self._prune(now)
            q = self._hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return max(1, int(q[0] + window - now) + 1)
            q.append(now)
            return 0

    def _prune(self, now, horizon=3600):
        for key in [k for k, q in self._hits.items() if not q or q[-1] <= now - horizon]:
            del self._hits[key]


def client_ip(request: Request) -> str:
    """取用戶端 IP。只有設定 TRUST_PROXY 時才信任 X-Forwarded-For（否則可偽造繞過限流）。"""
    if config.TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check(request, key, limit, window):
    if not config.RATE_LIMIT_ENABLED:
        return
    limiter = getattr(request.app.state, "limiter", None)
    if limiter is None:
        return
    wait = limiter.hit(key, limit, window)
    if wait:
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試",
                            headers={"Retry-After": str(wait)})


def limit_ip(scope, limit, window=60):
    def dep(request: Request):
        _check(request, f"{scope}:ip:{client_ip(request)}", limit, window)
    return dep


def limit_user(scope, limit, window=60):
    def dep(request: Request, user=Depends(get_current_user)):
        _check(request, f"{scope}:user:{user['id']}", limit, window)
    return dep


# 常用等級：LLM 一般呼叫、重量級（多輪 LLM / 外部抓取）
llm_limit = limit_user("llm", config.RATE_LIMIT_LLM_PER_MIN)
heavy_limit = limit_user("heavy", config.RATE_LIMIT_HEAVY_PER_MIN)
