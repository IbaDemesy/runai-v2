# Handoff — round five

## Current implementation/evidence boundary (2026-11-09)
Round 4 recorded **0/5 visible live successes** and a 7/10 design score.
Read [docs/eval/round-4.md](docs/eval/round-4.md) for observed evidence, not
a claim of generic live readiness. Planner-verified causes for round 5:
H's organization quota is three sessions; queued browsers consumed the old
45-second startup deadline. Step limits arrived without force_answer, even
after safe pages were observed. Redirect targets lacked diagnostics, gateway
cities/fragments could not verify, and real Njuko ids failed scrubbing.

Owner feedback (a)–(d), Strava-first design, adversarial requirements, Accor
denial and the exact live-success definition remain top priority in
[docs/feedback/owner.md](docs/feedback/owner.md) (Round 5 section first).
Synthetic tests/footage are not proof of live success.

## Round-five queue
Exact file ownership is authoritative in [index.json](docs/tickets/index.json).

| Ticket | Scope | Merge |
| --- | --- | --- |
| R5-01 | Queue-aware runtime, P11 checkpoints, P12 gateway/fragments, diagnostics, shared docs | PR-A any time green; PR-B acceptance last |
| R5-02 | Hotel/transport stop pages, redirect fixes, rail/air alternatives | Any order |
| R5-03 | Registration stop pages, NL/CH/Spain/FR/DE/PT coverage and availability | Any order |
| R5-04 | No-loop guide, named races, mind/origin changes, >=130 adversarial cases | Any order |
| R5-05 | Strava-grade UI polish, preparation badges, honest live stage | Any order |

CONTRACTS.md pins P1–P12. Import lazily and fail closed. Each ticket branches
from current main, owns one PR and writes its docs/handoff/<id>.md with pasted
checks and dated scrubbed evidence. Only R5-01 edits this shared handoff.
R4/R3/R2/R1/T tickets are history, not current scope.

## Acceptance and next steps
After R5-02..R5-05 merge, R5-01 PR-B rebases and records >=5 UI-driven live cases in
[docs/eval/round-5-acceptance.md](docs/eval/round-5-acceptance.md). That report
is a planned deliverable, not evidence already produced. Evaluate the Milan
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
sites. H budget is not a constraint.

## Offline checks
Python 3.12: `uv sync --frozen`, then
`uv run ruff check . && uv run pytest -q`, including journey E2E,
tests/test_r5_scope_contract.py and >=130 adversarial FR/EN cases.
Run configured pre-commit hooks. CI never calls live providers. Merge only
green reviewed PRs, then turn observed failures into the next scoped queue.
