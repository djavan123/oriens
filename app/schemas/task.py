# app/schemas/task.py
from typing import Optional
from pydantic import BaseModel

from app.models.task import EnergyLevel, TaskStatus


class TaskCreate(BaseModel):
    title: str
    project_id: Optional[int] = None
    energy: EnergyLevel = EnergyLevel.medium
    is_quick_win: bool = False


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[TaskStatus] = None
    energy: Optional[EnergyLevel] = None
    is_quick_win: Optional[bool] = None
    project_id: Optional[int] = None
