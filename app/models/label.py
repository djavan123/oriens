# app/models/label.py
from typing import Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Label(Base):
    __tablename__ = "labels"

    id:      Mapped[int]           = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int]           = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name:    Mapped[str]           = mapped_column(String(50), nullable=False)
    color:   Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
