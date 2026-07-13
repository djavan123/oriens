# app/worker.py
"""Processo de background do Oriens (lembretes + captura por Telegram).

Roda em UM único processo, separado do web. Assim o web pode escalar com vários
workers (gunicorn -w N) sem duplicar envios de lembrete nem consumir os updates
do Telegram em corrida.

Resiliência:
- O offset do getUpdates é persistido em `app_state` (chave `telegram_offset`) —
  um restart do worker NÃO reprocessa mensagens antigas (evita capturas duplicadas).
- Backoff exponencial em falha contínua (até 300s), reset em sucesso.
- Heartbeat em `app_state` (chave `worker_heartbeat`) a cada iteração de lembretes —
  o healthcheck do compose (scripts/worker_health.py) detecta loop travado.

Subir:  python -m app.worker   (serviço `worker` no docker-compose).
"""
import asyncio
import logging

from app.logging_setup import configure_logging, check_production_secrets

configure_logging()
logger = logging.getLogger("oriens.worker")

TELEGRAM_OFFSET_KEY = "telegram_offset"
HEARTBEAT_KEY = "worker_heartbeat"

_REMINDER_BASE_DELAY = 60.0
_TELEGRAM_BASE_DELAY = 2.0
_MAX_BACKOFF = 300.0


async def _reminder_loop():
    """Verifica lembretes vencidos a cada 60s, dispara o Telegram e grava heartbeat."""
    from app.database import AsyncSessionLocal
    from app.repositories.app_state_repo import AppStateRepository
    from app.services.reminder_service import process_due_telegram
    from app.utils.time import utcnow

    delay = _REMINDER_BASE_DELAY
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await process_due_telegram(db)
                await AppStateRepository(db).set(HEARTBEAT_KEY, utcnow().isoformat())
            delay = _REMINDER_BASE_DELAY
        except Exception:
            logger.exception("Erro no loop de lembretes")
            delay = min(delay * 2, _MAX_BACKOFF)
        await asyncio.sleep(delay)


async def _telegram_capture_loop():
    """Long polling getUpdates → caixa de entrada. Offset persistido em app_state."""
    from app.database import AsyncSessionLocal
    from app.repositories.app_state_repo import AppStateRepository
    from app.services.reminder_service import process_telegram_updates

    # Recupera o offset persistido (0 = nunca rodou / chave ausente).
    offset = 0
    try:
        async with AsyncSessionLocal() as db:
            raw = await AppStateRepository(db).get(TELEGRAM_OFFSET_KEY)
            offset = int(raw) if raw else 0
    except Exception:
        logger.exception("Falha ao recuperar telegram_offset; começando de 0")

    delay = _TELEGRAM_BASE_DELAY
    while True:
        try:
            async with AsyncSessionLocal() as db:
                new_offset = await process_telegram_updates(db, offset)
                if new_offset != offset:
                    await AppStateRepository(db).set(TELEGRAM_OFFSET_KEY, str(new_offset))
                    offset = new_offset
            delay = _TELEGRAM_BASE_DELAY
        except Exception:
            logger.exception("Erro no loop de captura do Telegram")
            delay = min(max(delay, 1.0) * 2, _MAX_BACKOFF)
        await asyncio.sleep(delay)


async def main():
    check_production_secrets()
    # Migração + seed são idempotentes e guardados por advisory lock (multi-processo).
    from app.database import init_db
    await init_db()
    logger.info("Worker Oriens iniciado (lembretes + captura Telegram).")
    await asyncio.gather(_reminder_loop(), _telegram_capture_loop())


if __name__ == "__main__":
    asyncio.run(main())
