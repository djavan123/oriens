from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Foco do dia (singleton por usuário, sem histórico) — editável no Dashboard.
    foco_do_dia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Chat do Telegram do usuário (lembretes + captura roteados por dono). NULL =
    # usa o TELEGRAM_CHAT_ID global do .env (compatibilidade single-user).
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
