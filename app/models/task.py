import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Float, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnergyLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    blocked = "blocked"


class CognitiveLoad(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    deep = "deep"
    pressure = "pressure"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    responsavel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    context_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contexts.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    energy: Mapped[EnergyLevel] = mapped_column(Enum(EnergyLevel), default=EnergyLevel.medium, nullable=False)
    is_quick_win: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Executive fields
    cognitive_load: Mapped[CognitiveLoad] = mapped_column(Enum(CognitiveLoad), default=CognitiveLoad.medium, nullable=False)
    financial_impact: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    operational_risk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    strategic_impact: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    task_urgency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    effort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    # Importância ponderada (0-5) calculada a partir dos critérios do contexto.
    importancia: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    sem_nota: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tags:     Mapped[Optional[str]]      = mapped_column(String, nullable=True)
    # Lembrete (sem recorrência)
    remind_at:               Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reminder_telegram_sent:  Mapped[bool]               = mapped_column(Boolean, default=False, nullable=False)
    reminder_acked:          Mapped[bool]               = mapped_column(Boolean, default=False, nullable=False)
    # Ordenação manual dentro do projeto (NULL para tarefas avulsas e subtarefas).
    order_index:             Mapped[Optional[int]]      = mapped_column(Integer, nullable=True)
