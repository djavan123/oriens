# app/models/weekly_directive.py
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeeklyDirective(Base):
    __tablename__ = "weekly_directives"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    weekly_theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    top_1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    top_2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    top_3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ignore_list: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    major_risk: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    physiological_priority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
