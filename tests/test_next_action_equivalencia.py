# tests/test_next_action_equivalencia.py
"""A próxima ação derivada tem de bater com a query dedicada.

`_build_tasks_panel_context` deixou de chamar `get_project_next_task` (28 ms por
abertura de projeto, a query mais cara da rota) e passou a tirar a próxima ação
da lista `open_tasks`, que já é buscada. Isso só é válido porque as duas usam a
mesma ordenação e os mesmos filtros.

Estes testes comparam as duas fontes em arranjos que exercitam cada critério da
ordenação — se alguém mudar `_project_task_order` ou os filtros de um lado só,
eles quebram.
"""
import pytest

from app.models.project import ProjectStatus
from app.models.task import TaskStatus
from app.repositories.project_section_repo import ProjectSectionRepository
from app.repositories.task_repo import TaskRepository
from app.routes.projects import _build_tasks_panel_context
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

pytestmark = pytest.mark.asyncio


async def _derivada_vs_query(db, user, project):
    """Devolve (id derivado pelo painel, id da query dedicada)."""
    ctx = await _build_tasks_panel_context(db, project, user)
    derivada = ctx["next_action"]["task"]
    real = await TaskRepository(db).get_project_next_task(project.id, user.id)
    return (derivada.id if derivada else None), (real.id if real else None)


async def _projeto(db, user):
    return await ProjectService(db).create(
        user.id, name="Proj", status=ProjectStatus.em_andamento
    )


async def test_ordem_entre_secoes(db, test_user):
    """Seção com order_index menor vem primeiro, mesmo criada depois."""
    p = await _projeto(db, test_user)
    repo = ProjectSectionRepository(db)
    s2 = await repo.create(p.id, "Segunda")
    s1 = await repo.create(p.id, "Primeira")
    s2.order_index, s1.order_index = 1, 0
    await db.flush()

    await TaskService(db).create(test_user.id, "B", project_id=p.id, section_id=s2.id)
    await TaskService(db).create(test_user.id, "A", project_id=p.id, section_id=s1.id)

    derivada, real = await _derivada_vs_query(db, test_user, p)
    assert derivada == real is not None


async def test_ordem_manual_dentro_da_secao(db, test_user):
    p = await _projeto(db, test_user)
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    svc = TaskService(db)
    t1 = await svc.create(test_user.id, "primeira", project_id=p.id, section_id=sec.id)
    t2 = await svc.create(test_user.id, "segunda", project_id=p.id, section_id=sec.id)
    # Inverte a ordem manual: a segunda passa a ser a próxima ação.
    t1.order_index, t2.order_index = 5, 1
    await db.flush()

    derivada, real = await _derivada_vs_query(db, test_user, p)
    assert derivada == real == t2.id


async def test_bloqueada_nao_e_proxima_acao(db, test_user):
    """`open_tasks` traz pendentes E bloqueadas; só pendente pode ser a próxima."""
    p = await _projeto(db, test_user)
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    svc = TaskService(db)
    bloqueada = await svc.create(test_user.id, "travada", project_id=p.id, section_id=sec.id)
    pendente = await svc.create(test_user.id, "livre", project_id=p.id, section_id=sec.id)
    bloqueada.status = TaskStatus.blocked
    bloqueada.order_index, pendente.order_index = 0, 1
    await db.flush()

    derivada, real = await _derivada_vs_query(db, test_user, p)
    assert derivada == real == pendente.id


async def test_concluida_nao_e_proxima_acao(db, test_user):
    p = await _projeto(db, test_user)
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    svc = TaskService(db)
    feita = await svc.create(test_user.id, "feita", project_id=p.id, section_id=sec.id)
    await svc.mark_done(feita.id, test_user.id)
    viva = await svc.create(test_user.id, "viva", project_id=p.id, section_id=sec.id)

    derivada, real = await _derivada_vs_query(db, test_user, p)
    assert derivada == real == viva.id


async def test_subtarefa_nao_e_proxima_acao(db, test_user):
    """Só tarefa de topo conta — subtarefa nunca vira próxima ação."""
    p = await _projeto(db, test_user)
    sec = await ProjectSectionRepository(db).create(p.id, "Seção")
    svc = TaskService(db)
    mae = await svc.create(test_user.id, "mãe", project_id=p.id, section_id=sec.id)
    await svc.create(test_user.id, "filha", project_id=p.id, parent_id=mae.id)

    derivada, real = await _derivada_vs_query(db, test_user, p)
    assert derivada == real == mae.id


async def test_projeto_sem_tarefa_pendente(db, test_user):
    """Sem pendente, o projeto não é executável — nos dois caminhos."""
    p = await _projeto(db, test_user)
    ctx = await _build_tasks_panel_context(db, p, test_user)

    assert ctx["next_action"]["task"] is None
    assert ctx["next_action"]["executable"] is False
    assert await TaskRepository(db).get_project_next_task(p.id, test_user.id) is None
