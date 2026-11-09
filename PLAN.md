# RunAI — guided race discovery and live preparation

**Dis-moi ton envie de course, je prépare ton déplacement.**

RunAI helps a runner choose any real race from a vague wish or a race name.
No race or destination is hard-coded. Official dates and distances come from
sources, never from an assumption the user must supply.

## Product journey
1. Start with a guided chat: accept wishes such as a spring marathon in Italy,
   a summer trail in Switzerland, or the Lisbon half marathon. Use real Linkup
   discovery to propose candidate races, editions, distances, official dates
   and registration links with provenance and retrieval time. Conflicting or
   unknown dates remain explicit; do not silently substitute an edition.
2. Ask at most one focused question at a time with clickable suggestion chips
   and free-text corrections. Propose editable origin, nights and budget
   defaults, visually distinct from sourced race facts. Present an attractive
   plan card and require explicit confirmation. Read-only discovery may precede
   confirmation; H preparation may not.
3. After confirmation, start registration, hotel and transport H agents in
   parallel on appropriate real sites, not race-specific hard-coded paths.
   Show all three working live using genuine streamed screenshots and only short friendly status lines. Desktop panels stack cleanly on mobile.
4. Stop before payment or any earlier prohibited action; hand off a safe public
   URL. A captcha, out-of-scope navigation, missing inventory, required consent,
   final submission or account requirement is an honest blocker, not success.

## Design is the first priority
Deliver a polished, premium Strava-inspired experience: bold athletic visual
identity, energetic orange accent, excellent typography, clean data-rich cards,
consistent spacing and motion, accessible controls and responsive layouts.
Chat, chips, plan cards and agent panels need intentional empty/loading/error
states. Follow docs/feedback/owner.md when present. Functional integration is
not a substitute for design work.
The conversation should feel natural in French and English, with chat bubbles,
streaming-like replies, a bottom composer, one-click defaults and typed corrections.

## Architecture and round-8 ownership
- R8-01: core/integration, P15 preflight blocks/freshness, P14 profile privacy, stall watchdog,
  live-shape verification gates, Omio scrub and shared docs/queue/contracts.
  Owns integrated visible acceptance after all siblings merge; rebases last.
- R8-02: transport coverage and selected round-trip fares, big-site adapters,
  SBB drift/gateway fixes, generic policy loader and base/transport registry.
  Existing hotel entries in the base registry are frozen.
- R8-03: hotel + registration, their policy shards, major-site adapters and
  guest/participant prefill up to safe pre-payment/terms boundaries.
- R8-04: guide/discovery, minimal questions, origin corrections, honest recovery,
  profile prompt once and adversarial regressions.
- R8-05: >=9/10 Strava-grade static UI, secure profile card, honest launch/live
  states, covered-agent CTAs, advanced-as-far-as-possible copy and mobile polish.

Exact disjoint file lists in index.json take precedence; request amendments for
cross-owner work. CONTRACTS.md (R8-01) pins additive P1–P15. Import siblings
lazily and fail closed; builders declare prefill only with runner_profile and
UI hides the profile card on 404. All five tickets may merge in any order.

## Modes and truthfulness
- `demo`: synthetic race options and simulated preparation; no keys.
- `replay`: recorded synthetic fixtures/frames, clearly labelled with provenance
  and original time where present. Missing frames are unavailable, not fabricated.
- `live`: real Linkup discovery plus real H runs with environment keys. Missing
  keys or modules produce an explicit 501/unavailable response, not fake success.
  Gladia voice input is optional and requires its own environment key/module.

Demo/replay homepage links do not represent prepared checkout sessions. Their
`ready_for_payment` state is synthetic. The bootstrap trace is synthetic and
contains no proof of live readiness; historical evidence from another project
does not prove this product works. Live success requires dated observed evidence.

## Evaluation set and success criterion
| Case | Runner's starting wish | What to establish |
| --- | --- | --- |
| Milan marathon | « le marathon de Milan au printemps » | Official April 2027 edition |
| Lisbon half | « le semi de Lisbonne » | Official March 2027 edition |
| Valencia 10K | « un 10 km en Espagne cet hiver » | Official January 2027 edition |
| Swiss summer trail | « un trail en Suisse cet été » | Sourced summer edition/distance |
| Freiburg half (EN) | "a half marathon in Germany next spring" | Official April 2027 edition |

Default origin: Paris; also evaluate Lyon/Bruxelles/Genève against coverage().
Prefer near-term editions for live acceptance: rail horizons are about
3–6 months. Never invent dates or quietly substitute a named race.

The exact live-success definition is in
[docs/feedback/owner.md](docs/feedback/owner.md): assistant-proposed sourced
date, explicit confirmation, three overlapping live H agents, changing on-page
screenshots and verified safe pre-payment stops for all three. An earlier
mandatory safety stop is a blocker. Never quietly swap a named request to force
a pass. Round-7 verdict: **33/100, 0/5 live successes**, design **7.5/10**
(docs/eval/round-7.md). Round-8 target: advance as far as safely possible while
minimizing client actions, with >=9/10 design. After siblings merge, R8-01
coordinates visible integrated acceptance of Milan (April 2027), Valencia (6 December 2026) and one
of Berlin/Lisbon/Frankfurt using clearly fake profiles, one mission at a time. Record only
within its allowed evidence/handoff files. This is planned, not completed live
evidence; individual backend smokes do not establish integrated readiness.

## Safety and evidence boundary
The owner approves read/prepare-only H runs and P14 runner-profile prefill:
ask once, type only supplied participant/guest/passenger fields, and allow
intermediate Continue/Next only to reach the next page, never to commit.
Profile values live only in process memory and clear on mission deletion/end;
never store them in repo, logs, evidence, committed screenshots or eval reports.
Use clearly fake identities such as 'Test Runner' for evaluations.

No site is excluded for terms-of-service reasons, including Accor, Booking,
Hilton and major transport sites. Use allowed_owner_rule adapter reviews; add
big-site coverage where it safely advances preparation. Unknown/expired reviews
still block before H. Never pay/book, create accounts/log in, accept terms or
medical consent, submit final forms or bypass captchas. Dismiss cookies only
without consenting, stop at prohibited boundaries and report blockers honestly.
robots.txt is not authorization; H/site frames remain in_session_only.
Never include real personal data, secrets, tokens or private H URLs in code,
fixtures, logs or evidence. Use safe public handoffs and scrubbed evidence;
never claim unobserved results. H quota is three: check before each live smoke;
one mission at a time, three parallel agents. The 15-minute agent wall-clock
cap includes retries, alternatives and queueing; cumulative queue cap is eight
minutes.

## Continuous implementation loop
Each ticket has one branch/PR and non-overlapping allowed files listed in
docs/tickets/index.json (validated by tests/test_r8_scope_contract.py). Round
8: R8-01..R8-05 merge in any order; R8-01 owns core + integration acceptance,
shared docs and the queue, and rebases last after siblings merge.
R7 and earlier ticket files are history and grant no current scope.

Keep main green: Python 3.12, `uv sync --frozen`,
`uv run ruff check . && uv run pytest -q`, including the journey E2E tests.
CI is offline; live verification is separate. Review code, design, safety and
dated scrubbed live evidence, squash-merge only green PRs, evaluate the five
cases, then turn real failures into focused follow-up tickets. Do not claim
completion until the live success criterion is observed.

## Out of scope
Purchasing, bookings, accounts, coach features, 3D flyover, Telegram, PDF/ICS,
Strava integration, multi-city itineraries, production persistence and autonomous
captcha/security workarounds. Strava is a visual reference, not an integration.
