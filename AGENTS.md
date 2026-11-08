# Coding agents

- The frozen journey in PLAN.md is the spine. No extra product features.
- One ticket = one branch = one PR. Bootstrap is the initial main commit only.
- Read CONTRACTS.md and the ticket first. Touch only its allowed files.
- If another file is required, stop and request a ticket scope amendment.
- Never invent provider results, tests, recordings, or live evidence.
- Label all synthetic demo/replay data visibly; replay is not proof of live success.
- Stop before payment, booking, consent, medical declarations, or submission.
- Never bypass captchas, create accounts, accept terms, or spend money.
- No secrets, contact details, private session URLs, or payment details in fixtures/logs.
- Every behavior change needs normal, empty, and error coverage where applicable.
- Run `uv sync --frozen`, then `uv run ruff check . && uv run pytest -q`.
- Start: `uv run uvicorn runai.app:app --reload` and open http://localhost:8000.
- Modes: `RUNAI_MODE=demo|replay|live`; API mode may override the server default.
- demo uses fakes; replay plays the checked-in synthetic JSON; neither needs keys.
- live is deliberately unavailable (501), not a fallback to fake success.
- Merge only with green CI, including tests/test_journey_e2e.py.
- Keep PRs small; review evidence and payment guardrails before merge.
- Update HANDOFF.md before stopping; parallel tickets instead use their scoped
  docs/handoff/Txx.md with changes, checks, evidence, blockers and next ticket.
- No live runs without explicit approval and applicable site authorization review.
