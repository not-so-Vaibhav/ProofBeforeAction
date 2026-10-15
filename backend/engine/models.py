from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Domain(str, Enum):
    coding_data = "coding_data"
    healthcare_ops = "healthcare_ops"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"


class Tier(str, Enum):
    REPRODUCED = "REPRODUCED"
    PROVEN = "PROVEN"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class FindingClass(str, Enum):
    confirmed = "confirmed"
    potential = "potential"
    unknown = "unknown"


class CheckStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_RUN = "NOT_RUN"


class Provenance(str, Enum):
    extracted = "extracted"
    declared = "declared"
    modeled = "modeled"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class NormalizedChange(BaseModel):
    domain: Domain
    change_type: str
    title: str
    affected_resources: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    irreversibility: int = Field(default=0, ge=0, le=100)


class GraphNode(BaseModel):
    id: str
    type: str
    name: str
    provenance: Provenance
    criticality: int = Field(default=50, ge=0, le=100)
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    provenance: Provenance


class ImpactResult(BaseModel):
    entry_nodes: list[str] = Field(default_factory=list)
    affected_nodes: list[str] = Field(default_factory=list)
    paths: dict[str, list[list[str]]] = Field(default_factory=dict)
    coverage: float = Field(default=1.0, ge=0.0, le=1.0)
    uncovered: list[str] = Field(default_factory=list)


class Validation(BaseModel):
    check_type: str
    status: CheckStatus
    weight: int = 1
    critical_rule: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    id: str
    severity: Severity
    tier: Tier
    klass: FindingClass
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    related_nodes: list[str] = Field(default_factory=list)
    recommendation: str | None = None


class RiskResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    factors: dict[str, float] = Field(default_factory=dict)


class DecisionResult(BaseModel):
    decision: Decision
    reasons: list[str] = Field(default_factory=list)


class RemediationStep(BaseModel):
    order: int
    description: str
    change: NormalizedChange
    verified_score: float
    verified_decision: Decision


class AnalysisReport(BaseModel):
    analysis_id: str
    change: NormalizedChange
    decision: DecisionResult
    risk: RiskResult
    impact: ImpactResult
    validations: list[Validation] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    remediation: list[RemediationStep] = Field(default_factory=list)
    explanation: str
    graph_version: str
    rules_version: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
