from datetime import timedelta

from app.services.reminder_service import get_due_popups
from app.services.task_service import TaskService
from app.utils.time import now_local


async def test_due_popups_returns_only_overdue(db, test_user):
    ts = TaskService(db)
    past = now_local() - timedelta(hours=1)
    future = now_local() + timedelta(hours=1)
    t_due = await ts.create(test_user.id, "Vencido", remind_at=past)
    t_future = await ts.create(test_user.id, "Futuro", remind_at=future)

    due = await get_due_popups(db, test_user.id)
    ids = {t.id for t in due}
    assert t_due.id in ids
    assert t_future.id not in ids


async def test_acked_reminder_not_returned(db, test_user):
    ts = TaskService(db)
    past = now_local() - timedelta(hours=1)
    t = await ts.create(test_user.id, "Vencido ack", remind_at=past, reminder_acked=True)
    due = await get_due_popups(db, test_user.id)
    assert t.id not in {x.id for x in due}
