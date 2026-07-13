# app/utils/link_meta.py
"""Detecta URL num texto e busca o título da página/vídeo (og:title / <title>).

Usado para exibir "Nome da página" em vez da URL crua nos itens de Repositório.

Proteção contra SSRF: além de recusar esquemas não-http(s), localhost e IPs
literais privados, o hostname é resolvido via DNS e TODOS os IPs retornados
são validados antes de qualquer requisição — inclusive a cada hop de redirect
(seguidos manualmente, máx. 3). Risco residual aceito: DNS rebinding na janela
resolve→connect (mitigá-lo exigiria pinning de IP com SNI, desproporcional aqui).
"""
import asyncio
import ipaddress
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger("oriens.link_meta")

_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
_TITLE_MAX_LEN = 300
_MAX_BYTES = 200_000
_TIMEOUT = 5.0
_USER_AGENT = "Mozilla/5.0 (compatible; OriensBot/1.0)"
_MAX_REDIRECTS = 3


def extract_url(text: Optional[str]) -> Optional[str]:
    """Primeira URL http(s) válida e segura encontrada no texto, ou None."""
    if not text:
        return None
    match = _URL_RE.search(text)
    if not match:
        return None
    url = match.group(0).rstrip(").,;")
    return url if _is_allowed_url(url) else None


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )


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
    if ip is not None and _is_forbidden_ip(ip):
        return False
    return True


async def _resolve_and_check(host: str) -> bool:
    """Resolve o hostname e valida todos os IPs retornados (anti-SSRF via DNS)."""
    try:
        ipaddress.ip_address(host)
        return True  # IP literal: já validado por _is_allowed_url
    except ValueError:
        pass
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if _is_forbidden_ip(ip):
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
    """Busca og:title ou <title> da página. None em qualquer falha (nunca levanta).

    Redirects são seguidos manualmente (máx. _MAX_REDIRECTS) para validar
    URL e DNS de cada hop ANTES do request — nada de conectar primeiro e
    checar depois.
    """
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=False, headers={"User-Agent": _USER_AGENT}
        ) as client:
            current = url
            for _ in range(_MAX_REDIRECTS + 1):
                if not _is_allowed_url(current):
                    return None
                host = (urlparse(current).hostname or "").lower()
                if not await _resolve_and_check(host):
                    return None
                async with client.stream("GET", current) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location")
                        if not location:
                            return None
                        current = urljoin(current, location)
                        continue
                    if resp.status_code >= 400:
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
                    return _extract_title_from_html(html)
            return None  # excedeu o limite de redirects
    except Exception:
        logger.info("Falha ao buscar título do link: %s", url)
        return None
