# ProofBeforeAction

**An evidence-backed, pre-execution consequence analysis engine.**

> *Understand the consequences before you commit to the action.*

Built for VIT CODE APEX 3.0 (Open Innovation).

**Status:** prototype in development. Sections marked *(planned)* are not built yet. Update this file as features land.

---

## What it does

AI coding agents, automated data pipelines and digital healthcare workflows change interconnected systems. A change that looks correct in isolation can break things downstream.

ProofBeforeAction takes a **proposed change** (a SQL migration, a code change, or a healthcare operational change), and answers three questions:

1. **What could this break?** It maps the change onto a dependency graph and finds the blast radius.
2. **How do we know?** It replays SQL migrations on a disposable in-memory copy and runs dependent queries, and it grades every finding by evidence strength.
3. **What should we do instead?** It recommends a safer sequence and re-verifies that sequence with the same engine.

The result is one of: `ALLOW`, `HUMAN_REVIEW` or `BLOCK`.

## What makes it different

- **Proof by replay.** Failures are reproduced, not just inferred. Example: dropping a column fails against a dependent view with a real SQLite error.
- **Evidence tiers.** Every finding is `REPRODUCED`, `PROVEN`, `INFERRED` or `UNKNOWN`.
- **Self-verified remediation.** The engine re-runs itself on its own recommended steps, for example `BLOCK (86) -> ... -> ALLOW (18)`.
- **Explicit uncertainty.** Unresolved dependencies and checks that never ran force human review.
- **One engine, two domains.** Coding & Data Engineering and Healthcare Operations (synthetic data, operational workflows only).
- **Agent-callable.** An AI agent can ask `POST /api/agent/check` before executing a change.

## Honest limits

- The risk score is a **transparent heuristic, not a probability** of failure.
- Replay targets SQLite-compatible SQL. If SQL cannot be transpiled, replay is marked `NOT_RUN` and findings fall back to static evidence.
- Python analysis covers a narrow set of supported patterns.
- The healthcare environment is a **modeled, synthetic** system. It makes no clinical decisions.
- Authentication is a demo role switch (`X-Role` header), not real auth.
- The evaluation suite is small (12 labeled scenarios). Results describe that suite, not general accuracy.
- The system analyzes and recommends. It never executes changes against real systems.

## Architecture

```
React UI  /  AI agent
        |
        v
FastAPI REST layer
        |
        v
Domain Adapter  (coding_data | healthcare_ops)
        |
        v
Dependency Graph + Impact Analysis   (NetworkX)
        |
        v
Validation Engine  (rules, SQL replay, capacity checks)   PASSED | FAILED | NOT_RUN
        |
        v
Risk Scoring  ->  Policy & Decision Engine  ->  ALLOW | HUMAN_REVIEW | BLOCK
        |
        +--> Remediation verifier (re-runs the engine on each safe step)
        +--> Explanation (template, optional LLM)
        |
        v
Evidence Report + Impact Graph  ->  PostgreSQL
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS, @xyflow/react, Recharts, Lucide |
| Backend | FastAPI, Pydantic v2, Python 3.11+ |
| Graph | NetworkX |
| SQL | SQLGlot, in-memory SQLite for replay |
| Data | PostgreSQL + SQLAlchemy (SQLite fallback), Pandas |
| Tests | Pytest |

## Quickstart

### Prerequisites

Python 3.11+, Node.js 18+, Docker (for PostgreSQL), SQLite 3.35+.

### 1. Clone and configure

```bash
git clone <repo-url> proofbeforeaction
cd proofbeforeaction
cp .env.example .env
```

### 2. Database

```bash
docker compose up -d
```

To use SQLite instead, set `DATABASE_URL=sqlite:///./pba.db` in `.env`.

### 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m db.seed
uvicorn main:app --reload --port 8000
```

Check `http://localhost:8000/health` and the API docs at `http://localhost:8000/docs`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL or SQLite connection string |
| `CORS_ORIGIN` | Frontend origin, default `http://localhost:5173` |
| `LLM_ENABLED` | `true` to enable the optional LLM explanation |
| `GEMINI_API_KEY` | Only needed if `LLM_ENABLED=true` |
| `VITE_API_URL` | Backend URL for the frontend |
| `VITE_USE_MOCK` | `true` to run the UI on mock JSON |

## Demo scenarios

| ID | Domain | Scenario | Expected |
|---|---|---|---|
| A1 | Coding & Data | `DROP COLUMN patients.patient_id` with a dependent view, queries and pipeline | BLOCK, reproduced error |
| A2 | Coding & Data | Auth function returns `True`; three endpoints depend on it | BLOCK |
| A3 | Coding & Data | Pipeline builds SQL dynamically; dependency unresolved | HUMAN_REVIEW |
| B1 | Healthcare Ops | Remove two Cardiology night shifts (staffing ratio breaks) | HUMAN_REVIEW or BLOCK |
| B2 | Healthcare Ops | Remove `department_id` from appointments | HUMAN_REVIEW or BLOCK |

Run the demo agent *(planned)*:

```bash
cd backend
python -m scripts.demo_agent
```

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/projects` | List demo projects |
| POST | `/api/changes/analyze` | Submit and analyze a change |
| GET | `/api/analyses/{id}` | Full report |
| GET | `/api/analyses/{id}/graph` | Impact graph |
| POST | `/api/agent/check` | Agent pre-execution check *(planned)* |
| GET | `/api/eval/results` | Evaluation results *(planned)* |

Full contracts are in `docs/SCHEMA.md`.

## Tests and evaluation

```bash
cd backend
pytest                      # unit, replay, scenario and API tests
python -m eval.run_eval     # 12-scenario evaluation, writes eval/results.json
```

Metrics reported: critical-risk detection, false-block rate, dependency precision and recall, mean analysis latency.

## Project structure

```
proofbeforeaction/
├── README.md
├── docs/              PRD, TRD, UI/UX, schema, roadmap, prompt pack
├── .agent/rules/      project rules for the coding agent
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── api/           routers
│   ├── engine/        models, graph, impact, findings, risk, decision, remediation
│   ├── domains/       coding_data/, healthcare_ops/
│   ├── services/      explanation, audit
│   ├── db/            models, session, seed
│   ├── fixtures/      demo-code-01/, demo-health-01/
│   ├── eval/          scenarios.yaml, run_eval.py
│   └── tests/
└── frontend/
    └── src/           components, pages, services, types
```

## Documentation

| Document | Purpose |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/TRD.md` | Technical requirements (source of truth for implementation) |
| `docs/UIUX.md` | Design system and screens |
| `docs/SCHEMA.md` | Database, fixtures and API contract |
| `docs/ROADMAP.md` | Phases, milestones and working agreement |
| `docs/PROMPTS.md` | Prompt pack for building with Antigravity |

## Roadmap

- Real authentication and role-based access control
- Container sandbox for running tests on untrusted code
- Tree-sitter for JavaScript and TypeScript, OpenAPI contract checks
- GitHub PR and CI integration, MCP tool for coding agents
- Config-defined domain packs
- Backtesting on real repository history
- Calibrated risk scoring from real incident data

## Safety statement

ProofBeforeAction is a decision-support prototype. It uses synthetic data only, makes no clinical decisions, and does not execute changes on real systems. Healthcare output is limited to operational workflow recommendations for an authorized human operator.

## Team

Add team members, roles and contact details here.

## License

Add a license before publishing.
