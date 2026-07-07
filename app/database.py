# app/database.py
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger("oriens.database")


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    is_sqlite = "sqlite" in settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    kwargs = dict(connect_args=connect_args, echo=settings.DEBUG)
    if not is_sqlite:
        # Pool dimensionado para múltiplos workers; pre_ping/recycle evitam
        # conexões mortas atrás de PG gerenciado/pgbouncer ou após restart do banco.
        kwargs.update(
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return create_async_engine(settings.DATABASE_URL, **kwargs)


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
        ("section_id", "INTEGER"),
    ],
    "users": [
        ("foco_do_dia", "TEXT"),
        ("telegram_chat_id", "VARCHAR(64)"),
    ],
    "contexts": [
        ("user_id", "INTEGER"),
    ],
    "project_timeline": [
        ("description", "VARCHAR(255)"),
    ],
    "capture_inbox": [
        ("resolved_at", "DATETIME"),
        ("discarded_at", "DATETIME"),
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
# Espelha _ENSURE_COLUMNS (SQLite) com sintaxe PostgreSQL. Mantê-los em paridade
# garante que um banco PG pré-existente receba as mesmas colunas que o SQLite adiciona.
_ENSURE_COLUMNS_PG: dict[str, list[tuple[str, str]]] = {
    "projects": [
        ("tags", "TEXT"),
        ("scope", "TEXT"),
        ("done_at", "TIMESTAMP"),
        ("proxima_acao", "TEXT"),
        ("premissas", "TEXT"),
        ("responsavel_id", "INTEGER"),
        ("archived", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ],
    "tasks": [
        ("deadline", "TIMESTAMP"),
        ("archived", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("parent_id", "INTEGER"),
        ("responsavel_id", "INTEGER"),
        ("tags", "TEXT"),
        ("remind_at", "TIMESTAMP"),
        ("reminder_telegram_sent", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("reminder_acked", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("importancia", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
        ("sem_nota", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("order_index", "INTEGER"),
        ("section_id", "INTEGER"),
    ],
    "users": [
        ("foco_do_dia", "TEXT"),
        ("telegram_chat_id", "VARCHAR(64)"),
    ],
    "contexts": [
        ("user_id", "INTEGER"),
    ],
    "project_timeline": [
        ("description", "VARCHAR(255)"),
    ],
    "capture_inbox": [
        ("resolved_at", "TIMESTAMP"),
        ("discarded_at", "TIMESTAMP"),
    ],
}


# Colunas que nasceram como ENUM nativo do PG e agora usam VARCHAR (native_enum=False).
# Converter elimina o risco de ALTER TYPE ao introduzir um novo valor de status/energia.
_PG_ENUM_TO_VARCHAR: dict[str, list[str]] = {
    "tasks": ["status", "energy", "cognitive_load"],
    "projects": ["status"],
    "project_risks": ["impact", "probability", "status"],
}


def _ensure_columns_postgres(conn) -> None:
    if conn.dialect.name != "postgresql":
        return
    for table, columns in _ENSURE_COLUMNS_PG.items():
        for name, ddl in columns:
            conn.exec_driver_sql(
                f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS {name} {ddl}'
            )
    # Converte colunas ainda em ENUM nativo → VARCHAR (uma vez; guardado por tipo).
    for table, cols in _PG_ENUM_TO_VARCHAR.items():
        for col in cols:
            row = conn.exec_driver_sql(
                "SELECT data_type FROM information_schema.columns "
                f"WHERE table_name = '{table}' AND column_name = '{col}'"
            ).fetchone()
            if row and row[0] == "USER-DEFINED":
                conn.exec_driver_sql(
                    f'ALTER TABLE "{table}" ALTER COLUMN {col} '
                    f"TYPE VARCHAR(50) USING {col}::text"
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
        logger.exception("Falha ao inicializar order_index (PostgreSQL)")


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
        logger.exception("Falha ao migrar status de projetos (SQLite)")
    try:
        tl_cols = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info("project_timeline")')}
        if tl_cols:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO project_timeline (project_id, user_id, event_type, description, created_at) "
                "SELECT id, user_id, 'project_created', 'Projeto criado', created_at FROM projects "
                "WHERE id NOT IN (SELECT DISTINCT project_id FROM project_timeline WHERE event_type = 'project_created')"
            )
    except Exception:
        logger.exception("Falha ao semear project_timeline (SQLite)")
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
        logger.exception("Falha ao inicializar order_index (SQLite)")


# Chave arbitrária do advisory lock que serializa migração/seed entre workers.
_MIGRATION_LOCK_KEY = 825739201

# Índices adicionais em colunas quentes (filtros frequentes). CREATE INDEX IF NOT
# EXISTS é suportado por SQLite e PostgreSQL; nomes iguais aos que o create_all gera.
_INDEXES: list[tuple[str, str, str]] = [
    ("ix_tasks_deadline", "tasks", "deadline"),
    ("ix_tasks_remind_at", "tasks", "remind_at"),
    ("ix_tasks_status", "tasks", "status"),
    ("ix_tasks_archived", "tasks", "archived"),
    ("ix_tasks_section_id", "tasks", "section_id"),
    ("ix_capture_inbox_processed", "capture_inbox", "processed"),
]


def _acquire_migration_lock(conn) -> None:
    """Lock de transação no PG — só um worker roda a migração por vez; os demais
    esperam e reexecutam passos idempotentes. No-op em SQLite (1 processo)."""
    if conn.dialect.name == "postgresql":
        conn.exec_driver_sql(f"SELECT pg_advisory_xact_lock({_MIGRATION_LOCK_KEY})")


def _ensure_indexes(conn) -> None:
    for name, table, col in _INDEXES:
        conn.exec_driver_sql(
            f'CREATE INDEX IF NOT EXISTS {name} ON "{table}" ({col})'
        )


def _seed_contexts(conn) -> None:
    """Semeia os 4 contextos padrão se a tabela estiver vazia (idempotente)."""
    row = conn.exec_driver_sql("SELECT COUNT(*) FROM contexts").fetchone()
    if row and row[0]:
        return
    conn.exec_driver_sql(
        "INSERT INTO contexts (name, type) VALUES "
        "('Trabalho', 'work'), ('Recuperação', 'home_recovery'), "
        "('Casa', 'home_operational'), ('Academia', 'gym')"
    )


async def init_db():
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        # O lock cobre toda a transação (DDL + índices + seed); libera no commit.
        await conn.run_sync(_acquire_migration_lock)
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_columns)
        await conn.run_sync(_ensure_columns_postgres)
        await conn.run_sync(_migrate_data)
        await conn.run_sync(_ensure_indexes)
        await conn.run_sync(_seed_contexts)
