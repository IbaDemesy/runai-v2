# Coding agents

## Product and priorities
- RunAI guides a runner from a vague wish to any real race, then prepares race
  registration, hotel and transport. Milan is one evaluation case, never a
  product restriction or hard-coded execution path. Read PLAN.md for the target.
- Beautiful UX is the owner's first priority: premium Strava-inspired athletic
  design, energetic orange accents, strong typography, spacing, motion and
  responsive layouts, including empty/loading/error states. Design is not optional.
- Read docs/feedback/owner.md if present; owner product/design feedback takes
  priority over older scope notes.
- The assistant proposes sourced races, distances and official dates through
  Linkup; users need not know dates. Suggest editable origin/nights/budget defaults
  and ask at most one focused question at a time with clickable suggestion chips.
- Keep the chat natural in French and English, with chat bubbles, streaming-like
  replies and a bottom composer; accept defaults in one click or typed corrections.
- Require explicit plan confirmation before starting the three real H Company
  browser agents in parallel. Show each agent's genuine streamed screenshots
  with one short friendly status line; never raw task/prompt/JSON/log text.
  Missing footage is unavailable, never simulated live.

## Modes and evidence
- Modes: `RUNAI_MODE=demo|replay|live`; API mode may override the server default.
- Demo uses fakes; replay plays recorded synthetic fixtures. Neither needs keys;
  visibly label both synthetic. Replay is not proof of live success.
- Live means real Linkup discovery and real H runs using environment keys.
  Missing keys or modules must return explicit HTTP 501/unavailable errors,
  never fake success or a silent fallback to demo. Other failures remain honest
  errors or blocked human handoffs, not successful preparation claims.
- Never invent provider results, tests, screenshots, recordings or live evidence.
  A public homepage is not a prepared checkout; synthetic `ready_for_payment`
  is not proof of a real pre-payment stop.
- The owner has explicitly approved read/prepare-only live H runs that stop
  before payment. Review applicable site authorization first; prefer sites
  without captchas and whose terms permit agents, and document the choice.
  Approval does not authorize purchases, submissions or any prohibited action.

## Safety and privacy
- Never pay, book, create accounts, accept terms, medical declarations or consent,
  submit forms, enter personal data, or bypass captchas. Cookie banners may only
  be dismissed without accepting consent. Stop at the earliest such boundary,
  even if that prevents reaching pre-payment, and report the blocker honestly.
- Hand off only a genuine safe public URL; never disclose private H session URLs
  or access tokens. No secrets, emails, contact details, other personal data or
  payment details in code, fixtures, logs, evidence, screenshots or recordings.
- Read `HAI_API_KEY`, `LINKUP_API_KEY`, `GLADIA_API_KEY` from environment only;
  never print or commit their values.

## Ticket loop and checks
- One ticket = one branch = one PR, branched from current main. Never push
  directly to main. Keep main green; merge only with green CI, including
  tests/test_journey_e2e.py, and reviewed safety/evidence boundaries.
- Read CONTRACTS.md, your ticket under docs/tickets/ and docs/tickets/index.json
  first. index.json is the authoritative current queue (round 4: R4-01..R4-05);
  R2-*/R1-*/T* ticket files are history and grant no current scope. Touch only the
  ticket's allowed files; otherwise stop and request a scope amendment.
- Round 4: R4-01..R4-05 merge in any order. R4-01 owns core integration
  (app/models/providers and hclient/scrub), CONTRACTS.md and shared docs; its
  PR-A lands the H runtime fixes and docs, and its PR-B runs final integrated
  live acceptance after R4-02..R4-05 merge, on a rebased branch. Code against
  the pinned additive interfaces in CONTRACTS.md; import sibling modules lazily
  and fail closed when they are missing.
- Each ticket writes docs/handoff/<id>.md with changes, checks (pasted
  output), evidence, blockers and next steps; only the integration ticket edits
  the shared HANDOFF.md.
- Every behavior change needs normal, empty and error coverage where applicable.
  CI tests never call live providers. Live verification is separate: record
  dated, scrubbed public evidence and actual stop states; do not invent success.
- Keep the adversarial FR/EN conversation suite green, and site policy
  fail-closed (Accor denied; unknown/expired reviews block before any H session).
- Use Python 3.12. Run `uv sync --frozen`, then
  `uv run ruff check . && uv run pytest -q`. Run configured pre-commit hooks.
- Start: `uv run uvicorn runai.app:app --reload` (port 8000).
- After integration, evaluate multiple races, review observed failures, create
  focused scoped tickets and repeat. Passing synthetic tests or one Milan run
  does not establish generic live readiness. The live-success definition is in
  docs/feedback/owner.md.
