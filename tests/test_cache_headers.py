# tests/test_cache_headers.py
"""Política de cache: HTML/fragmentos nunca reusados do navegador; estáticos nunca
`immutable` sem versão. Trava o bug "site velho até Ctrl+F5"."""
import pytest

from app.logging_setup import check_asset_version


@pytest.mark.asyncio
async def test_html_page_is_no_store(client):
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "no-store" in resp.headers["cache-control"]


@pytest.mark.asyncio
async def test_login_page_is_no_store(anon_client):
    resp = await anon_client.get("/auth/login")
    assert resp.status_code == 200
    assert "no-store" in resp.headers["cache-control"]


@pytest.mark.asyncio
async def test_htmx_fragment_is_no_store(client):
    """Fragmento HTMX cacheado pelo browser reaparece numa navegação normal."""
    resp = await client.get("/api/reminders/due")
    assert resp.status_code == 200
    assert "no-store" in resp.headers["cache-control"]


@pytest.mark.asyncio
async def test_auth_redirect_is_no_store(anon_client):
    resp = await anon_client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "no-store" in resp.headers["cache-control"]


@pytest.mark.asyncio
async def test_static_revalidates_and_is_never_immutable(anon_client):
    resp = await anon_client.get("/static/css/theme.css")
    assert resp.status_code == 200
    cc = resp.headers["cache-control"]
    assert cc == "no-cache"
    assert "immutable" not in cc


@pytest.mark.asyncio
async def test_service_worker_is_gone(anon_client):
    """SW desligado: o 404 é o que faz o navegador desregistrar o órfão."""
    resp = await anon_client.get("/static/sw.js")
    assert resp.status_code == 404


def test_asset_version_guard_blocks_fallback_in_prod(monkeypatch):
    """Sem o SHA no APP_VERSION, dois builds compartilham a URL do asset e o cache
    longo congela CSS/JS antigo — o boot deve abortar."""
    from app.config import Settings, get_settings

    def fake(debug: bool, version: str):
        base = get_settings().model_dump()
        base.update(DEBUG=debug, APP_VERSION=version)
        return Settings(**base)

    monkeypatch.setattr(
        "app.logging_setup.get_settings", lambda: fake(False, "prod")
    )
    with pytest.raises(RuntimeError, match="APP_VERSION"):
        check_asset_version()

    # Com SHA real, passa; e em DEBUG o fallback é permitido.
    monkeypatch.setattr(
        "app.logging_setup.get_settings", lambda: fake(False, "a1b2c3d")
    )
    check_asset_version()
    monkeypatch.setattr(
        "app.logging_setup.get_settings", lambda: fake(True, "dev")
    )
    check_asset_version()
