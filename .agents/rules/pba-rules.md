# ProofBeforeAction — Project Rules for Antigravity

These rules govern all work in the ProofBeforeAction repository. Every agent session and developer must follow these rules.

## Core Rules

1. **Source of Truth**: The `docs/TRD.md` and `docs/SCHEMA.md` are the source of truth. If code disagrees with these documents, fix the code or update the documents in the exact same commit if a contract must change.
2. **No Hardcoded or Faked Results**: Never hardcode analysis results. Every finding, score, and decision must come from a real check, SQLite replay, or graph path.
3. **LLM Boundary**: The LLM is an explanation layer only (template fallback default). The LLM never influences the decision or risk score.
4. **Execution Safety**: Never execute user-supplied code or SQL outside the disposable, in-memory SQLite replay. Never connect to or execute against real production systems.
5. **Typing & Testing**: All Python code must have type hints. Every engine module must have accompanying Pytest unit tests.
6. **Frontend Model Parity**: Frontend TypeScript types in `frontend/src/types/` must mirror Pydantic models in `backend/engine/models.py` exactly. The frontend never reimplements scoring or decision logic.
7. **Small, Explained Changes**: Keep changes focused and small, and explain rationale clearly in commits and diffs.
8. **Contract Stability**: Always ask before changing a documented contract or API specification.
9. **Ask Before Pushing**: ALWAYS ask the user for explicit confirmation before pushing any changes to remote/GitHub (`https://github.com/not-so-Vaibhav/ProofBeforeAction`). Never run `git push` without user permission.
