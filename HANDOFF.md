# Handoff — round three

## Current implementation/evidence boundary (2026-11-09)
Round 2 recorded **0/5 visible live successes** and a 6.5/10 design score.
Read [docs/eval/round-2.md](docs/eval/round-2.md) for observed evidence, not
a claim of generic live readiness. Main failures: no adapters for most cities,
default Paris origin incompatible with transport coverage, false unsafe
verdicts, stale live frames, step limits and unavailable inventory.

Owner feedback (a)–(d), Strava-first design, adversarial requirements, Accor
denial and the exact live-success definition remain top priority in
[docs/feedback/owner.md](docs/feedback/owner.md). Synthetic tests/footage are
not proof of live success.

## Round-three queue
Exact file ownership is authoritative in [index.json](docs/tickets/index.json).

| Ticket | Scope | Merge |
| --- | --- | --- |
| R3-01 | Registry fragments, adapter validation, coverage(), hotel/transport | Any order |
| R3-02 | Reviewed registration adapters and first-data-page stops | Any order; fails closed until R3-01 |
| R3-03 | Strava UI, suggestions, live stage, FR/EN friendly reasons | Any order |
| R3-04 | Guide robustness, distance/origin chips, language | Any order |
| R3-05 | Core + H runtime, shared docs/contracts, final acceptance | Docs/core any time green; acceptance last |

CONTRACTS.md pins P1–P6. Import lazily and fail closed. Each ticket branches
from current main, owns one PR and writes its docs/handoff/<id>.md with pasted
checks and dated scrubbed evidence. Only R3-05 edits this shared handoff.
R2/R1/T tickets are history, not current scope.

## Acceptance and next steps
After R3-01..R3-04 merge, R3-05 rebases and records >=5 UI-driven live cases in
[docs/eval/round-3-acceptance.md](docs/eval/round-3-acceptance.md). That report
is a planned deliverable, not evidence already produced. Evaluate Milan
marathon Apr 2027, Lisbon half Mar 2027, Valencia 10K Jan 2027, a Swiss summer
trail and Freiburg half Apr 2027, default Paris plus Lyon/Bruxelles/Genève.
Prefer near-term editions for rail horizons (~3–6 months), without inventing
dates or silently changing a named request. Target >=1 complete success,
ideally Milan and Lisbon.

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
tests/test_r3_scope_contract.py and >=30 adversarial FR/EN cases.
Run configured pre-commit hooks. CI never calls live providers. Merge only
green reviewed PRs, then turn observed failures into the next scoped queue.
