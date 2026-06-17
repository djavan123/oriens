from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    objective: Optional[str] = None
    status: ProjectStatus = ProjectStatus.active
    priority: int = 2
    deadline: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def priority_range(cls, v: int) -> int:
        if v not in (1, 2, 3):
            raise ValueError("priority must be 1, 2, or 3")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[int] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
