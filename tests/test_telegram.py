from app.repositories.user_repo import UserRepository
from app.services.reminder_service import send_telegram


async def test_set_and_get_telegram_chat_id(db, test_user):
    repo = UserRepository(db)
    await repo.set_telegram_chat_id(test_user.id, "123456789")
    found = await repo.get_by_telegram_chat_id("123456789")
    assert found is not None
    assert found.id == test_user.id


async def test_clear_telegram_chat_id(db, test_user):
    repo = UserRepository(db)
    await repo.set_telegram_chat_id(test_user.id, "999")
    await repo.set_telegram_chat_id(test_user.id, "")  # limpa → None
    assert await repo.get_by_telegram_chat_id("999") is None
    refreshed = await repo.get_by_id(test_user.id)
    assert refreshed.telegram_chat_id is None


async def test_send_telegram_noop_without_config(db):
    # Sem token/chat configurados, não deve levantar exceção (no-op).
    await send_telegram("oi", chat_id=None)
