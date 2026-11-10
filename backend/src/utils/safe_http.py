"""對「使用者提供的 URL」發請求時的 SSRF 防護。

伺服器代抓 RSS 等外部內容時，URL 可能指向內網服務或雲端 metadata
（169.254.169.254）。這裡集中處理：
- 只允許 http/https，拒絕帶帳密的 URL；
- 解析主機後，任何一個位址不是公開位址就拒絕；
- 不自動跟隨轉址，逐跳重新檢查（否則可用公開網址轉進內網）；
- 限制回應大小，避免被巨大回應拖垮。

已知限制：檢查與實際連線各解析一次 DNS，理論上仍有 DNS rebinding 的時間差；
要完全消除需在網路層（egress 防火牆/代理）限制對內連線。
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests

MAX_BYTES = 2 * 1024 * 1024
_BLOCKED_HOSTS = {"localhost", "localhost.localdomain", "metadata.google.internal"}
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")


class UnsafeURLError(ValueError):
    """URL 不允許由伺服器代為請求。"""


def is_public_ip(value) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    # IPv4-mapped IPv6（::ffff:10.0.0.1）要看內層位址
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return ip.is_global and not ip.is_multicast


def _resolve(host, port):
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return {info[4][0] for info in infos}


def check_url(url, resolve=True, resolver=None):
    """驗證 URL 可安全代抓，回傳正規化後的 URL；不合格丟 UnsafeURLError。

    resolve=False 只做語法與字面位址檢查（不查 DNS），適合在儲存 URL 當下使用。
    """
    try:
        parts = urlsplit(str(url).strip())
        port = parts.port
    except ValueError:
        raise UnsafeURLError("網址格式不正確")
    if parts.scheme not in ("http", "https"):
        raise UnsafeURLError("只允許 http 或 https 網址")
    if parts.username or parts.password:
        raise UnsafeURLError("網址不可包含帳號密碼")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise UnsafeURLError("網址缺少主機名稱")
    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_SUFFIXES):
        raise UnsafeURLError("不允許存取內部主機")

    try:
        ipaddress.ip_address(host)
        literal = True
    except ValueError:
        literal = False
    if literal:
        if not is_public_ip(host):
            raise UnsafeURLError("不允許存取內部或保留位址")
    elif resolve:
        try:
            addresses = (resolver or _resolve)(host, port or (443 if parts.scheme == "https" else 80))
        except OSError:
            raise UnsafeURLError("無法解析主機名稱")
        if not addresses or not all(is_public_ip(a) for a in addresses):
            raise UnsafeURLError("不允許存取內部或保留位址")
    return parts.geturl()


def safe_get(url, headers=None, timeout=10, max_bytes=MAX_BYTES, max_redirects=3,
             session=None, resolver=None):
    """安全地 GET 一個外部 URL，回傳解碼後的文字。"""
    http = session or requests
    current = url
    for _ in range(max_redirects + 1):
        current = check_url(current, resolver=resolver)
        resp = http.get(current, headers=headers, timeout=timeout,
                        allow_redirects=False, stream=True)
        try:
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    raise UnsafeURLError("轉址缺少目的地")
                current = urljoin(current, location)
                continue
            resp.raise_for_status()
            chunks, total = [], 0
            for chunk in resp.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > max_bytes:
                    raise UnsafeURLError("回應內容過大")
                chunks.append(chunk)
            return b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
        finally:
            resp.close()
    raise UnsafeURLError("轉址次數過多")
