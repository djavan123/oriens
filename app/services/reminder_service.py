# app/services/reminder_service.py
import asyncio
import logging
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.task import Task, TaskStatus
from app.utils.time import now_local

logger = logging.getLogger("oriens.reminders")

# Lote máximo de lembretes por ciclo + pausa entre envios (Telegram limita ~30 msg/s;
# ficamos bem abaixo para nunca tomar 429 em rajada).
REMINDER_BATCH_LIMIT = 100
_SEND_THROTTLE_S = 0.05


async def send_telegram(text: str, chat_id: Optional[str] = None) -> None:
    """Envia mensagem ao Telegram. No-op se não configurado.

    `chat_id` = destino (chat do usuário). Se omitido, cai no TELEGRAM_CHAT_ID
    global do .env (compatibilidade single-user). O bot token é sempre global.
    Em 429 respeita o retry_after e re-tenta UMA vez; status != 200 é logado.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    target = chat_id or settings.TELEGRAM_CHAT_ID
    if not token or not target:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": target, "text": text}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 429:
                retry_after = 1.0
                try:
                    retry_after = float(
                        (resp.json().get("parameters") or {}).get("retry_after", 1)
                    )
                except Exception:
                    pass
                await asyncio.sleep(min(retry_after, 30.0))
                resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    "Telegram sendMessage retornou %s: %s",
                    resp.status_code, resp.text[:200],
                )
    except Exception:
        # Lembrete não deve derrubar o loop nem o app.
        logger.exception("Falha ao enviar mensagem ao Telegram")


async def process_telegram_updates(db: AsyncSession, offset: int) -> int:
    """Long polling getUpdates. Cada mensagem é roteada ao usuário dono do chat
    (users.telegram_chat_id); cria a captura dele e confirma com '✓ Capturado'.

    Compatibilidade single-user: se nenhum usuário tem aquele chat mas ele é o
    TELEGRAM_CHAT_ID global do .env, a captura vai para o primeiro usuário.

    Retorna o novo offset (último update_id + 1). No-op se o bot não estiver
    configurado.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return offset

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"timeout": 30, "allowed_updates": '["message"]'}
    if offset:
        params["offset"] = offset
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.get(url, params=params)
            payload = resp.json()
        if not payload.get("ok"):
            logger.warning("getUpdates retornou erro: %s", payload.get("description"))
            return offset
        updates = payload.get("result", [])
    except Exception:
        logger.exception("Falha ao consultar getUpdates do Telegram")
        return offset

    if not updates:
        return offset

    from app.repositories.user_repo import UserRepository
    from app.services.capture_service import CaptureService

    urepo = UserRepository(db)
    legacy_chat = (settings.TELEGRAM_CHAT_ID or "").strip()
    new_offset = offset
    for upd in updates:
        new_offset = max(new_offset, upd.get("update_id", 0) + 1)
        message = upd.get("message") or {}
        text = (message.get("text") or "").strip()
        chat = (message.get("chat") or {}).get("id")
        if not text or chat is None:
            continue
        chat = str(chat)
        user = await urepo.get_by_telegram_chat_id(chat)
        if user is None and legacy_chat and chat == legacy_chat:
            user = await urepo.get_first()
        if user is None:
            # Chat desconhecido — ignora (não vaza captura para outro usuário).
            continue
        await CaptureService(db).create(user_id=user.id, content=text)
        await send_telegram(f"✓ Capturado: {text[:60]}", chat_id=chat)

    return new_offset


def _due_filter():
    now = now_local()
    return (
        Task.remind_at.is_not(None),
        Task.remind_at <= now,
        Task.status != TaskStatus.done,
        Task.archived.is_(False),
    )


async def process_due_telegram(db: AsyncSession) -> None:
    """Envia ao Telegram os lembretes vencidos, cada um ao chat do dono da tarefa.

    Limitado a REMINDER_BATCH_LIMIT por ciclo (mais antigos primeiro) com pausa
    entre envios — um backlog grande não estoura o rate limit nem trava o loop;
    o restante sai nos próximos ciclos (o flag reminder_telegram_sent garante
    que nada se perde nem duplica).
    """
    result = await db.execute(
        select(Task)
        .where(
            *_due_filter(),
            Task.reminder_telegram_sent.is_(False),
        )
        .order_by(Task.remind_at.asc())
        .limit(REMINDER_BATCH_LIMIT)
    )
    tasks = list(result.scalars().all())
    if not tasks:
        return

    from app.repositories.user_repo import UserRepository
    urepo = UserRepository(db)
    legacy_chat = (get_settings().TELEGRAM_CHAT_ID or "").strip() or None
    chat_cache: dict[int, Optional[str]] = {}
    changed = False
    for task in tasks:
        if task.user_id not in chat_cache:
            owner = await urepo.get_by_id(task.user_id)
            chat_cache[task.user_id] = (owner.telegram_chat_id if owner else None) or legacy_chat
        chat = chat_cache[task.user_id]
        if not chat:
            continue  # dono sem Telegram e sem fallback — tenta de novo depois
        quando = task.remind_at.strftime("%d/%m %H:%M") if task.remind_at else ""
        await send_telegram(f"🔔 Lembrete Oriens\n{task.title}\n{quando}", chat_id=chat)
        task.reminder_telegram_sent = True
        changed = True
        await asyncio.sleep(_SEND_THROTTLE_S)
    if changed:
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
