from engine.models import (
    CheckStatus,
    Domain,
    ImpactResult,
    NormalizedChange,
    Validation,
)
from engine.risk import calculate_risk


def make_change(irreversibility: int = 0) -> NormalizedChange:
    return NormalizedChange(
        domain=Domain.coding_data,
        change_type="sql_migration",
        title="Test migration",
        affected_resources=["table:test"],
        payload={},
        irreversibility=irreversibility,
    )


def test_risk_factors_on_known_inputs() -> None:
    """Verify calculation of S, D, V, I, U factors individually on known values."""
    change = make_change(irreversibility=40)
    impact = ImpactResult(
        entry_nodes=["A"],
        affected_nodes=["B", "C", "D"],  # 3 affected
        coverage=0.8,
        uncovered=[],
    )
    validations = [
        Validation(check_type="c1", status=CheckStatus.PASSED, weight=1),
        Validation(check_type="c2", status=CheckStatus.FAILED, weight=3),
        Validation(check_type="c3", status=CheckStatus.NOT_RUN, weight=2),
    ]
    node_criticalities = {"B": 60, "C": 90, "D": 70}

    result = calculate_risk(
        change=change,
        impact=impact,
        validations=validations,
        node_criticalities=node_criticalities,
    )

    # S: max criticality among affected nodes B(60), C(90), D(70) -> 90.0
    assert result.factors["S"] == 90.0

    # D: min(100, 10 * 3) -> 30.0
    assert result.factors["D"] == 30.0

    # V: 100 * 3 / (1 + 3) -> 75.0
    assert result.factors["V"] == 75.0

    # I: 40.0
    assert result.factors["I"] == 40.0

    # U: 100 * (0.6 * (1 - 0.8) + 0.4 * (1/3))
    # = 100 * (0.12 + 0.13333...) = 25.33
    assert result.factors["U"] == 25.33

    # Total score = 0.30*90 + 0.25*30 + 0.25*75 + 0.10*40 + 0.10*25.33
    # = 27 + 7.5 + 18.75 + 4 + 2.533 = 59.78
    assert result.score == 59.78


def test_risk_score_clamping() -> None:
    """Verify score clamping to [0, 100]."""
    change_zero = make_change(irreversibility=0)
    impact_zero = ImpactResult(affected_nodes=[], coverage=1.0)
    res_zero = calculate_risk(change_zero, impact_zero, [])
    assert res_zero.score == 0.0
    assert res_zero.factors["S"] == 0.0
    assert res_zero.factors["D"] == 0.0
    assert res_zero.factors["V"] == 0.0
    assert res_zero.factors["I"] == 0.0
    assert res_zero.factors["U"] == 0.0

    change_max = make_change(irreversibility=100)
    impact_max = ImpactResult(
        affected_nodes=[f"N{i}" for i in range(15)],  # 15 nodes -> D = 100
        coverage=0.0,  # 1 - 0 = 1.0
    )
    validations_max = [
        Validation(check_type="c1", status=CheckStatus.FAILED, weight=3),
        Validation(check_type="c2", status=CheckStatus.NOT_RUN, weight=1),
    ]
    node_criticalities = {f"N{i}": 100 for i in range(15)}
    res_max = calculate_risk(
        change_max,
        impact_max,
        validations_max,
        node_criticalities=node_criticalities,
    )
    assert res_max.score <= 100.0
    assert res_max.factors["S"] == 100.0
    assert res_max.factors["D"] == 100.0
    assert res_max.factors["V"] == 100.0
    assert res_max.factors["I"] == 100.0
    # U = 100 * (0.6 * (1 - 0) + 0.4 * (1/2)) = 80.0
    assert res_max.factors["U"] == 80.0
    # Score = 0.30*100 + 0.25*100 + 0.25*100 + 0.10*100 + 0.10*80 = 98.0
    assert res_max.score == 98.0

    # Test full 100 factor and clamping with all NOT_RUN and coverage=0.0
    validations_all_not_run = [
        Validation(check_type="c1", status=CheckStatus.NOT_RUN, weight=1),
    ]
    res_full = calculate_risk(
        change_max,
        impact_max,
        validations_all_not_run,
        node_criticalities=node_criticalities,
    )
    # U = 100 * (0.6*1 + 0.4*1) = 100.0
    assert res_full.factors["U"] == 100.0
    assert 0.0 <= res_full.score <= 100.0
