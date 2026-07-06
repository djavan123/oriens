from app.services.importancia_service import (
    faixa_importancia,
    importancia_from_prioridade,
)


# ── importancia_from_prioridade (Alta/Média/Baixa → 5/3/1) ─────────────────────

def test_from_prioridade_alta():
    assert importancia_from_prioridade("alta") == 5.0


def test_from_prioridade_media():
    assert importancia_from_prioridade("media") == 3.0


def test_from_prioridade_baixa():
    assert importancia_from_prioridade("baixa") == 1.0


def test_from_prioridade_default_media():
    assert importancia_from_prioridade(None) == 3.0
    assert importancia_from_prioridade("") == 3.0
    assert importancia_from_prioridade("qualquer") == 3.0


def test_from_prioridade_case_insensitive():
    assert importancia_from_prioridade("ALTA") == 5.0
    assert importancia_from_prioridade(" Baixa ") == 1.0


# ── faixa_importancia (banda textual) ──────────────────────────────────────────

def test_faixa_sem_nota_is_none():
    assert faixa_importancia(5.0, sem_nota=True) is None
    assert faixa_importancia(None) is None


def test_faixa_baixa():
    assert faixa_importancia(1.0) == "baixa"
    assert faixa_importancia(2.0) == "baixa"


def test_faixa_media():
    assert faixa_importancia(3.0) == "media"


def test_faixa_alta():
    assert faixa_importancia(4.0) == "alta"
    assert faixa_importancia(5.0) == "alta"
