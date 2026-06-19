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


async def process_telegram_updates(db: AsyncSession, offset: int) -> int:
    """Long polling getUpdates (SCRIPT 13). Aceita só mensagens do TELEGRAM_CHAT_ID,
    cria captura para o usuário dono e confirma com '✓ Capturado'.

    Retorna o novo offset (último update_id + 1). No-op (retorna o offset recebido)
    se o bot/chat não estiverem configurados.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return offset
    try:
        allowed_chat = int(chat_id)
    except (TypeError, ValueError):
        return offset

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": 30, "allowed_updates": '["message"]'}
    if offset:
        params["offset"] = offset
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.get(url, params=params)
            updates = resp.json().get("result", [])
    except Exception:
        return offset

    if not updates:
        return offset

    from app.repositories.user_repo import UserRepository
    from app.services.capture_service import CaptureService

    owner = await UserRepository(db).get_first()
    new_offset = offset
    for upd in updates:
        new_offset = max(new_offset, upd.get("update_id", 0) + 1)
        message = upd.get("message") or {}
        text = (message.get("text") or "").strip()
        chat = (message.get("chat") or {}).get("id")
        # Só o chat configurado; ignora comandos vazios e outros chats.
        if not text or chat != allowed_chat or owner is None:
            continue
        await CaptureService(db).create(user_id=owner.id, content=text)
        await send_telegram(f"✓ Capturado: {text[:60]}")

    return new_offset


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
