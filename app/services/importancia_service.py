# app/services/importancia_service.py
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.criterio_contexto import CriterioContexto
from app.models.tarefa_criterio_valor import TarefaCriterioValor
from app.repositories.criterio_repo import CriterioContextoRepository


def calcular_importancia(
    criterios: list[CriterioContexto], valores: dict[int, int]
) -> tuple[float, bool]:
    """Retorna (importancia 0-5, sem_nota).

    importancia = soma(valor_efetivo × peso) / soma(pesos), onde valor_efetivo é
    (5 - valor) quando o critério tem inverter=True. Contexto sem critérios → (0, True).
    """
    if not criterios:
        return 0.0, True
    soma_peso = sum(c.peso for c in criterios)
    if soma_peso <= 0:
        return 0.0, True
    num = 0.0
    for c in criterios:
        v = valores.get(c.id, 0)
        efetivo = (5 - v) if c.inverter else v
        num += efetivo * c.peso
    return round(num / soma_peso, 2), False


# Criação direta (SCRIPT 13): em vez dos critérios 0-5, a tarefa avulsa escolhe
# Alta/Média/Baixa, mapeado no campo existente `importancia` (sem migração).
PRIORIDADE_IMPORTANCIA = {"alta": 5.0, "media": 3.0, "baixa": 1.0}


def importancia_from_prioridade(prioridade: Optional[str]) -> float:
    """Mapeia 'alta'|'media'|'baixa' → importancia (5/3/1). Default 'media' → 3.0."""
    return PRIORIDADE_IMPORTANCIA.get((prioridade or "").strip().lower(), 3.0)


def faixa_importancia(importancia: Optional[float], sem_nota: bool = False) -> Optional[str]:
    """'baixa' (1-2), 'media' (3), 'alta' (4-5) ou None quando sem nota."""
    if sem_nota or importancia is None:
        return None
    if importancia < 2.5:
        return "baixa"
    if importancia < 3.5:
        return "media"
    return "alta"


class ImportanciaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.criterios = CriterioContextoRepository(db)

    async def parse_form_valores(
        self, context_id: Optional[int], form: dict
    ) -> tuple[list[CriterioContexto], dict[int, int], list[CriterioContexto]]:
        """Lê os campos `crit_<id>` do form para o contexto dado.

        Retorna (criterios, valores, faltando). `faltando` lista critérios sem
        resposta válida (0-5) — usado para bloquear o salvamento.
        """
        if context_id is None:
            return [], {}, []
        criterios = await self.criterios.get_by_context(context_id)
        valores: dict[int, int] = {}
        faltando: list[CriterioContexto] = []
        for c in criterios:
            raw = form.get(f"crit_{c.id}")
            try:
                v = int(raw) if raw is not None and str(raw).strip() != "" else None
            except (TypeError, ValueError):
                v = None
            if v is None or v < 0 or v > 5:
                faltando.append(c)
            else:
                valores[c.id] = v
        return criterios, valores, faltando

    async def apply(
        self, task_id: int, criterios: list[CriterioContexto], valores: dict[int, int]
    ) -> tuple[float, bool]:
        """Persiste os valores (substituindo os anteriores) e retorna (importancia, sem_nota)."""
        await self.db.execute(
            delete(TarefaCriterioValor).where(TarefaCriterioValor.task_id == task_id)
        )
        for crit_id, v in valores.items():
            self.db.add(TarefaCriterioValor(task_id=task_id, criterio_id=crit_id, valor=v))
        await self.db.commit()
        return calcular_importancia(criterios, valores)

    async def get_valores_by_task(self, task_id: int) -> dict[int, int]:
        result = await self.db.execute(
            select(TarefaCriterioValor).where(TarefaCriterioValor.task_id == task_id)
        )
        return {r.criterio_id: r.valor for r in result.scalars().all()}
