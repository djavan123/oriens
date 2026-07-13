# app/models/app_state.py
"""Estado interno do app (chave→valor). Usado pelo worker de fundo para
persistir o offset do getUpdates do Telegram (evita reprocessar mensagens após
restart) e o heartbeat de liveness (healthcheck do serviço worker)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.time import utcnow


class AppState(Base):
    __tablename__ = "app_state"

    key:        Mapped[str]           = mapped_column(String(64), primary_key=True)
    value:      Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime]      = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
