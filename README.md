# RunAI v2

**Dis-moi ton envie de course, je prépare ton déplacement.**

A guided race travel assistant: describe a wish like « un marathon au printemps
en Italie », « un trail en Suisse cet été » or « le semi de Lisbonne ». RunAI's
target is to propose real races and official dates through Linkup, suggest
editable travel defaults, and ask one focused question at a time. You do not
need to know the race date.

After explicit plan confirmation, three H Company browser agents prepare race
registration, hotel and transport **in parallel**, with genuine streamed screenshots and short friendly status lines, then hand off before payment or any earlier
consent/commitment boundary. A premium, responsive Strava-inspired chat with
chips, plan cards and three agent panels is the design priority.
The chat should feel natural in French and English, with streaming-like replies,
a bottom composer and one-click defaults or free-text corrections.

**Status:** round 2 recorded 0/5 visible live successes
([docs/eval/round-2.md](docs/eval/round-2.md)). Round 3 (R3-01..R3-05)
targets reviewed adapter coverage, coherent origins, honest H outcomes, fresh
frames and Strava-grade FR/EN UX. Read [HANDOFF.md](HANDOFF.md) for the evidence
boundary. R3-05 owns core/shared docs and final acceptance after the other four
merge. Milan is one evaluation case only.

## Run locally (Python 3.12)
```sh
uv sync --frozen --python 3.12
RUNAI_MODE=demo uv run uvicorn runai.app:app --reload
# Open http://localhost:8000
```

Choose the mode in the page when available, or restart with a server default:
```sh
RUNAI_MODE=replay uv run uvicorn runai.app:app --reload
RUNAI_MODE=live uv run uvicorn runai.app:app --reload
```

| Mode | Behavior | Keys |
| --- | --- | --- |
| `demo` | Clearly labelled synthetic candidates and simulated preparation | None |
| `replay` | Clearly labelled recorded synthetic trace/frames; unavailable frames stay unavailable | None |
| `live` | Real Linkup discovery and policy-gated, screenshot-only H browser preparation | `LINKUP_API_KEY`, `HAI_API_KEY` |

Missing live keys/modules must produce an explicit 501/unavailable response;
there is no silent fake-success fallback. A synthetic `ready_for_payment` state
or official homepage link does not mean a real cart/session was prepared. Replay
is not proof of a live run. The UI calls the API with `background=true` and
polls `discovery_progress` events, so feedback is immediate during searches.

## Environment
[.env.example](.env.example) lists names only: `RUNAI_MODE`, `HAI_API_KEY`,
`LINKUP_API_KEY`, `GLADIA_API_KEY` (optional voice, when implemented). Supported
mode values are `demo`, `replay`, `live`; the default is `demo`. Export variables
through your shell or secret manager before starting the server. There is no
automatic `.env` loader. Never print keys or commit secret values.

## Safety
The owner approved read/prepare-only live H runs; applicable site authorization
must still be reviewed. Prefer sites without captchas and whose terms permit
agents. Never pay, book, create accounts, accept terms/consent or medical
declarations, submit forms, enter personal data or bypass captchas. Only dismiss
cookie banners without accepting consent. Stop earlier than payment whenever
any such boundary appears and report the blocker honestly.

No secrets, tokens, private H session URLs, emails or other personal data belong
in code, fixtures, logs or evidence. Hand off safe public links only; do not
represent a generic homepage as a prepared checkout.

## Checks and contribution loop
```sh
uv sync --frozen
uv run ruff check . && uv run pytest -q
```
CI tests never call live providers. Live verification requires separate dated,
scrubbed observed evidence. See [AGENTS.md](AGENTS.md) for scoped branch/PR and
safety rules, [PLAN.md](PLAN.md) for the architecture/evaluation set,
[CONTRACTS.md](CONTRACTS.md) for API contracts, and
[docs/tickets/index.json](docs/tickets/index.json) for the current round-3 queue.
R2, R1 and T01..T12 tickets are history. Keep main green; R3-01..R3-04 merge
in any order, then R3-05 runs final live acceptance on a rebased branch in
docs/eval/round-3-acceptance.md.

`render.yaml` is an unverified deployment blueprint, not a deployed URL.
