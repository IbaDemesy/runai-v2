# Handoff

## Bootstrap
- Fresh repository; old RunAI consulted only for domain/evidence boundaries.
- Typed FastAPI journey, synthetic demo and replay, parallel runners, polling UI.
- Framing extraction, all live integrations, voice UI, deployment remain tickets.
- Never describe the synthetic homepage handoffs as prepared bookings.
- Target race date is an assumption pending T03 verification.
- Validation: `ruff check . && pytest -q` — All checks passed; 7 passed in 0.57s.
- One dependency warning: Starlette deprecates its httpx TestClient integration;
  no test failures. No live run, deployment, or browser visual verification performed.
- Next: T02 after bootstrap review. One branch and PR per ticket.
- GitHub repository creation/push and actual agent loop launch belong to the lead.

## T01 — Review skeleton and frozen safety contract
- Reviewed bootstrap against PLAN.md/CONTRACTS.md; synthetic journey kept green in demo and replay.
- Fix: a replay runner that cannot load (missing/invalid trace) now yields three visible
  `failed` StepResults (mission status `failed`, payment_executed false) instead of an HTTP 500,
  per "Runner failures produce failed StepResults".
- Fix: ReplayRunner now enforces replay `schema_version` 1 (CONTRACTS.md).
- Tests added (tests/test_units.py): valid trace (normal), empty results (empty),
  wrong schema_version / non-synthetic provenance and broken replay at confirm (error).
- Checks: `uv sync --frozen && uv run ruff check . && uv run pytest -q`
  → All checks passed!; 9 passed, 1 warning (Starlette httpx TestClient deprecation).
- Evidence: n/a — offline synthetic only; no live run, deployment or browser verification.
- Blockers: none. Unknown `RUNAI_MODE` env values still raise a server error (out of scope).
- Next: T02.
