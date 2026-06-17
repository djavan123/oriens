# app/routes/api/reminders.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.task_repo import TaskRepository
from app.services.reminder_service import get_due_popups
from app.templates_env import templates
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/reminders", tags=["api:reminders"])


@router.get("/due", response_class=HTMLResponse)
async def due_reminders(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = await get_due_popups(db, current_user.id)
    return templates.TemplateResponse(
        request, "partials/reminder_popup.html", {"reminders": tasks}
    )


@router.post("/{task_id}/ack", response_class=HTMLResponse)
async def ack_reminder(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id, current_user.id)
    if task:
        await repo.update(task, reminder_acked=True)
    return HTMLResponse("")
