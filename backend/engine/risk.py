from typing import Any
import networkx as nx
from engine.config import WEIGHT_D, WEIGHT_I, WEIGHT_S, WEIGHT_U, WEIGHT_V
from engine.models import CheckStatus, ImpactResult, NormalizedChange, RiskResult, Validation


def calculate_risk(
    change: NormalizedChange,
    impact: ImpactResult,
    validations: list[Validation],
    graph: nx.DiGraph | None = None,
    node_criticalities: dict[str, int] | None = None,
) -> RiskResult:
    """
    Computes transparent risk heuristic score R using weights from config (S, D, V, I, U).
    Clamped to 0..100.

    - S (Impact Severity): max criticality among affected nodes (0 if none)
    - D (Dependency Exposure): min(100, 10 * affected_nodes count)
    - V (Validation Failures): 100 * (sum weights of FAILED) / (sum weights of PASSED or FAILED), 0 if none ran
    - I (Irreversibility): change.irreversibility (0..100)
    - U (Uncertainty): min(100, 100 * (0.6 * (1 - coverage) + 0.4 * not_run_fraction))
    """
    # S: max criticality among affected nodes (0 if none)
    if not impact.affected_nodes:
        S = 0.0
    elif node_criticalities is not None:
        crits = [node_criticalities.get(n, 50) for n in impact.affected_nodes]
        S = float(max(crits)) if crits else 0.0
    elif graph is not None:
        crits = [graph.nodes[n].get("criticality", 50) for n in impact.affected_nodes if n in graph]
        S = float(max(crits)) if crits else 50.0
    else:
        S = 50.0

    # D: min(100, 10 * affected count)
    D = float(min(100, 10 * len(impact.affected_nodes)))

    # V: 100 * (sum of weights of FAILED) / (sum of weights of checks with status PASSED or FAILED), 0 if none ran
    ran_checks = [v for v in validations if v.status in (CheckStatus.PASSED, CheckStatus.FAILED)]
    failed_checks = [v for v in validations if v.status == CheckStatus.FAILED]
    sum_ran = sum(v.weight for v in ran_checks)
    sum_failed = sum(v.weight for v in failed_checks)
    V = (100.0 * sum_failed / sum_ran) if sum_ran > 0 else 0.0

    # I: irreversibility
    I = float(change.irreversibility)

    # U: min(100, 100 * (0.6 * (1 - coverage) + 0.4 * not_run_fraction))
    total_validations = len(validations)
    not_run_count = sum(1 for v in validations if v.status == CheckStatus.NOT_RUN)
    not_run_fraction = (not_run_count / total_validations) if total_validations > 0 else 0.0
    U = float(min(100.0, 100.0 * (0.6 * (1.0 - impact.coverage) + 0.4 * not_run_fraction)))

    # Weighted sum clamped 0 to 100
    raw_score = (WEIGHT_S * S) + (WEIGHT_D * D) + (WEIGHT_V * V) + (WEIGHT_I * I) + (WEIGHT_U * U)
    score = max(0.0, min(100.0, raw_score))

    factors = {
        "S": round(S, 2),
        "D": round(D, 2),
        "V": round(V, 2),
        "I": round(I, 2),
        "U": round(U, 2),
    }

    return RiskResult(score=round(score, 2), factors=factors)
