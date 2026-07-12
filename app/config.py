from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/oriens.db"
    SECRET_KEY: str = "troque-isso-em-producao"
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "null"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEBUG: bool = True
    # Em produção (HTTPS) defina COOKIE_SECURE=true para enviar cookies só por TLS.
    COOKIE_SECURE: bool = False
    # Lembretes via Telegram (opcional). Só envia se ambos estiverem preenchidos.
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    # Pool de conexões do PostgreSQL, POR PROCESSO. Com 3 workers web + 1 worker
    # de fundo: (5+5) × 4 = 40 conexões potenciais < max_connections=100 do PG.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    # extra="ignore": o .env de produção também contém POSTGRES_PASSWORD (consumido
    # só pelo serviço `db` do docker-compose, não por este app) — sem isso, o Pydantic
    # aborta o boot com ValidationError sempre que o .env tiver uma chave não declarada aqui.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
