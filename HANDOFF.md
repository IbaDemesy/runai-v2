# Handoff — round four

## Current implementation/evidence boundary (2026-11-09)
Round 3 recorded **0/5 visible live successes** and a 7/10 design score.
Read [docs/eval/round-3.md](docs/eval/round-3.md) for observed evidence, not
a claim of generic live readiness. Main verified root causes: the hclient gate
treated the registration `fallback_url` as a navigation scope (Milan blocked
before any H session), the first H observation is often `about:blank`
(transport killed in seconds), frames update only once per H step, thin
hotel/transport/registration coverage and sold-out editions.

Owner feedback (a)–(d), Strava-first design, adversarial requirements, Accor
denial and the exact live-success definition remain top priority in
[docs/feedback/owner.md](docs/feedback/owner.md) (Round 4 section first).
Synthetic tests/footage are not proof of live success.

## Round-four queue
Exact file ownership is authoritative in [index.json](docs/tickets/index.json).

| Ticket | Scope | Merge |
| --- | --- | --- |
| R4-01 | H runtime fixes (P7, P10), core, shared docs/contracts, final acceptance | PR-A any time green; PR-B acceptance last |
| R4-02 | Hotel + transport coverage to pre-payment, P7 alternatives | Any order |
| R4-03 | Registration coverage/availability, `registration_coverage()` (P8) | Any order |
| R4-04 | Preparation-aware guide (P9), adversarial fixes, first-reply latency | Any order |
| R4-05 | Strava-grade UI polish, preparation badges, honest live stage | Any order |

CONTRACTS.md pins P1–P10. Import lazily and fail closed. Each ticket branches
from current main, owns one PR and writes its docs/handoff/<id>.md with pasted
checks and dated scrubbed evidence. Only R4-01 edits this shared handoff.
R3/R2/R1/T tickets are history, not current scope.

## Acceptance and next steps
After R4-02..R4-05 merge, R4-01 PR-B rebases and records >=5 UI-driven live cases in
[docs/eval/round-4-acceptance.md](docs/eval/round-4-acceptance.md). That report
is a planned deliverable, not evidence already produced. Evaluate the Milan
marathon, Lisbon/Porto, a Barcelona/Spain half, a Swiss trail and a Netherlands
10K (plus Valencia/Seville if useful), default Paris plus Lyon/Bruxelles/Genève.
Organizers whose terms forbid extraction stay prohibited; the guide steers to
preparable races instead. Never invent dates or silently change a named
request. Target >=1 complete success.

A complete success requires assistant-proposed official dates, explicit
confirmation, three real H agents running in parallel, changing visible frames
and verified safe pre-payment stops for all three. Any earlier safety boundary
is a blocker. Never pay/book/create accounts/accept terms or consent/submit
forms/enter personal data/bypass captchas. Accor and prohibited entries stay
denied; unknown/expired reviews block before H. Prefer authorized captcha-free
sites. H budget is not a constraint.

## Offline checks
Python 3.12: `uv sync --frozen`, then
`uv run ruff check . && uv run pytest -q`, including journey E2E,
tests/test_r4_scope_contract.py and >=30 adversarial FR/EN cases.
Run configured pre-commit hooks. CI never calls live providers. Merge only
green reviewed PRs, then turn observed failures into the next scoped queue.
