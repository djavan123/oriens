import pytest

from app.models.mission import EnergyLevel, MissionStatus
from app.models.task import TaskStatus
from app.services.mission_service import ACTIVE_MISSION_LIMIT, MissionLimitError, MissionService
from app.services.task_service import TaskService, TaskVerbError


# ── MissionService ─────────────────────────────────────────────────────────────

async def test_create_first_mission(db, test_user):
    service = MissionService(db)
    mission = await service.create(user_id=test_user.id, title="Lançar produto")
    assert mission.id is not None
    assert mission.title == "Lançar produto"
    assert mission.status == MissionStatus.active

async def test_create_up_to_limit(db, test_user):
    service = MissionService(db)
    for i in range(ACTIVE_MISSION_LIMIT):
        m = await service.create(user_id=test_user.id, title=f"Missão {i + 1}")
        assert m.id is not None

async def test_create_fourth_active_raises_limit_error(db, test_user):
    service = MissionService(db)
    for i in range(ACTIVE_MISSION_LIMIT):
        await service.create(user_id=test_user.id, title=f"Missão {i + 1}")
    with pytest.raises(MissionLimitError):
        await service.create(user_id=test_user.id, title="Missão extra")

async def test_paused_mission_not_counted_in_limit(db, test_user):
    service = MissionService(db)
    missions = []
    for i in range(ACTIVE_MISSION_LIMIT):
        m = await service.create(user_id=test_user.id, title=f"Missão {i + 1}")
        missions.append(m)
    # Pause the first one
    await service.update_status(missions[0].id, test_user.id, MissionStatus.paused)
    # Now a new active mission is allowed
    new_m = await service.create(user_id=test_user.id, title="Missão pós-pausa")
    assert new_m.id is not None

async def test_reactivate_paused_while_at_limit_raises(db, test_user):
    service = MissionService(db)
    paused = await service.create(
        user_id=test_user.id, title="Missão pausada", status=MissionStatus.paused
    )
    for i in range(ACTIVE_MISSION_LIMIT):
        await service.create(user_id=test_user.id, title=f"Missão ativa {i + 1}")
    with pytest.raises(MissionLimitError):
        await service.update_status(paused.id, test_user.id, MissionStatus.active)

async def test_done_mission_not_counted_in_limit(db, test_user):
    service = MissionService(db)
    done = await service.create(
        user_id=test_user.id, title="Missão concluída", status=MissionStatus.done
    )
    assert done.id is not None
    active_count = await service.repo.count_active(test_user.id)
    assert active_count == 0


# ── TaskService ────────────────────────────────────────────────────────────────

async def test_create_task_with_verb(db, test_user):
    service = TaskService(db)
    task = await service.create(user_id=test_user.id, title="Criar novo branch de feature")
    assert task.id is not None
    assert task.title == "Criar novo branch de feature"
    assert task.status == TaskStatus.pending

async def test_create_task_without_verb_raises(db, test_user):
    service = TaskService(db)
    with pytest.raises(TaskVerbError):
        await service.create(user_id=test_user.id, title="Novo branch de feature")

async def test_task_verb_error_has_suggestions(db, test_user):
    service = TaskService(db)
    with pytest.raises(TaskVerbError) as exc_info:
        await service.create(user_id=test_user.id, title="Reunião de alinhamento")
    assert len(exc_info.value.suggestions) == 3

async def test_task_verb_error_message_contains_first_word(db, test_user):
    service = TaskService(db)
    with pytest.raises(TaskVerbError) as exc_info:
        await service.create(user_id=test_user.id, title="Reunião diária")
    assert "Reunião" in str(exc_info.value)

async def test_mark_done_sets_done_at(db, test_user):
    service = TaskService(db)
    task = await service.create(user_id=test_user.id, title="Fazer revisão de código")
    done = await service.mark_done(task.id, test_user.id)
    assert done.status == TaskStatus.done
    assert done.done_at is not None

async def test_mark_blocked(db, test_user):
    service = TaskService(db)
    task = await service.create(user_id=test_user.id, title="Resolver bug crítico")
    blocked = await service.mark_blocked(task.id, test_user.id)
    assert blocked.status == TaskStatus.blocked

async def test_mark_pending_clears_done_at(db, test_user):
    service = TaskService(db)
    task = await service.create(user_id=test_user.id, title="Escrever documentação")
    done = await service.mark_done(task.id, test_user.id)
    assert done.done_at is not None
    pending = await service.mark_pending(done.id, test_user.id)
    assert pending.status == TaskStatus.pending
    assert pending.done_at is None

async def test_update_title_validates_verb(db, test_user):
    service = TaskService(db)
    task = await service.create(user_id=test_user.id, title="Configurar CI pipeline")
    with pytest.raises(TaskVerbError):
        await service.update(task.id, test_user.id, title="CI pipeline configurado")

async def test_task_quick_win_flag(db, test_user):
    service = TaskService(db)
    task = await service.create(
        user_id=test_user.id, title="Atualizar README", is_quick_win=True
    )
    assert task.is_quick_win is True

async def test_task_isolation_between_users(db, test_user):
    """Tasks from one user are not visible to another."""
    from app.models.user import User
    from app.utils.auth import hash_password

    other = User(email="other@pos.dev", password=hash_password("x"), name="Other")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    service = TaskService(db)
    await service.create(user_id=test_user.id, title="Criar feature A")
    tasks_other = await service.get_all(user_id=other.id)
    assert tasks_other == []
