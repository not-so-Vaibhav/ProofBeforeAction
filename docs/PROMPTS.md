# ProofBeforeAction — Antigravity Prompt Pack

Run the prompts in order. One prompt, one commit. Paste the text inside each quote block into Antigravity as written.

## How to use this pack

1. Put the specs in `/docs`: `PRD.md`, `TRD.md`, `UIUX.md`, `SCHEMA.md`, `ROADMAP.md`.
2. Run **Prompt 0** first. It sets up the repo and the project rules.
3. After each prompt: read the agent's plan and diff, run the tests, run the app, then commit.
4. If a prompt fails, paste the error back and ask the agent to fix it. Do not move on until the acceptance checks pass.
5. Backend and frontend prompts can run in parallel in separate sessions once Prompt 6 is done, because they touch different directories. Until then the frontend can use mock mode.
6. If a prompt is too big for one session, split it by its numbered tasks.

**Ground rules (repeated in the project rules file):** follow the TRD and SCHEMA exactly; no hardcoded or fake results; every finding must come from a real check or graph path; add tests; keep functions small and typed; ask before changing a documented contract.

## Phase P0 — Foundation

### Prompt 0 — Bootstrap repo and project rules

> You are building ProofBeforeAction, a pre-execution consequence analysis engine. Read `docs/PRD.md`, `docs/TRD.md`, `docs/SCHEMA.md`, `docs/UIUX.md` and `docs/ROADMAP.md` fully before doing anything.
>
> Tasks:
> 1. Create the monorepo layout from section 10 of `docs/ROADMAP.md` with empty packages (`__init__.py`) and placeholder files.
> 2. Backend: `backend/requirements.txt` (fastapi, uvicorn[standard], sqlalchemy, psycopg[binary], pydantic, networkx, sqlglot, pandas, pyyaml, pytest, httpx, python-dotenv), `backend/main.py` with CORS for `http://localhost:5173` and `GET /health`.
> 3. Frontend: Vite + React + TypeScript in `frontend/`, install react-router-dom, @xyflow/react, axios, recharts, lucide-react, and set up Tailwind CSS following the current official Vite guide. Add the design tokens from `docs/UIUX.md` section 2 to the Tailwind config.
> 4. Create `.agent/rules/pba-rules.md` containing the project rules below.
> 5. Create `docker-compose.yml` for PostgreSQL only, `.env.example`, `.gitignore`, and a minimal `README.md`.
>
> Project rules for `.agent/rules/pba-rules.md`: (a) the TRD and SCHEMA are the source of truth, update them in the same commit if a contract must change; (b) never hardcode analysis results, every finding must come from a real check or graph path; (c) the LLM never influences the decision; (d) never execute user-supplied code or SQL outside the in-memory SQLite replay; (e) all Python is typed and every engine module has Pytest tests; (f) frontend types mirror Pydantic models exactly and the frontend never reimplements scoring or decision logic; (g) keep changes small and explain them; (h) ask before changing a documented contract.
>
> Acceptance: `uvicorn main:app --reload --port 8000` serves `/health`; `npm run dev` shows a page that fetches `/health` and displays the result; `pytest` runs (even with zero tests).

## Phase P1 — Engine core

### Prompt 1 — Models, graph and impact analysis

> Read `docs/TRD.md` sections 3, 4 and 5. Implement `backend/engine/models.py` with all Pydantic models and enums exactly as specified. Implement `backend/engine/graph.py` (build a NetworkX DiGraph from nodes and edges with provenance and criticality) and `backend/engine/impact.py` (BFS from entry nodes along outgoing edges, depth cap 6, node cap 500, up to 3 simple paths per target, coverage and uncovered list).
>
> Write Pytest tests in `backend/tests/test_impact.py`: linear chain, branching graph, cycle safety, depth cap, paths returned, coverage below 1 when an unresolved reference is present.
>
> Do not add any API code yet. Acceptance: all tests pass.

### Prompt 2 — Findings, risk and decision

> Read `docs/TRD.md` sections 8, 9 and 10. Implement `backend/engine/findings.py` (build findings with tier and class from validations and impact), `backend/engine/risk.py` (factors S, D, V, I, U and the weighted score with weights in `engine/config.py`) and `backend/engine/decision.py` (the decision function with a reason string for every branch).
>
> Tests in `backend/tests/test_risk.py` and `test_decision.py`: each factor on known inputs, score clamped 0 to 100, every decision branch (critical failed blocks regardless of score, critical NOT_RUN or coverage below 0.95 gives HUMAN_REVIEW, score 70 or more blocks, any failed check or score 30 or more gives HUMAN_REVIEW, otherwise ALLOW), and a test proving a low score cannot override missing evidence.
>
> Acceptance: all tests pass.

## Phase P2 — Coding & Data slice

### Prompt 3 — Fixtures, SQL analyzer and orchestrator skeleton

> Read `docs/TRD.md` sections 1, 4 and 6.1, and `docs/SCHEMA.md` section 4.1. Create `backend/fixtures/demo-code-01/` with `schema.sql`, `seed.sql` (synthetic rows), `queries.sql`, `dependencies.yaml` and `README.md` exactly as in the Schema doc. Implement `backend/domains/coding_data/sql_analyzer.py` using SQLGlot: parse the migration (DROP COLUMN, ADD COLUMN, RENAME COLUMN, ALTER COLUMN TYPE, DROP TABLE, CREATE INDEX), set the irreversibility taxonomy value, extract exact column references from fixture queries and views using the qualify optimizer, and build graph nodes and edges with provenance `extracted`; merge declared edges from `dependencies.yaml`; report unresolved references for dynamic SQL.
>
> Implement the `DomainAdapter` protocol, a registry, and `engine/orchestrator.py` that runs the pipeline steps without replay yet.
>
> Tests: the DROP COLUMN scenario finds the view, the dependent queries and the pipeline as affected; ADD COLUMN affects nothing; the dynamic SQL pipeline yields coverage below 1.
>
> Acceptance: tests pass; a CLI `python -m engine.cli demo-code-01 "ALTER TABLE patients DROP COLUMN patient_id;"` prints the affected nodes.

### Prompt 4 — Proof by replay

> Read `docs/TRD.md` section 6.2 carefully. Implement `backend/domains/coding_data/replay.py`: build an in-memory SQLite database from the fixture schema and seed, transpile the migration and each dependent statement with SQLGlot (postgres to sqlite; if transpilation fails mark the replay NOT_RUN with the reason), apply the migration capturing any error, then run each dependent query and view select capturing success or the exact error, and always discard the database. Enforce a 2 second limit, block ATTACH and file paths, and never touch a real database.
>
> Return `Validation` objects with structured evidence `{statement, error, phase}`. Update `findings.py` so a replay error produces a finding with tier REPRODUCED and class confirmed, and mark the migration replay check as a critical rule.
>
> Tests: DROP COLUMN patients.patient_id returns a REPRODUCED finding containing a real SQLite error; ADD COLUMN passes; an unsupported statement gives NOT_RUN and an UNKNOWN finding rather than a crash.
>
> Acceptance: the CLI prints BLOCK with the reproduced error text. This is milestone M1.

### Prompt 5 — Python authentication rule

> Read `docs/TRD.md` sections 6.3 and 6.4. Implement `backend/domains/coding_data/code_analyzer.py` and `rules.py`. Using the `ast` module, detect rule `auth_check_removed`: a function flagged `auth_gate: true` in `dependencies.yaml` whose original body returned a non-constant expression and whose proposed body returns `True` unconditionally. Produce a critical Validation with tier PROVEN and use declared `exposes` edges to list dependent endpoints.
>
> Add fixtures `auth_before.py` and tests for: the unsafe change (BLOCK with three dependent endpoints), a harmless refactor of the same function (no failure), and a change to a non-gate function.
>
> Acceptance: tests pass; the CLI handles `change_type=code_change`.

## Phase P3 — API and persistence

### Prompt 6 — Database models, persistence and API

> Read `docs/SCHEMA.md` sections 2, 3 and 6, and `docs/TRD.md` sections 14 and 16. Implement SQLAlchemy 2.x models matching the DDL, `db/session.py` driven by `DATABASE_URL` (PostgreSQL by default, SQLite fallback), and `db/seed.py` that loads the projects, resources and dependencies for `demo-code-01`. Implement routers: `GET /api/projects`, `GET /api/projects/{id}/scenarios`, `POST /api/changes/analyze`, `GET /api/analyses/{id}`, `GET /api/analyses/{id}/graph`, `GET /api/projects/{id}/history`. Persist the change, analysis, validations, findings and an audit event in one transaction, compute `graph_version` and `rules_version` hashes, and record latency. Use the uniform error format and an `X-Role` dependency.
>
> Tests with the `httpx` TestClient: analyze returns a response that validates against `AnalysisReport`; GET returns the stored report; the graph endpoint marks entry, affected and on-path edges; an invalid payload returns the error format.
>
> Acceptance: `/docs` shows all endpoints and the DROP COLUMN scenario returns BLOCK from the API. This completes P3.

## Phase P4 — Frontend core

### Prompt 7 — Frontend foundation and design system

> Read `docs/UIUX.md` sections 1, 2, 3, 5 and 11, and `docs/SCHEMA.md` section 7. In `frontend/src`, create TypeScript types in `types/` that mirror the Pydantic models, and `services/api.ts` (axios, base URL from `VITE_API_URL`, `X-Role` header, and a mock mode via `VITE_USE_MOCK` that loads JSON from `src/mocks/` shaped like the Schema doc). Build the layout (sidebar, top bar with project selector, role switcher and presenter toggle) and the design-system components: `DecisionBadge`, `ScoreGauge`, `TierBadge`, `StatusChip`, `FindingCard`, `FactorBar`, `EmptyState`, `ErrorState`, `Skeleton`. Use the dark theme tokens, Inter and JetBrains Mono, and Lucide icons as specified.
>
> Add a temporary `/styleguide` route that shows every component in all states.
>
> Acceptance: `npm run build` passes with no type errors; the styleguide renders; decisions and tiers always show icon plus label, not colour alone.

### Prompt 8 — Report screen

> Read `docs/UIUX.md` sections 4.3 and 7. Build `/analyses/:id` with the header band, a decision card (large verdict, score gauge with thresholds at 30 and 70, one-line reason, and the note that the score is a heuristic), and tabs Overview, Evidence and Remediation. Overview: ordered decision reasons, risk factor bars with tooltips, findings grouped by Confirmed, Potential and Unknown, and the explanation text. Evidence: a validations table with status chips and expandable findings showing raw evidence in monospace, with a tier filter. Remediation: the vertical timeline showing each step's re-verified decision and score, with the verification caption and an amber not-fully-verified state.
>
> Wire to the real API; keep the mock mode working. Handle loading, empty and error states, and show a coverage banner when coverage is below 95 percent.
>
> Acceptance: the DROP COLUMN analysis shows BLOCK with a REPRODUCED finding and its actual error visible. This is milestone M2.

### Prompt 9 — Impact graph and New Analysis

> Read `docs/UIUX.md` sections 4.2 and 6. Build the Impact graph tab with `@xyflow/react`: layered left-to-right layout by BFS depth, node styles by type with provenance borders (solid, dashed, dotted), the entry node highlighted with a pulsing ring, affected paths emphasised and the rest dimmed, red or orange corner markers on nodes with REPRODUCED or PROVEN findings, ghost nodes for unresolved dependencies, a legend, a side panel with node details and paths, and a Show only affected toggle. Build `/new` with the domain selector, a scenario picker that fills the form from `/api/projects/{id}/scenarios`, the payload textarea, and the progress stepper (Parse, Graph, Validate, Replay, Score, Decide). Route to the report on completion.
>
> Acceptance: a user can pick the DROP COLUMN scenario, run it and see the graph with highlighted paths.

## Phase P5 — Healthcare adapter

### Prompt 10 — Healthcare Operations adapter

> Read `docs/TRD.md` section 7 and `docs/SCHEMA.md` section 4.2. Create `backend/domains/healthcare_ops/` with `model.yaml`, `rules.yaml`, `synthetic_data.py` (fixed seed, Pandas, writes CSVs including the deliberate problems), `rules.py` (rule check functions `staff_ratio` and `required_mapping` driven by the YAML params) and `workflow_analyzer.py` implementing the `DomainAdapter` protocol. Register it. The cascade from staff shift to department coverage to ward capacity to appointment slot to daily ops report must be traversed by the generic impact engine, with provenance `modeled`. Support change types `schedule_change` and `schema_change`.
>
> Seed `demo-health-01` and add its scenarios to the scenarios endpoint. Findings are operational only; never produce clinical output.
>
> Tests: removing two Cardiology night shifts fails `min_staff_to_bed_ratio` and reaches at least three hops downstream; moving one shift with the ratio still met returns ALLOW; removing `department_id` fails the critical mapping rule.
>
> Acceptance: the same report and graph screens render the healthcare scenario without frontend changes except node icons. This is milestone M3.

## Phase P6 — Remediation and agent

### Prompt 11 — Self-verified remediation

> Read `docs/TRD.md` section 11. Implement `backend/engine/remediation.py` and `propose_remediation` in both adapters. For SQL drop column, generate the ordered steps (add replacement column, migrate consumers, re-validate, backup then drop) using the `remediation/` fixture SQL; for healthcare staffing, reassign surplus staff, re-check the ratio, submit for operator approval. For each step run the full pipeline on the post-previous-step state and store `verified_score` and `verified_decision`. Mark the plan verified only if the final step passes with all checks run. Persist to `remediation_steps` and include the steps in the report.
>
> Tests: the DROP COLUMN plan shows a decreasing score and a final ALLOW or reviewed state backed by real replay results; a plan whose last step still fails is flagged not verified.
>
> Acceptance: the report's Remediation tab shows real re-verified scores. This is milestone M4.

### Prompt 12 — Agent check endpoint and demo agent

> Read `docs/TRD.md` section 12 and `docs/SCHEMA.md` section 6.4. Implement `POST /api/agent/check` running the same pipeline and returning `proceed` (true only for ALLOW), top findings, safer alternative and report URL; store the change with `source = agent`. Create `backend/scripts/demo_agent.py`: a small script acting as a coding agent that proposes three changes (a safe index, the DROP COLUMN migration, the unsafe auth change), calls the endpoint before executing each, prints decisions with colour, executes only when `proceed` is true (simulate by printing, never touch any real database) and stops with the report link on BLOCK.
>
> Acceptance: running the script prints ALLOW for the safe change and halts on the other two with real findings.

## Phase P7 — Evaluation and dashboard

### Prompt 13 — Evaluation runner

> Read `docs/SCHEMA.md` section 5 and `docs/TRD.md` section 17. Create `backend/eval/scenarios.yaml` with all 12 scenarios (with expected decisions and ground-truth edges) and `backend/eval/run_eval.py` that runs each through the orchestrator, records decision, score and latency, computes critical-risk detection, false-block rate, dependency precision and recall, and mean latency, prints a table and writes `eval/results.json`. Add `GET /api/eval/results`. Add a Pytest that asserts every scenario matches its expected decision.
>
> If a scenario fails, do not edit expectations to make it pass. Report which rule or fixture needs fixing and fix that.
>
> Acceptance: the table prints and the test passes. This is milestone M5.

### Prompt 14 — Dashboard, History and Evaluation screens

> Read `docs/UIUX.md` sections 4.1, 4.4 and 4.5. Build the Dashboard (stat tiles, recent analyses, evaluation summary), History (filterable table), and `/eval` (stat tiles, scenario table with expected vs actual and a match tick, a Recharts bar chart of scores by scenario coloured by decision, and the caption about the suite). Wire to `GET /api/projects/{id}/history` and `GET /api/eval/results`. Include empty, loading and error states.
>
> Acceptance: dashboard and evaluation pages show real data from the backend.

## Phase P8 — Stretch (only if P0 to P7 are complete)

### Prompt 15 — LLM explanation with fallback

> Read `docs/TRD.md` section 13. Implement `services/explanation.py` with an `Explainer` interface, a `TemplateExplainer` (default, builds text from findings and tiers) and an `LLMExplainer` calling Gemini when `LLM_ENABLED=true` and `GEMINI_API_KEY` is set. The prompt must instruct the model to use only the supplied evidence, label hypotheses as potential, and never change the decision. Timeout 8 seconds; on any error fall back to the template and record `explanation_source`.
>
> Tests mock the LLM: fallback on error, decision unchanged, explanation_source recorded.

### Prompt 16 — Review and approval

> Read `docs/UIUX.md` section 4.4 and `docs/SCHEMA.md` section 6.5. Implement `POST /api/analyses/{id}/approve` and `/reject` requiring `X-Role: reviewer` (else 403), writing `approvals` and `audit_events`. Add the Review panel to the report and the `/review` queue, with a required comment and an audit timeline in History. Do not expose any update or delete route for audit events.

## Phase P9 — Polish and pitch

### Prompt 17 — Presenter mode and demo reliability

> Read `docs/UIUX.md` section 9. Implement presenter mode: a floating scenario bar with A1 Drop column, A2 Auth change, A3 Ambiguous, B1 Night shifts, B2 Department mapping and Agent demo, each loading the scenario, running the analysis and opening the report in one click; larger base font; a Reset demo data button calling `POST /api/demo/reset`; and a seed step that pre-runs three analyses so the dashboard is never empty.
>
> Then run every scenario five times and report any inconsistency or slow run (over 5 seconds). Fix the causes without changing expected decisions.
>
> Acceptance: all six presenter scenarios run from one click each, five times in a row, without errors.

### Prompt 18 — Final README and QA pass

> Update `README.md` using the accurate project state: what it does, honest limits, architecture, quickstart commands, scenarios, API summary, test and evaluation commands, and the roadmap. Make sure no document claims anything the code does not do (for example, do not call the score a probability). Run `pytest`, `python -m eval.run_eval`, `npm run build` and a manual pass over every screen. List any known issues honestly in the README.
>
> Acceptance: a new developer can follow the README from a clean clone to a running demo.

## Troubleshooting prompts

- **Agent faked a result:** *This looks hardcoded. Show me which check or graph path produces this value. Remove any fixed return values and make the output come from the engine, then add a test that would fail if it were hardcoded.*
- **Test fails:** *Do not change the test to pass. Explain the root cause, then fix the code or fixture. If the TRD is wrong, tell me before changing it.*
- **Scope creep:** *Stop. Only implement what this prompt specifies. List anything extra you added and remove it.*
- **Frontend and backend mismatch:** *Compare `types/` against `engine/models.py` and `docs/SCHEMA.md`. List mismatches and fix the frontend types.*
- **Replay breaks on some SQL:** *If SQLGlot cannot transpile, mark replay NOT_RUN with the reason and fall back to static evidence. Never swallow the error silently.*
