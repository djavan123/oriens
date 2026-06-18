# app/models/project_timeline.py
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimelineEventType(str, enum.Enum):
    project_created   = "project_created"
    status_changed    = "status_changed"
    task_created      = "task_created"
    task_done         = "task_done"
    decision_recorded = "decision_recorded"


class ProjectTimeline(Base):
    __tablename__ = "project_timeline"

    id:          Mapped[int]           = mapped_column(primary_key=True, index=True)
    project_id:  Mapped[int]           = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id:     Mapped[int]           = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type:  Mapped[str]           = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), index=True)
