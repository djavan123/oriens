# app/services/importancia_service.py
"""Importância da tarefa avulsa (SCRIPT 13): Alta/Média/Baixa mapeadas no campo
`importancia`. O antigo sistema de critérios ponderados por contexto foi removido.
"""
from typing import Optional

# Criação direta (SCRIPT 13): a tarefa avulsa escolhe Máxima/Alta/Média/Baixa,
# mapeado no campo existente `importancia` (sem migração). Máxima > Alta > Média > Baixa.
PRIORIDADE_IMPORTANCIA = {"maxima": 6.0, "alta": 5.0, "media": 3.0, "baixa": 1.0}


def importancia_from_prioridade(prioridade: Optional[str]) -> float:
    """Mapeia 'maxima'|'alta'|'media'|'baixa' → importancia (6/5/3/1). Default 'media' → 3.0."""
    return PRIORIDADE_IMPORTANCIA.get((prioridade or "").strip().lower(), 3.0)


def faixa_importancia(importancia: Optional[float], sem_nota: bool = False) -> Optional[str]:
    """'baixa' (1-2), 'media' (3), 'alta' (4-5), 'maxima' (6) ou None quando sem nota."""
    if sem_nota or importancia is None:
        return None
    if importancia < 2.5:
        return "baixa"
    if importancia < 3.5:
        return "media"
    if importancia < 5.5:
        return "alta"
    return "maxima"
