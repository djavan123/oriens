from app.models.project import ProjectStatus
from app.repositories.project_section_repo import ProjectSectionRepository
from app.repositories.project_timeline_repo import ProjectTimelineRepository
from app.repositories.task_repo import TaskRepository
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


async def test_create_project_records_timeline(db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="Projeto A", status=ProjectStatus.em_andamento
    )
    assert p.id is not None
    assert p.status == ProjectStatus.em_andamento
    events = await ProjectTimelineRepository(db).get_by_project(p.id)
    assert len(events) >= 1  # project_created


async def test_project_task_order_index_appends(db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="P", status=ProjectStatus.em_andamento
    )
    ts = TaskService(db)
    t1 = await ts.create(test_user.id, "T1", project_id=p.id)
    t2 = await ts.create(test_user.id, "T2", project_id=p.id)
    assert t1.order_index == 0
    assert t2.order_index == 1


async def test_next_action_is_first_pending(db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="P", status=ProjectStatus.em_andamento
    )
    ts = TaskService(db)
    t1 = await ts.create(test_user.id, "First", project_id=p.id)
    await ts.create(test_user.id, "Second", project_id=p.id)
    na = await ProjectService(db).get_project_next_action(p.id, test_user.id)
    assert na["executable"] is True
    assert na["task"].id == t1.id


async def test_executability_states(db, test_user):
    svc = ProjectService(db)
    p_active = await svc.create(test_user.id, name="Active", status=ProjectStatus.em_andamento)
    p_new = await svc.create(test_user.id, name="New", status=ProjectStatus.nao_iniciado)
    p_done = await svc.create(test_user.id, name="Done", status=ProjectStatus.concluido)
    await TaskService(db).create(test_user.id, "do it", project_id=p_active.id)

    exe = await svc.get_executability(test_user.id, [p_active, p_new, p_done])
    assert exe[p_active.id]["state"] == "executable"
    assert exe[p_new.id]["state"] == "not_started"
    assert exe[p_done.id]["state"] == "completed"


async def test_executability_no_action_when_no_pending(db, test_user):
    svc = ProjectService(db)
    p = await svc.create(test_user.id, name="Empty", status=ProjectStatus.em_andamento)
    exe = await svc.get_executability(test_user.id, [p])
    assert exe[p.id]["state"] == "no_action"


async def test_section_task_reorder_moves_and_reindexes(db, test_user):
    p = await ProjectService(db).create(
        test_user.id, name="P", status=ProjectStatus.em_andamento
    )
    sec = await ProjectSectionRepository(db).create(p.id, "Seção 1")
    ts = TaskService(db)
    t1 = await ts.create(test_user.id, "A", project_id=p.id)
    t2 = await ts.create(test_user.id, "B", project_id=p.id)

    repo = TaskRepository(db)
    ok = await repo.reorder_section_tasks(p.id, test_user.id, sec.id, [t2.id, t1.id])
    assert ok is True

    await db.refresh(t1)
    await db.refresh(t2)
    assert t2.section_id == sec.id and t2.order_index == 0
    assert t1.section_id == sec.id and t1.order_index == 1


async def test_reorder_rejects_foreign_task(db, test_user):
    p1 = await ProjectService(db).create(test_user.id, name="P1", status=ProjectStatus.em_andamento)
    p2 = await ProjectService(db).create(test_user.id, name="P2", status=ProjectStatus.em_andamento)
    t_other = await TaskService(db).create(test_user.id, "outra", project_id=p2.id)
    # Tentar reordenar em p1 uma tarefa que pertence a p2 → False.
    ok = await TaskRepository(db).reorder_section_tasks(p1.id, test_user.id, None, [t_other.id])
    assert ok is False
