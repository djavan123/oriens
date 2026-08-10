# tests/test_context_switch.py
"""Troca de contexto.

A rota não tinha nenhum teste — e não tinha nenhuma checagem de sessão: aceitava
qualquer `context_id`, inclusive de contexto personalizado de outro usuário.
Também devolvia `HX-Refresh`, forçando reload completo do documento a cada
troca, sendo que o contexto é o filtro usado o dia inteiro.
"""
import json

import pytest

from app.models.user import User
from app.repositories.context_repo import ContextRepository
from app.utils.auth import hash_password

pytestmark = pytest.mark.asyncio


async def test_switch_re_renderiza_sem_reload(client, db, test_user):
    """Responde com HX-Location (re-render por AJAX), não HX-Refresh (reload)."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")

    r = await client.post(
        "/api/context/switch",
        data={"context_id": str(ctx.id)},
        headers={"HX-Request": "true", "HX-Current-URL": "http://testserver/lists?list=2"},
    )

    assert r.status_code == 200
    assert "HX-Refresh" not in r.headers
    destino = json.loads(r.headers["HX-Location"])
    assert destino["path"] == "/lists?list=2"   # volta para a MESMA tela, com a query
    assert destino["target"] == "body"
    assert "select" not in destino              # `select: body` esvaziaria a página
    assert r.cookies.get("oriens_context") == str(ctx.id)


async def test_switch_ignora_url_externa(client, db, test_user):
    """O HX-Current-URL vem do cliente; um host externo não vira destino."""
    ctx = await ContextRepository(db).create(user_id=test_user.id, name="Trabalho")

    r = await client.post(
        "/api/context/switch",
        data={"context_id": str(ctx.id)},
        headers={"HX-Current-URL": "https://evil.example.com/phish"},
    )

    assert json.loads(r.headers["HX-Location"])["path"] == "/dashboard"


async def test_switch_recusa_contexto_de_outro_usuario(client, db, test_user):
    """Ownership: contexto personalizado alheio não pode virar o contexto ativo."""
    outro = User(email="outro@oriens.local", password=hash_password("x"), name="Outro")
    db.add(outro)
    await db.flush()
    alheio = await ContextRepository(db).create(user_id=outro.id, name="Contexto do outro")
    await db.commit()

    r = await client.post("/api/context/switch", data={"context_id": str(alheio.id)})

    assert r.status_code == 404
    assert "oriens_context" not in r.cookies


async def test_switch_recusa_id_invalido(client, db, test_user):
    assert (await client.post("/api/context/switch", data={"context_id": "abc"})).status_code == 404
    assert (await client.post("/api/context/switch", data={"context_id": "999999"})).status_code == 404
