# app/repositories/note_repo.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


class NoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        content: str,
        project_id: Optional[int] = None,
    ) -> Note:
        note = Note(
            user_id=user_id,
            content=content,
            project_id=project_id,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def get_all_by_user(self, user_id: int) -> list[Note]:
        result = await self.db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())
