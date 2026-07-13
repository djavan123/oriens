# scripts/worker_health.py
"""Healthcheck do serviço `worker` no docker-compose.

Falha (exit 1) se o heartbeat gravado em app_state (worker_heartbeat, UTC naive)
estiver mais velho que 5 minutos — indica loop de lembretes travado sem crashar.
Falha branda (exit 0) se a tabela ainda não existir (primeiro boot em migração).
"""
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

MAX_AGE = timedelta(minutes=5)


async def main() -> int:
    from app.database import AsyncSessionLocal
    from app.repositories.app_state_repo import AppStateRepository
    from app.worker import HEARTBEAT_KEY

    try:
        async with AsyncSessionLocal() as db:
            raw = await AppStateRepository(db).get(HEARTBEAT_KEY)
    except Exception as exc:
        # Banco fora do ar ou tabela ainda não criada: não mata o worker por isso
        # (o healthcheck do serviço db já cobre o banco).
        print(f"heartbeat indisponível ({exc}); tolerando", file=sys.stderr)
        return 0
    if not raw:
        print("sem heartbeat ainda; tolerando (worker recém-iniciado)", file=sys.stderr)
        return 0
    try:
        beat = datetime.fromisoformat(raw)
    except ValueError:
        print(f"heartbeat ilegível: {raw!r}", file=sys.stderr)
        return 1
    age = datetime.utcnow() - beat
    if age > MAX_AGE:
        print(f"heartbeat velho demais: {age}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
