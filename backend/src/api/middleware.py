"""安全相關的 ASGI middleware：回應標頭與請求 body 大小上限。

寫成純 ASGI（非 BaseHTTPMiddleware），不會緩衝回應，SSE 串流不受影響。
"""
import json

from src import config

# SPA 的樣式由 styled-components 於執行期注入，style-src 需允許 inline；
# script 一律只允許同源，擋下注入的 inline script。
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

# Swagger / ReDoc 頁面從 CDN 載入腳本，不套用 CSP（production 預設不提供這些頁面）
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        https = scope.get("scheme") == "https" or config.API_PUBLIC_URL.startswith("https://")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                present = {k.lower() for k, _ in headers}

                def add(name, value):
                    if name.encode() not in present:
                        headers.append((name.encode(), value.encode()))

                add("x-content-type-options", "nosniff")
                add("x-frame-options", "DENY")
                add("referrer-policy", "no-referrer")
                add("permissions-policy", "camera=(), microphone=(), geolocation=()")
                add("cross-origin-opener-policy", "same-origin")
                if not path.startswith(_DOCS_PATHS):
                    add("content-security-policy", CSP)
                if https:
                    add("strict-transport-security", "max-age=31536000; includeSubDomains")
                if path.startswith(("/api", "/auth")):
                    # API 回應含個人資料，不讓瀏覽器或中間快取留存
                    add("cache-control", "no-store")
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """超過上限回 413。有 Content-Length 時直接拒絕；沒有（chunked）時邊讀邊計數。"""

    def __init__(self, app, max_bytes=None):
        self.app = app
        self.max_bytes = max_bytes or config.MAX_BODY_BYTES

    async def _reject(self, send):
        body = json.dumps({"detail": "請求內容過大"}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)

        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    return await self._reject(send)
            except ValueError:
                return await self._reject(send)

        seen = 0
        too_large = False
        rejected = False

        async def counting_receive():
            nonlocal seen, too_large
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    too_large = True
                    raise _BodyTooLarge()
            return message

        async def guarded_send(message):
            # 框架會把讀取 body 時的例外轉成 400；超量時一律改回 413，
            # 並丟棄應用程式原本要送出的回應。
            nonlocal rejected
            if too_large:
                if not rejected:
                    rejected = True
                    await self._reject(send)
                return
            await send(message)

        try:
            await self.app(scope, counting_receive, guarded_send)
        except _BodyTooLarge:
            if not rejected:
                await self._reject(send)


class _BodyTooLarge(Exception):
    pass
