# H client: private screenshot transport and evidence boundary

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
  authentication. Legacy trajectory paths do not. At most six download hops;
  each destination must be public HTTPS without URL credentials. External hops
  have empty Authorization (also overriding a supplied client's default).
  PNG/JPEG/WebP MIME agreement and a 5 MiB content limit are checked. Consumers
  receive bytes, never resource URLs. Terminal events keep draining through a
  final empty response, including HTTP 204.
- `max_steps` counts decide-and-act cycles: minimum 1, no documented provider
  maximum. The client defaults to 80 and clamps at 120. At the provider cap H
  asks for a final answer; it does not kill the agent. Likewise `max_time_s`
  requests an answer and allows a further 60 seconds before provider failure.
  Independent local timeout defaults to 600 seconds and is bounded at 900.
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
policy lists. A null expiry means no expiry; a past date is blocked. Optional `allowed_paths` prefixes are
honored; the pinned host-wide interface otherwise uses `/`.

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
claims cannot become ready. Handoff must match the observed page's host/path
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
