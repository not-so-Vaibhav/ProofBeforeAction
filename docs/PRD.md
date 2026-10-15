# ProofBeforeAction — Product Requirements Document (PRD)

Version 1.0 · VIT CODE APEX 3.0 · Open Innovation

## 1. Overview

**ProofBeforeAction (PBA)** is a pre-execution consequence analysis engine. Given a proposed change (SQL migration, code change, or healthcare operational change), it maps what the change touches, **proves** likely failures by replaying the change on a disposable copy where possible, grades every finding by how strong its evidence is, and returns an evidence-backed decision: `ALLOW`, `HUMAN_REVIEW` or `BLOCK`. It also recommends a safer alternative and **re-verifies that alternative with the same engine**.

Tagline: *"Understand the consequences before you commit to the action."*

## 2. Problem

AI coding agents, automated data pipelines and digital healthcare workflows modify interconnected systems. A change that looks correct in isolation can break downstream queries, jobs, endpoints or operational workflows. Existing checks (tests, linters, policy rules) each catch individual errors, but none gives one explanation of the change's wider consequences with clear evidence and a safe next step.

Central question: **What could this change break, what evidence supports that, and how do we make it safer?**

## 3. Goals and non-goals

### Goals

- G1: Show real, reproducible consequences of a proposed change before it is executed.
- G2: Distinguish confirmed failures, estimated risks and unknowns explicitly.
- G3: Use one engine for two domains (Coding & Data, Healthcare Operations).
- G4: Provide a safer alternative that the engine has itself verified.
- G5: Be callable by an AI agent as a pre-execution gate.
- G6: Report measured accuracy on a labeled scenario suite.

### Non-goals

- Executing changes against production systems.
- Autonomous clinical diagnosis or treatment decisions.
- Real authentication, multi-tenancy or enterprise RBAC (roadmap).
- Running untrusted code (a sandbox is roadmap; analysis is static plus SQL replay on fixtures).
- Claiming a calibrated failure probability. The score is a heuristic.

## 4. Users and personas

| Persona | Context | Needs |
|---|---|---|
| **Dana, Data Engineer** | Reviews schema migrations and pipeline changes | See which queries, views and jobs break, with proof, and a safe migration sequence |
| **Agent integrator (Ravi)** | Runs AI coding agents that propose changes | A single API call that says proceed or stop, and why |
| **Hospital operations reviewer (Meera)** | Approves scheduling and workflow changes (synthetic data only) | Plain-language impact on departments, staffing and reports, plus an alternative that satisfies constraints |
| **Hackathon judge** | Evaluates impact and feasibility in minutes | A clear demo, visible evidence, honest limits and measured results |

## 5. User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|---|---|---|
| US-1 | As Dana, I submit a SQL migration and see its decision | Report shows decision, score, affected resources and findings within 5 seconds for fixtures |
| US-2 | As Dana, I see proof, not guesses | At least one finding for the DROP COLUMN scenario has tier `REPRODUCED` with the actual error message |
| US-3 | As any user, I see how certain each finding is | Every finding displays a tier badge: `REPRODUCED`, `PROVEN`, `INFERRED` or `UNKNOWN` |
| US-4 | As Dana, I explore the impact graph | Graph highlights the path from the changed resource to each affected node; node styles show provenance |
| US-5 | As Dana, I get a safer alternative that was verified | Report shows a step sequence and re-analysis scores per step (e.g. 86 → 18) |
| US-6 | As Ravi, an agent calls a check endpoint | `POST /api/agent/check` returns `proceed: false` for BLOCK and includes findings and a safer alternative |
| US-7 | As Meera, I analyze a staffing change | Cascade from shifts to coverage to bed capacity to slots to reports is shown, with the failed rule |
| US-8 | As any user, an unresolvable dependency is not hidden | The ambiguous dynamic-SQL scenario returns `HUMAN_REVIEW` with an `UNKNOWN` finding and a coverage warning |
| US-9 | As a judge, I see measured accuracy | An evaluation page or script prints precision, recall, false-block rate and latency from real runs |
| US-10 | As a reviewer (stretch), I approve or reject | Approval requires the Reviewer role and writes an audit event |

## 6. Functional requirements

Priority: **P0** must ship, **P1** should ship, **P2** stretch.

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Accept a change with domain, change type, title and payload | P0 |
| FR-2 | Normalize changes to a common internal structure | P0 |
| FR-3 | Build a dependency graph with provenance (`extracted`, `declared`, `modeled`) on every node and edge | P0 |
| FR-4 | Compute blast radius by graph traversal and return paths | P0 |
| FR-5 | Parse SQL with SQLGlot and extract column and table references | P0 |
| FR-6 | Replay SQL migrations on an in-memory copy built from fixtures and run dependent queries, capturing real errors | P0 |
| FR-7 | Run a Python AST rule detecting unconditional-True authentication | P1 |
| FR-8 | Classify each finding with an evidence tier and a class (`confirmed`, `potential`, `unknown`) | P0 |
| FR-9 | Record each validation as `PASSED`, `FAILED` or `NOT_RUN` | P0 |
| FR-10 | Compute a 0–100 risk score with documented factors | P0 |
| FR-11 | Apply decision precedence (critical rule, then incomplete evidence, then score) | P0 |
| FR-12 | Report graph coverage and flag uncovered dependencies | P0 |
| FR-13 | Generate a remediation sequence and re-run analysis on each step | P0 |
| FR-14 | Healthcare adapter driven by a YAML domain model and rule file, using synthetic data | P0 |
| FR-15 | Persist analyses, findings, validations and audit events | P0 |
| FR-16 | Agent pre-check endpoint | P1 |
| FR-17 | Evaluation runner over a labeled scenario suite | P0 |
| FR-18 | LLM explanation grounded in findings, with template fallback | P2 |
| FR-19 | Approve/reject with role check and audit trail | P2 |
| FR-20 | Presenter mode with one-click scenario loading | P1 |

## 7. Non-functional requirements

| Area | Requirement |
|---|---|
| Honesty | No hardcoded results; every finding traces to a check or graph path |
| Performance | Fixture analysis under 5 s end to end; replay under 2 s |
| Reliability | Replay or LLM failure degrades gracefully and never crashes analysis |
| Safety | Never execute changes outside the disposable in-memory replay; no real patient data |
| Reproducibility | Each analysis stores a graph and rule version |
| Usability | Report readable in 30 seconds; decision and tiers always visible |
| Accessibility | Decision never conveyed by colour alone; keyboard navigable |
| Maintainability | Domain logic isolated in adapters; TypeScript types mirror Pydantic models |

## 8. Scenarios in scope

| ID | Domain | Scenario | Expected |
|---|---|---|---|
| A1 | Coding & Data | `DROP COLUMN patients.patient_id` with dependent view, queries and a pipeline | BLOCK, reproduced error |
| A2 | Coding & Data | `verify_user` returns `True` unconditionally; three endpoints depend on it | BLOCK |
| A3 | Coding & Data | Pipeline builds SQL dynamically; columns cannot be resolved | HUMAN_REVIEW, `UNKNOWN` finding |
| B1 | Healthcare | Remove two Cardiology night shifts; staffing ratio breaks | HUMAN_REVIEW or BLOCK |
| B2 | Healthcare | Remove `department_id` from appointments | HUMAN_REVIEW or BLOCK |
| S1–S4 | Both | Safe changes (nullable column, index, valid reassignment, rename of unreferenced column) | ALLOW |

The full 12-scenario suite is defined in the Schema doc and the evaluation runner.

## 9. Success metrics

| Metric | Target for prototype |
|---|---|
| Critical-risk detection on labeled risky scenarios | 100% |
| False-block rate on safe scenarios | 0% |
| Dependency precision / recall on fixtures | Reported honestly, aim above 90% |
| Findings with traceable evidence | 100% of confirmed findings |
| Remediation verified by re-analysis | 100% of generated plans |
| Analysis latency | Under 5 s |

The suite is small. We report results as *measured on our labeled scenarios*, not as general accuracy.

## 10. Release scope

- **MVP (P0):** engine, SQL replay, evidence tiers, healthcare cascade, remediation verification, report and graph screens, evaluation runner.
- **Should (P1):** Python auth rule, agent endpoint, presenter mode, dashboard and history.
- **Stretch (P2):** LLM explanation, approve/reject, charts.
- **Roadmap:** real auth and RBAC, container sandbox, Tree-sitter, OpenAPI checks, GitHub/CI/MCP integration, calibrated scoring, backtesting on real repositories.

## 11. Assumptions and risks

| Item | Detail |
|---|---|
| Assumption | Demo uses fixtures and synthetic data only |
| Assumption | Replay targets SQLite-compatible SQL; Postgres-only syntax degrades to static analysis |
| Risk | Graph incompleteness. Mitigation: coverage metric and forced review |
| Risk | Healthcare seen as a re-skin. Mitigation: multi-hop cascade scenario |
| Risk | Overclaiming. Mitigation: wording rules below |

**Wording rules.** Never call the score a probability. Never say "first ever". Say *"no single tool combines replay-confirmed evidence, tiered certainty and verified remediation across code, data and operational workflows."*

## 12. Glossary

| Term | Meaning |
|---|---|
| Blast radius | Nodes reachable downstream from the changed resource; exposure, not confirmed failure |
| Evidence tier | `REPRODUCED` (failed in replay), `PROVEN` (static rule or parse confirms), `INFERRED` (reachable, unverified), `UNKNOWN` (coverage gap) |
| Finding class | `confirmed`, `potential` or `unknown` |
| Provenance | How a node or edge was obtained: `extracted`, `declared`, `modeled` |
| Coverage | Fraction of the change's dependencies the engine could resolve |
| Remediation verification | Re-running the engine on each step of the recommended safe plan |
