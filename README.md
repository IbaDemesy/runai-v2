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

**Status:** round 5 scored 41, with 0/5 visible live successes and design 7.5/10
([docs/eval/round-5.md](docs/eval/round-5.md)). Round 6 (R6-01..R6-05)
targets IHG verification/P13 reached-to-verify states, honest frame timestamps
and heartbeats, transport alternatives, no-loop sourced guide recovery,
registration boundaries and >=8.5/10 Strava-grade UI. R6-01 owns core integration
and shared docs. R6-03 is the actual registration ticket merged in PR #41;
its live-stop acceptance remains unmet. R6-05 UI merged in PR #40.
Only R6-02 transport/R6-04 guide specs are inferred; planner may amend.
R6-01 hotel-only smokes returned READY in three cities, not a visible three-agent
acceptance. No complete live success is claimed. Read [HANDOFF.md](HANDOFF.md)
for the evidence boundary. Milan is one evaluation case only.

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
Accor/prohibited entries stay denied; unknown/expired reviews block before H.
robots.txt is not authorization. H/site frames are in_session_only, never
published or committed. P13 checkpoint_unverified means blocked/reached-to-verify,
not verified READY; a public checkpoint handoff does not change that status.

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
[docs/tickets/index.json](docs/tickets/index.json) for the current round-6 queue,
validated by tests/test_r6_scope_contract.py. R5/R4/R3/R2/R1/T tickets are history.
Keep main green; R6-01..R6-05 merge in any order, then R6-01 coordinates visible
integrated live acceptance on a rebased branch, recording within its allowed
evidence/handoff files. Only R6-01 edits shared docs/queue/contracts (P1–P13).

H's organization quota is three sessions: final acceptance runs **one mission
at a time**, with its three agents parallel. A queued browser displays honest
waiting feedback and does not consume the ten-minute running budget; queue
wait is bounded to eight minutes. No site frames or private H URLs are committed.

`render.yaml` is an unverified deployment blueprint, not a deployed URL.
