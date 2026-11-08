# RunAI — guided race discovery and live preparation

**Dis-moi ton envie de course, je prépare ton déplacement.**

RunAI helps a runner choose any real race from a vague wish or a race name.
Milan is one evaluation case, not a restriction. Official dates and distances
come from sources, never from an assumption the user must supply.

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
   URL. A captcha, disallowed automation, missing inventory, required consent,
   form submission or account requirement is an honest blocker, not success.

## Design is the first priority
Deliver a polished, premium Strava-inspired experience: bold athletic visual
identity, energetic orange accent, excellent typography, clean data-rich cards,
consistent spacing and motion, accessible controls and responsive layouts.
Chat, chips, plan cards and agent panels need intentional empty/loading/error
states. Follow docs/feedback/owner.md when present. Functional integration is
not a substitute for design work.
The conversation should feel natural in French and English, with chat bubbles,
streaming-like replies, a bottom composer, one-click defaults and typed corrections.

## Architecture and round-3 ownership
- R3-01: site-policy registry fragments, registration adapter validation,
  coverage(), reviewed exact-date hotel/transport adapters.
- R3-02: registration builders and the registration registry fragment;
  first personal-data page reached untouched.
- R3-03: premium Strava UI, chronological ChatGPT-style suggestions, fresh
  screenshot-only three-agent stage, friendly reason codes and FR/EN cards.
- R3-04: guide/discovery robustness, distance chips, coverage-aware origins
  and GuidedTurn.language; >=30 adversarial FR/EN conversations.
- R3-05: core app/models/providers plus hclient/scrub, reason codes, language,
  honest outcomes, fresh frames, runtime limits, shared docs and final acceptance.

CONTRACTS.md (owned by R3-05) pins P1–P6. Import sibling modules lazily and
fail closed when absent.

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
a pass. Round-3 target: >=1 complete success, ideally Milan and Lisbon.
Record >=5 cases in docs/eval/round-3-acceptance.md after the other four merge.

## Safety and evidence boundary
The owner has approved read/prepare-only live H runs, not transactions. Never
pay, book, create accounts, accept terms/consent or medical declarations, submit
forms, enter personal data or bypass captchas. Cookie banners may only be
dismissed without consent. Prefer sites without captchas and whose terms permit
agents; document the selection and stop honestly if authorization is unclear.
H budget is not a constraint: run agents live in parallel whenever useful. Never include secrets, tokens, private H URLs,
emails or personal data in code, fixtures, logs or evidence. Use only safe public
handoff links and scrubbed evidence. Never claim unobserved results.

## Continuous implementation loop
Each ticket has one branch/PR and non-overlapping allowed files listed in
docs/tickets/index.json (validated by tests/test_r3_scope_contract.py). Round
3: R3-01..R3-04 merge in any order; R3-05 integrates and certifies live last.
R2-*, R1-* and T* ticket files are history and grant no current scope.

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
