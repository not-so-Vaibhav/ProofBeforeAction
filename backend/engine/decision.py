from engine.config import THRESHOLD_BLOCK, THRESHOLD_REVIEW
from engine.models import (
    CheckStatus,
    Decision,
    DecisionResult,
    Finding,
    ImpactResult,
    Validation,
)


def decide(
    score: float,
    validations: list[Validation],
    impact: ImpactResult,
    findings: list[Finding] | None = None,
) -> DecisionResult:
    """
    Applies decision precedence with evidence completeness rules:
    1. Critical rule FAILED -> BLOCK (regardless of score).
    2. No validations ran -> HUMAN_REVIEW (reason: 'no checks ran').
    3. Incomplete evidence (any uncovered entry or critical check NOT_RUN) -> HUMAN_REVIEW.
    4. Score >= 70 -> BLOCK.
    5. Any validation FAILED or score >= 30 -> HUMAN_REVIEW.
    6. Passed validation with score < 30 -> ALLOW.
    """
    # 1. Critical rule failed -> BLOCK
    critical_failed = [v for v in validations if v.critical_rule and v.status == CheckStatus.FAILED]
    if critical_failed:
        reasons = [
            f"Critical rule failed: {v.check_type}"
            + (f" ({v.details.get('error')})" if v.details.get("error") else "")
            for v in critical_failed
        ]
        return DecisionResult(decision=Decision.BLOCK, reasons=reasons)

    # 2. No validations exist at all -> HUMAN_REVIEW
    if not validations:
        return DecisionResult(decision=Decision.HUMAN_REVIEW, reasons=["no checks ran"])

    # 3. Evidence completeness check
    critical_not_run = [v for v in validations if v.critical_rule and v.status == CheckStatus.NOT_RUN]
    uncovered_present = bool(impact.uncovered)
    if critical_not_run or uncovered_present:
        reasons: list[str] = []
        if critical_not_run:
            reasons.extend(f"Critical check not run: {v.check_type}" for v in critical_not_run)
        if uncovered_present:
            reasons.extend(f"Uncovered dependency: {item}" for item in impact.uncovered)
        return DecisionResult(decision=Decision.HUMAN_REVIEW, reasons=reasons)

    # 4. Score >= 70 -> BLOCK
    if score >= THRESHOLD_BLOCK:
        return DecisionResult(
            decision=Decision.BLOCK,
            reasons=[f"Risk score {score:.1f} exceeds block threshold ({THRESHOLD_BLOCK})"],
        )

    # 5. Non-critical failures or score >= 30 -> HUMAN_REVIEW
    failed_checks = [v for v in validations if v.status == CheckStatus.FAILED]
    if failed_checks or score >= THRESHOLD_REVIEW:
        reasons = []
        if failed_checks:
            reasons.extend(f"Validation failed: {v.check_type}" for v in failed_checks)
        if score >= THRESHOLD_REVIEW:
            reasons.append(f"Risk score {score:.1f} exceeds review threshold ({THRESHOLD_REVIEW})")
        return DecisionResult(decision=Decision.HUMAN_REVIEW, reasons=reasons)

    # 6. At least one passed check with low risk -> ALLOW
    has_passed = any(v.status == CheckStatus.PASSED for v in validations)
    if has_passed:
        return DecisionResult(
            decision=Decision.ALLOW,
            reasons=["All checks passed and risk score is within acceptable limits"],
        )

    return DecisionResult(decision=Decision.HUMAN_REVIEW, reasons=["no checks ran"])
