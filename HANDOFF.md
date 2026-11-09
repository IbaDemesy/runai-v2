# Handoff — round eight

## Current evidence boundary
Round 7 scored **33/100, 0/5 live successes**, with one unverified transport
READY. Synthetic tests and backend smokes do not establish visible live success.
Historical observations remain in [H evidence](docs/evidence/h-client.md).
No round-eight live acceptance has run.

## Round-eight queue
Exact disjoint file sets in [index.json](docs/tickets/index.json) are authoritative.
Earlier queue entries are history, not current edit authority.

| Ticket | Scope | Merge |
| --- | --- | --- |
| R8-01 | Core/P15, profile alias, scrub, watchdog, gates, shared docs and integrated acceptance | Last/integration; rebases after siblings |
| R8-02 | Transport, booking horizons, policy loader/base and transport shard | Any sibling order |
| R8-03 | Hotel + registration, safe checkpoints/prefill and policy shards | Any sibling order |
| R8-04 | Guide/discovery, minimal questions and adversarial regressions | Any sibling order |
| R8-05 | Static UI/profile, honest launch/coverage/freshness states and mobile | Any sibling order |

The base registry/loader belongs to R8-02; existing hotel base entries are frozen.
Hotel/registration builders and shards belong to R8-03. R8-01 owns core and shared
docs/contracts, not those adapters. P1–P15 are additive; import siblings lazily
and fail closed. Each ticket writes its own handoff.

## Implemented core and remaining dependencies
- Validated `address` alias for `address_line`; differing duplicates/unknown
  fields return 422. Profile values never enter Mission JSON/events/logs.
- Public Omio UUID results survive scrubbing with dates/party; tracking is
  stripped and other opaque paths stay rejected.
- P15 `preflight_block` returns blocked without H sessions or launch events;
  unknown reasons become no_site_coverage, and not_yet_bookable is additive.
- After a 150-second observation gap the watchdog checks for a terminal answer,
  forces once if running, then cancels after 60 further seconds with blocked/
  timeout and the last reviewed checkpoint-frame handoff when available. Total
  agent cap remains 15 minutes. Nullable stale_frame reaches step events;
  missing footage is unknown, never asserted fresh.
- Synthetic Booking/Njuko fixtures cover stringified/mixed-case verification,
  localized dates and formatted totals. City/dates/party, selection, checkpoint
  frames and beyond-pattern gates remain mandatory; P13 unverified stays blocked.
  Verification diagnostics contain gate names, not extracted values.
- **R8-03 dependency:** r7-booking-hotel in docs/site-policy.d/hotel.json lists
  only www.booking.com, with empty navigation_hosts. Add secure.booking.com to
  the same reviewed entry before cross-host guest details can pass. Core
  equivalence does not grant access to unreviewed hosts.
- R8-02 owns the six known transport-matrix assertions exposed by Omio
  scrubbing. R8-05 owns preflight/uncovered CTA coverage and canonical address
  submission. Core did not change either sibling-owned file.

See [R8-01 handoff](docs/handoff/R8-01.md) for checks and the live placeholder.

## Safety and evidence
The existing round 7-8 owner decision is unchanged. No site is excluded for ToS
reasons; use allowed_owner_rule reviews and fail closed on unknown/expired
reviews. P14 profile values live only in process memory until deletion/end and
may enter only supplied participant/guest/passenger fields. Never store them
in repo/logs/evidence/committed screenshots/eval reports. Intermediate Continue/
Next may only change pages. Never pay/book, create accounts/log in, accept
terms/medical consent, submit final forms or bypass captchas. Frames remain
in_session_only; no private H URLs or secrets in evidence.

## Live acceptance — pending
After siblings merge, R8-01 rebases last and coordinates visible real-UI cases:
**Milan (April 2027), Valencia (6 December 2026), and one of Berlin/Lisbon/Frankfurt**.
Use a clearly fake profile through the UI card, explicit current-plan confirmation,
one mission at a time with three parallel agents and quota checked before each
run. Record H starts, frames/stale gaps, reason_code, checkpoint, READY and public
handoff host/path in H evidence. Target one 3/3 verified READY case; never disguise
safety stops or missing footage as success.

## Checks
Python 3.12: uv sync --frozen, then uv run ruff check . && uv run pytest -q,
including tests/test_r8_scope_contract.py and journey/adversarial coverage.
Before this docs update: 3023 passed, six known transport failures, one
Starlette/httpx deprecation warning; lint passed. Updated results are in the
R8-01 handoff. CI is offline; merge only green reviewed PRs after sibling-owned
failures are fixed. Live acceptance and visual verification remain pending.
