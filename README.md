# ProofBeforeAction

**An evidence-backed, pre-execution consequence analysis engine.**

> *Understand the consequences before you commit to the action.*

Built for VIT CODE APEX 3.0 (Open Innovation).

---

## What It Does

ProofBeforeAction takes a proposed change (SQL migration, code change, or healthcare operational change) and answers three critical questions before execution:

1. **What could this break?** Maps changes onto a dependency graph (NetworkX) and computes blast radius.
2. **How do we know?** Replays migrations in-memory on disposable SQLite instances, runs dependent queries, and tags findings with evidence tiers (`REPRODUCED`, `PROVEN`, `INFERRED`, `UNKNOWN`).
3. **What should we do instead?** Recommends a safer migration sequence and re-verifies every step through the engine.

Decisions: `ALLOW`, `HUMAN_REVIEW`, or `BLOCK`.

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional, for PostgreSQL; SQLite fallback supported)

### 1. Database (optional PostgreSQL)
```bash
docker compose up -d
```
Or use SQLite fallback by setting `DATABASE_URL=sqlite:///./pba.db` in `.env`.

### 2. Backend Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run backend
cd backend
uvicorn main:app --reload --port 8000
```
Health endpoint: [http://localhost:8000/health](http://localhost:8000/health)  
API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Vite dev server: [http://localhost:5173](http://localhost:5173)

### 4. Running Tests
```bash
pytest backend/tests
```

---

## Documentation

Full architectural specifications and contracts are in `docs/`:
- [PRD.md](docs/PRD.md) — Product Requirements Document
- [TRD.md](docs/TRD.md) — Technical Requirements Document
- [SCHEMA.md](docs/SCHEMA.md) — Database Schema, Fixtures & API Contracts
- [UIUX.md](docs/UIUX.md) — Design System & Interaction Specs
- [ROADMAP.md](docs/ROADMAP.md) — Implementation Plan & Working Agreement
