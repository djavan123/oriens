# app/logging_setup.py
"""Configuração de logging única para o web e o worker."""
import json
import logging
from logging.config import dictConfig

from app.config import get_settings


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por evento (LOG_JSON=true) — pronto para agregadores
    (Loki, CloudWatch, `docker logs | jq`). Sem dependência externa."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    settings = get_settings()
    app_level = "DEBUG" if settings.DEBUG else "INFO"
    formatter = (
        {"()": "app.logging_setup.JsonFormatter"}
        if settings.LOG_JSON
        else {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}
    )
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        # Root em INFO evita ruído de DEBUG de libs (passlib, sqlalchemy, httpx).
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            "oriens": {"handlers": ["console"], "level": app_level, "propagate": False},
        },
    })


def check_production_secrets() -> None:
    """Aborta o boot se rodar em produção com a SECRET_KEY padrão (JWT forjável)."""
    settings = get_settings()
    if not settings.DEBUG and settings.SECRET_KEY == "troque-isso-em-producao":
        raise RuntimeError(
            "SECRET_KEY padrão detectada com DEBUG=false. Defina uma SECRET_KEY "
            "forte no .env (ex.: openssl rand -hex 32) antes de subir em produção."
        )


logger = logging.getLogger("oriens")
