# ProofBeforeAction — Backend Schema, Fixtures & API Contract

Version 1.0 · Database: PostgreSQL via SQLAlchemy 2.x (SQLite fallback through `DATABASE_URL`)

## 1. Entity relationships

```
projects 1---* resources 1---* dependencies (source_id, target_id)
projects 1---* change_requests 1---* analyses
analyses 1---* findings
analyses 1---* validations
analyses 1---* remediation_steps
analyses 1---* approvals
analyses 1---* audit_events   (also project-level events)
```

The role for the demo is sent in the `X-Role` header, so there is no `users` table in the MVP.

## 2. Enumerations

| Enum | Values |
|---|---|
| `domain` | `coding_data`, `healthcare_ops` |
| `decision` | `ALLOW`, `HUMAN_REVIEW`, `BLOCK` |
| `tier` | `REPRODUCED`, `PROVEN`, `INFERRED`, `UNKNOWN` |
| `finding_class` | `confirmed`, `potential`, `unknown` |
| `check_status` | `PASSED`, `FAILED`, `NOT_RUN` |
| `provenance` | `extracted`, `declared`, `modeled` |
| `severity` | `critical`, `high`, `medium`, `low`, `info` |
| `change_status` | `submitted`, `analyzed`, `approved`, `rejected` |

## 3. Table definitions (PostgreSQL DDL)

IDs are text (short readable ids such as `analysis-001`, or UUID strings). Timestamps are `timestamptz` defaulting to `now()`.

```sql
CREATE TABLE projects (
  id          text PRIMARY KEY,
  name        text NOT NULL,
  domain      text NOT NULL,
  description text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE resources (            -- graph nodes
  id           text PRIMARY KEY,    -- e.g. 'table:patients', 'column:patients.patient_id'
  project_id   text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  type         text NOT NULL,       -- table, column, view, query, pipeline, function, endpoint, ward, ...
  name         text NOT NULL,
  provenance   text NOT NULL,       -- extracted | declared | modeled
  criticality  int  NOT NULL DEFAULT 50 CHECK (criticality BETWEEN 0 AND 100),
  meta         jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_resources_project ON resources(project_id);

CREATE TABLE dependencies (         -- graph edges, provider -> consumer
  id           bigserial PRIMARY KEY,
  project_id   text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_id    text NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  target_id    text NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  relationship text NOT NULL,
  provenance   text NOT NULL,
  UNIQUE (source_id, target_id, relationship)
);
CREATE INDEX ix_dependencies_source ON dependencies(source_id);
CREATE INDEX ix_dependencies_target ON dependencies(target_id);

CREATE TABLE change_requests (
  id          text PRIMARY KEY,
  project_id  text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  domain      text NOT NULL,
  change_type text NOT NULL,        -- sql_migration | code_change | schedule_change | schema_change
  title       text NOT NULL,
  payload     jsonb NOT NULL,
  status      text NOT NULL DEFAULT 'submitted',
  source      text NOT NULL DEFAULT 'ui',   -- ui | agent
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE analyses (
  id              text PRIMARY KEY,
  change_id       text NOT NULL REFERENCES change_requests(id) ON DELETE CASCADE,
  decision        text NOT NULL,
  risk_score      numeric(5,2) NOT NULL,
  risk_factors    jsonb NOT NULL,   -- {S, D, V, I, U}
  decision_reasons jsonb NOT NULL,  -- ["Critical rule failed: ..."]
  coverage        numeric(4,3) NOT NULL,
  uncovered       jsonb NOT NULL DEFAULT '[]',
  explanation     text,
  explanation_source text NOT NULL DEFAULT 'template',  -- template | llm
  graph_version   text NOT NULL,
  rules_version   text NOT NULL,
  latency_ms      int,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE validations (
  id            bigserial PRIMARY KEY,
  analysis_id   text NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  check_type    text NOT NULL,
  status        text NOT NULL,      -- PASSED | FAILED | NOT_RUN
  weight        int  NOT NULL DEFAULT 1,
  critical_rule boolean NOT NULL DEFAULT false,
  details       jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE findings (
  id             text PRIMARY KEY,
  analysis_id    text NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  severity       text NOT NULL,
  tier           text NOT NULL,     -- REPRODUCED | PROVEN | INFERRED | UNKNOWN
  class          text NOT NULL,     -- confirmed | potential | unknown
  message        text NOT NULL,
  evidence       jsonb NOT NULL,    -- {validation_id?, statement?, error?, path?}
  related_nodes  jsonb NOT NULL DEFAULT '[]',
  recommendation text
);
CREATE INDEX ix_findings_analysis ON findings(analysis_id);

CREATE TABLE remediation_steps (
  id               bigserial PRIMARY KEY,
  analysis_id      text NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  step_order       int  NOT NULL,
  description      text NOT NULL,
  change           jsonb NOT NULL,
  verified_score   numeric(5,2) NOT NULL,
  verified_decision text NOT NULL
);

CREATE TABLE approvals (            -- stretch
  id           bigserial PRIMARY KEY,
  analysis_id  text NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  reviewer_role text NOT NULL,
  decision     text NOT NULL,       -- approved | rejected
  comment      text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_events (         -- append-only in application code
  id          bigserial PRIMARY KEY,
  actor_role  text NOT NULL,
  action      text NOT NULL,        -- change_submitted, analysis_completed, approved, rejected
  entity_type text NOT NULL,
  entity_id   text NOT NULL,
  detail      jsonb NOT NULL DEFAULT '{}',
  created_at  timestamptz NOT NULL DEFAULT now()
);
```

Notes:

- `ON DELETE CASCADE` exists so the demo reset script can wipe a project cleanly. Normal application code never deletes analyses or audit events.
- Do not expose update or delete endpoints for `audit_events`.
- `graph_version` and `rules_version` are short hashes (SHA-256, first 8 characters) of the graph content and rule configuration.

## 4. Fixtures

Fixtures live in `backend/fixtures/<project>/` and are loaded by `python -m db.seed`.

### 4.1 `demo-code-01` (Coding & Data)

Files: `schema.sql`, `seed.sql`, `queries.sql`, `dependencies.yaml`, `auth_before.py`, `README.md`.

```sql
-- schema.sql (SQLite-compatible; patient_id is NOT a primary key or unique)
CREATE TABLE patients (
  id INTEGER PRIMARY KEY,
  patient_id TEXT NOT NULL,
  full_name TEXT NOT NULL,
  dob TEXT
);
CREATE TABLE appointments (
  id INTEGER PRIMARY KEY,
  patient_id TEXT NOT NULL,
  department_id INTEGER,
  slot_time TEXT
);
CREATE TABLE bed_allocation (
  id INTEGER PRIMARY KEY,
  patient_id TEXT NOT NULL,
  ward TEXT
);
CREATE VIEW v_patient_report AS
  SELECT p.patient_id, p.full_name, COUNT(a.id) AS visits
  FROM patients p LEFT JOIN appointments a ON a.patient_id = p.patient_id
  GROUP BY p.patient_id, p.full_name;
```

`queries.sql` holds named statements (`q_appointments_by_patient`, `q_beds_by_patient`, `q_patient_lookup`) that reference `patients.patient_id`. All data is synthetic.

`dependencies.yaml` (declared edges):

```yaml
nodes:
  - { id: pipeline:analytics_pipeline, type: pipeline, criticality: 70 }
  - { id: endpoint:/api/profile, type: endpoint, criticality: 80 }
  - { id: endpoint:/api/orders, type: endpoint, criticality: 80 }
  - { id: endpoint:/api/admin,  type: endpoint, criticality: 95 }
  - { id: function:verify_user, type: function, criticality: 95, auth_gate: true }
edges:
  - { source: column:patients.patient_id, target: pipeline:analytics_pipeline, relationship: reads }
  - { source: function:verify_user, target: endpoint:/api/profile, relationship: exposes }
  - { source: function:verify_user, target: endpoint:/api/orders,  relationship: exposes }
  - { source: function:verify_user, target: endpoint:/api/admin,   relationship: exposes }
dynamic_sql_pipelines:
  - { id: pipeline:nightly_export, reason: builds SQL from a string at runtime }
```

The `dynamic_sql_pipelines` entry produces an uncovered reference for scenario A3.

To make remediation verification real, the fixtures also include `remediation/` SQL: a replacement column (`patient_ref`), updated view and queries that use it, and a final drop. Step re-analysis replays these.

### 4.2 `demo-health-01` (Healthcare Operations, synthetic)

Files: `model.yaml`, `rules.yaml`, generated CSVs (`departments`, `wards`, `staff_shifts`, `appointment_slots`, `reports`), `README.md`.

| Entity | Key fields |
|---|---|
| departments | id, name |
| wards | id, department_id, staffed_beds |
| staff_shifts | id, ward_id, shift (`day`/`night`), nurse_count |
| appointment_slots | id, department_id, slot_time, capacity |
| reports | id, name, depends_on (department coverage, slots) |

Cascade edges (all `modeled`): `staff_shift → department_coverage → ward_capacity → appointment_slot → daily_ops_report` and `appointments.department_id → routing`, `→ staff_allocation_report`.

Deliberate problems in the data: one ward at the exact staffing minimum, one appointment with a missing `department_id`, one over-capacity slot. Seed uses a fixed random seed for reproducibility.

## 5. Evaluation scenario suite (`backend/eval/scenarios.yaml`)

| ID | Project | Change | Label | Expected decision |
|---|---|---|---|---|
| E01 | demo-code-01 | `ALTER TABLE patients ADD COLUMN notes TEXT` | safe | ALLOW |
| E02 | demo-code-01 | `CREATE INDEX ix_appt_dept ON appointments(department_id)` | safe | ALLOW |
| E03 | demo-code-01 | Rename unreferenced column `patients.dob` | safe | ALLOW |
| E04 | demo-code-01 | `DROP COLUMN patients.patient_id` | risky | BLOCK |
| E05 | demo-code-01 | `verify_user` returns `True` | risky | BLOCK |
| E06 | demo-code-01 | `DROP TABLE appointments` | risky | BLOCK |
| E07 | demo-code-01 | Change touching `pipeline:nightly_export` (dynamic SQL) | ambiguous | HUMAN_REVIEW |
| E08 | demo-health-01 | Move one night shift, ratio still met | safe | ALLOW |
| E09 | demo-health-01 | Remove two Cardiology night shifts | risky | HUMAN_REVIEW or BLOCK |
| E10 | demo-health-01 | Drop `appointments.department_id` | risky | HUMAN_REVIEW or BLOCK |
| E11 | demo-health-01 | Reassign surplus staff, capacity met | safe | ALLOW |
| E12 | demo-health-01 | Remove report field with unknown mapping | ambiguous | HUMAN_REVIEW |

Risky scenarios with a critical rule must return BLOCK. The runner records the actual decision, score and latency for each, and computes: critical-risk detection, false-block rate (safe scenarios that were blocked), dependency precision and recall (against `ground_truth` edges listed per scenario), and mean latency.

## 6. API contract

Base URL `http://localhost:8000`. JSON only. Header `X-Role: analyst | reviewer` (default `analyst`). Error format:

```json
{ "error": { "code": "validation_error", "message": "payload.sql is required", "details": {} } }
```

### 6.1 Endpoints

| Method | Path | Purpose | Priority |
|---|---|---|---|
| GET | `/health` | Service health | P0 |
| GET | `/api/projects` | List projects | P0 |
| GET | `/api/projects/{id}/scenarios` | Preset scenarios for the picker | P0 |
| POST | `/api/changes/analyze` | Submit and analyze in one call | P0 |
| GET | `/api/analyses/{id}` | Full report | P0 |
| GET | `/api/analyses/{id}/graph` | Nodes, edges, affected paths | P0 |
| GET | `/api/projects/{id}/history` | Past analyses | P1 |
| POST | `/api/agent/check` | Agent pre-execution check | P1 |
| GET | `/api/eval/results` | Latest evaluation results | P1 |
| POST | `/api/demo/reset` | Reseed demo data | P1 |
| POST | `/api/analyses/{id}/approve` | Approve (reviewer only) | P2 |
| POST | `/api/analyses/{id}/reject` | Reject (reviewer only) | P2 |

### 6.2 `POST /api/changes/analyze`

Request:

```json
{
  "project_id": "demo-code-01",
  "domain": "coding_data",
  "change_type": "sql_migration",
  "title": "Remove patient identifier",
  "payload": { "sql": "ALTER TABLE patients DROP COLUMN patient_id;" }
}
```

Response `200` (illustrative; real values come from real analysis):

```json
{
  "analysis_id": "analysis-001",
  "decision": { "decision": "BLOCK", "reasons": ["Critical rule failed: dependent view references patients.patient_id"] },
  "risk": { "score": 86.0, "factors": { "S": 90, "D": 40, "V": 100, "I": 100, "U": 0 } },
  "impact": {
    "entry_nodes": ["column:patients.patient_id"],
    "affected_nodes": ["view:v_patient_report", "query:q_appointments_by_patient", "pipeline:analytics_pipeline"],
    "paths": { "pipeline:analytics_pipeline": [["column:patients.patient_id", "pipeline:analytics_pipeline"]] },
    "coverage": 1.0,
    "uncovered": []
  },
  "validations": [
    { "check_type": "replay_migration", "status": "FAILED", "weight": 3, "critical_rule": true,
      "details": { "phase": "migration", "error": "error in view v_patient_report: no such column: p.patient_id" } }
  ],
  "findings": [
    { "id": "f-1", "severity": "critical", "tier": "REPRODUCED", "klass": "confirmed",
      "message": "Migration fails because view v_patient_report still references the column",
      "evidence": { "statement": "ALTER TABLE patients DROP COLUMN patient_id", "error": "no such column: p.patient_id" },
      "related_nodes": ["view:v_patient_report"],
      "recommendation": "Migrate dependent view and queries before removal" }
  ],
  "remediation": [
    { "order": 1, "description": "Add replacement column patient_ref and backfill", "verified_score": 41, "verified_decision": "HUMAN_REVIEW" },
    { "order": 2, "description": "Migrate view and queries to patient_ref", "verified_score": 33, "verified_decision": "HUMAN_REVIEW" },
    { "order": 3, "description": "Re-validate, backup, then drop old column", "verified_score": 18, "verified_decision": "ALLOW" }
  ],
  "explanation": "...",
  "graph_version": "9f3a1c2e",
  "rules_version": "2c1d7b90",
  "created_at": "2026-10-14T10:00:00Z"
}
```

The response is the `AnalysisReport` model from the TRD. The sample numbers above are illustrative and must not be hardcoded.

### 6.3 `GET /api/analyses/{id}/graph`

```json
{
  "nodes": [ { "id": "column:patients.patient_id", "type": "column", "name": "patients.patient_id",
               "provenance": "extracted", "is_entry": true, "affected": true, "finding_ids": ["f-1"] } ],
  "edges": [ { "source": "column:patients.patient_id", "target": "view:v_patient_report",
               "relationship": "references", "provenance": "extracted", "on_path": true } ],
  "unresolved": [ { "id": "unresolved:nightly_export", "reason": "dynamic SQL" } ]
}
```

### 6.4 `POST /api/agent/check`

Request: same body as analyze, plus `"agent_id": "demo-agent"`.

```json
{
  "analysis_id": "analysis-002",
  "decision": "BLOCK",
  "proceed": false,
  "risk_score": 86.0,
  "top_findings": [ { "tier": "REPRODUCED", "message": "..." } ],
  "safer_alternative": "Add replacement column, migrate consumers, validate, then drop",
  "report_url": "/analyses/analysis-002"
}
```

`proceed` is `true` only when the decision is `ALLOW`.

### 6.5 `POST /api/analyses/{id}/approve` (stretch)

Body `{ "comment": "Reviewed with DB owner" }`. Requires `X-Role: reviewer`, else `403`. Writes an `approvals` row and an `audit_events` row. A reject endpoint mirrors this.

### 6.6 `GET /api/eval/results`

Returns the contents of `eval/results.json`: per-scenario expected vs actual decision, score and latency, plus the aggregate metrics.

## 7. TypeScript mirror

The frontend defines `Decision`, `Tier`, `FindingClass`, `CheckStatus`, `Provenance`, `Severity`, `Finding`, `Validation`, `ImpactResult`, `RiskResult`, `RemediationStep` and `AnalysisReport` in `src/types/` with identical field names. When a Pydantic model changes, update the TypeScript type in the same commit.

## 8. Seed and reset

- `python -m db.seed` creates both projects, loads resources and dependencies, and optionally pre-runs three analyses so the dashboard is not empty.
- `POST /api/demo/reset` drops and reseeds demo data. It is the only place cascading deletes run.
