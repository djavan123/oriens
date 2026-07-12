# tests/test_labels_xss.py
"""Etiquetas: nome com HTML deve sair escapado; cor fora do padrão hex cai no default."""
import pytest

from app.routes.api.settings import DEFAULT_LABEL_COLOR


@pytest.mark.asyncio
async def test_label_name_html_is_escaped(client):
    resp = await client.post(
        "/api/settings/labels",
        data={"name": '<img src=x onerror=alert(1)>', "color": "#aabbcc"},
    )
    assert resp.status_code == 200
    assert "<img" not in resp.text
    assert "&lt;img" in resp.text


@pytest.mark.asyncio
async def test_label_invalid_color_falls_back_to_default(client):
    resp = await client.post(
        "/api/settings/labels",
        data={"name": "urgente", "color": 'red" onmouseover="alert(1)'},
    )
    assert resp.status_code == 200
    assert "onmouseover" not in resp.text
    assert DEFAULT_LABEL_COLOR in resp.text


@pytest.mark.asyncio
async def test_label_valid_color_is_kept(client):
    resp = await client.post(
        "/api/settings/labels",
        data={"name": "casa", "color": "#12AbCd"},
    )
    assert resp.status_code == 200
    assert "#12AbCd" in resp.text


@pytest.mark.asyncio
async def test_settings_page_sanitizes_persisted_color(client, db, test_user):
    """Cor maliciosa já persistida não chega ao CSS na renderização."""
    from app.repositories.label_repo import LabelRepository

    await LabelRepository(db).create(test_user.id, "legada", 'x";background:url(evil)')
    resp = await client.get("/settings")
    assert resp.status_code == 200
    assert "url(evil)" not in resp.text
