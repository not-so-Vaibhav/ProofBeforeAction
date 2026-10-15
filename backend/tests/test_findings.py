from engine.findings import build_findings
from engine.models import (
    CheckStatus,
    FindingClass,
    ImpactResult,
    Severity,
    Tier,
    Validation,
)


def test_findings_tier_and_class_mapping() -> None:
    """
    Test findings generation:
    1. Replay failure -> REPRODUCED, confirmed
    2. Static rule failure -> PROVEN, confirmed
    3. Untied affected node -> INFERRED, potential
    4. Uncovered entry -> UNKNOWN, unknown
    5. NOT_RUN validation -> UNKNOWN, unknown
    """
    validations = [
        # Replay failure
        Validation(
            check_type="replay_migration",
            status=CheckStatus.FAILED,
            weight=3,
            critical_rule=True,
            details={"phase": "migration", "error": "no such column: p.id", "related_nodes": ["view:v1"]},
        ),
        # Static rule failure
        Validation(
            check_type="schema_rule",
            status=CheckStatus.FAILED,
            weight=2,
            critical_rule=False,
            details={"message": "Type mismatch", "related_nodes": ["table:t2"]},
        ),
        # Passed check (should not produce a finding)
        Validation(
            check_type="safe_check",
            status=CheckStatus.PASSED,
            weight=1,
        ),
        # NOT_RUN validation
        Validation(
            check_type="dynamic_query_check",
            status=CheckStatus.NOT_RUN,
            weight=1,
            details={"reason": "SQL could not be qualified"},
        ),
    ]

    impact = ImpactResult(
        entry_nodes=["table:t1"],
        # view:v1 and table:t2 are tied to failures; endpoint:ep3 is untied
        affected_nodes=["view:v1", "table:t2", "endpoint:ep3"],
        paths={"endpoint:ep3": [["table:t1", "endpoint:ep3"]]},
        uncovered=["pipeline:dynamic_sql", "truncated:depth_cap"],
        coverage=0.75,
    )

    findings = build_findings(validations, impact)

    # 1. Replay failure finding
    replay_f = next(f for f in findings if f.evidence.get("check_type") == "replay_migration")
    assert replay_f.tier == Tier.REPRODUCED
    assert replay_f.klass == FindingClass.confirmed
    assert replay_f.severity == Severity.critical
    assert replay_f.evidence["validation_index"] == 0
    assert "no such column" in replay_f.message

    # 2. Static rule failure finding
    static_f = next(f for f in findings if f.evidence.get("check_type") == "schema_rule")
    assert static_f.tier == Tier.PROVEN
    assert static_f.klass == FindingClass.confirmed
    assert static_f.evidence["validation_index"] == 1

    # 3. Untied affected node finding
    inferred_f = next(f for f in findings if f.tier == Tier.INFERRED)
    assert inferred_f.klass == FindingClass.potential
    assert inferred_f.related_nodes == ["endpoint:ep3"]
    assert inferred_f.evidence["path"] == [["table:t1", "endpoint:ep3"]]

    # Ensure tied nodes (view:v1, table:t2) did NOT get duplicate INFERRED findings
    inferred_node_ids = [f.related_nodes[0] for f in findings if f.tier == Tier.INFERRED]
    assert "view:v1" not in inferred_node_ids
    assert "table:t2" not in inferred_node_ids

    # 4. Uncovered entry findings
    uncovered_f = [f for f in findings if "uncovered_marker" in f.evidence]
    assert len(uncovered_f) == 2
    for uf in uncovered_f:
        assert uf.tier == Tier.UNKNOWN
        assert uf.klass == FindingClass.unknown

    # 5. NOT_RUN validation finding
    notrun_f = next(f for f in findings if f.evidence.get("check_type") == "dynamic_query_check")
    assert notrun_f.tier == Tier.UNKNOWN
    assert notrun_f.klass == FindingClass.unknown
    assert notrun_f.evidence["validation_index"] == 3

    # All findings must have an ID and non-empty evidence
    for f in findings:
        assert f.id is not None and len(f.id) > 0
        assert isinstance(f.evidence, dict) and len(f.evidence) > 0
