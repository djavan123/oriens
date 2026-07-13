# scripts/run_migrations.py
"""Roda init_db() isolado (fora do boot do app).

Uso na VPS, para migrações potencialmente pesadas ANTES de trocar o container:

    docker compose -f docker-compose.prod.yml run --rm app \
        python scripts/run_migrations.py

Assim o schema já está migrado quando os novos containers sobem — o init_db()
do boot vira uma passada rápida por guards idempotentes.
"""
import asyncio
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

from app.logging_setup import configure_logging  # noqa: E402


async def main() -> None:
    configure_logging()
    from app.database import init_db

    await init_db()
    print("Migração concluída.")


if __name__ == "__main__":
    asyncio.run(main())
