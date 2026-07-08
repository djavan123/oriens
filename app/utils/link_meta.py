# app/utils/link_meta.py
"""Detecta URL num texto e busca o título da página/vídeo (og:title / <title>).

Usado para exibir "Nome da página" em vez da URL crua nos itens de Repositório.
"""
import ipaddress
import logging
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("oriens.link_meta")

_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
_TITLE_MAX_LEN = 300
_MAX_BYTES = 200_000
_TIMEOUT = 5.0
_USER_AGENT = "Mozilla/5.0 (compatible; OriensBot/1.0)"


def extract_url(text: Optional[str]) -> Optional[str]:
    """Primeira URL http(s) válida e segura encontrada no texto, ou None."""
    if not text:
        return None
    match = _URL_RE.search(text)
    if not match:
        return None
    url = match.group(0).rstrip(").,;")
    return url if _is_allowed_url(url) else None


def _is_allowed_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host or host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    ):
        return False
    return True


def prepare_task_link_metadata(title: str) -> str:
    """Normaliza um título bruto (espaços colapsados, tamanho limitado)."""
    cleaned = " ".join((title or "").split())
    return cleaned[:_TITLE_MAX_LEN]


def _extract_title_from_html(html: str) -> Optional[str]:
    og_match = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE,
    )
    if not og_match:
        og_match = re.search(
            r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:title["\']',
            html, re.IGNORECASE,
        )
    title = og_match.group(1) if og_match else None
    if not title:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1)
    if not title:
        return None
    cleaned = prepare_task_link_metadata(title)
    return cleaned or None


async def fetch_link_title(url: str) -> Optional[str]:
    """Busca og:title ou <title> da página. None em qualquer falha (nunca levanta)."""
    if not _is_allowed_url(url):
        return None
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
        ) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code >= 400:
                    return None
                # Revalida o host final (após redirects) contra SSRF.
                if not _is_allowed_url(str(resp.url)):
                    return None
                content_type = resp.headers.get("content-type", "")
                if "html" not in content_type.lower():
                    return None
                chunks = bytearray()
                async for chunk in resp.aiter_bytes():
                    chunks += chunk
                    if len(chunks) >= _MAX_BYTES:
                        break
                html = chunks.decode(resp.encoding or "utf-8", errors="ignore")
    except Exception:
        logger.info("Falha ao buscar título do link: %s", url)
        return None
    return _extract_title_from_html(html)
