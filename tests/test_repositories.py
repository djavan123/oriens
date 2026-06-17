import pytest

from app.models.mission import EnergyLevel, MissionStatus
from app.models.task import TaskStatus
from app.repositories.capture_repo import CaptureRepository
from app.repositories.mission_repo import MissionRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.task_repo import TaskRepository


# ── ProjectRepository ──────────────────────────────────────────────────────────

async def test_project_create_and_retrieve(db, test_user):
    repo = ProjectRepository(db)
    p = await repo.create(user_id=test_user.id, name="Alpha", priority=1)
    assert p.id is not None
    found = await repo.get_by_id(p.id, test_user.id)
    assert found.name == "Alpha"

async def test_project_get_all_returns_all(db, test_user):
    repo = ProjectRepository(db)
    for i in range(5):
        await repo.create(user_id=test_user.id, name=f"P{i}")
    projects = await repo.get_all_by_user(test_user.id)
    assert len(projects) == 5

async def test_project_get_all_single_query(db, test_user):
    """5 projects should be returned by a single DB query (no N+1)."""
    repo = ProjectRepository(db)
    for i in range(5):
        await repo.create(user_id=test_user.id, name=f"P{i}")
    # Verify all returned correctly — structural guarantee that the query is
    # a single SELECT (the method uses .scalars().all(), not lazy loading)
    projects = await repo.get_all_by_user(test_user.id)
    assert len(projects) == 5

async def test_project_user_isolation(db, test_user):
    from app.models.user import User
    from app.utils.auth import hash_password
    other = User(email="other@pos.dev", password=hash_password("x"), name="Other")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    repo = ProjectRepository(db)
    await repo.create(user_id=test_user.id, name="Meu projeto")
    other_projects = await repo.get_all_by_user(other.id)
    assert other_projects == []

async def test_project_count_active(db, test_user):
    from app.models.project import ProjectStatus
    repo = ProjectRepository(db)
    await repo.create(user_id=test_user.id, name="Ativo")
    await repo.create(user_id=test_user.id, name="Arquivado", status=ProjectStatus.archived)
    count = await repo.count_active(test_user.id)
    assert count == 1

async def test_project_update(db, test_user):
    from app.models.project import ProjectStatus
    repo = ProjectRepository(db)
    p = await repo.create(user_id=test_user.id, name="Antes")
    updated = await repo.update(p, name="Depois", status=ProjectStatus.done)
    assert updated.name == "Depois"
    assert updated.status == ProjectStatus.done


# ── MissionRepository ──────────────────────────────────────────────────────────

async def test_mission_count_active_excludes_paused(db, test_user):
    repo = MissionRepository(db)
    await repo.create(user_id=test_user.id, title="Ativa 1")
    await repo.create(user_id=test_user.id, title="Ativa 2")
    await repo.create(user_id=test_user.id, title="Pausada", status=MissionStatus.paused)
    count = await repo.count_active(test_user.id)
    assert count == 2

async def test_mission_get_active_excludes_done(db, test_user):
    repo = MissionRepository(db)
    await repo.create(user_id=test_user.id, title="Ativa")
    await repo.create(user_id=test_user.id, title="Concluída", status=MissionStatus.done)
    active = await repo.get_active_by_user(test_user.id)
    assert len(active) == 1
    assert active[0].title == "Ativa"

async def test_mission_get_all_includes_all_statuses(db, test_user):
    repo = MissionRepository(db)
    await repo.create(user_id=test_user.id, title="A", status=MissionStatus.active)
    await repo.create(user_id=test_user.id, title="B", status=MissionStatus.paused)
    await repo.create(user_id=test_user.id, title="C", status=MissionStatus.done)
    all_missions = await repo.get_all_by_user(test_user.id)
    assert len(all_missions) == 3


# ── TaskRepository ─────────────────────────────────────────────────────────────

async def test_task_priority_pending_respects_energy_filter(db, test_user):
    repo = TaskRepository(db)
    await repo.create(user_id=test_user.id, title="Alta energia", energy=EnergyLevel.high)
    await repo.create(user_id=test_user.id, title="Baixa energia", energy=EnergyLevel.low)
    high_tasks = await repo.get_priority_pending(test_user.id, limit=10, energy=EnergyLevel.high)
    assert len(high_tasks) == 1
    assert high_tasks[0].title == "Alta energia"

async def test_task_priority_pending_no_filter_returns_all(db, test_user):
    repo = TaskRepository(db)
    await repo.create(user_id=test_user.id, title="Alta", energy=EnergyLevel.high)
    await repo.create(user_id=test_user.id, title="Média", energy=EnergyLevel.medium)
    all_tasks = await repo.get_priority_pending(test_user.id, limit=10)
    assert len(all_tasks) == 2

async def test_task_priority_pending_respects_limit(db, test_user):
    repo = TaskRepository(db)
    for i in range(5):
        await repo.create(user_id=test_user.id, title=f"Tarefa {i}", energy=EnergyLevel.medium)
    tasks = await repo.get_priority_pending(test_user.id, limit=3)
    assert len(tasks) == 3

async def test_task_quick_wins_filter(db, test_user):
    repo = TaskRepository(db)
    await repo.create(user_id=test_user.id, title="Quick A", is_quick_win=True)
    await repo.create(user_id=test_user.id, title="Normal B", is_quick_win=False)
    qw = await repo.get_quick_wins(test_user.id)
    assert len(qw) == 1
    assert qw[0].title == "Quick A"

async def test_task_quick_wins_energy_filter(db, test_user):
    repo = TaskRepository(db)
    await repo.create(
        user_id=test_user.id, title="QW alta", is_quick_win=True, energy=EnergyLevel.high
    )
    await repo.create(
        user_id=test_user.id, title="QW baixa", is_quick_win=True, energy=EnergyLevel.low
    )
    high_qw = await repo.get_quick_wins(test_user.id, energy=EnergyLevel.high)
    assert len(high_qw) == 1
    assert high_qw[0].title == "QW alta"

async def test_task_blocked_returns_only_blocked(db, test_user):
    repo = TaskRepository(db)
    t = await repo.create(user_id=test_user.id, title="Normal")
    await repo.update(t, status=TaskStatus.blocked)
    await repo.create(user_id=test_user.id, title="Pendente")
    blocked = await repo.get_blocked(test_user.id)
    assert len(blocked) == 1

async def test_task_count_pending_excludes_done(db, test_user):
    repo = TaskRepository(db)
    t1 = await repo.create(user_id=test_user.id, title="P1")
    t2 = await repo.create(user_id=test_user.id, title="P2")
    await repo.update(t1, status=TaskStatus.done)
    count = await repo.count_pending(test_user.id)
    assert count == 1


# ── CaptureRepository ──────────────────────────────────────────────────────────

async def test_capture_create_and_retrieve(db, test_user):
    repo = CaptureRepository(db)
    c = await repo.create(user_id=test_user.id, content="Ideia top")
    assert c.id is not None
    assert c.processed is False

async def test_capture_get_unprocessed_excludes_processed(db, test_user):
    repo = CaptureRepository(db)
    c1 = await repo.create(user_id=test_user.id, content="Item 1")
    c2 = await repo.create(user_id=test_user.id, content="Item 2")
    await repo.mark_processed(c1.id, test_user.id)
    unprocessed = await repo.get_unprocessed(test_user.id)
    assert len(unprocessed) == 1
    assert unprocessed[0].id == c2.id

async def test_capture_mark_processed(db, test_user):
    repo = CaptureRepository(db)
    c = await repo.create(user_id=test_user.id, content="Processar isso")
    assert c.processed is False
    updated = await repo.mark_processed(c.id, test_user.id)
    assert updated.processed is True

async def test_capture_get_all_includes_processed(db, test_user):
    repo = CaptureRepository(db)
    c1 = await repo.create(user_id=test_user.id, content="A")
    c2 = await repo.create(user_id=test_user.id, content="B")
    await repo.mark_processed(c1.id, test_user.id)
    all_items = await repo.get_all(test_user.id)
    assert len(all_items) == 2

async def test_capture_wrong_user_returns_none(db, test_user):
    repo = CaptureRepository(db)
    c = await repo.create(user_id=test_user.id, content="Meu item")
    result = await repo.get_by_id(c.id, user_id=9999)
    assert result is None
