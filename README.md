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

**Status:** round 6 scored **38/100, 0/5 visible live successes**, design 8/10
([docs/eval/round-6.md](docs/eval/round-6.md)). The current R7 queue targets
transport coverage, verified safe checkpoints, owner-approved private profile
prefill, fewer questions and >=9/10 design. R7-01 owns core + integration
acceptance/shared docs; R7-02 transport + generic policy/base registry;
R7-03 hotel + registration and their shards; R7-04 guide/discovery;
R7-05 UI/profile card. No complete live success is claimed. Read
[HANDOFF.md](HANDOFF.md) for evidence and remaining integration work.

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
