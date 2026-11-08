# Handoff — round one

## Current implementation/evidence boundary (2026-11-08)
- Round-one baseline: typed FastAPI missions, explicitly confirmed three-runner
  synthetic demo/replay, an in-memory store, polling UI and a synthetic trace.
  The bootstrap implementation still uses fixed sample framing and live stubs;
  those are limitations to replace, not the product's intended scope.
- No end-to-end live success, prepared real checkout, real live-frame UI,
  deployment or browser visual acceptance is established by this docs-only PR.
  Official homepage links in the synthetic trace are not prepared sessions.
- Target: generic race proposals with official Linkup dates/distances, natural
  FR/EN guided chat, editable defaults, explicit confirmation, then registration,
  hotel and transport H agents live in parallel with all three visible on-page.
  Milan is one evaluation case alongside spring Italy marathons, Swiss summer
  trails and the Lisbon half; dates must be sourced, never assumed.
- Owner's first priority is beautiful Strava-inspired UX. Read
  [docs/feedback/owner.md](docs/feedback/owner.md) before product/design decisions.
- R1-08 updates documentation only. R1-01 owns CONTRACTS.md and core integration;
  component/interface details and actual evidence live in each ticket's handoff.

## Round-one queue
The exact allowed files, dependencies and merge stages are in
[docs/tickets/index.json](docs/tickets/index.json); each id below links its scope.

| Ticket | Responsibility | Merge stage |
| --- | --- | --- |
| [R1-02](docs/tickets/R1-02.md) | Shared H client, genuine live frames, scrubbing and safety | 1, independent |
| [R1-03](docs/tickets/R1-03.md) | Real Linkup race discovery and official dates/distances | 1, independent |
| [R1-04](docs/tickets/R1-04.md) | FR/EN guided proposing engine, defaults and chips | 1, independent |
| [R1-05](docs/tickets/R1-05.md) | Generic official registration task builder | 1, independent |
| [R1-06](docs/tickets/R1-06.md) | Generic hotel/transport task builders and site choices | 1, independent |
| [R1-08](docs/tickets/R1-08.md) | Generic product/process docs and queue (this change) | 1, independent |
| [R1-01](docs/tickets/R1-01.md) | Core API, dependency injection, parallel execution, frames/replay | 2, after all stage 1 |
| [R1-07](docs/tickets/R1-07.md) | Premium responsive chat, plan cards and three live panels | 3, after R1-01 |

T01..T12 are superseded; they grant no implementation scope. Independent
components coordinate interfaces through docs/handoff/<id>.md and lazy optional
imports; they do not edit shared core files. Use one branch/PR per ticket,
squash-merge only green CI, never push directly to main.

## Checks and evidence
- Python 3.12: `uv sync --frozen && uv run ruff check . && uv run pytest -q`
  passed: `All checks passed!` and `7 passed, 1 warning in 0.79s`.
  The warning is the existing Starlette/httpx TestClient deprecation.
- Queue JSON, matching ticket scopes, non-overlapping ownership, dependency/merge
  ordering, legacy superseded notices and names-only environment example passed
  local validation. The requested obsolete-rule scan returned no matches.
- Full pasted check output and R1-08 evidence/blockers/next steps are in
  [docs/handoff/R1-08.md](docs/handoff/R1-08.md). No live provider calls were made
  for this documentation-only change; CI is offline, never live evidence.

## Safety and next
Owner approval covers read/prepare-only H runs, not payment or other side effects.
Review site authorization and prefer no-captcha sites whose terms permit agents;
document the choice. Never pay, book, create accounts, accept terms/consent or
medical declarations, submit forms, enter personal data or bypass captchas.
Only dismiss cookie banners without consent. Stop at the earliest boundary and
report blockers honestly. Never expose secrets, tokens, private H URLs, emails
or personal data in code/fixtures/logs/evidence. Demo/replay remain synthetic;
missing live keys/modules must fail explicitly, not fall back to fake success.

Next: land the stage-one component PRs, integrate R1-01, then R1-07. Evaluate
the four cases with sourced race dates and actual scrubbed live evidence. A
successful case requires all three agents to reach pre-payment live in parallel,
visible on the page after the assistant's proposal and user confirmation. Earlier
mandatory safety stops are blockers, not success. Turn observed failures into
focused scoped follow-up tickets; do not infer readiness from synthetic tests.
