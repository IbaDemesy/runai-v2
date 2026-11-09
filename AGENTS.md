# Coding agents

## Product and priorities
- Guide runners from a vague wish to any real race, then prepare registration,
  hotel and transport. Read PLAN.md and docs/feedback/owner.md (newest first).
- Beautiful Strava-inspired UX is the owner's first priority: energetic orange,
  strong typography, spacing, motion, responsive empty/loading/error states.
- Source races, distances and official dates through Linkup. Propose sensible
  editable travel defaults, ask as few questions as possible, one at a time.
- Natural FR/EN chat: immediate typing/progress, clickable suggestion pills under
  the latest reply, chronological questions and a bottom composer.
- Require explicit current-plan confirmation before the three H agents launch
  in parallel. Show genuine streamed frames and one friendly status line;
  never raw prompts, JSON or logs. Missing footage is unavailable, never simulated.

## Modes and evidence
- Modes: RUNAI_MODE=demo|replay|live; API mode may override the server default.
  Demo/replay are visibly synthetic and never proof of live success.
- Live uses real Linkup/H with environment keys. Missing keys/modules return
  explicit HTTP 501/unavailable, never fake success or silent demo fallback.
- Never invent provider results, tests, frames or evidence. A homepage is not a
  prepared checkout; an earlier safety stop remains an honest blocker.
- Round 7-8 owner decision: no site is excluded for ToS reasons, including
  Booking, Trainline, SNCF Connect, Accor, Hilton, Omio, Google and SBB.
  Use allowed_owner_rule reviews; add scoped adapters for major sites to
  advance as far as safely possible and minimize the client's actions.
  Unknown/expired reviews still fail closed; robots.txt is not authorization.

## Safety and privacy (P14)
- Owner-approved runner-profile prefill is allowed only into
  participant/guest/passenger fields. Ask for the profile once. Intermediate
  Continue/Next may move to the next page only; never commit a transaction.
- Profile values live only in process memory, cleared on mission deletion/end;
  never stored in repo, logs, evidence, committed screenshots or eval reports.
  Mission/events expose only profile_status metadata for the profile; H receives declared
  prefill_fields. Use clearly fake identities such as 'Test Runner' in evals.
- Never pay/book, create accounts/log in, accept terms/medical consent, submit
  final forms or bypass captchas. Dismiss cookies only without consent.
  Stop honestly at the earliest prohibited boundary.
- Hand off genuine safe public URLs only; never disclose private H URLs,
  access tokens, secrets, contact or payment data. Site frames remain
  in_session_only, never committed or published.
- Read HAI_API_KEY, LINKUP_API_KEY and GLADIA_API_KEY from environment only;
  never print or commit their values.

## Ticket loop and checks
- Read CONTRACTS.md, your ticket and docs/tickets/index.json first. Current
  queue: round 8, R8-01..R8-05. R7 and earlier tickets are history, not scope.
- R8-01 owns core (app/models/providers, hclient/scrub), shared docs/contracts/
  queue and integrated visible acceptance. R8-02 owns transport, generic policy
  loader/base registry (existing hotel entries frozen) and transport shard.
  R8-03 owns hotel + registration and their policy shards. R8-04 owns
  guide/discovery + adversarial tests. R8-05 owns static UI and profile card.
- Exact disjoint file lists are authoritative. Touch only allowed files;
  request scope amendments before cross-owner edits. Code against additive
  P1–P15, import siblings lazily and fail closed; UI hides profile on 404.
- Merge in any order; R8-01 rebases last and coordinates visible integrated
  acceptance after siblings merge: Milan, Valencia and one of Berlin/Lisbon/Frankfurt,
  using fake profiles. One mission at a time, three agents parallel.
- H organization concurrency is 3. Check quota before EACH live smoke; use at
  most one H session per ticket. Queue cap is eight minutes; total agent
  wall-clock cap is 15 minutes including retries, alternatives and queueing.
- One ticket = one branch = one PR from current main. Never push directly to
  main; merge only green reviewed CI, including tests/test_journey_e2e.py.
- Each ticket writes docs/handoff/<id>.md with pasted checks, evidence,
  blockers and next steps; only R8-01 edits shared HANDOFF.md.
- Every behavior needs normal/empty/error coverage. CI never calls live
  providers; live verification requires separate dated scrubbed evidence.
  Preserve the FR/EN adversarial suite and fail-closed site-policy checks.
- Framed P13 checkpoint_unverified stays blocked, never READY. Stale/absent
  frames must never be labelled fresh live footage.
- Python 3.12: uv sync --frozen, then uv run ruff check . && uv run pytest -q.
  Run configured pre-commit hooks. Start: uv run uvicorn runai.app:app --reload.
- Round 7 scored 33/100, 0/5 live successes; scoped smokes or synthetic tests
  do not establish readiness. Evaluate multiple races and iterate from observed
  failures. The exact live-success definition is in docs/feedback/owner.md.
