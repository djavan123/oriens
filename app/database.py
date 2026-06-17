# app/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    return create_async_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        echo=settings.DEBUG,
    )


engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


_ENSURE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "projects": [
        ("tags", "TEXT"),
        ("scope", "TEXT"),
        ("done_at", "DATETIME"),
        ("proxima_acao", "TEXT"),
        ("premissas", "TEXT"),
        ("responsavel_id", "INTEGER"),
    ],
    "tasks": [
        ("deadline", "DATETIME"),
        ("archived", "BOOLEAN NOT NULL DEFAULT 0"),
        ("parent_id", "INTEGER"),
        ("responsavel_id", "INTEGER"),
        ("tags", "TEXT"),
    ],
    "contexts": [
        ("user_id", "INTEGER"),
    ],
    "project_timeline": [
        ("description", "VARCHAR(255)"),
    ],
}


def _ensure_columns(conn) -> None:
    # Migração por ALTER TABLE é específica do SQLite (dev). Em PostgreSQL o
    # create_all já cria o schema completo a partir dos models — nada a ajustar.
    if conn.dialect.name != "sqlite":
        return
    for table, columns in _ENSURE_COLUMNS.items():
        existing = {
            row[1] for row in conn.exec_driver_sql(f'PRAGMA table_info("{table}")')
        }
        if not existing:
            continue
        for name, ddl in columns:
            if name not in existing:
                conn.exec_driver_sql(
                    f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl}'
                )


def _migrate_data(conn) -> None:
    """Migra status de projetos do schema antigo e semeia o project_timeline.

    Usa SQL específico do SQLite (PRAGMA / INSERT OR IGNORE). Só roda em SQLite;
    em PostgreSQL o banco nasce já no schema atual, sem dados legados a migrar.
    """
    if conn.dialect.name != "sqlite":
        return
    try:
        existing = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info("projects")')}
        if "status" not in existing:
            return
        conn.exec_driver_sql(
            "UPDATE projects SET status='em_andamento' WHERE status='active'"
        )
        conn.exec_driver_sql(
            "UPDATE projects SET status='nao_iniciado' WHERE status='paused'"
        )
        conn.exec_driver_sql(
            "UPDATE projects SET status='concluido' WHERE status IN ('done', 'archived')"
        )
    except Exception:
        pass
    try:
        tl_cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info("project_timeline")')}
        if tl_cols:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO project_timeline (project_id, user_id, event_type, description, created_at) "
                "SELECT id, user_id, 'project_created', 'Projeto criado', created_at FROM projects "
                "WHERE id NOT IN (SELECT DISTINCT project_id FROM project_timeline WHERE event_type = 'project_created')"
            )
    except Exception:
        pass


async def init_db():
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_columns)
        await conn.run_sync(_migrate_data)
