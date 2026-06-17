# app/models/context.py
import enum
from typing import Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContextType(str, enum.Enum):
    work = "work"
    home_recovery = "home_recovery"
    home_operational = "home_operational"
    gym = "gym"


_LABELS = {
    ContextType.work: "Trabalho",
    ContextType.home_recovery: "Recuperação",
    ContextType.home_operational: "Casa",
    ContextType.gym: "Academia",
}


class Context(Base):
    __tablename__ = "contexts"

    id:      Mapped[int]           = mapped_column(primary_key=True, index=True)
    name:    Mapped[str]           = mapped_column(String(100), nullable=False)
    type:    Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    @property
    def label(self) -> str:
        try:
            ct = ContextType(self.type)
            return _LABELS.get(ct, self.name)
        except (ValueError, TypeError):
            return self.name
