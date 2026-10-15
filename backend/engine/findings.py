import networkx as nx
from engine.models import (
    CheckStatus,
    Finding,
    FindingClass,
    ImpactResult,
    Severity,
    Tier,
    Validation,
)


def build_findings(
    validations: list[Validation],
    impact: ImpactResult,
    graph: nx.DiGraph | None = None,
) -> list[Finding]:
    """
    Builds structured findings with evidence tiers and classes:
    - FAILED validation -> class: confirmed; tier: REPRODUCED (if replay error) or PROVEN (default).
    - Affected node without failed validation -> class: potential; tier: INFERRED.
    - Uncovered entry or NOT_RUN validation -> class: unknown; tier: UNKNOWN.
    """
    findings: list[Finding] = []
    tied_nodes: set[str] = set()

    # 1. FAILED validations -> confirmed findings
    for i, val in enumerate(validations):
        if val.status == CheckStatus.FAILED:
            related = list(val.details.get("related_nodes", []))
            tied_nodes.update(related)

            # Determine tier
            tier_val = val.details.get("tier")
            if tier_val == Tier.REPRODUCED or tier_val == "REPRODUCED":
                tier = Tier.REPRODUCED
            elif val.details.get("phase") in ("migration", "query") or val.details.get("replay"):
                tier = Tier.REPRODUCED
            elif tier_val:
                tier = Tier(tier_val)
            else:
                tier = Tier.PROVEN

            # Determine severity
            if val.critical_rule or val.weight >= 3:
                severity = Severity.critical
            elif val.weight == 2:
                severity = Severity.high
            else:
                severity = Severity.medium

            msg = (
                val.details.get("error")
                or val.details.get("message")
                or f"Validation check failed: {val.check_type}"
            )

            findings.append(
                Finding(
                    id=f"finding-val-{i}",
                    severity=severity,
                    tier=tier,
                    klass=FindingClass.confirmed,
                    message=msg,
                    evidence={"validation_index": i, "check_type": val.check_type, **val.details},
                    related_nodes=related,
                    recommendation=val.details.get("recommendation"),
                )
            )

    # 2. Affected nodes without failed validations -> INFERRED potential findings
    for node in impact.affected_nodes:
        if node not in tied_nodes:
            criticality = 50
            if graph is not None and node in graph:
                criticality = graph.nodes[node].get("criticality", 50)

            if criticality >= 80:
                severity = Severity.high
            elif criticality >= 60:
                severity = Severity.medium
            else:
                severity = Severity.low

            paths = impact.paths.get(node, [])
            findings.append(
                Finding(
                    id=f"finding-inferred-{node}",
                    severity=severity,
                    tier=Tier.INFERRED,
                    klass=FindingClass.potential,
                    message=f"Resource '{node}' is downstream of proposed change and potentially impacted",
                    evidence={"path": paths, "node": node},
                    related_nodes=[node],
                    recommendation=f"Review downstream dependencies for '{node}' before execution",
                )
            )

    # 3. Uncovered dependencies -> UNKNOWN unknown findings
    for j, marker in enumerate(impact.uncovered):
        is_truncation = marker.startswith("truncated:")
        is_unknown_entry = marker.startswith("unknown_entry:")
        severity = Severity.high if (is_truncation or is_unknown_entry) else Severity.medium

        findings.append(
            Finding(
                id=f"finding-uncovered-{j}",
                severity=severity,
                tier=Tier.UNKNOWN,
                klass=FindingClass.unknown,
                message=f"Unresolved dependency or graph boundary reached: {marker}",
                evidence={"uncovered_marker": marker},
                related_nodes=[],
                recommendation="Investigate unresolved reference or expand traversal boundary",
            )
        )

    # 4. NOT_RUN validations -> UNKNOWN unknown findings
    for k, val in enumerate(validations):
        if val.status == CheckStatus.NOT_RUN:
            related = list(val.details.get("related_nodes", []))
            severity = Severity.critical if val.critical_rule else Severity.medium
            reason = val.details.get("reason", "Required input or dependency missing")

            findings.append(
                Finding(
                    id=f"finding-notrun-{k}",
                    severity=severity,
                    tier=Tier.UNKNOWN,
                    klass=FindingClass.unknown,
                    message=f"Check not run: {val.check_type} ({reason})",
                    evidence={"validation_index": k, "check_type": val.check_type, **val.details},
                    related_nodes=related,
                    recommendation="Ensure prerequisite data and analyzers are configured to run this check",
                )
            )

    return findings
