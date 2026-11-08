# H browser client — API and live evidence

## Official API reviewed, 2026-11-08

Base: `https://agp.eu.hcompany.ai/api/v2` (documented EU region).
Authentication: `Authorization: Bearer $HAI_API_KEY`, supplied in memory only.
No API keys, provider session identifiers, private session URLs or screenshot
resource URLs are recorded here. This client has no city/race-specific path.

| Operation actually used | Official documentation | Client behavior |
| --- | --- | --- |
| `POST /sessions` | [Create](https://hub.hcompany.ai/agents-api/sessions/create.md), [structured answers](https://hub.hcompany.ai/agents-api/structured-output.md) | `h/web-surfer-flash`, safety instructions, start URL override, JSON answer schema, one-shot task, time and step limits |
| `GET /sessions/{id}/changes?from_index=…&wait_for_seconds=…` | [Changes](https://hub.hcompany.ai/agents-api/sessions/changes.md) | Long-poll, handle 204, advance cursor, drain terminal events before reading the answer |
| `GET /sessions/{id}` | [Retrieve](https://hub.hcompany.ai/agents-api/sessions/retrieve.md) | Read `latest_answer` if a drained terminal changes response has no answer |
| `POST /sessions/{id}/share` | [Share](https://hub.hcompany.ai/agents-api/sessions/share.md) | Resolve documented relative `share_url` on the same API origin; emit only HTTPS `/share/` URLs documented as public/key-free |
| `GET <AgentEvent.data.image.source>` | [Event images](https://hub.hcompany.ai/agents-api/sessions/event-object.md), [resources](https://hub.hcompany.ai/agents-api/sessions/resources.md) | Download provider-returned image source, following its redirect to image bytes; inline base64 images also supported |
| `DELETE /sessions/{id}` | [Cancel](https://hub.hcompany.ai/agents-api/sessions/cancel.md) | Cancel on local timeout, asyncio cancellation, observed step cap, unsafe claims, HTTP/parse/consumer failure; caller cancellation propagates |
| `GET /sessions?search=…&created_after=…&size=…` (smoke reconciliation only) | [List](https://hub.hcompany.ai/agents-api/sessions/list.md) | Locate only this ticket's interrupted smoke after its shell output was interrupted; not used by `HAgentRunner` |

The resource docs show `GET /sessions/{id}/resources/{bucket}/{key}` with a 302
redirect. Real `image.source` values in this smoke used an older
`/api/v1/trajectories/{id}/resources/{bucket}/{key}` shape. **The client follows
the API-returned source; it never constructs or guesses this legacy endpoint.**
Only same-provider-origin, own-session API resource URLs receive the bearer;
external/signed image URLs never do. Every redirect is validated again before a
request (public HTTPS, no URL credentials; at most six hops); bearer scope is
recomputed per hop. Emit image **bytes**, MIME and observed time, never a resource URL.
Ignore raw `LiveViewUrlEvent` and `agent_view_url`: these are not documented as
public, key-free shares. Do not persist the share link in repository evidence.

## Safety boundary

- Every task includes `GUARDRAILS`, task instructions, `stop_before`, the success
  signal and a required structured final answer. Higher-priority agent
  instructions repeat the guardrails. No profiles, vaults, logins or personal
  information are supplied. Cookie rejection/necessary-only dismissal is the
  only allowed banner interaction; otherwise stop.
- The client defaults to 30 steps, clamps task requests to 50, and defaults to a
  600-second local wall-clock timeout. It requests provider `max_steps` and
  `max_time_s` too. If polled metrics reach the cap while still active, cancel.
  Provider caps ask the agent for a final answer rather than hard-killing it;
  local cancellation happens at observation/timeout, not synchronously per click.
- Missing keys raise `HUnavailable`. HTTP/timeouts return `failed`, never fake
  success. Failed remote cancellation is reported in the result error.
- A successful handoff requires an actual HTTPS public URL; missing/invalid
  links or a blocker downgrade to `blocked`. Never substitute a fallback URL to
  manufacture success. Payment/booking execution claims fail and cancel the run.
- Messages and URLs strip known keys, contact details, URL credentials,
  fragments and sensitive query parameters before emission/return. H URLs are
  suppressed except the exact regional public-share path documented above.
  Raw reasoning/tool arguments and user-prompt echoes are not exposed. Query removal
  may invalidate a session-bound checkout; no prepared-cart claim is made.
- **Not a deterministic browser-action firewall:** H's documented hosted
  [browser actions](https://hub.hcompany.ai/agents-api/browser/configuration.md)
  are fixed and cannot be intercepted by this HTTP client. Prompt restrictions,
  caps and post-action claim rejection reduce risk but cannot prove that an
  action never occurred. Screenshots are anonymous public-page pixels, not OCR
  redacted; do not use this runner with authenticated/personal pages. Stronger
  per-tool enforcement would require a provider-supported action gate.
- Failed screenshot/share HTTP requests deliberately fail closed and cancel
  the run, matching the ticket's HTTP-error contract. They do not silently
  degrade to apparently successful preparation without its live surface.
- Post-review offline hardening covers private/insecure screenshot redirects,
  mixed negation/payment claims, session/opaque/contact path URLs, date query
  preservation and cancellation failure reporting for malformed responses and
  callbacks. Public sharing publishes the provider trace: do not run this
  client on sites whose policies disallow redistributing live footage.

## Live smoke — 2026-11-08 UTC (owner-approved, read-only)

Public official target: [Maratona Clube de Portugal](https://maratonaclubedeportugal.com/en/),
EDP Lisbon Half Marathon. This is link-discovery only, **not** registration,
payment-page preparation, a three-agent product run, or a Milan-only fixture.

Site review before the final smoke:

- [robots.txt](https://maratonaclubedeportugal.com/robots.txt) disallows only
  `/wp-admin/` and allows the AJAX endpoint; public race-information pages are
  not disallowed. Robots policy is not affirmative legal authorization.
- [Privacy policy](https://maratonaclubedeportugal.com/privacy_policy.pdf) and
  [2027 half-marathon rules](https://maratonaclubedeportugal.com/wp-content/uploads/REGULAMENTO_EDP_MEIA_MARATONA_DE_LISBOA_2027_EN.docx.pdf)
  were read/extracted. No automated-agent/robot/scraping prohibition was located;
  the rules' "automatic" reference concerns transferring entries on postponement.
  This is a bounded policy review, not a representation of express site approval.
- No third-party registration page was to be opened. Stop before any form,
  personal data, terms/consent, account, submission, captcha or payment.

### Attempt 1 — interrupted, not counted as success

- Provider created at `2026-11-08T20:32:01.045199Z`; finished
  `2026-11-08T20:33:32.975514Z` (provider latency **91.93 s**).
- Start/end observed URL: `https://maratonaclubedeportugal.com/en/`.
- Observed public race detail URL during navigation:
  `https://maratonaclubedeportugal.com/en/corrida-marco/edp-lisbon-half-marathon/`.
- Reconciliation of the documented status/changes API showed **interrupted at
  15 steps**, with 14 screenshot observations available. Its latest answer
  claimed a registration link; **this is not accepted as a successful run**.
  Original shell stdout was unavailable after a tool interruption; status,
  timings and observation counts above were recovered from the provider.
- A second, narrower one-page task was used to avoid exploratory navigation.

### Attempt 2 — real provider completion, client timeout exposed a bug

- Client start `2026-11-08T20:34:18.547572Z`, end
  `2026-11-08T20:37:18.809635Z`, measured **180.26 s**.
- Start/end observed URL:
  `https://maratonaclubedeportugal.com/en/corrida-marco/edp-lisbon-half-marathon/`.
- H itself completed at `2026-11-08T20:35:12.546978Z`, nine steps, **53.39 s**
  after provider creation. Its structured answer identified the public official
  link `https://meia-maratona.inscricoes.maratonaportugal.com/default.aspx?prova_id=3767`.
  The third-party registration page was not opened; no form was filled.
- The client emitted a documented public-share event and **8 actual PNG frame
  events**, but incorrectly returned `failed: H run timed out`. It had received
  terminal events, then H returned HTTP 204 for the drained stream. The client
  previously treated every 204 as "keep waiting". Timeout called DELETE (safe
  no-op on the already-completed session).
- Fixed by retaining the last terminal state and treating a subsequent 204 as
  drained. Added a MockTransport regression for this exact live-observed case.
  This attempt is **not** recorded as a successful client run.

### Attempt 3 — final post-fix verification

- Client start `2026-11-08T20:37:59.311035Z`, end
  `2026-11-08T20:39:54.787312Z`, measured **115.48 s**.
- Start/end observed URL:
  `https://maratonaclubedeportugal.com/en/corrida-marco/edp-lisbon-half-marathon/`.
- **Result: `blocked`**, retaining the same official public page as handoff.
  The agent reported that the half-marathon registration CTA could not be
  verified as a public link on that page without further interaction; other
  visible registration links referred to different concurrent races. This is
  an agent-reported blocker, not a claim that registration does not exist.
- **Observed stream: 10 real PNG frame events, 1 documented public-share event,
  12 step-progress events.** Action-name progress excludes arguments, raw
  reasoning and user-prompt echoes. The client drained the terminal stream and
  returned promptly rather than waiting for its 180-second timeout.
- Safe stop: remained on the public official race-information page; no
  third-party registration form was opened, no data entered, no terms accepted,
  no submission/payment/booking attempted. Evidence is the anonymous API trace
  and observed page sequence, not a tool-level proof of all negative actions.
- **No successful pre-payment preparation is claimed.** This validates the
  real client transport, public sharing, screenshots and honest blocked outcome.
  It does not establish the owner's three-agent live product criterion.
- Three live runs total; no further live attempts made for this ticket.
