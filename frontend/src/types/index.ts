// Core ProofBeforeAction Enums and Types mirroring backend Pydantic models

export type Domain = 'coding_data' | 'healthcare_ops';
export type Decision = 'ALLOW' | 'HUMAN_REVIEW' | 'BLOCK';
export type Tier = 'REPRODUCED' | 'PROVEN' | 'INFERRED' | 'UNKNOWN';
export type FindingClass = 'confirmed' | 'potential' | 'unknown';
export type CheckStatus = 'PASSED' | 'FAILED' | 'NOT_RUN';
export type Provenance = 'extracted' | 'declared' | 'modeled';
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
}
