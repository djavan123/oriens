# LEGADO — lido apenas por services/list_migration.py (itens antigos → Task).
# TODO remover junto com list_migration após um ciclo de produção sem linhas
# legadas não-migradas (a tabela `repository_items` fica órfã; nunca é dropada).
from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RepositoryItem(Base):
    __tablename__ = "repository_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
