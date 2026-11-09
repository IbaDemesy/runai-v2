# Handoff — round seven

## Current evidence boundary (2026-11-09)
Round 6 recorded **38/100, 0/5 visible live successes, design 8/10**.
See [round-6 evaluation](docs/eval/round-6.md). Only one of fifteen agents
verified READY; transport blocked every complete mission. Reached Njuko/IHG
screens were not verified success. Earlier hotel-only smokes in Milan, Zurich
and Lisbon are backend evidence, not visible integrated acceptance; the original
Lisbon differing query was not retained, so its historical cause is unresolved.
See [hotel evidence](docs/evidence/hotel.md) and
[runtime evidence](docs/evidence/h-client.md). Synthetic tests are not live proof.

## Round-seven queue
Exact file ownership is authoritative in [index.json](docs/tickets/index.json).

| Ticket | Scope | Merge |
| --- | --- | --- |
| R7-01 | Core/P14, privacy/safety, runtime alternatives, verification, shared docs and integrated acceptance | Any order; rebases last |
| R7-02 | Transport, big-site adapters, selected round-trip fares, generic policy/base and transport registry | Any order |
| R7-03 | Hotel + registration, major-site adapters, guest/participant prefill and policy shards | Any order |
| R7-04 | Guide/discovery, minimal questions, corrections/recovery, profile prompt and adversarial regressions | Any order |
| R7-05 | >=9/10 static UI, profile card, honest launch/live/coverage states and mobile | Any order |

The base registry/loader belongs to R7-02 (existing hotel base entries frozen);
hotel and registration shards/builders belong to R7-03. R7-01 owns core and
shared docs/contracts, not those builders. Import additive P1–P14 lazily and
fail closed. Each ticket writes its own handoff; older tickets are history.

## Implemented core and remaining work
See [R7-01 handoff](docs/handoff/R7-01.md) for profile storage/endpoints,
contextual redaction, bounded runtime alternatives and synthetic checkpoint
checks. Query-key ordering no longer causes handoff_observed failures;
historical R6 cause remains unverified without the original H answer/observation.
Hotel-BB room/rate lists remain blocked by the builder's checkpoint_pattern:
its reviewed adapter requires a selected /booking/extras or /booking/review
checkpoint. Do not weaken mandatory verification or call unselected rates READY.
The legacy Frankfurt scrub assertion needs the registration owner's update.

## Owner decision and safety
[Owner feedback](docs/feedback/owner.md), Round 7-8 first, supersedes earlier
ToS exclusions: no site is excluded for that reason. Use allowed_owner_rule;
unknown/expired reviews still block. Add major-site adapters where useful.
Minimize questions/actions, ask for the runner profile once, and allow P14
typing only into supplied participant/guest/passenger fields. Values live only
in process memory, cleared at mission deletion/end, never in repo/logs/evidence/
committed screenshots/eval reports. Use fake identities such as 'Test Runner'.
Intermediate Continue/Next may only change pages; never pay/book, create
accounts/log in, accept terms/medical consent, submit final forms or bypass
captchas. Site frames stay in_session_only. P13 unverified stays blocked.
Show only genuine changing frames and friendly copy, never raw prompts/logs.

## Acceptance and checks
After siblings merge, R7-01 rebases last and coordinates at least Milan, Berlin
and one other visible live case with a fake profile. This is planned, not evidence
already produced. Quota-check before each live smoke, one session per ticket;
integrated acceptance runs one mission at a time with three agents parallel.
Record H starts, queue time, frames/gaps, reason_code, checkpoint and READY.
A complete success still requires sourced dates, explicit plan confirmation
and three verified safe pre-payment stops visible live.

Python 3.12: uv sync --frozen, then uv run ruff check . && uv run pytest -q,
including tests/test_r7_scope_contract.py and journey/adversarial coverage.
CI never calls live providers. Record dated scrubbed live evidence separately;
never commit site frames. Merge only green reviewed PRs.
