# app/repositories/criterio_repo.py
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.criterio_contexto import CriterioContexto
from app.models.context import Context, ContextType

MAX_CRITERIOS = 3

# Critérios iniciais por TIPO de contexto (seed na primeira execução).
_SEED = {
    ContextType.work.value: [
        ("Financeiro", 4, False),
        ("Diretor pediu", 3, False),
        ("Facilidade", 3, True),
    ],
    ContextType.home_operational.value: [
        ("Financeiro", 1, False),
        ("Saúde", 1, False),
        ("Bem-estar", 1, False),
    ],
}


class CriterioContextoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_context(self, context_id: int) -> list[CriterioContexto]:
        result = await self.db.execute(
            select(CriterioContexto)
            .where(CriterioContexto.context_id == context_id)
            .order_by(CriterioContexto.id)
        )
        return list(result.scalars().all())

    async def get_for_contexts(self, context_ids: list[int]) -> dict[int, list[CriterioContexto]]:
        if not context_ids:
            return {}
        result = await self.db.execute(
            select(CriterioContexto)
            .where(CriterioContexto.context_id.in_(context_ids))
            .order_by(CriterioContexto.context_id, CriterioContexto.id)
        )
        grouped: dict[int, list[CriterioContexto]] = {}
        for c in result.scalars().all():
            grouped.setdefault(c.context_id, []).append(c)
        return grouped

    async def replace_for_context(
        self, context_id: int, items: list[tuple[str, int, bool]]
    ) -> list[CriterioContexto]:
        """Substitui todos os critérios de um contexto pelos informados (máx. 3)."""
        items = [(n.strip(), p, inv) for (n, p, inv) in items if n and n.strip()][:MAX_CRITERIOS]
        await self.db.execute(
            delete(CriterioContexto).where(CriterioContexto.context_id == context_id)
        )
        novos = [
            CriterioContexto(context_id=context_id, nome=n, peso=max(1, p), inverter=inv)
            for (n, p, inv) in items
        ]
        self.db.add_all(novos)
        await self.db.commit()
        return await self.get_by_context(context_id)

    async def delete(self, criterio_id: int) -> None:
        await self.db.execute(
            delete(CriterioContexto).where(CriterioContexto.id == criterio_id)
        )
        await self.db.commit()

    async def seed_defaults(self) -> None:
        existing = await self.db.execute(select(CriterioContexto.id).limit(1))
        if existing.first() is not None:
            return
        ctx_result = await self.db.execute(select(Context))
        novos: list[CriterioContexto] = []
        for ctx in ctx_result.scalars().all():
            for (nome, peso, inverter) in _SEED.get(ctx.type or "", []):
                novos.append(
                    CriterioContexto(context_id=ctx.id, nome=nome, peso=peso, inverter=inverter)
                )
        if novos:
            self.db.add_all(novos)
            await self.db.commit()
