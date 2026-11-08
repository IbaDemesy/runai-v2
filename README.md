# RunAI v2

**Dis-moi ta course, je prépare tout le déplacement.**

Jury prototype: one confirmed plan, three parallel preparation agents, human handoff.
Current build is **synthetic only**, not a working live booking service.
Target: Milano Marathon · Paris–Milano · 3–5 April 2027 · Accor · Trenitalia.

```sh
uv sync --frozen --python 3.12
uv run uvicorn runai.app:app --reload
# Open http://localhost:8000
uv run ruff check . && uv run pytest -q
```

Use demo or replay in the page; both require no keys and clearly show simulation.
Describe your race, validate the displayed fixed framing, explicitly confirm,
then open the three official handoff links. No real cart has been created.
live returns an explicit not-implemented error; .env.example lists future keys.
Environment variables must be exported; no automatic .env loader is installed.

See PLAN.md for frozen scope, CONTRACTS.md for API, AGENTS.md for coding rules,
docs/tickets/index.json for the implementation queue, HANDOFF.md for status.
render.yaml is an unverified deployment blueprint, not a deployed URL.
No provider live runs or live-success metrics have been recorded here.
