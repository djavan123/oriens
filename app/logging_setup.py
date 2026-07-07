# app/logging_setup.py
"""Configuração de logging única para o web e o worker."""
import logging
from logging.config import dictConfig

from app.config import get_settings


def configure_logging() -> None:
    app_level = "DEBUG" if get_settings().DEBUG else "INFO"
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            },
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
