# Generic guided-mission contract

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
live_view_url?,error?,synthetic,payment_executed:false}`.
Statuses: `ready_for_payment | blocked | failed`. `ready_for_payment` requires
a genuine handoff URL. `payment_executed` is literal false; no paid status exists.
Demo/replay handoffs are only official public homepages, **not prepared carts**.

`Event`: `{sequence,type,kind?,message,synthetic,observed_at,recorded_at?,
frame_id?,live_view_url?}`. Sequence is increasing from 1 per mission. Types:
`turn | discovery_progress | discovery_failed | confirmed | step_started |
step_progress | live_view_available | live_frame | step_finished`. `observed_at` is current UTC observation time;
`recorded_at` preserves original replay time. Frame bytes never enter mission JSON.

`Mission`: `{id,mode,synthetic,status,error: string|null,turns: [dict],trip: dict|null,
results: [StepResult],events: [Event]}`. No frozen framing or TARGET constant.
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
   `max_steps` can be up to 80; the H client caps it at 120.
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
