from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, name: str) -> User:
        user = User(email=email, password=password_hash, name=name)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_first(self) -> Optional[User]:
        """Menor id — usado pela captura por Telegram (sistema single-user)."""
        result = await self.db.execute(select(User).order_by(User.id.asc()).limit(1))
        return result.scalar_one_or_none()

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def update_foco(self, user_id: int, foco: Optional[str]) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.foco_do_dia = foco
        await self.db.commit()
        await self.db.refresh(user)
        return user
