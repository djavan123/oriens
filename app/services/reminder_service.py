# app/services/reminder_service.py
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.task import Task, TaskStatus


async def send_telegram(text: str) -> None:
    """Envia mensagem ao Telegram. No-op se não configurado."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text})
    except Exception:
        # Lembrete não deve derrubar o loop nem o app.
        pass


def _due_filter():
    now = datetime.now()
    return (
        Task.remind_at.is_not(None),
        Task.remind_at <= now,
        Task.status != TaskStatus.done,
        Task.archived.is_(False),
    )


async def process_due_telegram(db: AsyncSession) -> None:
    """Envia ao Telegram os lembretes vencidos ainda não enviados."""
    result = await db.execute(
        select(Task).where(
            *_due_filter(),
            Task.reminder_telegram_sent.is_(False),
        )
    )
    tasks = list(result.scalars().all())
    if not tasks:
        return
    for task in tasks:
        quando = task.remind_at.strftime("%d/%m %H:%M") if task.remind_at else ""
        await send_telegram(f"🔔 Lembrete Oriens\n{task.title}\n{quando}")
        task.reminder_telegram_sent = True
    await db.commit()


async def get_due_popups(db: AsyncSession, user_id: int) -> list[Task]:
    """Lembretes vencidos ainda não confirmados (para o popup no app)."""
    result = await db.execute(
        select(Task)
        .where(
            *_due_filter(),
            Task.user_id == user_id,
            Task.reminder_acked.is_(False),
        )
        .order_by(Task.remind_at.asc())
    )
    return list(result.scalars().all())
