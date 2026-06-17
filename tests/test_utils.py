import pytest

from app.utils.overload_detector import OVERLOAD_THRESHOLD, calculate_overload
from app.utils.verb_validator import validate_starts_with_verb


# ── Overload detector ──────────────────────────────────────────────────────────

def test_overload_score_formula():
    result = calculate_overload(active_projects=2, active_missions=2, pending_tasks=5)
    # 2*2 + 2*3 + 5 = 4 + 6 + 5 = 15
    assert result.score == 15

def test_overload_at_threshold_is_not_overload():
    result = calculate_overload(2, 2, 5)
    assert result.score == OVERLOAD_THRESHOLD
    assert not result.is_overload

def test_overload_above_threshold_is_overload():
    result = calculate_overload(3, 3, 6)
    # 6 + 9 + 6 = 21
    assert result.score == 21
    assert result.is_overload

def test_overload_zero_state():
    result = calculate_overload(0, 0, 0)
    assert result.score == 0
    assert not result.is_overload

def test_overload_result_exposes_counts():
    result = calculate_overload(active_projects=1, active_missions=2, pending_tasks=3)
    assert result.active_projects_count == 1
    assert result.active_missions_count == 2
    assert result.pending_tasks_count == 3

def test_overload_projects_weight_2():
    r1 = calculate_overload(active_projects=1, active_missions=0, pending_tasks=0)
    r2 = calculate_overload(active_projects=0, active_missions=0, pending_tasks=2)
    assert r1.score == 2
    assert r2.score == 2

def test_overload_missions_weight_3():
    r = calculate_overload(active_projects=0, active_missions=1, pending_tasks=0)
    assert r.score == 3


# ── Verb validator ─────────────────────────────────────────────────────────────

def test_verb_accepts_pt_infinitive():
    valid, _ = validate_starts_with_verb("Criar relatório mensal")
    assert valid

def test_verb_accepts_en_infinitive():
    valid, _ = validate_starts_with_verb("Deploy to production")
    assert valid

def test_verb_rejects_noun_start():
    valid, suggestions = validate_starts_with_verb("Relatório mensal")
    assert not valid
    assert len(suggestions) == 3

def test_verb_rejects_adjective_start():
    valid, _ = validate_starts_with_verb("Nova funcionalidade")
    assert not valid

def test_verb_suggestions_start_with_verb():
    _, suggestions = validate_starts_with_verb("reunião de equipe")
    for s in suggestions:
        first_word = s.split()[0]
        assert first_word in ("Criar", "Revisar", "Implementar")

def test_verb_suggestion_contains_original_content():
    original = "reunião de equipe"
    _, suggestions = validate_starts_with_verb(original)
    for s in suggestions:
        assert original in s

def test_verb_empty_string_is_invalid():
    valid, suggestions = validate_starts_with_verb("")
    assert not valid
    assert suggestions == []

def test_verb_case_insensitive():
    valid, _ = validate_starts_with_verb("CRIAR novo branch")
    assert valid

def test_verb_trailing_punctuation_stripped():
    valid, _ = validate_starts_with_verb("criar. algo")
    assert valid

def test_verb_no_suggestions_when_valid():
    _, suggestions = validate_starts_with_verb("Testar integração")
    assert suggestions == []
