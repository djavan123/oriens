# app/models/criterio_contexto.py
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CriterioContexto(Base):
    """Critério ponderado de importância, configurado por contexto (máx. 3 por contexto).

    `inverter`=True faz nota alta no critério REDUZIR a importância (ex.: Facilidade —
    quanto mais fácil, menos importante priorizar).
    """
    __tablename__ = "criterio_contexto"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    context_id: Mapped[int] = mapped_column(
        ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    peso: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    inverter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
