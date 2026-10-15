from engine.decision import decide
from engine.models import CheckStatus, Decision, ImpactResult, Validation


def test_critical_failed_blocks_regardless_of_score() -> None:
    """Critical validation failure forces BLOCK even with low risk score."""
    validations = [
        Validation(
            check_type="critical_auth_rule",
            status=CheckStatus.FAILED,
            critical_rule=True,
            details={"error": "Auth gate bypass detected"},
        )
    ]
    impact = ImpactResult(coverage=1.0, uncovered=[])

    # Low score of 12.0
    res = decide(score=12.0, validations=validations, impact=impact)
    assert res.decision == Decision.BLOCK
    assert any("critical_auth_rule" in r for r in res.reasons)


def test_no_validations_gives_human_review() -> None:
    """If no validations ran, decision is HUMAN_REVIEW with reason 'no checks ran'."""
    impact = ImpactResult(coverage=1.0, uncovered=[])
    res = decide(score=5.0, validations=[], impact=impact)
    assert res.decision == Decision.HUMAN_REVIEW
    assert "no checks ran" in res.reasons


def test_critical_not_run_gives_human_review() -> None:
    """Critical validation NOT_RUN forces HUMAN_REVIEW even with low score."""
    validations = [
        Validation(check_type="critical_replay", status=CheckStatus.NOT_RUN, critical_rule=True),
        Validation(check_type="safe_rule", status=CheckStatus.PASSED, critical_rule=False),
    ]
    impact = ImpactResult(coverage=1.0, uncovered=[])
    res = decide(score=10.0, validations=validations, impact=impact)
    assert res.decision == Decision.HUMAN_REVIEW
    assert any("critical_replay" in r for r in res.reasons)


def test_uncovered_entry_forces_human_review_even_with_high_coverage() -> None:
    """Any uncovered dependency forces HUMAN_REVIEW even when coverage is 0.97."""
    validations = [
        Validation(check_type="safe_rule", status=CheckStatus.PASSED, critical_rule=False),
    ]
    # Coverage is 97%, but uncovered has an entry
    impact = ImpactResult(coverage=0.97, uncovered=["pipeline:dynamic_sql"])
    res = decide(score=15.0, validations=validations, impact=impact)
    assert res.decision == Decision.HUMAN_REVIEW
    assert any("pipeline:dynamic_sql" in r for r in res.reasons)


def test_high_score_blocks() -> None:
    """Risk score >= 70 forces BLOCK even if all checks passed."""
    validations = [
        Validation(check_type="safe_rule", status=CheckStatus.PASSED, critical_rule=False),
    ]
    impact = ImpactResult(coverage=1.0, uncovered=[])
    res = decide(score=75.0, validations=validations, impact=impact)
    assert res.decision == Decision.BLOCK
    assert any("exceeds block threshold" in r for r in res.reasons)


def test_moderate_score_or_failed_check_gives_human_review() -> None:
    """Score >= 30 or any non-critical failed check yields HUMAN_REVIEW."""
    # Case A: score >= 30 with passed checks
    validations_pass = [
        Validation(check_type="safe_rule", status=CheckStatus.PASSED, critical_rule=False),
    ]
    impact = ImpactResult(coverage=1.0, uncovered=[])
    res_a = decide(score=35.0, validations=validations_pass, impact=impact)
    assert res_a.decision == Decision.HUMAN_REVIEW
    assert any("exceeds review threshold" in r for r in res_a.reasons)

    # Case B: score < 30 with a non-critical failed check
    validations_fail = [
        Validation(check_type="style_check", status=CheckStatus.FAILED, critical_rule=False),
    ]
    res_b = decide(score=20.0, validations=validations_fail, impact=impact)
    assert res_b.decision == Decision.HUMAN_REVIEW
    assert any("style_check" in r for r in res_b.reasons)


def test_clean_pass_gives_allow() -> None:
    """All checks passed, evidence complete, and score < 30 yields ALLOW."""
    validations = [
        Validation(check_type="safe_index_rule", status=CheckStatus.PASSED, critical_rule=False),
    ]
    impact = ImpactResult(coverage=1.0, uncovered=[])
    res = decide(score=14.0, validations=validations, impact=impact)
    assert res.decision == Decision.ALLOW
    assert any("All checks passed" in r for r in res.reasons)


def test_low_score_cannot_override_missing_evidence() -> None:
    """A low score (e.g. 0.0) cannot override incomplete evidence (uncovered dependencies)."""
    validations = [
        Validation(check_type="quick_check", status=CheckStatus.PASSED, critical_rule=False),
    ]
    impact = ImpactResult(coverage=0.5, uncovered=["unknown_entry:missing_ref"])

    res = decide(score=0.0, validations=validations, impact=impact)
    # Must NOT be ALLOW
    assert res.decision == Decision.HUMAN_REVIEW
    assert any("unknown_entry:missing_ref" in r for r in res.reasons)
