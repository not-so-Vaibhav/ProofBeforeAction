# ProofBeforeAction — Build Roadmap & Working Agreement

Prototype plan for building with Antigravity · Companion to PRD, TRD, UI/UX, Schema and Prompt Pack

## 1. What we are building

The v2 blueprint plus three novelty features that make the name literal:

1. **Proof by replay.** Apply the proposed SQL migration to a disposable in-memory copy and run the dependent queries. Failures are *reproduced*, not guessed.
2. **Evidence tiers.** Every finding is graded `REPRODUCED`, `PROVEN`, `INFERRED` or `UNKNOWN`.
3. **Self-verified remediation.** The engine re-runs itself on its own recommended safe sequence and shows `BLOCK (86) → step 1 ALLOW (18)`.

Two domains (Coding & Data, Healthcare Operations) share one engine. Output is `ALLOW`, `HUMAN_REVIEW` or `BLOCK`.

## 2. Assumptions

- The prototype is built by a small team using Antigravity as the main coding environment.
- The plan fits a 24-hour live build, but is organized in phases so it also works over several days.
- Stack is frozen: React + Vite + TypeScript + Tailwind, FastAPI, NetworkX, SQLGlot, SQLAlchemy, PostgreSQL (SQLite fallback), Pytest.
- The LLM layer and approval flow are stretch items.

## 3. Build principle: vertical slice first

Do not build every module before something runs. The first target is one thin path that works end to end:

> SQL migration → graph → replay → decision → report API → report screen

Only after that slice works do we add the healthcare domain, remediation, evaluation and polish.

## 4. Phases

| Phase | Goal | Output | Definition of done | Est. |
|---|---|---|---|---|
| P0 | Foundation and spec lock | Repo, `/docs` specs, agent rules, health endpoint, Vite app talking to FastAPI | `GET /health` works from the frontend; docs committed | 1–2 h |
| P1 | Engine core | Models, graph builder, BFS impact analysis, finding classes, decision function | Unit tests pass for graph traversal and decision precedence | 3 h |
| P2 | Coding & Data slice | SQLGlot analyzer, replay engine, evidence tiers, Python AST auth rule | CLI prints BLOCK for the DROP COLUMN scenario with a reproduced error | 3–4 h |
| P3 | API and persistence | `/api/changes/analyze`, report and graph endpoints, DB models, seed script | Analysis stored and retrievable by id | 2 h |
| P4 | Frontend core | Design system, Report screen, Impact Graph, New Analysis form | First BLOCK visible in the browser | 4 h |
| P5 | Healthcare adapter | Synthetic data, YAML domain model, rule engine, cascade scenario B1/B2 | Healthcare scenario returns real findings through the same engine | 3 h |
| P6 | Remediation and agent | Remediation verifier, `/api/agent/check`, agent demo script | BLOCK → ALLOW trajectory shown; agent script halts on BLOCK | 2–3 h |
| P7 | Evaluation and dashboard | 12-scenario suite, metrics script, Dashboard and History | Results table generated from real runs | 2–3 h |
| P8 | Stretch | LLM explanation with template fallback, approve/reject flow, charts | Only started if P0–P7 are done | 2 h |
| P9 | Polish and pitch | Seeded demo data, presenter mode, rehearsal, backup video | Full demo runs three times without a failure | 2–3 h |

## 5. Milestone gates

| Gate | Proof it is real |
|---|---|
| M1 | CLI outputs BLOCK with a reproduced `no such column` error |
| M2 | The same result is visible in the browser report screen |
| M3 | Healthcare cascade scenario returns a real failed rule through the same engine |
| M4 | Remediation re-analysis shows a falling score |
| M5 | Evaluation table is generated from the test suite, not typed by hand |

Do not start the next phase until the current gate is green.

## 6. Parallel tracks

| Track | Owner area | Directories | Can run in parallel with |
|---|---|---|---|
| A: Engine and API | Backend | `backend/` | B and C after P0 |
| B: Frontend | UI | `frontend/` | A, once the API contract in the Schema doc is fixed |
| C: Data and pitch | Fixtures, tests, deck | `backend/fixtures`, `backend/tests`, `docs/` | A and B |

Track B can start against mocked JSON that follows the Schema doc, then switch to the real API at the end of P3.

## 7. Working agreement for Antigravity

- **Specs live in the repo.** Keep `PRD.md`, `TRD.md`, `UIUX.md`, `SCHEMA.md`, `ROADMAP.md` in `/docs`. Every prompt tells the agent which sections to read.
- **Add a rules file** so every agent session starts with the same constraints. As far as I know Antigravity reads workspace rules from an `.agent/rules` folder; check the current Antigravity docs for the exact location. Use the rules text in Prompt 0.
- **One prompt, one commit.** Run the tests, review the diff and the agent's plan, then commit before the next prompt.
- **Plan before code for engine work.** Use the planning mode for P1, P2, P5 and P6, and the faster mode for UI tweaks.
- **Parallelize only across separate directories.** Never let two agents edit the same files.
- **No hardcoded results.** Any API response must come from real analysis. Reject agent output that fakes data.
- **Tests are the contract.** Each engine prompt includes the tests it must pass.
- **Verify, do not trust.** Run the app yourself after each prompt before merging.

## 8. Cut order if time slips

1. LLM explanation (use templated text)
2. Approve/reject flow
3. Recharts
4. Dashboard polish and history
5. Python AST rule (keep SQL replay)

Never cut: the engine, replay, the report screen, one coding scenario, one healthcare scenario, the evaluation table.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Replay fails on Postgres-only syntax | Keep fixtures SQLite-compatible; if SQLGlot cannot transpile, mark replay `NOT_RUN` and fall back to `PROVEN`/`INFERRED` |
| Agent invents results | Rules file bans hardcoding; tests assert real evidence fields |
| Frontend/backend drift | API contract frozen in the Schema doc; shared TypeScript types mirror Pydantic models |
| Scope creep | Cut order above; phase gates |
| Demo failure | Seed script, presenter mode, recorded backup video |
| Healthcare looks like a re-skin | Cascade scenario that requires multi-hop traversal |

## 10. Target repository layout

```
proofbeforeaction/
├── README.md
├── docs/            PRD.md TRD.md UIUX.md SCHEMA.md ROADMAP.md PROMPTS.md
├── .agent/rules/    project rules for Antigravity
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── api/         projects.py changes.py analyses.py agent.py
│   ├── engine/      models.py graph.py impact.py findings.py risk.py decision.py remediation.py
│   ├── domains/
│   │   ├── coding_data/   sql_analyzer.py replay.py code_analyzer.py rules.py
│   │   └── healthcare_ops/ model.yaml rules.py synthetic_data.py
│   ├── services/    explanation.py audit.py
│   ├── db/          models.py session.py seed.py
│   ├── fixtures/    demo-code-01/ demo-health-01/
│   ├── eval/        scenarios.yaml run_eval.py
│   └── tests/
└── frontend/
    └── src/ components/ pages/ services/ types/ App.tsx main.tsx
```
