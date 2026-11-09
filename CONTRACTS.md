# Generic guided-mission contract

## P15 Preflight availability and frame freshness (round 8)

Task builders may return `preflight_block: {reason_code, summary, handoff_url}`.
`summary` is short French user-facing text; `handoff_url` is an HTTPS public URL
or null. LiveRunner returns a non-synthetic `blocked` StepResult without creating
an H session (zero H POSTs), emitting launch events or trying alternatives.
These tasks are not launched agents and count as uncovered for CTA coverage,
never as READY. `not_yet_bookable` is an additive ReasonCode for booking windows
that have not opened; unknown/missing preflight reasons become `no_site_coverage`.
The handoff is scrubbed and must pass the same public HTTPS, reviewed host/path
policy gates as other handoffs; unavailable/denied policy or unsafe URLs yield
null, never an unchecked fallback. Profile privacy applies to this result too.

`StepResult.stale_frame: bool|null = null` is additive: old JSON remains valid.
True means the agent is running and its newest genuine frame is older than
60 seconds. False means it is not stale; null means freshness was not reported.
Missing footage is unavailable, never simulated or asserted fresh. This metadata
does not weaken P13 verification or turn blocked checkpoints into READY.

While running, an observation gap of 150 seconds triggers a terminal-session
check before one force-answer request. A further 60 seconds without an answer
cancels the session and returns blocked/timeout, retaining the last reviewed
checkpoint frame URL when available. These timings and the 60-second frame
freshness threshold are module constants; the total per-agent cap remains
15 minutes. Step progress/frame events carry nullable `stale_frame` metadata;
no frame means unknown, not fresh. A watchdog timeout does not try alternatives.

Google Flights public itinerary query keys `tfs`/`tfu` survive opaque-token
scrubbing only on google.com or google.<two-letter cc> (optionally www), at
exact paths `/travel/flights/booking` and `/travel/flights/search`, with values
matching `[A-Za-z0-9_-]{1,600}`. Invalid/oversized values there are dropped.
Other keys/hosts/paths retain existing scrubbing; tracking is still stripped.
Omio com/fr/de hosts (bare or www) also preserve redirected result paths exactly
matching `/app/search-frontend/results/<id>/<train|bus|flight>`, where id is
`[A-Za-z0-9_-]{1,64}`. Only that id segment is exempt from opaque-path rejection;
other frontend subpaths/hosts remain unchanged. Travel dates/party survive
normal query scrubbing and tracking is still removed.

RunnerProfile also accepts `address` as an input alias of `address_line` with
the same validation. Matching duplicate keys are accepted; differing values
return 422, as do unknown keys. `profile_status.fields` always uses canonical
`address_line`; neither alias exposes profile values in missions/events/logs.

## P14 Runner profile prefill (round 7)

`RunnerProfile` has twelve optional, length-capped strings: full_name, given_name,
family_name, email, phone, birth_date (ISO date), gender, nationality (ISO-3166
alpha-2), address_line, postal_code, city and country. Empty strings are absent.
POST `/api/missions/{id}/profile` replaces the profile in process memory; DELETE clears it.
Both return Mission and are allowed only in guiding/ready (otherwise HTTP 409).
Mission exposes only `profile_status: {complete, fields}`; complete means the
core identity fields are present: (full_name OR given_name + family_name), email,
phone, birth_date, gender and nationality. Address fields are optional.
Values never enter Mission JSON, events, logs, evidence,
fixtures or disk. Mission deletion and run completion clear the profile/status.

At confirmation live execution receives an ephemeral `trip['runner_profile']`
dictionary, absent without a profile. Builders must not interpolate values into
instructions; they declare `prefill_fields` and `prefill_scope`. Only H's prompt
gets the selected values under `Runner profile (type only into the {prefill_scope}
fields; never submit a final form)`. Every supplied profile value, including
case-folded and URL-encoded variants, is handled before outgoing text and URLs.
Identifying fields (full_name, given_name, family_name, email, phone, birth_date,
address_line, postal_code) are redacted in free text and invalidate any URL
containing them. Quasi-identifiers (gender, nationality, city, country) are
redacted only as whole words in free text, never inside URLs. A quasi-identifier
equal (case-folded) to a public trip/expected string is exempt from text redaction;
this preserves public route/destination evidence without exempting identifiers.

Supplied participant/guest/passenger fields may be typed, and intermediate
Continue/Next may move to the next form page. Payment, booking, final submission,
account creation/login, terms, medical declarations, consent and captcha solving
remain forbidden. `personal_data_entered=true` is accepted only with effective
`prefill_fields`; payment/booking/form_submitted/account_created/terms_accepted
claims remain rejected. `checkpoint.prefill_patterns` identifies typing pages:
never force an answer there during prefill, even if also a final URL pattern.
Without a profile the original untouched-personal-data boundary is unchanged.
StepResult may expose only `prefilled: bool` and a short `stop_label`, never values.

Njuko public event IDs are preserved on canonical Njuko hosts and DNS names
ending in `*-registrations.com` (including subdomains). This constrained
white-label suffix does not exempt arbitrary hosts, contacts, or opaque paths;
the existing event-slug/year/13-digit-ID validation still applies.

## Owner site-exclusion override (2026-11-08)
The owner lifted site-based exclusions for read/prepare-only automation. Committed
registry decisions now use allowed_owner_rule, including historically prohibited
or ambiguous sites; old reviews are evidence, not permission from those sites.
Review expiry does not expire the owner's rule. Unknown HTTPS hosts pass the
default navigation policy on their exact host; this does not create an adapter
or expand task navigation allowlists. Explicit injected registries retain strict
evaluation for tests/custom configurations. Malformed registries fail closed.
The H client's Accor-specific exclusion is removed. Frames remain in-session only.
All action/payment/consent/CAPTCHA/privacy guardrails and honest blocked states
remain unchanged. This product-owner decision does not imply site authorization.

Pydantic v2 schemas: `runai/models.py`; unknown request/model fields are forbidden.
The product supports any discoverable race. Milan is one evaluation, not a path.
No agent starts before explicit confirmation. No purchase, booking, account,
consent, personal-data entry, form submission or captcha bypass is permitted.

## Dependency injection and lazy defaults

`create_app(*, guide=None, runner_factory=None, replay_path=None)` creates an
isolated in-memory store. Sibling-ticket modules are imported only at request
time, never on module import. Missing modules/keys produce explicit HTTP 501;
live never falls back to synthetic results.

- `guide.start(text)` asynchronously returns `(state, turn)`.
- `guide.step(state, {text?, suggestion_id?})` returns `(state, turn)`.
- State can be a Pydantic model or dict. Its `trip` is the builder input; when
  absent, the ready turn's `draft` is the complete trip. When the engine exposes
  `trip_payload(state)`, its clean payload is preferred for ready plans. State is private to the
  mission. Turns are serialized with FastAPI's JSON encoder.
- `runner_factory(mode)` supplies an object with asynchronous
  `run(kind, trip: dict, emit: async callable(dict)) -> StepResult`.
  The factory is called independently for each concurrent kind; it may return
  a shared instance. Tests inject fakes and never contact providers.
- demo: `runai.guide.GuideEngine(runai.guide.fake.FakeDiscovery())`, `FakeRunner`.
- replay: same guide, `ReplayRunner(replay_path)` (default checked-in fixture).
- live: `GuideEngine(runai.discovery.linkup.discover)` and `LiveRunner`.
  Core binds discovery's `timeout_s=120` for deep searches: observed official
  race discovery takes longer than the provider's 20-second default. This is
  still real discovery; errors remain visible and never fall back to fakes.
  The live wrapper translates guide `months` to `month_from/month_to` (retaining
  a winter wraparound such as 12 -> 2) and `named` to `race_name`.
  Discovery needs `LINKUP_API_KEY`; confirmation needs `HAI_API_KEY` and all H
  task/client modules. Keys are read from environment only, never returned.

## JSON shapes

`Mode`: `demo | replay | live`; `Kind`: `registration | hotel | transport`.

`GuidedTurn` (owned by the guide):

```text
{message, question: string|null,
 suggestions: [{id,label,value,kind,provenance}], candidates: [RaceOption],
 draft, ready_to_confirm: boolean, error: string|null}
```

At most one focused question, clickable chips, and proposed official dates:
the user does not need to supply a date. Suggested origin/nights/budget are
clearly distinct from sourced race facts. No-results/date conflicts remain
visible; they must not silently become invented dates.

Complete trip dict passed to task builders:

```text
{race: {id,name,edition,distance_km,distance_label,race_date,date_status,
        city,country,official_url,registration_url,source_urls,retrieved_at,synthetic},
 origin_city, travelers, nights, budget_eur, arrival_date, departure_date}
```

Dates are ISO dates; retrieval/event timestamps are ISO datetimes. RaceOption is
the `race` object above, defined and validated by discovery/guide modules.

`StepResult`: `{kind,status,summary,handoff_url?,start_url?,final_url?,
live_view_url?,error?,reason_code?,synthetic,payment_executed:false}`.
Statuses: `ready_for_payment | blocked | failed`. `ready_for_payment` requires
a genuine handoff URL. `payment_executed` is literal false; no paid status exists.
Demo/replay handoffs are only official public homepages, **not prepared carts**.

`Event`: `{sequence,type,kind?,message,synthetic,observed_at,recorded_at?,
frame_id?,live_view_url?}`. Sequence is increasing from 1 per mission. Types:
`turn | discovery_progress | discovery_failed | confirmed | step_started |
step_progress | live_view_available | live_frame | step_finished`. `observed_at` is current UTC observation time;
`recorded_at` preserves original replay time. Frame bytes never enter mission JSON.

`Mission`: `{id,mode,synthetic,status,error: string|null,turns: [dict],trip: dict|null,
results: [StepResult],events: [Event],language?}`. No frozen framing or TARGET constant.
Statuses: `[discovering] -> guiding <-> ready -> running -> completed | partial | failed`.
`completed` means all three ready; `partial` means one/two ready; `failed`
means none ready (including three blocked outcomes). Individual blockers remain
visible in results. Synthetic is true for demo/replay, false for live.

## HTTP

| Request | Response |
| --- | --- |
| `POST /api/missions {text, mode?, background?}` | 201 Mission with first guided turn; **202** `discovering` Mission when `background:true` |
| `POST /api/missions/{id}/messages {text?,suggestion_id?,background?}` | 200 updated Mission; **202** `discovering` when `background:true` |
| `POST /api/missions/{id}/confirm {confirmed:true}` | **202**, running Mission; background preparation |
| `GET /api/missions/{id}` | 200 current Mission, results and ordered events |
| `GET /api/missions/{id}/events?after=N` | 200 event array with sequence strictly greater than N |
| `GET /api/frames/{frame_id}` | image bytes with MIME, no-store/nosniff and restrictive CSP |
| `GET /api/health` | `{mode,live_ready:{linkup:bool,h:bool}}`; booleans indicate key presence only |
| `GET /`, `GET /static/*` | index.html / static assets |

400: confirmation is false. 404: unknown mission/frame. 409: plan not ready,
duplicate confirmation, message after confirmation, message/confirm while
`discovering`, or a plan failing the confirmation gate (see below). 422: invalid/empty text,
empty message (both answer fields absent/blank), unknown mode, invalid guide
answer, non-boolean confirmation, negative event cursor. Both text and chip may
be sent together for guide-defined interpretation. Server `RUNAI_MODE` defaults
to demo; an unknown value raises a clean startup ValueError, not a request 500.
501: missing guide/live modules or required keys. Legacy `/reply` is removed.

Confirmation launches three asyncio tasks concurrently without waiting for them.
Each emits started/progress/frames/finished independently. Exceptions are isolated
as visible failed results; their raw text is not returned (may contain secrets).
Startup is single-process; shutdown cancels pending preparation tasks. The API
does not persist state across restarts or expose authentication; production
storage, quotas and authenticated access remain out of scope.

## Frames and live adapter boundary

`FakeRunner` emits three labelled SVG frames per kind and progress events.
SVG contains no third-party URLs or user-provided HTML. Live frames accept only
PNG/JPEG/WebP/GIF; maximum frame size is 5 MiB. Unsupported/empty frames become
an explicit unavailable progress message, never fabricated live footage.
The process retains at most 256 frames / 32 MiB, evicting the oldest across
missions. Evicted frame IDs return 404; clients should keep the latest frame
and treat expired earlier footage as unavailable rather than re-create it.

Live adapter: `runai.agents.<kind>.build_task(trip)` followed by
`runai.agents.hclient.HAgentRunner().run(task, on_event)`. Callback events:
`{type:"step_progress",message}`, `{type:"live_view_available",live_view_url}`,
`{type:"live_frame",image:bytes,mime,message?}`. Kind is assigned by the core,
not trusted from provider events. Only supported event types are forwarded.
Public authorized view URLs/frames and scrubbed step logs are the H client's
responsibility: never expose private H session URLs, tokens or personal data.
Core event/result validators also suppress credential/session/token URLs and
private H paths. Only the documented HTTPS regional H share path
`/share/api/v1/trajectories/{id}` is permitted for H-hosted public links.
The three task builders enforce site-specific pre-consent/pre-commitment stops;
the response schema is not itself a browser safety boundary.

`build_task` ValueError maps to blocked with the race official registration
page or genuine public hotel/transport homepage. H blocked results use the
task's `fallback_url` for manual continuation. Other exceptions become failed,
without synthetic success fallback; malformed ready results fail validation.

## Replay schema v2

`fixtures/synthetic-journey.json`:

```text
{schema_version:2, provenance:"synthetic", agents:{
 registration:{result:StepResult,steps:[{recorded_at,message,frame?:"<svg ...>SYNTHETIC...</svg>"}]},
 hotel:{result:StepResult,steps:[...]}, transport:{result:StepResult,steps:[...]}
}}
```

All three kinds required, result kind/provenance validated, payment false;
step timestamps must be ordered and timezone-aware. Other versions/provenance
are rejected. Original recorded timestamps appear on progress/frame events;
observed time remains current. Missing/corrupt/invalid replay files fail all
three steps visibly after 202 rather than causing an HTTP 500. Replay frames
are recorded synthetic illustrations and never evidence of a live booking.
Registration's manual homepage handoff follows the currently selected race,
not the example race in the synthetic recording; its summary states this.

## Round-2 pinned additive interfaces

All of these are additive and optional, so baseline main keeps working.
Consumers import sibling modules lazily. If a module or function is missing,
they treat the value as unknown and fail closed for H runs.

1. `runai.agents.site_policy.evaluate_url(url: str, kind: str) -> dict` (R2-02
   implements it; R2-03 calls it before creating any H session):
   `{allowed: bool, reason: str, policy_id: str|null, screenshot_scope: bool,
   allowed_hosts: [str], expires_at: ISO date|null}`. Unknown, expired, denied
   or ambiguous scopes return `allowed:false`. The function never raises.
2. `runai.agents.site_policy.registration_info(url: str) -> dict|None`
   (optional for R2-04): `{account_required: bool|null, captcha: bool|null,
   source: str, observed_at: ISO date}`. This is an observation, not a
   permission. `None` means unknown.
3. `RaceOption.registration_access` (optional; R2-04 adds it, R2-01 displays
   it): `null | {account_required, captcha, source, observed_at, note}`.
   Unknown is never shown as "login-free".
4. The `build_task(trip)` dict keeps its keys and adds `expected: {kind,
   race_name?, race_date?, distance_km?, city, country?, origin_city?,
   arrival_date, departure_date, travelers}` and `allowed_hosts: [str]`.
   `max_steps` can be up to 80; the H client caps it at 80.
5. Background discovery (R2-05 implements it; R2-01 uses it):
   - When `background` is true on create/messages, the endpoint resolves the
     guide synchronously, so missing keys/modules still return 501. It then
     returns 202 at once with `status:"discovering"`. Without the flag, the
     endpoints still return 201/200.
   - `discovery_progress` events are truthful and monotonic: a "started"
     event, heartbeats with the real elapsed seconds, then "finished". After
     that comes the usual `turn` event and the status becomes `guiding` or
     `ready`. Events never contain invented source counts or percentages.
   - Failure emits `discovery_failed` with a short generic message. It sets
     `Mission.error` and restores the previous status (`guiding` for a failed
     create, which has zero turns). The client retries by re-sending its
     message. A mission with zero turns runs the initial search again.
     A per-mission generation counter discards stale results.
   - While a mission is `discovering`, messages and confirm return 409.
6. Privacy: user text is redacted before the guide, state or events see it.
   This covers contact details, credentials and payment card/IBAN patterns;
   dates, budgets and distances are kept. Public turn/trip/event/result/error
   strings are sanitized again recursively. A 422 body has only
   `{loc,msg,type}`, with no echoed input. Request bodies and provider
   exception text are never logged.
7. Confirmation gate: confirm returns 409 unless all of these hold, even when
   the guide says ready:
   - status is `ready` and the latest turn is `ready_to_confirm`;
   - the race has a name and a future ISO `race_date`;
   - `arrival_date <= race_date <= departure_date` and arrival is before
     departure;
   - `nights` matches the stay, `travelers >= 1`, `origin_city` is set and
     `budget_eur > 0` when given.

   Live also requires `synthetic:false`, `date_status:"official"` and a public
   official or registration URL. Demo and replay require a synthetic race.
   Chips, "yes" or "ok" never launch.
8. Handoffs: Accor/Omio homepage fallbacks are removed. Blocked or failed
   results keep their own observed safe handoff, then the builder's
   `fallback_url`, otherwise `null`. For registration, the sourced race URL is
   used. No result is ever upgraded to `ready_for_payment`. Demo/replay
   hotel/transport handoffs are neutral synthetic example.com URLs.

## Round-3 pinned additive interfaces

Consumers import sibling modules lazily and fail closed when missing. These
additive interfaces supersede conflicting R2 runtime limits, not its safety rules.

### P1 Registry fragments
`site_policy.load_registry()` merges `docs/site-policy.json` with every
`docs/site-policy.d/*.json`, sorted by filename, using the same schema
`{schema_version, entries}`. Duplicate entry ids or overlapping
`(host,path_prefix)` scopes with different decisions raise `PolicyError`:
everything fails closed. R3-01 implements; R3-02 only ADDS
`docs/site-policy.d/registration.json`.

### P2 Registration adapters
Entries may carry adapters with `{kind:'registration',
race_match:{name_patterns:[regex], countries:[ISO2]?}, url_template,
success_evidence, blocked_evidence, platform_hosts:[str]}`. `url_template`
must use HTTPS on a reviewed host; placeholders occur only in query/fragment.
R3-01 makes `_adapter()` accept and validate them. Each `platform_hosts` entry
must be covered by an allowed, unexpired entry for purpose `registration`.
R3-02 consumes them.

### P3 Coverage
`site_policy.coverage(kind, *, country=None, city=None, origin_city=None,
today=None) -> {covered: bool, policy_ids:[str]}` never raises. R3-01 implements;
R3-04 may use it to order origin chips; R3-05 may use it for friendly blocked reasons.

### P4 Terminal reason codes
`StepResult.reason_code` is optional: null or one of `no_site_coverage`,
`policy_denied`, `date_mismatch`, `no_inventory`, `sold_out`,
`registration_closed`, `login_required`, `captcha`, `consent_required`,
`unreviewed_redirect`, `over_budget`, `step_limit`, `session_failed`, `timeout`,
`unsafe_claim`, `provider_error`. R3-05 adds it in models/providers; hclient sets
`result['reason_code']`. The UI maps it to a friendly FR/EN sentence plus next
step and falls back to status when absent. Builder ValueError maps to blocked
with `no_site_coverage`, or `policy_denied` when its message says denied, and
a friendly summary. No result is upgraded to success.

### P5 Live frame cadence
hclient emits each new observation screenshot within <=3 s of it appearing in
`/changes`, de-duplicated by image hash (H exposes no current-screenshot
endpoint between steps; see docs/evidence/h-client.md). Missing frames are never fabricated.
R3 runtime caps `max_steps` at 80 and each agent at 10 minutes, with remote
cancellation; it retries once on session failure only before progress.

### P6 Mission language
`Mission.language` is optional `'fr'|'en'`, from the latest guide turn language.
R3-04 exposes `GuidedTurn.language`; R3-05 copies it; R3-03 localizes plan and
agent cards, defaulting to browser/thread language when absent.

## Round-4 pinned additive interfaces

Consumers import sibling modules lazily and fail closed when missing. All
round-3 interfaces (P1–P6) remain in force.

### P7 Task alternatives
A builder task dict may carry `alternatives`: a list of task-like dicts with
`kind, site_name, start_url, fallback_url, instructions, success_signal,
stop_before, expected, allowed_hosts, max_steps`. R4-02
(hotel/transport) and R4-03 (registration) produce them; R4-01/hclient consumes
them. Round 7 supersedes the original retry rules: sequential alternatives may
follow `provider_error`, runtime `no_site_coverage`, or another frameless block.
Never continue after READY, any framed block, captcha, consent/terms, login,
policy denial, unsafe claims or `checkpoint_unverified`. Browser startup
unavailability receives one same-task retry after an injectable 20-second delay.
Each switch passes the policy gate and emits one step_progress
"Essai d’un autre site". The total agent wall-clock cap is 15 minutes including
queueing, retries and alternatives; each attempt retains its 10-minute cap.
The result is the first `ready_for_payment` attempt,
else the last attempt; never upgraded or merged. Missing, malformed or
policy-failing alternatives are skipped.

### P8 Registration coverage
`runai.agents.registration.registration_coverage(race, *, today=None,
registry=None) -> {covered: bool, status: 'open'|'sold_out'|'not_open'|'closed'|
'unknown', policy_id: str|None, observed_at: str|None, prohibited: bool}`.
Pure, offline, never raises; observations older than 21 days are `unknown`.
`covered` means `build_task` would succeed. R4-03 implements; R4-04 consumes.

### P9 RaceOption.preparation
`RaceOption` gains optional `preparation: {registration: 'covered'|'sold_out'|
'not_open'|'closed'|'prohibited'|'uncovered'|'unknown', hotel: bool|null,
transport: bool|null, origin_city: str|null}`. R4-04 produces it lazily (P8 and
P3; missing modules give `unknown`/null); R4-05 renders badges when present.
It is display-only: `trip_payload` and the app strip it, so builders receive the
CONTRACTS trip dict unchanged.

### P10 hclient fallback gate (handoff-only)
`start_url` (and each alternative's `start_url`) is a navigation scope checked
as before: public HTTPS, not Accor, allowed, unexpired review with policy id and
screenshot scope, host and path inside review hosts ∩ task `allowed_hosts`.
`fallback_url` is a handoff-only link: it must be public HTTPS, not Accor,
`evaluate_url(fallback_url, kind)` allowed and unexpired, but its host need not
be in task `allowed_hosts` and it never widens navigation reviews. A denied,
expired or unknown `fallback_url` still blocks before any H session. Startup
observations whose URL is exactly `about:blank` (or empty) are skipped without
frame, progress or final URL; 45 s or 3 such observations before the first
reviewed page end blocked `provider_error`. A session that fails after reviewed
progress ends blocked `session_failed` with the last reviewed public URL as
handoff.

### P11 H deterministic observed checkpoints (round 5)
A task and each P7 alternative may carry optional
`checkpoint: {url_patterns: list[str], beyond_patterns: list[str]}`.
Both lists contain case-insensitive regexes matched against the **unquoted
path + '?' + query** of a policy-reviewed observed URL, never a suggested URL.
`url_patterns` must be nonempty. Invalid types/regexes disable the checkpoint
and fail closed for READY when the key is present. Tasks without the key retain
normal verification. Patterns are private stop-page hints in H's prompt, never
user-facing messages.

At an observed checkpoint the client emits its genuine observation frame,
requests `POST /sessions/{id}/force_answer` once, then waits at most 60 seconds.
READY still requires all existing kind-specific `_verified` evidence, a frame
for the final observed URL, and handoff == the observed checkpoint URL. A later
page outside that checkpoint cannot be READY. At `max_steps-3` (or an accepted
provider step_limit) force_answer is requested once, with <=45 seconds to answer.
The max step cap remains 80. No synthetic frame or unobserved claim establishes
readiness. These are observation/cancellation boundaries, not a tool interceptor.

`beyond_patterns` take precedence: cancel immediately, block `policy_denied`
(or `unsafe_claim` for a payment/booking admission), never READY. Preserve the
last reviewed checkpoint URL for handoff if one was observed; otherwise existing
policy-checked fallback rules apply. Never enter data, submit forms, consent,
book or pay to reach a checkpoint.

H startup reads status from create/changes. `queued`/`pending` pause the 45-second
and 3-blank-observation startup limits and the per-agent 10-minute active budget.
Emit "En attente d'un navigateur disponible" once; total queue wait is capped at
8 minutes, then blocked provider_error. Each create (including one pre-progress
retry) gets a fresh Idempotency-Key. Browser-internal URLs (`about:`, `chrome:`,
`chrome-error:`, `data:`, `blob:` and empty) are blank observations, not redirects.
Real metrics.steps emit monotonic friendly "Étape N" activity, never fake frames.
App/LiveRunner continue to launch all three kinds concurrently; quota queueing
does not serialize a mission. Round 7 includes queue time in the shared
15-minute P7 wall-clock cap; the eight-minute cumulative queue limit remains.

`StepResult.blocked_url_host: str|null` is additive: the scrubbed public host +
path of an unreviewed redirect, **without scheme, query, fragment, credentials
or private identifiers**. It may appear in internal step logs, never raw in UI
copy. Invalid/private values are discarded by the model and API sanitizer.

### P13 Observed but unverified checkpoints (round 6)

`StepResult.checkpoint_reached: bool|null = null` and reason code
`checkpoint_unverified` are additive. A reviewed public checkpoint observed with
a genuine frame may be handed off when the final answer fails verification:
status remains `blocked`, checkpoint_reached is true, and handoff_url is that
observed checkpoint (handoff-only, P10; never a wider navigation scope).
Friendly copy: « Étape de réservation atteinte — à vérifier sur le site »
(EN: “Booking step reached — verify on the site”). Explicit safety/site blockers
and date mismatches keep their precise reasons. Verification failures never use
provider_error. Internal steps alone may contain `verify_failed: [gate names]`,
never extracted values or personal data; diagnostics are not UI copy.

READY still requires complete selected evidence, matching dates/party/city,
a genuine frame of the final checkpoint, a reviewed handoff equal to the observed
URL after scrubbing (query-key ordering is immaterial; values and duplicate-value
order must match), and no beyond-pattern. Scrubbing drops known tracking query
parameters, not booking dates or party. IHG qCiMy/qCoMy encode zero-based months:
062027 is July 2027. Verification dates must be ISO dates of the actual stay.
The optional field passes through model-based provider/API serialization; old
synthetic fixtures remain valid without it.

### P12 Gateway city and fragment-routed starts (round 5)
`expected.gateway_city: str` is optional for hotel/transport. Verification city
may match expected.city **or** gateway_city using existing accent/case-normalized
substring equality; no arbitrary third city is permitted. All dates, travelers,
origin and selection evidence remain required and unchanged.

`keep_fragment: true` opts a task into a fragment-routed start URL (e.g. NS
International `#/...`). Retain only a public fragment whose route and query
survive scrubbing unchanged, with the fragment-less URL policy-reviewed and
unchanged by scrub_url. Sensitive/changed fragments or absent/false flags strip
the fragment as before. This never widens allowed hosts/paths. No raw fragment
or private URL is exposed as progress copy.
