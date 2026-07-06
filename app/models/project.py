import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectStatus(str, enum.Enum):
    nao_iniciado = "nao_iniciado"
    em_andamento = "em_andamento"
    concluido = "concluido"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    responsavel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    context_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contexts.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus, native_enum=False, length=50), default=ProjectStatus.nao_iniciado, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Executive fields
    strategic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quarter: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    strategic_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proxima_acao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    premissas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
