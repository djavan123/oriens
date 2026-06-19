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
        ("archived", "BOOLEAN NOT NULL DEFAULT 0"),
    ],
    "tasks": [
        ("deadline", "DATETIME"),
        ("archived", "BOOLEAN NOT NULL DEFAULT 0"),
        ("parent_id", "INTEGER"),
        ("responsavel_id", "INTEGER"),
        ("tags", "TEXT"),
        ("remind_at", "DATETIME"),
        ("reminder_telegram_sent", "BOOLEAN NOT NULL DEFAULT 0"),
        ("reminder_acked", "BOOLEAN NOT NULL DEFAULT 0"),
        ("importancia", "REAL NOT NULL DEFAULT 0"),
        ("sem_nota", "BOOLEAN NOT NULL DEFAULT 1"),
        ("order_index", "INTEGER"),
    ],
    "users": [
        ("foco_do_dia", "TEXT"),
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


# Migrações aditivas para PostgreSQL (prod). Usa ADD COLUMN IF NOT EXISTS
# (idempotente, PG 9.6+). Tipos em sintaxe PostgreSQL.
_ENSURE_COLUMNS_PG: dict[str, list[tuple[str, str]]] = {
    "tasks": [
        ("remind_at", "TIMESTAMP"),
        ("reminder_telegram_sent", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("reminder_acked", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("importancia", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
        ("sem_nota", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("order_index", "INTEGER"),
    ],
    "projects": [
        ("archived", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ],
    "users": [
        ("foco_do_dia", "TEXT"),
    ],
}


def _ensure_columns_postgres(conn) -> None:
    if conn.dialect.name != "postgresql":
        return
    for table, columns in _ENSURE_COLUMNS_PG.items():
        for name, ddl in columns:
            conn.exec_driver_sql(
                f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS {name} {ddl}'
            )
    # Inicializa order_index para tarefas de projeto existentes (idempotente).
    try:
        conn.exec_driver_sql("""
            UPDATE tasks SET order_index = sub.rn
            FROM (
                SELECT id,
                    (ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY id ASC) - 1) AS rn
                FROM tasks
                WHERE project_id IS NOT NULL AND parent_id IS NULL
            ) sub
            WHERE tasks.id = sub.id AND tasks.order_index IS NULL
        """)
    except Exception:
        pass


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
    # Inicializa order_index para tarefas de projeto existentes (0-based, por id asc).
    try:
        task_cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info("tasks")')}
        if "order_index" in task_cols:
            conn.exec_driver_sql(
                "UPDATE tasks "
                "SET order_index = ("
                "  SELECT COUNT(*) FROM tasks t2"
                "  WHERE t2.project_id = tasks.project_id"
                "  AND t2.parent_id IS NULL"
                "  AND t2.id < tasks.id"
                ") "
                "WHERE project_id IS NOT NULL AND parent_id IS NULL AND order_index IS NULL"
            )
    except Exception:
        pass


async def init_db():
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_columns)
        await conn.run_sync(_ensure_columns_postgres)
        await conn.run_sync(_migrate_data)
