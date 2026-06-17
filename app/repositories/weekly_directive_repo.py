# app/repositories/weekly_directive_repo.py
from datetime import date
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weekly_directive import WeeklyDirective


class WeeklyDirectiveRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_week(self, user_id: int, week_start: date) -> Optional[WeeklyDirective]:
        result = await self.db.execute(
            select(WeeklyDirective).where(
                WeeklyDirective.user_id == user_id,
                WeeklyDirective.week_start == week_start,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: int, week_start: date, **kwargs) -> WeeklyDirective:
        directive = await self.get_by_week(user_id, week_start)
        if directive is None:
            directive = WeeklyDirective(user_id=user_id, week_start=week_start, **kwargs)
            self.db.add(directive)
        else:
            for key, value in kwargs.items():
                setattr(directive, key, value)
        await self.db.commit()
        await self.db.refresh(directive)
        return directive
