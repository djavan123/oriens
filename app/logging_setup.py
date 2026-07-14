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


# Fallbacks de APP_VERSION (config.py e o ARG do Dockerfile). Em produção eles são
# valores fixos: dois builds diferentes compartilhariam a mesma URL de asset (?v=prod)
# e o cache longo do nginx congelaria o CSS/JS antigo por um ano.
_APP_VERSION_FALLBACKS = {"dev", "prod", ""}


def check_asset_version() -> None:
    """Aborta o boot (web) se em produção o APP_VERSION for o fallback fixo.

    O cache `immutable` dos estáticos só é seguro porque a URL carrega ?v=<git SHA>.
    """
    settings = get_settings()
    if not settings.DEBUG and settings.APP_VERSION.strip() in _APP_VERSION_FALLBACKS:
        raise RuntimeError(
            f"APP_VERSION={settings.APP_VERSION!r} com DEBUG=false. Os estáticos são "
            "cacheados por URL (?v=APP_VERSION); um valor fixo faz o navegador servir "
            "CSS/JS antigos após o deploy. Suba com o SHA do commit:\n"
            "  APP_VERSION=$(git rev-parse --short HEAD) docker compose "
            "-f docker-compose.prod.yml up -d --build"
        )


logger = logging.getLogger("oriens")
