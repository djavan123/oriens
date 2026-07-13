# app/repositories/app_state_repo.py
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_state import AppState
from app.utils.time import utcnow


class AppStateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: str) -> Optional[str]:
        result = await self.db.execute(select(AppState).where(AppState.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else None

    async def set(self, key: str, value: str) -> None:
        result = await self.db.execute(select(AppState).where(AppState.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            self.db.add(AppState(key=key, value=value))
        else:
            row.value = value
            row.updated_at = utcnow()
        await self.db.commit()
