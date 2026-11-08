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
`turn | confirmed | step_started | step_progress | live_view_available |
live_frame | step_finished`. `observed_at` is current UTC observation time;
`recorded_at` preserves original replay time. Frame bytes never enter mission JSON.

`Mission`: `{id,mode,synthetic,status,turns: [dict],trip: dict|null,
results: [StepResult],events: [Event]}`. No frozen framing or TARGET constant.
Statuses: `guiding -> ready -> running -> completed | partial | failed`.
`completed` means all three ready; `partial` means one/two ready; `failed`
means none ready (including three blocked outcomes). Individual blockers remain
visible in results. Synthetic is true for demo/replay, false for live.

## HTTP

| Request | Response |
| --- | --- |
| `POST /api/missions {text, mode?}` | 201 Mission with first guided turn |
| `POST /api/missions/{id}/messages {text?,suggestion_id?}` | 200 updated Mission |
| `POST /api/missions/{id}/confirm {confirmed:true}` | **202**, running Mission; background preparation |
| `GET /api/missions/{id}` | 200 current Mission, results and ordered events |
| `GET /api/missions/{id}/events?after=N` | 200 event array with sequence strictly greater than N |
| `GET /api/frames/{frame_id}` | image bytes with MIME, no-store/nosniff and restrictive CSP |
| `GET /api/health` | `{mode,live_ready:{linkup:bool,h:bool}}`; booleans indicate key presence only |
| `GET /`, `GET /static/*` | index.html / static assets |

400: confirmation is false. 404: unknown mission/frame. 409: plan not ready,
duplicate confirmation, or message after confirmation. 422: invalid/empty text,
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

Live adapter: `runai.agents.<kind>.build_task(trip)` followed by
`runai.agents.hclient.HAgentRunner().run(task, on_event)`. Callback events:
`{type:"step_progress",message}`, `{type:"live_view_available",live_view_url}`,
`{type:"live_frame",image:bytes,mime,message?}`. Kind is assigned by the core,
not trusted from provider events. Only supported event types are forwarded.
Public authorized view URLs/frames and scrubbed step logs are the H client's
responsibility: never expose private H session URLs, tokens or personal data.
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
