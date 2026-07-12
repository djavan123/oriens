# tests/test_link_meta.py
"""Anti-SSRF do link_meta: URLs bloqueadas, DNS que resolve p/ IP privado, redirects."""
from unittest.mock import AsyncMock, patch

import pytest

from app.utils.link_meta import (
    _is_allowed_url,
    _resolve_and_check,
    extract_url,
    fetch_link_title,
)


# ---------- _is_allowed_url (checagens estáticas) ----------

@pytest.mark.parametrize("url", [
    "http://example.com/page",
    "https://example.com",
])
def test_allowed_public_urls(url):
    assert _is_allowed_url(url) is True


@pytest.mark.parametrize("url", [
    "ftp://example.com/file",
    "file:///etc/passwd",
    "http://localhost/admin",
    "http://foo.localhost/x",
    "http://127.0.0.1/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://0.0.0.0/",
])
def test_blocked_urls(url):
    assert _is_allowed_url(url) is False


def test_extract_url_ignores_private_ip():
    assert extract_url("veja http://169.254.169.254/meta") is None
    assert extract_url("veja https://example.com/x") == "https://example.com/x"


# ---------- _resolve_and_check (DNS → IP) ----------

def _addrinfo(*ips):
    return [(0, 0, 0, "", (ip, 0)) for ip in ips]


@pytest.mark.asyncio
async def test_resolve_public_ip_allowed():
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=_addrinfo("93.184.216.34"))
        assert await _resolve_and_check("example.com") is True


@pytest.mark.asyncio
async def test_resolve_private_ip_blocked():
    """Hostname público que resolve para IP interno (o vetor clássico de SSRF)."""
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=_addrinfo("169.254.169.254"))
        assert await _resolve_and_check("evil.example.com") is False


@pytest.mark.asyncio
async def test_resolve_mixed_ips_blocked():
    """Basta UM IP proibido na resposta DNS para bloquear."""
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(
            return_value=_addrinfo("93.184.216.34", "10.0.0.7")
        )
        assert await _resolve_and_check("evil.example.com") is False


@pytest.mark.asyncio
async def test_resolve_failure_blocked():
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(side_effect=OSError("nx"))
        assert await _resolve_and_check("nao-existe.example") is False


# ---------- fetch_link_title (fluxo completo) ----------

@pytest.mark.asyncio
async def test_fetch_blocks_hostname_resolving_private():
    with patch("app.utils.link_meta._resolve_and_check", AsyncMock(return_value=False)):
        assert await fetch_link_title("http://evil.example.com/") is None


@pytest.mark.asyncio
async def test_fetch_blocks_redirect_to_private():
    """Redirect para host privado é barrado ANTES de qualquer request ao destino."""
    class FakeResp:
        is_redirect = True
        headers = {"location": "http://169.254.169.254/latest/"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def stream(self, method, url):
            assert "169.254" not in url, "não deveria requisitar o destino privado"
            return FakeResp()

    with patch("app.utils.link_meta._resolve_and_check", AsyncMock(return_value=True)), \
         patch("httpx.AsyncClient", return_value=FakeClient()):
        assert await fetch_link_title("http://public.example.com/") is None


@pytest.mark.asyncio
async def test_fetch_never_raises():
    with patch("httpx.AsyncClient", side_effect=RuntimeError("boom")):
        assert await fetch_link_title("https://example.com/") is None
