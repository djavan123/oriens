# tests/test_project_detail_perf.py
"""Custo de abrir um projeto.

`/projects/{id}` era a rota mais lenta do sistema (264–291 ms de servidor em
produção, contra 32–100 ms da lista). Dois desperdícios mediados e removidos:

1. `risks`, `audit` e `timeline` eram consultados e passados ao template sem
   nunca serem renderizados — 45 ms de banco por abertura (9,0 + 12,2 + 23,7,
   medidos no projeto 13 em produção), um terço do tempo total de query.
2. `sortable.min.js` era síncrono no <head> e segurava a renderização por
   428 ms (886 ms → 1314 ms no waterfall), só para carregar o drag-and-drop.
"""
import pytest

from app.models.project import ProjectStatus
from app.repositories.project_section_repo import ProjectSectionRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

pytestmark = pytest.mark.asyncio


async def _projeto_com_tarefa(db, user):
    p = await ProjectService(db).create(
        user.id, name="Proj", status=ProjectStatus.em_andamento
    )
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    await TaskService(db).create(user.id, "Ação", project_id=p.id, section_id=sec.id)
    return p


async def test_sortable_nao_bloqueia_a_renderizacao(client, db, test_user):
    p = await _projeto_com_tarefa(db, test_user)

    r = await client.get(f"/projects/{p.id}")

    assert r.status_code == 200
    assert "sortable.min.js" in r.text
    # O <script> do sortable precisa ter defer; sem isso ele trava o parse.
    marca = r.text[r.text.index("sortable.min.js") - 120:r.text.index("sortable.min.js")]
    assert "defer" in marca, "sortable.min.js voltou a ser síncrono no <head>"


async def test_nao_consulta_dados_que_nao_renderiza(client, db, test_user, monkeypatch):
    """Riscos/auditoria/cronologia não podem voltar a ser lidos na abertura."""
    from app.repositories import (
        project_audit_repo,
        project_risk_repo,
        project_timeline_repo,
    )

    chamadas = []
    for mod, classe, metodo in [
        (project_risk_repo, "ProjectRiskRepository", "get_by_project"),
        (project_audit_repo, "ProjectAuditRepository", "get_by_project"),
        (project_timeline_repo, "ProjectTimelineRepository", "get_by_project"),
    ]:
        alvo = getattr(mod, classe)
        original = getattr(alvo, metodo)

        async def espiao(self, *a, _nome=classe, _orig=original, **kw):
            chamadas.append(_nome)
            return await _orig(self, *a, **kw)

        monkeypatch.setattr(alvo, metodo, espiao)

    p = await _projeto_com_tarefa(db, test_user)
    r = await client.get(f"/projects/{p.id}")

    assert r.status_code == 200
    assert chamadas == [], f"query morta de volta na abertura do projeto: {chamadas}"


async def test_pagina_continua_completa(client, db, test_user):
    """A remoção não pode ter levado junto nada que a tela usa."""
    p = await _projeto_com_tarefa(db, test_user)

    r = await client.get(f"/projects/{p.id}")

    assert r.status_code == 200
    for bloco in ("Visão geral", "Tarefas", "Decisões", "Comentários", "Ação"):
        assert bloco in r.text, bloco
