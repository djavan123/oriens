from app.models.task import TaskStatus
from app.services.importancia_service import importancia_from_prioridade
from app.services.task_service import TaskService


async def test_task_lifecycle(db, test_user):
    ts = TaskService(db)
    t = await ts.create(test_user.id, "Tarefa avulsa", importancia=5.0, sem_nota=False)
    assert t.status == TaskStatus.pending
    assert t.project_id is None

    done = await ts.mark_done(t.id, test_user.id)
    assert done.status == TaskStatus.done
    assert done.done_at is not None

    blocked = await ts.mark_blocked(t.id, test_user.id)
    assert blocked.status == TaskStatus.blocked

    pending = await ts.mark_pending(t.id, test_user.id)
    assert pending.status == TaskStatus.pending
    assert pending.done_at is None


async def test_standalone_task_importancia_mapping(db, test_user):
    t = await TaskService(db).create(
        test_user.id,
        "Avulsa alta",
        importancia=importancia_from_prioridade("alta"),
        sem_nota=False,
    )
    assert t.importancia == 5.0
    assert t.sem_nota is False


async def test_archive_hides_from_listing(db, test_user):
    ts = TaskService(db)
    t = await ts.create(test_user.id, "Some task", importancia=3.0, sem_nota=False)
    await ts.archive(t.id, test_user.id)
    listed = await ts.get_all(test_user.id)
    assert t.id not in {x.id for x in listed}
