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
   Show all three working live using genuine authorized live views or streamed
   screenshots and step logs. Desktop panels stack cleanly on mobile.
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

## Round-one target architecture
- `runai/guide/`: isolated guided dialogue and state, one-question turns,
  suggestions, editable defaults and confirmation readiness (R1-04).
- `runai/discovery/`: real Linkup search, official-source validation, dated race
  candidates and explicit empty/conflict/error outcomes (R1-03).
- `runai/agents/hclient.py` and `scrub.py`: shared H client, safe progress/live
  frames, output scrubbing and safety boundaries (R1-02).
- `runai/agents/registration.py`: generic official registration preparation
  (R1-05); `hotel.py` and `transport.py`: destination/date-aware preparation
  with authorized site selection (R1-06). These use the shared H client.
- `runai/app.py`, `models.py`, `providers.py`: core FastAPI/schema integration,
  guided mission API, lazy adapters, mode routing, explicit confirmation,
  three concurrent agents and live progress delivery (R1-01).
- `static/index.html`, `styles.css`, `app.js`: polished responsive chat, chips,
  plan cards and three genuine live agent panels (R1-07).
- R1-08 owns product/process documentation and the scoped queue.

These are integration targets, not a claim that all modules already exist.
CONTRACTS.md describes API/schema details and is owned by R1-01.

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
| Milan marathon | A named Milan marathon, no date | Discover the official edition/date; no fixed race path |
| Spring Italy marathon | « un marathon au printemps en Italie » | Propose real matching races and official dates |
| Swiss summer trail | « un trail en Suisse cet été » | Handle a different distance/type, country and season |
| Lisbon half | « le semi de Lisbonne » | Resolve the official edition/date and destination |

ONE successful case means the assistant proposes the race/date, the user
explicitly confirms, all three H agents actually run live in parallel and reach
their pre-payment stops, and the user sees all three working on the page. An
earlier mandatory safety stop is a blocker, not a successful case. A passing
synthetic test or one successful Milan case does not establish generic coverage.
Dates, availability and applicable site authorization must be checked per run.

## Safety and evidence boundary
The owner has approved read/prepare-only live H runs, not transactions. Never
pay, book, create accounts, accept terms/consent or medical declarations, submit
forms, enter personal data or bypass captchas. Cookie banners may only be
dismissed without consent. Prefer sites without captchas and whose terms permit
agents; document the selection and stop honestly if authorization is unclear.
No H API budget optimization should replace useful parallel live verification;
respect each ticket's run limit. Never include secrets, tokens, private H URLs,
emails or personal data in code, fixtures, logs or evidence. Use only safe public
handoff links and scrubbed evidence. Never claim unobserved results.

## Continuous implementation loop
Each ticket has one branch/PR and non-overlapping allowed files. Parallel tickets
write their own docs/handoff/<id>.md. The queue in docs/tickets/index.json is
authoritative: merge R1-02..R1-06 and R1-08 in any order, then R1-01, then R1-07.
T01..T12 are superseded and grant no current implementation scope.

Keep main green: Python 3.12, `uv sync --frozen`,
`uv run ruff check . && uv run pytest -q`, including the journey E2E tests.
CI is offline; live verification is separate. Review code, design, safety and
dated scrubbed live evidence, squash-merge only green PRs, evaluate the four
cases, then turn real failures into focused follow-up tickets. Do not claim
completion until the live success criterion is observed.

## Out of scope
Purchasing, bookings, accounts, coach features, 3D flyover, Telegram, PDF/ICS,
Strava integration, multi-city itineraries, production persistence and autonomous
captcha/security workarounds. Strava is a visual reference, not an integration.
