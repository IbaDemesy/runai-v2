# H client: private screenshot transport and evidence boundary

## R5-01 runtime integration — 2026-11-09

- Queue-aware startup reads nested create status and changes status. Pending/
  queued browsers emit one honest waiting line, pause the startup/active clocks,
  and are capped at eight total queued minutes. Creates and pre-progress retry
  use independent Idempotency-Key values; three mission agents remain concurrent.
- P11 compiles task/alternative stop and beyond patterns, case-insensitively
  against decoded observed path/query. Checkpoint frames precede force_answer;
  READY requires final checkpoint URL equality and unchanged kind verification.
  Beyond pages cancel immediately and preserve only a reviewed checkpoint link.
  Step budgets request an answer three steps early; waits are bounded.
- P12 permits only the race city or declared gateway city, and preserves only
  scrub-clean opted-in fragment routes with reviewed fragment-less URLs.
- Redirect diagnostics contain public host/path only, never query/fragment or
  keys; browser-internal URLs are blanks. UI progress contains only friendly
  messages, with monotonic provider metrics steps. No images are fabricated.
- Njuko's known public event/widget identifiers survive URL and API scrubbing;
  query/text contacts and arbitrary opaque paths remain redacted. Real H may
  serialize `verification` as JSON text despite the object answer schema: decode
  valid object JSON before normal verification; malformed values fail closed.

Official API references reviewed before POST changes:
[create/idempotency](https://hub.hcompany.ai/agents-api/sessions/create.md),
[changes/status](https://hub.hcompany.ai/agents-api/sessions/changes.md),
[force_answer](https://hub.hcompany.ai/agents-api/sessions/force-answer.md).
force_answer asks an agent to answer on its next step and can restart a finished
session; the client cancels after consuming a forced final answer. Observation
monitoring is not a tool-level interception guarantee.

### Live smoke boundary

2026-11-09: three sequential single-session read/prepare-only Milan registration
smokes, quota checked before each (limit 3, available 3). Njuko is the reviewed
official registration platform; its allowed owner-rule review permits only this
public preparation scope and in-session screenshots. No captcha bypass, data,
consent, submission, booking or payment was attempted. No images or private H
ids/URLs were published or committed.

Both started pending, then running at 7.2 seconds, showed genuine changing
frames and reached the untouched participant form:
`https://in.njuko.com/wizz-air-milano-marathon-20271776152378557?currentPage=form_individual-form`.
force_answer returned 202 once in each. First: four frames, max inter-frame gap
18.5 s, 48.0 s elapsed. Second: six frames, max gap 22.8 s, 74.6 s elapsed.
Both honestly ended blocked provider_error because H returned string-valued
verification, exposing a pre-existing AttributeError in blocked classification.
This is fixed with guarded JSON decoding and offline malformed-type regressions.
Neither is claimed as READY. A third smoke after the fix reached the same
untouched participant form and returned ready_for_payment with handoff exactly
equal to that observed checkpoint, force_answer 202 once, six real frames,
25.3 s max inter-frame gap, 78.7 s total; pending at 1.7 s, running at 7.1 s.
This is one registration-only runtime success, NOT a three-agent UI success.
Integrated UI acceptance is reserved for PR-B after the other R5 tickets merge.

## R4-01 runtime changes — 2026-11-09

Offline synthetic regression evidence only; no live certification.

The owner's H documentation review found no endpoint for a current browser
screenshot between steps. Screenshots are per-observation resources:
`GET /sessions/{id}/resources/screenshots/<key>` redirects (302) to a presigned
URL. OpenAPI access is restricted to H employees; it is not used here.
References: [changes](https://hub.hcompany.ai/agents-api/sessions/changes.md),
[status](https://hub.hcompany.ai/agents-api/sessions/status.md),
[resources](https://hub.hcompany.ai/agents-api/sessions/resources.md),
[observe and steer](https://hub.hcompany.ai/agents-api/observe-and-steer.md).

- Long polls wait at most two seconds. Each new reviewed observation's image
  is fetched immediately after its changes batch, with a three-second download
  bound. Failed transient fetches are retried, not successful payloads. SHA-256
  deduplication remains. A fake-clock regression proves distinct frames emit
  within three seconds of arrival under successful mocked downloads; network
  failures cannot guarantee delivery. No between-step frames are fabricated.
- French progress lines are short, fixed, and emitted only when they change;
  provider task, prompt and action text are never progress messages.
- Fallback URLs are public HTTPS, non-Accor, unexpired policy-approved handoff
  links only. They do not expand the task's reviewed navigation scopes.
- Raw about:blank, empty and missing observation URLs produce no progress,
  final URL or frame. Before a reviewed page, three blanks or 45 monotonic
  seconds block startup as provider_error and stop the session. Later blanks
  are ignored. Nonblank unreviewed redirects remain immediately blocked.
- P7 alternatives use at most the first two supplied entries, within the
  original ten-minute maximum budget. Invalid, kind-mismatched and policy-denied
  alternatives are skipped. Only blocked unreviewed_redirect, provider_error,
  no_inventory, sold_out, captcha and session_failed allow another attempt.
  Results are never merged or upgraded: return first READY or last attempt.
- Failed/interrupted sessions after reviewed progress return blocked
  session_failed with the last reviewed public URL and a friendly resume line;
  they are stopped before any alternative starts. Pre-progress retry stays
  limited to one fresh session. All attempts share the event consumer.

## R3-05 runtime changes — 2026-11-09 UTC

Offline regression coverage, not live certification:
- Unsafe claims are checked by clause (sentence punctuation, commas, colons,
  semicolons and but/however/mais; never and/or). Negation and conditional
  markers neutralize a claim in that clause, including trailing conditional
  boundaries such as "payment is completed only after clicking Pay". URLs,
  field names and stop_before echoes are not execution evidence. Affirmative
  EN/FR claims and explicit true execution flags still cancel the session.
- Every terminal H result includes a P4 reason_code (null only when ready).
  Policy, redirect, login/captcha, timeout, step-limit, failed-session, unsafe
  and provider failures are distinguished. Completed blockers use EN/FR/ES/IT/
  PT/DE keywords; mismatched verification dates have their own code. Prompts
  require immediate stops on no inventory, sold out, closed, login, captcha
  and required consent, not repeated searching until the step cap.
- Changes long-polls are capped at three seconds. Only the latest observation
  image in each batch is fetched; later cycles retry the latest image, including
  transient network/5xx failures. Download attempts have a three-second bound;
  polling consumes only the remaining cadence budget. SHA-256 suppresses
  duplicate frame emissions. Existing MIME/size/redirect/bearer isolation and
  no-share guarantees remain. No screenshot endpoint or footage is invented.
- A failed/interrupted session before any observation is cancelled and retried
  once with a fresh session, under the same policy decision and overall time
  budget. There is no retry after an observation. Max steps is 80; local wall
  clock is at most 600 seconds, with remote DELETE on expiry/cancellation.

The cadence fake-clock test uses synthetic image bytes and does not prove live
provider cadence. Live acceptance is pending after the other R3 tickets merge.

## R2-03 documentation review — 2026-11-08 UTC

Reviewed official H Agents API documentation before changing requests:
[create](https://hub.hcompany.ai/agents-api/sessions/create.md),
[changes](https://hub.hcompany.ai/agents-api/sessions/changes.md),
[event objects](https://hub.hcompany.ai/agents-api/sessions/event-object.md),
[resources](https://hub.hcompany.ai/agents-api/sessions/resources.md),
[cancel](https://hub.hcompany.ai/agents-api/sessions/cancel.md), and
[cloud browser](https://hub.hcompany.ai/agents-api/browser/configuration.md).

- No public sharing request is made. `live_view_url` remains null. No H
  session, share or resource URL is returned to consumers, including formerly
  allowed public trajectory URLs. A broken share endpoint is irrelevant.
- Images come from genuine observation-event base64 or URL sources. Only the
  exact API-origin `/api/v2/sessions/<own session>/resources/` path gets bearer
  authentication. Same-origin, own-session legacy trajectory resource URLs are
  normalized to that documented v2 endpoint before fetching (query preserved).
  Foreign-host or cross-session legacy URLs are never normalized/authenticated.
  At most six download hops;
  each destination must be public HTTPS without URL credentials. External hops
  have empty Authorization (also overriding a supplied client's default).
  PNG/JPEG/WebP MIME agreement and a 5 MiB content limit are checked. Consumers
  receive bytes, never resource URLs. Terminal events keep draining through a
  final empty response, including HTTP 204.
- `max_steps` counts decide-and-act cycles: minimum 1, no documented provider
  maximum. The client defaults to 80 and clamps at 80. At the provider cap H
  asks for a final answer; it does not kill the agent. Likewise `max_time_s`
  requests an answer and allows a further 60 seconds before provider failure.
  Independent local timeout defaults to 600 seconds and is bounded at 600.
  Provider `max_time_s` is 90 seconds shorter (510 by default) to leave room for
  its final-answer grace period; local timeouts of 90 seconds or less instead
  give the provider half the local budget.
  Active step-cap observation, timeout, client cancellation, unsafe claims,
  HTTP/parse/callback failures and unauthorized observations trigger DELETE.
  Failed remote cancellation is explicitly reported, not treated as success.
- Documented `delete_after_min` and `delete_screenshot_after_min` are both 60:
  provider evidence is short-lived, not automatically published or retained
  indefinitely by the request. The application frame store is separately owned.

## Pre-run authorization and hosted-action limitation

Lazy `runai.agents.site_policy.evaluate_url(url, kind)` is called before any H
session creation. Missing module/function, exceptions, denied/unknown/expired
review, missing policy identifier, missing screenshot scope or forbidden Accor
destination blocks with zero provider create calls. The pinned result is
`allowed`, `reason`, `policy_id`, `screenshot_scope`, `allowed_hosts`,
`expires_at` (ISO date). Mapping and attribute-style results are supported.
The actual start and fallback URLs are reviewed for the task kind; no synthetic
domain-root evaluations are made. Every task `allowed_hosts` entry must be
included in the returned reviewed scope. Effective hosts intersect task and
policy lists. A null expiry means no expiry. Date-only reviews remain valid
through that UTC date; timestamp expiries compare the full instant (naive
timestamps mean UTC). Optional `allowed_paths` prefixes are
honored on path-segment boundaries (`/race` does not authorize `/race-private`);
the pinned host-wide interface otherwise uses `/`.

The reviewed hosts/path prefixes are explicit in the hosted instructions.
Observed unauthorized destinations or login/account/captcha/payment-card signals
in URL paths/queries and page titles cause cancellation before frame forwarding.
Page markdown/navigation text is not scanned for these signals, and checkout
alone does not cause observation-time cancellation; handoff restrictions remain.
There is no documented pre-action host allowlist/interception field in the
reviewed API. **Prompt instructions and post-observation cancellation are not
an enforceable per-action firewall.** They cannot prove a forbidden action never
occurred between observations. A flow requiring a forbidden action must remain
blocked; never rerun it to bypass the boundary. No authenticated/personal pages,
profiles or vaults may be used. There is no OCR redaction guarantee: suspected
sensitive frames are suppressed, not stored with a claim of anonymization.

## Honest outcomes and user-visible surface

The prompt and structured schema include task `expected` plus kind-specific
verification. Ready requires selected options and a next safe boundary:

- Registration: edition, date, distance, untouched participant-data boundary.
- Hotel: selected room/rate, stay dates, party size and total.
- Transport: selected outbound AND return, fare, route, arrival/return dates,
  party size and total.

Only kind-relevant expected values are compared: race date/distance/name/edition
for registration; stay dates/travelers/city for hotel; origin/city and travel
dates/travelers for transport. Dates normalize to their ISO date, travelers to
integer equality, distance to within 0.5 km (numeric strings/units accepted),
and names to accent-insensitive casefolded containment. Verification schemas
exclude unrelated trip fields. Missing expected/verification fields,
blockers/account walls, non-success provider outcomes, homepages, unselected
search results, private URLs, contradictory ISO URL dates or unsafe action
claims cannot become ready. Scrubbed handoff must equal the last observed URL,
including its selected room/fare/date query parameters,
and a genuine frame for the latest observed context must have been received.
**Model-reported verification is not external proof. Final human inspection
of screenshot evidence is required**, even for a structurally accepted result.

Only curated browser-start/browsing statuses and short classified terminal
summaries/errors are returned. Policy/message text, reasoning, tools/arguments,
task echoes, raw reached-step prose and raw provider errors are never user logs.
Sanitizers suppress contact, financial and credential patterns while preserving
ISO dates, ordinary budgets, distances and public event/date/route URLs. This
is defense in depth, not a promise to identify arbitrary personal pixels/text.

## R2 live smoke status — blocked before provider creation

At implementation time the R2-02 reviewed policy module/registry was not present
on this branch. No R2 live H session was created (zero of three allowed runs).
Do not bypass the gate with a fabricated review or reuse historical R1 sharing
evidence. After R2-02 lands, select one narrowly authorized public read-only
page under its current purpose AND screenshot scope, inspect its terms review,
run one bounded smoke, inspect real image bytes, and record the actual safe
stop/blocker here. Do not call a homepage/read-only smoke a prepared checkout
or the owner's three-agent product success. Historical R1 runs used sharing;
they do not validate this private R2 transport.

Offline MockTransport checks cover policy rejection without creation, no share
requests, bounded budgets, terminal final-frame/204 drain, authenticated resource
redirects, MIME/size rejection, forged verification, unsafe observations and
cancellation failure. CI never calls live providers. See R2-03 handoff for output.
