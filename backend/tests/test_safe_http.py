"""SSRF 防護：URL 檢查、轉址逐跳檢查、回應大小上限。全離線。"""
import pytest

from src.utils.safe_http import UnsafeURLError, check_url, is_public_ip, safe_get


def _public(host, port):
    return {"93.184.216.34"}


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "172.16.0.1", "192.168.1.1",
                                "169.254.169.254", "0.0.0.0", "::1", "fe80::1",
                                "fc00::1", "::ffff:10.0.0.1", "224.0.0.1", "100.64.0.1"])
def test_internal_addresses_are_not_public(ip):
    assert not is_public_ip(ip)


def test_public_address_is_public():
    assert is_public_ip("93.184.216.34")
    assert is_public_ip("2606:4700:4700::1111")


@pytest.mark.parametrize("url", [
    "ftp://example.com/x", "file:///etc/passwd", "gopher://example.com",
    "http://user:pw@example.com/", "http://localhost/x", "http://foo.internal/x",
    "http://127.0.0.1:8000/", "http://[::1]/", "http://169.254.169.254/latest/meta-data",
    "http://2130706433/", "http:///nohost", "http://example.com:99999/",
])
def test_check_url_rejects_unsafe(url):
    with pytest.raises(UnsafeURLError):
        check_url(url, resolver=lambda h, p: {"127.0.0.1"})


def test_check_url_rejects_hostname_resolving_to_internal():
    with pytest.raises(UnsafeURLError):
        check_url("https://evil.example.com/rss", resolver=lambda h, p: {"192.168.0.10"})


def test_check_url_rejects_when_any_resolved_address_is_internal():
    with pytest.raises(UnsafeURLError):
        check_url("https://mixed.example.com/",
                  resolver=lambda h, p: {"93.184.216.34", "10.0.0.1"})


def test_check_url_syntax_only_does_not_resolve():
    def boom(host, port):
        raise AssertionError("不應查 DNS")
    assert check_url("https://example.com/rss", resolve=False, resolver=boom)


class Resp:
    encoding = "utf-8"

    def __init__(self, status=200, body=b"", location=None):
        self.status_code = status
        self._body = body
        self.headers = {"Location": location} if location else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        pass


class Session:
    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses[url]


def test_safe_get_returns_body_and_disables_auto_redirects():
    sess = Session({"https://example.com/rss": Resp(body=b"<rss/>")})
    assert safe_get("https://example.com/rss", session=sess, resolver=_public) == "<rss/>"
    assert sess.calls[0][1]["allow_redirects"] is False


def test_safe_get_follows_safe_redirect():
    sess = Session({
        "https://example.com/a": Resp(302, location="/b"),
        "https://example.com/b": Resp(body=b"ok"),
    })
    assert safe_get("https://example.com/a", session=sess, resolver=_public) == "ok"


def test_safe_get_blocks_redirect_into_internal_network():
    sess = Session({
        "https://example.com/a": Resp(302, location="http://169.254.169.254/latest/"),
    })
    with pytest.raises(UnsafeURLError):
        safe_get("https://example.com/a", session=sess, resolver=_public)
    assert len(sess.calls) == 1


def test_safe_get_caps_response_size():
    sess = Session({"https://example.com/big": Resp(body=b"x" * 5000)})
    with pytest.raises(UnsafeURLError):
        safe_get("https://example.com/big", session=sess, resolver=_public, max_bytes=1000)


def test_safe_get_limits_redirect_chain():
    sess = Session({"https://example.com/loop": Resp(302, location="/loop")})
    with pytest.raises(UnsafeURLError):
        safe_get("https://example.com/loop", session=sess, resolver=_public)
