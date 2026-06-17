# app/services/weekly_directive_service.py
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weekly_directive import WeeklyDirective
from app.repositories.weekly_directive_repo import WeeklyDirectiveRepository


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


class WeeklyDirectiveService:
    def __init__(self, db: AsyncSession):
        self.repo = WeeklyDirectiveRepository(db)

    async def get_current(self, user_id: int) -> Optional[WeeklyDirective]:
        return await self.repo.get_by_week(user_id, current_week_start())

    async def save(
        self,
        user_id: int,
        weekly_theme: Optional[str],
        top_1: Optional[str],
        top_2: Optional[str],
        top_3: Optional[str],
        ignore_list: Optional[str],
        major_risk: Optional[str],
        physiological_priority: Optional[str],
    ) -> WeeklyDirective:
        return await self.repo.upsert(
            user_id=user_id,
            week_start=current_week_start(),
            weekly_theme=weekly_theme or None,
            top_1=top_1 or None,
            top_2=top_2 or None,
            top_3=top_3 or None,
            ignore_list=ignore_list or None,
            major_risk=major_risk or None,
            physiological_priority=physiological_priority or None,
        )
