# scripts/migrate_to_postgres.py
# Copia TODOS os dados do SQLite local para o PostgreSQL de produção.
#
# OPCIONAL — só use se quiser preservar dados já criados no SQLite.
# O mais simples para um primeiro deploy é começar do zero (refazer o /setup).
#
# Uso (na VPS, com o Postgres já no ar e o .env de produção carregado):
#   1) Copie o seu data/oriens.db para a VPS, dentro da pasta do projeto.
#   2) Rode o Postgres:  docker compose -f docker-compose.prod.yml up -d db
#   3) Exponha a porta do Postgres OU rode este script dentro de um container
#      com acesso ao banco. A forma mais simples:
#        docker compose -f docker-compose.prod.yml run --rm \
#          -v "$PWD/data:/app/data" app python scripts/migrate_to_postgres.py
#
# Lê SQLITE_URL e PG_URL do ambiente (ou usa os padrões abaixo).
import asyncio
import os

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registra todos os models no metadata)
from app.database import Base

SQLITE_URL = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./data/oriens.db")
PG_URL = os.getenv("PG_URL") or os.getenv("DATABASE_URL", "postgresql+asyncpg://oriens:senha@db:5432/oriens")


async def main() -> None:
    src = create_async_engine(SQLITE_URL)
    dst = create_async_engine(PG_URL)

    # Cria o schema completo no destino (idempotente).
    async with dst.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with src.connect() as s, dst.begin() as d:
        # sorted_tables respeita a ordem das foreign keys.
        for table in Base.metadata.sorted_tables:
            rows = (await s.execute(select(table))).mappings().all()
            if rows:
                await d.execute(insert(table), [dict(r) for r in rows])
            print(f"{table.name:24s} {len(rows):>5d} linhas")

        # Reacerta as sequências dos IDs (senão o próximo INSERT colide).
        for table in Base.metadata.sorted_tables:
            pk_cols = list(table.primary_key.columns)
            if len(pk_cols) == 1 and pk_cols[0].autoincrement:
                col = pk_cols[0].name
                await d.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', '{col}'), "
                    f"COALESCE((SELECT MAX({col}) FROM {table.name}), 1))"
                ))

    await src.dispose()
    await dst.dispose()
    print("\nMigração concluída.")


if __name__ == "__main__":
    asyncio.run(main())
