from app.utils.overload_detector import OVERLOAD_THRESHOLD, calculate_overload


# ── Overload detector (score = projetos*2 + tarefas; threshold 15) ─────────────

def test_overload_score_formula():
    # 5*2 + 5 = 15
    result = calculate_overload(active_projects=5, pending_tasks=5)
    assert result.score == 15


def test_overload_at_threshold_is_not_overload():
    result = calculate_overload(5, 5)
    assert result.score == OVERLOAD_THRESHOLD
    assert not result.is_overload


def test_overload_above_threshold_is_overload():
    # 6*2 + 6 = 18
    result = calculate_overload(6, 6)
    assert result.score == 18
    assert result.is_overload


def test_overload_zero_state():
    result = calculate_overload(0, 0)
    assert result.score == 0
    assert not result.is_overload


def test_overload_projects_weight_2():
    assert calculate_overload(active_projects=3, pending_tasks=0).score == 6


def test_overload_result_exposes_counts():
    result = calculate_overload(active_projects=2, pending_tasks=3)
    assert result.active_projects_count == 2
    assert result.pending_tasks_count == 3
