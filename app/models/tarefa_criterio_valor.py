# app/models/tarefa_criterio_valor.py
from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TarefaCriterioValor(Base):
    """Nota (0-5) que uma tarefa recebeu em um critério do seu contexto."""
    __tablename__ = "tarefa_criterio_valor"
    __table_args__ = (UniqueConstraint("task_id", "criterio_id", name="uq_tarefa_criterio"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterio_id: Mapped[int] = mapped_column(
        ForeignKey("criterio_contexto.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valor: Mapped[int] = mapped_column(Integer, nullable=False)
