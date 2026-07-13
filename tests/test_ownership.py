# tests/test_ownership.py
"""Isolamento multi-tenant: usuário B não pode ler/alterar recursos do usuário A.

Cada teste cria o recurso como A (fixtures do conftest) e ataca como B
(other_client). Espera-se 4xx e o dado intacto.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import ProjectStatus
from app.models.user import User
from app.repositories.capture_repo import CaptureRepository
from app.repositories.label_repo import LabelRepository
from app.repositories.project_decision_repo import ProjectDecisionRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.project_section_repo import ProjectSectionRepository
from app.repositories.task_list_repo import TaskListRepository
from app.repositories.task_repo import TaskRepository
from app.utils.auth import COOKIE_NAME, create_access_token, hash_password

FORBIDDEN = (400, 403, 404)


@pytest_asyncio.fixture(scope="function")
async def other_user(db: AsyncSession) -> User:
    user = User(email="other@oriens.dev", password=hash_password("outra"), name="Other")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def other_client(db: AsyncSession, other_user: User) -> AsyncClient:
    """Cliente HTTP autenticado como o usuário B (mesmo banco de teste)."""
    from app.main import app

    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    token = create_access_token(other_user.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set(COOKIE_NAME, token)
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_task_cross_user(client, other_client, db, test_user):
    task = await TaskRepository(db).create(test_user.id, title="minha tarefa")

    r = await other_client.patch(f"/api/tasks/{task.id}/done")
    assert r.status_code in FORBIDDEN

    r = await other_client.patch(f"/api/tasks/{task.id}", data={"title": "hackeada"})
    assert r.status_code in FORBIDDEN

    r = await other_client.get(f"/api/tasks/{task.id}/panel")
    assert r.status_code in FORBIDDEN

    fresh = await TaskRepository(db).get_by_id(task.id, test_user.id)
    assert fresh.title == "minha tarefa"
    assert fresh.status.value == "pending"


@pytest.mark.asyncio
async def test_project_cross_user(client, other_client, db, test_user):
    project = await ProjectRepository(db).create(
        test_user.id, name="meu projeto", status=ProjectStatus.em_andamento, priority=1
    )

    r = await other_client.patch(
        f"/api/projects/{project.id}", data={"name": "invadido", "context_id": "1"}
    )
    assert r.status_code in FORBIDDEN

    r = await other_client.get(f"/projects/{project.id}")
    assert r.status_code in FORBIDDEN

    fresh = await ProjectRepository(db).get_by_id(project.id, test_user.id)
    assert fresh.name == "meu projeto"


@pytest.mark.asyncio
async def test_project_children_cross_user(client, other_client, db, test_user):
    project = await ProjectRepository(db).create(
        test_user.id, name="p", status=ProjectStatus.em_andamento, priority=1
    )
    section = await ProjectSectionRepository(db).create(project.id, "Fase 1")
    decision = await ProjectDecisionRepository(db).create(project.id, test_user.id, "decidido")
    task = await TaskRepository(db).create(
        test_user.id, title="t1", project_id=project.id, order_index=0
    )

    r = await other_client.patch(
        f"/api/projects/{project.id}/sections/{section.id}", data={"name": "roubada"}
    )
    assert r.status_code in FORBIDDEN

    r = await other_client.delete(f"/api/projects/{project.id}/decisions/{decision.id}")
    assert r.status_code in FORBIDDEN

    r = await other_client.patch(
        f"/api/projects/{project.id}/task-order", json={"task_ids": [task.id]}
    )
    assert r.status_code in FORBIDDEN

    fresh_section = await ProjectSectionRepository(db).get_by_id(section.id, project.id)
    assert fresh_section.name == "Fase 1"
    fresh_decision = await ProjectDecisionRepository(db).get_by_id(decision.id, test_user.id)
    assert fresh_decision is not None


@pytest.mark.asyncio
async def test_capture_cross_user(client, other_client, db, test_user):
    capture = await CaptureRepository(db).create(test_user.id, "ideia privada")

    r = await other_client.patch(
        f"/api/capture/{capture.id}", data={"content": "alterada"}
    )
    assert r.status_code in FORBIDDEN

    r = await other_client.patch(f"/api/capture/{capture.id}/discard")
    assert r.status_code in FORBIDDEN

    fresh = await CaptureRepository(db).get_by_id(capture.id, test_user.id)
    assert fresh.content == "ideia privada"
    assert fresh.discarded_at is None


@pytest.mark.asyncio
async def test_label_cross_user(client, other_client, db, test_user):
    label = await LabelRepository(db).create(test_user.id, "pessoal", "#aabbcc")

    await other_client.delete(f"/api/settings/labels/{label.id}")

    remaining = await LabelRepository(db).get_all_by_user(test_user.id)
    assert any(l.id == label.id for l in remaining), "label de A não pode sumir via B"


@pytest.mark.asyncio
async def test_list_cross_user(client, other_client, db, test_user):
    task_list = await TaskListRepository(db).create(test_user.id, "minha lista")

    r = await other_client.patch(f"/api/lists/{task_list.id}", data={"name": "de B"})
    assert r.status_code in FORBIDDEN

    r = await other_client.delete(f"/api/lists/{task_list.id}")
    assert r.status_code in FORBIDDEN

    fresh = await TaskListRepository(db).get_by_id(task_list.id, test_user.id)
    assert fresh is not None and fresh.name == "minha lista" and not fresh.archived
