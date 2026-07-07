# app/utils/time.py
"""Helpers de data/hora com convenção única.

Todas as colunas DateTime do banco são *naive* (sem tzinfo). Para não misturar
valores tz-aware com naive — o que quebra comparações no PostgreSQL e a ordenação
lexical no SQLite — o código usa SEMPRE `utcnow()` (naive UTC) para timestamps
internos (created/updated/done, comparação de prazos, expiração de token).

A única exceção são os lembretes (`remind_at`), que são horários *locais* digitados
pelo usuário e comparados contra o relógio local do container (TZ=America/Sao_Paulo).
Para esse caso específico use `now_local()`, deixando a fronteira explícita.
"""
from datetime import datetime


def utcnow() -> datetime:
    """Agora em UTC, naive (sem tzinfo). Convenção padrão do sistema."""
    return datetime.utcnow()


def now_local() -> datetime:
    """Agora no fuso local do processo (TZ), naive. Use só para lembretes."""
    return datetime.now()
