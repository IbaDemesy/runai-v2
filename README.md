# RunAI v2

**Plan a race trip from a vague idea, then prepare the next steps without making a booking.**

Describe the race you have in mind. RunAI uses Linkup to find sourced race options, presents a plan for your explicit confirmation, then starts three H Company browser agents in parallel to prepare registration, hotel and transport. In live mode, the agents show genuine browser frames and stop before payment or any other commitment.

## Key features

- Guided race and trip planning, with editable plan details
- Linkup-sourced race options and clear demo/replay labels for synthetic results
- Explicit plan confirmation before agent launch
- Parallel browser preparation for race registration, accommodation and transport
- Live browser frames and progress updates, with a safe handoff before commitment
- Demo, replay and live modes

## Tech stack

Python 3.12, FastAPI, Pydantic, httpx, a vanilla JavaScript/CSS frontend, and pytest.

**Status:** Early prototype; a complete live end-to-end success has not yet been demonstrated. See [HANDOFF.md](HANDOFF.md) for evidence and remaining work.

## Project structure

- `runai/guide/` — conversation flow, intent parsing and trip-plan state.
- `runai/discovery/` — sourced race discovery and candidate normalization.
- `runai/agents/` — registration, hotel and transport task builders, site policy and browser client.
- `static/` — browser interface HTML, JavaScript and CSS.
- `tests/` — unit, API, journey, safety and frontend checks.
- `docs/` — product policy and feedback alongside evaluation and engineering records.

For a map of product documentation and internal development records, see [docs/README.md](docs/README.md).

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
The owner approved read/prepare-only H runs with **P14 runner-profile prefill**:
ask once, type only supplied participant/guest/passenger fields, and allow
intermediate Continue/Next only to reach the next page, never to commit.
The profile lives only in process memory until mission deletion/end; never
store it in the repo, logs, evidence, committed screenshots or eval reports.
Use clearly fake identities such as 'Test Runner' in evaluations.

No site is excluded for terms-of-service reasons (including Accor/Booking and
major transport sites); use allowed_owner_rule in docs/site-policy.json and
review applicable adapter scope. Unknown/expired reviews still block before H.
Never pay/book, create accounts/log in, accept terms/medical consent, submit
final forms or bypass captchas. Dismiss cookies without consenting; report any
earlier prohibited boundary honestly. robots.txt is not authorization.

Site frames are in_session_only, never published or committed. P13
checkpoint_unverified stays blocked/reached-to-verify, not verified READY.
No real contact data, secrets, tokens or private H session URLs in code,
fixtures, logs or evidence. Hand off genuine safe public links only.

## Checks and contribution loop
```sh
uv sync --frozen
uv run ruff check . && uv run pytest -q
```
CI tests never call live providers. Live verification requires separate dated,
scrubbed observed evidence. See [AGENTS.md](AGENTS.md) for scoped branch/PR and
safety rules, [PLAN.md](PLAN.md) for the architecture/evaluation set,
[CONTRACTS.md](CONTRACTS.md) for API contracts, and
[docs/tickets/index.json](docs/tickets/index.json) for the current round-7 queue,
validated by tests/test_r7_scope_contract.py. R6 and earlier tickets are history.
Keep main green; R7-01..R7-05 merge in any order. R7-01 rebases last for visible
integrated acceptance after siblings merge: at least Milan, Berlin and one other
case, using fake profiles. This is planned, not completed evidence. Only R7-01
edits shared docs/queue/contracts (P1–P14).

H's organization quota is three sessions: final acceptance runs **one mission
at a time**, with its three agents parallel. A queued browser displays honest
waiting feedback; queue wait is bounded to eight minutes and included in the
15-minute total agent wall-clock cap alongside retries and alternatives. No site frames or private H URLs are committed.

`render.yaml` is an unverified deployment blueprint, not a deployed URL.
