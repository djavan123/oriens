# app/utils/overload_detector.py
from dataclasses import dataclass

OVERLOAD_THRESHOLD = 15


@dataclass
class OverloadResult:
    score: int
    is_overload: bool
    active_projects_count: int
    pending_tasks_count: int


def calculate_overload(
    active_projects: int,
    pending_tasks: int,
) -> OverloadResult:
    score = (active_projects * 2) + pending_tasks
    return OverloadResult(
        score=score,
        is_overload=score > OVERLOAD_THRESHOLD,
        active_projects_count=active_projects,
        pending_tasks_count=pending_tasks,
    )
