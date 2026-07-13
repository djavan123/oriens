# app/repositories/project_risk_repo.py
from typing import Optional
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_risk import ProjectRisk, RiskLevel, RiskStatus

# Ordena por severidade (impacto×probabilidade) decrescente, abertos primeiro.
_level_order = case(
    (ProjectRisk.impact == RiskLevel.high, 3),
    (ProjectRisk.impact == RiskLevel.medium, 2),
    else_=1,
)


class ProjectRiskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_project(self, project_id: int) -> list[ProjectRisk]:
        result = await self.db.execute(
            select(ProjectRisk)
            .where(ProjectRisk.project_id == project_id)
            .order_by(_level_order.desc(), ProjectRisk.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_open(self, project_id: int) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count())
            .select_from(ProjectRisk)
            .where(ProjectRisk.project_id == project_id, ProjectRisk.status == RiskStatus.open)
        )
        return result.scalar_one()

    async def count_open_by_projects(self, project_ids: list[int]) -> dict[int, int]:
        """{project_id: nº de riscos abertos} numa única query (evita N+1 no relatório)."""
        if not project_ids:
            return {}
        from sqlalchemy import func
        result = await self.db.execute(
            select(ProjectRisk.project_id, func.count())
            .where(
                ProjectRisk.project_id.in_(project_ids),
                ProjectRisk.status == RiskStatus.open,
            )
            .group_by(ProjectRisk.project_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def create(
        self,
        project_id: int,
        user_id: int,
        description: str,
        impact: RiskLevel,
        probability: RiskLevel,
        mitigation: Optional[str] = None,
    ) -> ProjectRisk:
        risk = ProjectRisk(
            project_id=project_id,
            user_id=user_id,
            description=description,
            impact=impact,
            probability=probability,
            mitigation=mitigation,
        )
        self.db.add(risk)
        await self.db.commit()
        await self.db.refresh(risk)
        return risk

    async def get_by_id(self, risk_id: int, user_id: int) -> Optional[ProjectRisk]:
        result = await self.db.execute(
            select(ProjectRisk).where(
                ProjectRisk.id == risk_id, ProjectRisk.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, risk_id: int, user_id: int, **kwargs) -> Optional[ProjectRisk]:
        risk = await self.get_by_id(risk_id, user_id)
        if not risk:
            return None
        for key, value in kwargs.items():
            setattr(risk, key, value)
        await self.db.commit()
        await self.db.refresh(risk)
        return risk

    async def delete(self, risk_id: int, user_id: int) -> bool:
        risk = await self.get_by_id(risk_id, user_id)
        if not risk:
            return False
        await self.db.delete(risk)
        await self.db.commit()
        return True
