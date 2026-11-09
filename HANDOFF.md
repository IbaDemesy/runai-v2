# Handoff — round six

## Current implementation/evidence boundary (2026-11-09)
Round 5 recorded **score 41, 0/5 visible live successes, design 7.5/10**.
Read [docs/eval/round-5.md](docs/eval/round-5.md) for observed evidence, not
a claim of generic live readiness. IHG reached select-enhance-stay but failed
verification; Vueling returned zero frames; Germany/Portugal recovery looped.

R6-01 implemented IHG verification/date fixes, P13 checkpoint_unverified,
friendly frame-gap heartbeats, browser-error diagnosis and validated observed_at.
Sequential hotel-only real smokes reached READY in Milan, Zurich and Lisbon
(retry). Lisbon's first attempt retained a safe framed checkpoint but failed
handoff_observed; its original differing query was not retained, so the deeper
cause remains unresolved. No verifier was weakened. Vueling chromewebdata and
plain-homepage failure were observed; provider ordering was not changed here.
See [hotel evidence](docs/evidence/hotel.md), [runtime evidence](docs/evidence/h-client.md)
and [R6-01 handoff](docs/handoff/R6-01.md). These backend-only smokes do not
establish visible integrated three-agent success.

Owner feedback (a)–(d), Strava-first design, adversarial requirements, Accor
denial and the exact live-success definition remain top priority in
[docs/feedback/owner.md](docs/feedback/owner.md) (Round 6 section first).
Synthetic tests/footage are not proof of live success.

## Round-six queue
Exact file ownership is authoritative in [index.json](docs/tickets/index.json).

| Ticket | Scope | Merge |
| --- | --- | --- |
| R6-01 | Core integration + hotel, P13, heartbeats/timestamps, browser diagnostics, shared docs | Any order |
| R6-02 | Transport ordering/working rail-air alternatives; generic policy/base registry | Any order |
| R6-03 | Actual registration: Stoos checkpoint, DE/PT/ES/NL alternatives, sold-out detection, verified live-stop target | Merged PR #41 |
| R6-04 | Inferred guide/discovery dead ends, unverified dates, chip ping-pong, >=130 adversarial cases | Any order |
| R6-05 | >=8.5/10 Strava UI: SVG flags, energetic opening, honest live/P13, pills/thread/mobile | Any order |

Only R6-02 transport and R6-04 guide/discovery are inferred from round-5
evaluation; planner may amend. R6-03 is the actual registration ticket from
merged PR #41, with exactly five files and docs/handoff/R6-03.md. R6-05 UI
merged in PR #40. Neither merge establishes complete visible live success.
R6-03 ran no H live smokes (missing keys); Stoos checkpoint/availability work
is offline/read-only evidence. Frankfurt's scrub restriction and Portugal's
no-open-permitted-option remain blockers. See its handoff, not an inferred spec.
The legacy docs/site-policy.json, loader and policy tests belong only R6-02;
registration owns its existing fragment, transport a new transport fragment,
hotel its allowed hotel fragment. Duplicate IDs across fragments/base fail closed.
Any needed legacy-base change must be coordinated through R6-02. Current core
ends site_unreachable_in_h without trying another site: R6-02 can order reviewed
alternatives first, but post-failure retry changes require scoped R6-01 integration.
Do not edit siblings to bridge these boundaries.

CONTRACTS.md pins P1–P13. Import lazily and fail closed. Each ticket branches
from current main, owns one PR and writes its docs/handoff/<id>.md with pasted
checks and dated scrubbed evidence. Only R6-01 edits shared docs/queue/contracts.
R5/R4/R3/R2/R1/T tickets are history, not current scope.

## Acceptance and next steps
After remaining R6-02/R6-04 merge (R6-03/R6-05 already merged), R6-01 coordinates
rebased visible integrated acceptance:
>=5 UI-driven live cases, recording only within allowed evidence/handoff paths.
This is planned, not evidence already produced. Evaluate the Milan
marathon, Lisbon/Porto, a Barcelona/Spain half, a Swiss trail and a Netherlands
10K (plus Valencia/Seville if useful), default Paris plus Lyon/Bruxelles/Genève.
Run ONE MISSION AT A TIME to respect the shared three-session quota. Record per
agent: H started, queue time, genuine frame count/max gap, reason_code,
checkpoint reached and READY; never commit H/site screenshots.
Organizers whose terms forbid extraction stay prohibited; the guide steers to
preparable races instead. Never invent dates or silently change a named
request. Target >=1 complete success.

A complete success requires assistant-proposed official dates, explicit
confirmation, three real H agents running in parallel, changing visible frames
and verified safe pre-payment stops for all three. Any earlier safety boundary
is a blocker. Never pay/book/create accounts/accept terms or consent/submit
forms/enter personal data/bypass captchas. Accor and prohibited entries stay
denied; unknown/expired reviews block before H. Prefer authorized captcha-free
sites. robots.txt is not authorization; H/site frames are in_session_only.
A P13 checkpoint_unverified stays blocked/reached-to-verify, never READY.
Design target >=8.5/10; H budget is not a constraint.

## Offline checks
Python 3.12: `uv sync --frozen`, then
`uv run ruff check . && uv run pytest -q`, including journey E2E,
tests/test_r6_scope_contract.py and >=130 adversarial FR/EN cases.
Run configured pre-commit hooks. CI never calls live providers. Merge only
green reviewed PRs, then turn observed failures into the next scoped queue.
