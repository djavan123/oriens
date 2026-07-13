# tests/test_worker_state.py
"""Resiliência do worker: offset persistente em app_state, LIMIT do batch de lembretes."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.repositories.app_state_repo import AppStateRepository
from app.repositories.task_repo import TaskRepository
from app.services.reminder_service import REMINDER_BATCH_LIMIT, process_due_telegram
from app.utils.time import now_local


@pytest.mark.asyncio
async def test_app_state_set_get_update(db):
    repo = AppStateRepository(db)
    assert await repo.get("telegram_offset") is None
    await repo.set("telegram_offset", "42")
    assert await repo.get("telegram_offset") == "42"
    await repo.set("telegram_offset", "99")
    assert await repo.get("telegram_offset") == "99"


@pytest.mark.asyncio
async def test_reminder_batch_respects_limit(db, test_user):
    """Backlog maior que o lote: envia só REMINDER_BATCH_LIMIT por ciclo (mais
    antigos primeiro); o resto fica para os próximos ciclos, sem se perder."""
    task_repo = TaskRepository(db)
    overdue = now_local() - timedelta(hours=1)
    total = REMINDER_BATCH_LIMIT + 5
    for i in range(total):
        await task_repo.create(
            test_user.id,
            title=f"lembrete {i}",
            remind_at=overdue - timedelta(minutes=total - i),
        )

    sent = []

    async def fake_send(text, chat_id=None):
        sent.append(text)

    with patch("app.services.reminder_service.send_telegram", side_effect=fake_send), \
         patch("app.services.reminder_service.asyncio.sleep", new=AsyncMock()), \
         patch("app.services.reminder_service.get_settings") as mock_settings:
        mock_settings.return_value.TELEGRAM_CHAT_ID = "111"
        await process_due_telegram(db)
        assert len(sent) == REMINDER_BATCH_LIMIT

        sent.clear()
        await process_due_telegram(db)
        assert len(sent) == 5  # restante sai no ciclo seguinte

        sent.clear()
        await process_due_telegram(db)
        assert len(sent) == 0  # nada duplica
