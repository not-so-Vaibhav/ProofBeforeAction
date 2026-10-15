# ProofBeforeAction — Technical Requirements Document (TRD)

Version 1.0 · This is the source of truth for implementation. If code disagrees with this document, fix the code or update this document in the same commit.

## 1. Architecture overview

Modular monolith. One FastAPI service, one frontend, one database.

```
React UI  /  Agent script
      |
      v
FastAPI routers (api/)
      |
      v
AnalysisOrchestrator (engine/orchestrator.py)
  1. adapter.parse(change)            -> NormalizedChange
  2. adapter.build_graph(project)     -> DependencyGraph (NetworkX)
  3. impact.analyze(graph, change)    -> ImpactResult (affected nodes, paths, coverage)
  4. adapter.validate(...)            -> list[Validation]  (includes replay)
  5. findings.build(...)              -> list[Finding] with tiers
  6. risk.score(...)                  -> RiskResult
  7. decision.decide(...)             -> Decision
  8. remediation.plan_and_verify(...) -> RemediationPlan (re-runs steps 1-7 per step)
  9. explanation.render(...)          -> text (LLM or template)
 10. persist + audit
```

The orchestrator contains no domain logic. Domains plug in through the adapter interface.

## 2. Technology and versions

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Type hints everywhere |
| API | FastAPI, Uvicorn, Pydantic v2 | OpenAPI at `/docs` |
| Graph | NetworkX `DiGraph` | In-memory per analysis |
| SQL | SQLGlot | Parse, qualify, transpile to SQLite |
| Replay | Python `sqlite3` in-memory | Needs SQLite 3.35+ for `DROP COLUMN` |
| ORM | SQLAlchemy 2.x | PostgreSQL via `psycopg`; SQLite fallback through `DATABASE_URL` |
| Data | Pandas | Synthetic healthcare data generation |
| Config | PyYAML | Healthcare model and rules |
| Tests | Pytest | Scenario tests double as evaluation |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS | Types mirror Pydantic models |
| Frontend libs | react-router-dom, @xyflow/react, axios, recharts, lucide-react | |
| LLM (P2) | Gemini API or other | Behind an interface with a template fallback |

## 3. Core data models (Pydantic)

Define in `engine/models.py`. Names are fixed because the frontend types mirror them.

```python
class Domain(str, Enum):      coding_data; healthcare_ops
class Decision(str, Enum):    ALLOW; HUMAN_REVIEW; BLOCK
class Tier(str, Enum):        REPRODUCED; PROVEN; INFERRED; UNKNOWN
class FindingClass(str, Enum):confirmed; potential; unknown
class CheckStatus(str, Enum): PASSED; FAILED; NOT_RUN
class Provenance(str, Enum):  extracted; declared; modeled
class Severity(str, Enum):    critical; high; medium; low; info

class NormalizedChange(BaseModel):
    domain: Domain
    change_type: str            # sql_migration | code_change | schedule_change | schema_change
    title: str
    affected_resources: list[str]   # e.g. ["table:patients.column:patient_id"]
    payload: dict
    irreversibility: int            # 0..100, from taxonomy

class GraphNode(BaseModel):
    id: str; type: str; name: str
    provenance: Provenance
    criticality: int = 50           # 0..100
    meta: dict = {}

class GraphEdge(BaseModel):
    source: str; target: str; relationship: str
    provenance: Provenance

class ImpactResult(BaseModel):
    entry_nodes: list[str]; affected_nodes: list[str]
    paths: dict[str, list[list[str]]]   # target -> list of paths from entry
    coverage: float                      # 0..1
    uncovered: list[str]                 # unresolved dependencies

class Validation(BaseModel):
    check_type: str; status: CheckStatus; weight: int  # 1 normal, 2 high, 3 critical
    critical_rule: bool = False
    details: dict = {}

class Finding(BaseModel):
    id: str; severity: Severity; tier: Tier; klass: FindingClass
    message: str; evidence: dict; related_nodes: list[str]
    recommendation: str | None = None

class RiskResult(BaseModel):
    score: float; factors: dict[str, float]   # S, D, V, I, U

class DecisionResult(BaseModel):
    decision: Decision; reasons: list[str]

class RemediationStep(BaseModel):
    order: int; description: str; change: NormalizedChange
    verified_score: float; verified_decision: Decision

class AnalysisReport(BaseModel):
    analysis_id: str; change: NormalizedChange
    decision: DecisionResult; risk: RiskResult
    impact: ImpactResult; validations: list[Validation]
    findings: list[Finding]; remediation: list[RemediationStep]
    explanation: str; graph_version: str; rules_version: str
    created_at: datetime
```

## 4. Adapter interface

```python
class DomainAdapter(Protocol):
    domain: Domain
    def parse(self, change_request: dict) -> NormalizedChange: ...
    def build_graph(self, project_id: str, change: NormalizedChange) -> tuple[nx.DiGraph, float]:
        """Returns graph and coverage (0..1)."""
    def validate(self, change: NormalizedChange, graph: nx.DiGraph, impact: ImpactResult) -> list[Validation]: ...
    def propose_remediation(self, change: NormalizedChange, report_so_far) -> list[NormalizedChange]: ...
```

Adapters live in `domains/coding_data/` and `domains/healthcare_ops/`. A registry in `engine/registry.py` maps `Domain` to adapter.

## 5. Graph model

**Node types.** `table`, `column`, `view`, `query`, `pipeline`, `function`, `endpoint`, `department`, `ward`, `staff_shift`, `appointment_slot`, `report`, `workflow`.

**Edge relationships.** `reads`, `writes`, `references`, `depends_on`, `calls`, `exposes`, `staffs`, `schedules`, `feeds`, `reports_on`.

**Direction.** Edges point from the *provider* to the *consumer* (changing the source can break the target). Impact analysis is a BFS from entry nodes along outgoing edges. Cap depth at 6 and node count at 500. If the depth or node cap cuts off nodes with unvisited successors, add `truncated:depth_cap` or `truncated:node_cap` to `uncovered` and count it in coverage.

**Path recording.** Use `nx.all_simple_paths` with a cutoff, limited to 3 paths per target, so reports stay readable.

**Coverage.** `coverage = resolved_references / total_references`. A reference is unresolved if SQLGlot cannot determine its table or column (for example dynamic SQL strings or `SELECT *` over an unknown source). Each unresolved reference is added to `uncovered`.

## 6. Coding & Data adapter

### 6.1 SQL analyzer (`sql_analyzer.py`)

- Parse the migration with `sqlglot.parse(sql, read="postgres")`.
- Supported statements for MVP: `ALTER TABLE ... DROP COLUMN`, `ADD COLUMN`, `RENAME COLUMN`, `ALTER COLUMN TYPE`, `DROP TABLE`, `CREATE INDEX`.
- Produce `affected_resources` as `table.column` or `table`.
- For each fixture query, view and pipeline SQL, parse and use `sqlglot.optimizer.qualify` with the fixture schema to extract exact column references. Add `reads` and `references` edges with provenance `extracted`.
- Pipeline, endpoint and function dependencies come from `fixtures/<project>/dependencies.yaml` with provenance `declared`.
- `SELECT *` over a known table expands via the schema. Over an unknown source it becomes an uncovered reference.

### 6.2 Replay engine (`replay.py`) — proof by replay

Purpose: turn inference into evidence.

1. Build an in-memory SQLite database from `fixtures/<project>/schema.sql`, plus `seed.sql` rows.
2. Transpile the migration and each dependent statement with `sqlglot.transpile(sql, read="postgres", write="sqlite")`. If transpilation raises, record the replay as `NOT_RUN` with the reason.
3. Apply the migration. If it errors (for example dropping a column referenced by a view), record the error text. This is tier `REPRODUCED`.
4. If the migration applies, run every dependent query and view select. Record each success or the exact SQLite error (such as `no such column`).
5. Always discard the database. Never connect to a real database.
6. Return a `Validation` per statement and structured evidence: `{statement, error, phase: "migration"|"query"}`.

Implementation rules: open with `sqlite3.connect(":memory:")`; use a 2-second time limit; run statements in a try/except; do not allow `ATTACH` or file paths.

Fixtures must keep the dropped column non-primary-key and non-unique, so failures reflect real consumer breakage. SQLite refuses `DROP COLUMN` when a view references the column, which gives a genuine reproduced error.

### 6.3 Python code analyzer (`code_analyzer.py`, P1)

- Parse original and proposed code with `ast`.
- Rule `auth_check_removed` (critical): a function marked as an authentication gate in `fixtures/<project>/dependencies.yaml` whose original returned a non-constant expression now returns `True` unconditionally (or contains no reference to the original check). Evidence tier `PROVEN`.
- Dependent endpoints come from declared `calls`/`exposes` edges.

### 6.4 Rules (`rules.py`)

Rules are small functions `(change, graph, impact) -> Validation`, registered by name. Mark critical rules with `critical_rule=True`. A rule that cannot run because input is missing returns `NOT_RUN` (never `PASSED`).

## 7. Healthcare Operations adapter

- The environment is defined in `domains/healthcare_ops/model.yaml` (departments, wards, staff roles, shifts, slots, reports and their relationships, all with provenance `modeled`).
- Synthetic data is generated by `synthetic_data.py` with a fixed random seed and written as CSV for Pandas. It must contain deliberate problems: a missing department mapping, an over-capacity ward and an incompatible schema change.
- Rules live in `rules.yaml`, for example:

```yaml
rules:
  - id: min_staff_to_bed_ratio
    critical: false
    description: Each ward needs at least 1 nurse per 4 staffed beds per shift
    check: staff_ratio
    params: { min_ratio: 0.25 }
  - id: department_mapping_required
    critical: true
    description: Every appointment must map to a department
    check: required_mapping
    params: { table: appointments, column: department_id }
```

- Cascade: `staff_shift -> department_coverage -> ward_capacity -> appointment_slot -> daily_report`. Impact analysis must traverse at least three hops for scenario B1.
- Healthcare findings are operational only. Recommendations go to an authorized operator. No clinical output.

## 8. Evidence tiers and finding classes

| Tier | Produced when | Class |
|---|---|---|
| `REPRODUCED` | Replay produced an error attributable to the change | `confirmed` |
| `PROVEN` | A static rule or parse result confirms the violation | `confirmed` |
| `INFERRED` | Node is reachable in the graph but no check confirmed failure | `potential` |
| `UNKNOWN` | Reference could not be resolved, or a required check was `NOT_RUN` | `unknown` |

Every finding stores `evidence` with the originating validation id or graph path.

## 9. Risk scoring

Formula: `R = 0.30*S + 0.25*D + 0.25*V + 0.10*I + 0.10*U` (clamped to 0–100). All weights live in `engine/config.py`.

| Factor | Definition |
|---|---|
| S, impact severity | Maximum `criticality` among affected nodes (0–100) |
| D, dependency exposure | `min(100, 10 * number_of_affected_nodes)` |
| V, validation failures | `100 * (sum of weights of FAILED checks) / (sum of weights of checks that ran)`; 0 if none ran |
| I, irreversibility | From taxonomy: additive 0, rename or type change 40, drop or delete 100 |
| U, uncertainty | `min(100, 100 * (0.6*(1 - coverage) + 0.4*not_run_fraction))` |

The score is a heuristic, not a probability. The report must say so.

## 10. Decision engine

```python
def decide(score, validations, impact, findings):
    critical_failed = any(v.critical_rule and v.status == FAILED for v in validations)
    if critical_failed:
        return BLOCK, ["Critical rule failed: ..."]

    if not validations:
        return HUMAN_REVIEW, ["no checks ran"]

    critical_not_run = any(v.critical_rule and v.status == NOT_RUN for v in validations)
    evidence_complete = not impact.uncovered and not critical_not_run
    if not evidence_complete:
        return HUMAN_REVIEW, ["Incomplete evidence: uncovered dependencies or critical check not run"]

    if score >= 70:
        return BLOCK, ["Risk score exceeds block threshold"]

    any_failed = any(v.status == FAILED for v in validations)
    if any_failed or score >= 30:
        return HUMAN_REVIEW, ["Validation failures detected or risk score exceeds review threshold"]

    has_passed = any(v.status == PASSED for v in validations)
    if has_passed:
        return ALLOW, ["All checks passed and risk score is within acceptable limits"]

    return HUMAN_REVIEW, ["no checks ran"]
```

Notes:
- `evidence_complete` requires `not impact.uncovered` and `not critical_not_run`. Any uncovered dependency (including `truncated:*` and `unknown_entry:*` markers) forces `HUMAN_REVIEW`. Coverage remains a reported metric only.
- If no validations exist at all (nothing was verified), the decision is `HUMAN_REVIEW` with the reason "no checks ran". `ALLOW` requires at least one check that ran and passed.
- Each branch appends a human-readable reason naming the rule that fired. Unit tests must cover every branch.

## 11. Self-verified remediation

1. `adapter.propose_remediation` returns an ordered list of safe `NormalizedChange` steps (templates):
   - SQL drop column: *add replacement or keep column, migrate consumers, validate, backup, drop*.
   - Healthcare staffing: *reassign from surplus ward, re-check ratio, submit for operator approval*.
2. For each step, run the full orchestrator pipeline on the post-previous-step state and store `verified_score` and `verified_decision`.
3. The report shows the trajectory. A plan is flagged **verified** only if the final step is `ALLOW` or `HUMAN_REVIEW` with all checks run.
4. For the demo the fixtures include the replacement column and migrated consumer SQL so that step re-analysis genuinely passes. Document this in `fixtures/README.md`.

## 12. Agent check endpoint

`POST /api/agent/check` runs the same pipeline. Response adds `proceed: bool` (true only for ALLOW), a compact findings list and `safer_alternative`. Idempotent. Stores the analysis like any other.

## 13. Explanation layer (P2)

Interface `Explainer.render(report) -> str`. Default `TemplateExplainer` builds text from findings. `LLMExplainer` calls Gemini with the findings JSON and a system prompt: *use only the supplied evidence; label hypotheses as potential; do not change the decision.* On any error or timeout (8 s), fall back to the template. The LLM never influences the decision.

## 14. Persistence and audit

- Persist after each analysis in one transaction: change request, analysis, validations, findings, audit event.
- `audit_events` is append-only in application code (no update or delete endpoints).
- Store `graph_version` (hash of nodes and edges) and `rules_version` (hash of rule config) for reproducibility.
- Table definitions are in the Schema document.

## 15. Security and safety

- Source and SQL inputs are untrusted text. Never `eval` or `exec` them. Parse only.
- Replay uses in-memory SQLite only, with a time limit.
- Request size limit 200 KB. Validate all inputs with Pydantic.
- CORS limited to the frontend origin.
- Role is passed in `X-Role` header (`analyst`, `reviewer`) for the demo. Approval requires `reviewer`. State clearly that this is a demo stand-in for real auth.
- Secrets in `.env`, never committed.
- Healthcare data is synthetic only.

## 16. Error handling

Uniform error body: `{"error": {"code": "...", "message": "...", "details": {}}}`. A failing check yields `NOT_RUN` plus a finding of tier `UNKNOWN`; it must not abort the analysis.

## 17. Testing strategy

| Level | What | Examples |
|---|---|---|
| Unit | Graph traversal, risk factors, decision branches, SQL extraction | BFS finds 3 downstream nodes; critical failure always blocks |
| Replay | Migration and query outcomes | A1 returns a `no such column`-type error, not just a graph hit |
| Scenario | The 12-scenario suite | Expected decision per scenario |
| API | Endpoint contracts | Response matches Pydantic schema |
| Frontend | Type-check and smoke render | Report page renders from a fixture JSON |

`backend/eval/run_eval.py` loads `scenarios.yaml`, runs the orchestrator, and prints precision, recall, false-block rate, critical detection and mean latency. It also writes `eval/results.json` for the UI.

## 18. Performance targets

Graph under 500 nodes. Full analysis under 5 s. Replay under 2 s. Report fetch under 300 ms.

## 19. Environment and deployment

- `docker-compose.yml` runs PostgreSQL only; backend and frontend run locally.
- Env vars: `DATABASE_URL`, `CORS_ORIGIN`, `GEMINI_API_KEY` (optional), `LLM_ENABLED`.
- Commands: `uvicorn main:app --reload --port 8000`, `npm run dev` (port 5173), `pytest`, `python -m eval.run_eval`, `python -m db.seed`.

## 20. Definition of done for any feature

Code matches this TRD, tests pass, no hardcoded results, types updated on both sides, and the behaviour was run by a human at least once.
