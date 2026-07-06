# app/models/project_risk.py
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RiskStatus(str, enum.Enum):
    open = "open"
    mitigated = "mitigated"
    closed = "closed"


class ProjectRisk(Base):
    __tablename__ = "project_risks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, native_enum=False, length=50), default=RiskLevel.medium, nullable=False)
    probability: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, native_enum=False, length=50), default=RiskLevel.medium, nullable=False)
    mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RiskStatus] = mapped_column(Enum(RiskStatus, native_enum=False, length=50), default=RiskStatus.open, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
