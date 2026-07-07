# app/worker.py
"""Processo de background do Oriens (lembretes + captura por Telegram).

Roda em UM único processo, separado do web. Assim o web pode escalar com vários
workers (gunicorn -w N) sem duplicar envios de lembrete nem consumir os updates
do Telegram em corrida (o offset fica na memória deste processo único).

Subir:  python -m app.worker   (serviço `worker` no docker-compose).
"""
import asyncio
import logging

from app.logging_setup import configure_logging, check_production_secrets

configure_logging()
logger = logging.getLogger("oriens.worker")


async def _reminder_loop():
    """Verifica lembretes vencidos a cada 60s e dispara o Telegram."""
    from app.database import AsyncSessionLocal
    from app.services.reminder_service import process_due_telegram
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await process_due_telegram(db)
        except Exception:
            logger.exception("Erro no loop de lembretes")
        await asyncio.sleep(60)


async def _telegram_capture_loop():
    """Long polling getUpdates → caixa de entrada. Mantém o offset em memória."""
    from app.database import AsyncSessionLocal
    from app.services.reminder_service import process_telegram_updates
    offset = 0
    while True:
        try:
            async with AsyncSessionLocal() as db:
                offset = await process_telegram_updates(db, offset)
        except Exception:
            logger.exception("Erro no loop de captura do Telegram")
        await asyncio.sleep(2)


async def main():
    check_production_secrets()
    # Migração + seed são idempotentes e guardados por advisory lock (multi-processo).
    from app.database import init_db
    await init_db()
    logger.info("Worker Oriens iniciado (lembretes + captura Telegram).")
    await asyncio.gather(_reminder_loop(), _telegram_capture_loop())


if __name__ == "__main__":
    asyncio.run(main())
