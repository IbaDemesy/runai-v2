# R7-03 Booking offline diagnosis — 2026-11-09

No further H sessions. Rebuilt the exact Berlin task from the smoke: same race,
dates, one adult and EUR600 budget, same Booking adapter, alternatives removed.
Found a deterministic adapter false positive: the bare `checkout` alternative
in beyond_patterns matches `checkout=2027-09-27` in the search URL. P11 matches
unquoted path plus query, not just the path. The original pattern matches both
the raw and scrub-normalized search URL before any room/rate selection.

### Gates and attempted disproof

| Check | Exact start and fallback result |
|---|---|
| evaluate_url | allowed; policy r7-booking-hotel; hosts www.booking.com; paths / |
| hclient._policy | ALLOW: [({'www.booking.com'}, ('/',))] |
| Task allowed_hosts subset of reviewed hosts | true |
| scrub_url(raw) == raw | false: `%2C%20DE` canonicalizes to `%2C+DE` |
| _reviewed(raw) / _reviewed(scrub_url(raw)) | false / true |
| Original beyond_patterns against raw/cleaned search | true: bare checkout matches the departure-date query key |
| Fixed beyond_patterns against raw/cleaned search | false |

The raw scrub inequality is not a blocking scrub rejection: hclient._attempt
uses clean_url at startup and for observations before _reviewed. Normalized
URLs pass review. Creation in the real smoke independently rules out a
pre-session denial. No core scrub/hclient change is needed for this defect.

The reachable observation dispatch in hclient._attempt checks _reviewed, then
beyond_patterns, then title/URL restrictions, and only afterward assigns
final_url or emits a frame. Thus an observation retaining the checkout date
query deterministically raises policy_denied with no final page/frame. This
explains the symptom for that input, but **the original first H observation
was not retained: its actual URL/title, and therefore the historical causal
link, remain unverified**. Title restrictions could also yield policy_denied;
the live trigger cannot be conclusively identified from the retained result.

Anonymous `curl -sI -L --max-time 45 --max-redirs 10` of the exact deep link:
```
HTTP/2 301
location: https://www.booking.com/searchresults.html
HTTP/2 202
```
The Location omitted the original query; only www.booking.com was observed.
HEAD redirects are not proof of the H browser's redirect chain or UI state.
Hypothetical www.booking.com/searchresults.en-gb.html passes the existing /
scope. secure.booking.com/book.html and account.booking.com are not reviewed,
but would raise unreviewed_redirect, not the reported policy_denied. Neither
host appeared in this curl chain; no speculative scopes were added.

### Fix and limits

docs/site-policy.d/hotel.json: Booking's bare `checkout` becomes `/checkout`.
This excludes the date query key while still blocking real checkout paths,
including nested next=/checkout/ URLs and encoded/case-insensitive variants.
Guest, payment, confirmation and selected-room checkpoint rules are unchanged.
tests/test_agent_hotel.py reproduces the exact task, reviews normalized URLs,
excludes search/localized search from both stop patterns, and preserves unsafe
path blocking. Initial tests exposed that a path-only anchor would miss unsafe
nested next URLs; used `/checkout` instead and kept all existing tests intact.
**Offline fix only; not re-verified live. Booking remains a blocked smoke.**

### B&B Milan follow-up

Reviewed the existing selected-state observation below and the read-only base
adapter. The property path /en/hotel/milano-sant-ambrogio was identical before
and after room/rate selection, with no distinguishing URL state recorded.
/booking/(?:extras|review) remains guessed; the other historical /checkout/
observation was beyond the safe boundary and did not verify a selected stop.
No safe URL discriminator was found in existing evidence. No shard/hotel.py
override or unselected-property checkpoint was added, and docs/site-policy.json
was not edited. State-based verification needs core support or new safe public
URL evidence, not a broadened URL checkpoint. No new browser/H observation.

Final checks (also covering Frankfurt merge-order-compatible tests):
```
uv run ruff check .
All checks passed!
uv run pytest -q
2353 passed, 1 warning in 69.02s (0:01:09)
uv run pytest -q tests/test_agent_hotel.py tests/test_agent_registration.py tests/test_site_policy.py
820 passed in 9.41s
```
Existing Starlette httpx TestClient deprecation warning. JSON shard formatting
matches json.dumps(indent=1, ensure_ascii=False). Visually/live unverified.

# R7-03 live hotel smoke — 2026-11-09

Real `hotel.build_task` -> `HAgentRunner.run`, without runner_profile. Selected
the Booking adapter and removed alternatives only, limiting this smoke to one
provider/session. Berlin race 2027-09-26, stay 2027-09-25 to 2027-09-27, one
adult, EUR600 budget, Paris origin. API key bound through exec environment;
no key, private H URL, session ID, query, personal data or image was logged.

| Adapter | Public requested host/path | Quota available | Status | reason_code | Accepted final/stop page | Max reported provider steps | Emitted frames | Elapsed |
|---|---|---:|---|---|---|---:|---:|---:|
| r7-booking-hotel | www.booking.com/searchresults.html | 2 | blocked | policy_denied | unavailable; final/handoff URLs null | 0 | 0 | 9.9s |

Quota immediately before the run: org limit=3, active=1, available=2. Exactly
one H session was created. Runner cancellation and explicit DELETE cleanup
both returned HTTP204 before the Milano registration smoke began.

This is **not READY** and provides no verified selected-room/rate boundary.
The session was created, so this was not the builder/pre-session review gate.
No accepted page/frame was emitted; the launcher did not retain rejected
observation metadata, so the particular policy/title/URL trigger and stop page
are unknown. Zero is the maximum returned metrics.steps value, not an audit
proving no hosted actions occurred. No adapter/checkpoint fix is justified by
this evidence; no speculative relaxation was made and no retry was run.

The normal task prohibits personal-data entry, login, consent, submission and
payment. No profile was supplied. No screenshot was saved or independently
reviewed; no comprehensive hosted-action audit is claimed. All three allowed
ticket sessions were used (one hotel, two registration), yielding zero hotel
READY results; the two-hotel target including Booking remains unmet.

Final implementation checks (including the separately committed registration
freshness fix):
```
uv run ruff check .
All checks passed!
uv run pytest -q
2340 passed, 1 warning in 63.08s (0:01:03)
uv run pytest -q tests/test_agent_hotel.py tests/test_agent_registration.py tests/test_site_policy.py
807 passed in 8.73s
```
Warning: existing Starlette httpx TestClient deprecation.

# R6-01 live IHG hotel acceptance — 2026-11-09

Runtime commit: `84e301e`. Real `hotel.build_task` → `HAgentRunner.run`;
selected the existing ihg-com candidate and removed alternatives only to keep
each smoke to one reviewed provider/session. No registry, provider ordering or
safety rules changed. One adult, two nights, EUR600 whole-stay budget, Paris
origin. Quota checked immediately before every run; all seven hotel/transport
sessions in this acceptance were strictly sequential, one at a time, with
explicit DELETE cleanup returning HTTP204 before the next smoke.

## Race/date provenance

Fresh real Linkup discovery through `runai.discovery.linkup.discover` on
2026-11-09, not demo/replay dates:

- Wizz Air Milano Marathon: **2027-04-04**, official source
  https://www.milanomarathon.it/en/ (also /en/marathon/).
- EDP Lisbon Half Marathon: **2027-03-07**, official source
  https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/.
  Initial discovery was conflicting and not used. A targeted deep official-date
  query resolved March 7; no historical March 14 date was assumed.
- OCHSNER SPORT Zürich Marathon: **2027-04-11**, official source
  https://www.zuerichmarathon.ch/ and /marathon-2/marathon.
  Amsterdam discovery was conflicting; Zurich was used instead.

IHG's current registry review is allowed_owner_rule, reviewed 2026-11-09,
expires 2027-02-07, screenshots in_session_only. The reviewed limited licence
and copying restrictions remain materially ambiguous; this is the owner's
read/prepare-only authorization, not a claim of express site permission.
The runner preserved the no-payment/booking/account/consent/form/personal-data/
captcha guardrails. No screenshots, frames, private URLs, queries, session IDs
or personal data were persisted as evidence. Frame bytes were counted then
discarded; no independent visual review or comprehensive hosted-action audit
is claimed.

## Actual hotel outcomes

All final and handoff paths below are on **www.ihg.com**. The path retained for
each run is `/hotels/gb/en/find-hotels/select-enhance-stay`; no query is retained.

| City/run | Race date | Stay | Quota available | Final status | reason_code | Observed framed checkpoint? | P13 checkpoint_reached | verify_failed gates | H metrics steps | Elapsed | Real frames |
|---|---|---|---:|---|---|---|---|---|---:|---:|---:|
| Milan | 2027-04-04 | Apr 3–5 | 3 | ready_for_payment | null | yes | null | none | 14 | 96.1s | 14 |
| Lisbon first | 2027-03-07 | Mar 6–8 | 2 | blocked | checkpoint_unverified | yes | true | handoff_observed | 9 | 55.9s | 8 |
| Zurich | 2027-04-11 | Apr 10–12 | 2 | ready_for_payment | null | yes | null | none | 10 | 71.2s | 9 |
| Lisbon diagnostic retry | 2027-03-07 | Mar 6–8 | 2 | ready_for_payment | null | yes | null | none | 8 | 53.1s | 8 |

**Three distinct cities returned READY; the first Lisbon run remains a real
blocked result, not retroactively upgraded.** READY here is the live hclient
verification result with genuine observed frames, not a three-agent UI success
or proof of a completed booking/payment. P13's optional field is set for the
unverified blocked checkpoint; it remains null on the READY results.

### Lisbon mismatch investigation

The first failure isolated `handoff_observed`: verification fields, selected,
boundary, dates/party/city, checkpoint matching and frame association all passed
the runtime gates; the scrubbed agent handoff differed from the observed URL.
P13 retained the reviewed observed checkpoint as a handoff and stayed blocked.
The exact first-run queries were not retained, so their differing parameter(s)
and values cannot be reconstructed. No claim is made that this was merely
tracking noise or that its deeper cause is fixed.

A sequential diagnostic retry on unchanged code compared query structure in
memory without logging values: path equal, query pairs equal after sorting,
no observed-only/handoff-only keys and no differing value keys. It returned
READY with no verify_failed gates. Thus this is an intermittent handoff mismatch,
not a consistently failing room/date verification gate. No safety check was
weakened to force success. A future recurrence needs the same value-free
parameter-name/equality diagnostics at the failing attempt; the successful retry
does not explain the first discrepancy.

Observed metric timing distribution and Vueling outcomes are in
`docs/evidence/h-client.md`. No live heartbeat was needed in the measured
Lisbon/Zurich runs: maximum adjacent frame gaps were 8.2s and 10.7s; Lisbon retry
did not record its frame-gap distribution. Heartbeat correctness remains covered
by fake-clock tests, not demonstrated by a >20s live observation gap here.

# Guest-query compatibility — 2026-11-09

Amsterdam's retained READY host/path still matches the IHG checkpoint. The exact
live query was intentionally not retained. Offline runtime-matcher reproduction
showed bare guest rejects benign guests=1; it does not reject qAdlt/qRms alone.
Guest detection is now path-specific across all adapters, with regression cases
for both IHG adapters' start/review paths and qAdlt, guests, rooms, numberOfGuests.
Guest forms, /enter-guest-info, checkout and confirmations remain forbidden.
No new live run or retroactive claim about the Amsterdam query was made.

# Safety correction — 2026-11-09

The Milan B&B run below reached /checkout/ without URL-boundary cancellation.
**Checkout is beyond, never a checkpoint.** Every hotel/transport adapter and
legacy task fallback now blocks checkout, /book(?:ing)?/confirm and guest forms,
in addition to payment/passenger paths. Ready-pattern negative lookaheads use
the same expression, including query matches. Existing start URLs remain outside
both lists. Tests cover every committed adapter and every tested task/alternative,
encoded checkout and unsafe queries appended to otherwise-ready paths.
The historical run still returned blocked/provider_error, not policy_denied;
this offline correction does not rewrite that observation or claim a live retest.

# R5-02 step 5 live hotel smokes — 2026-11-09

Real merged HAgentRunner.run with branch build_task output; only alternatives
removed to keep each invocation single-task. Stay March 20–22 2027, race March21,
one adult, EUR600 budget. External launcher: /home/ubuntu/scratch/r5_smokes.py;
scrubbed summaries only: /home/ubuntu/scratch/r5-smokes.jsonl. H key bound through
exec environment, never logged. No private URLs, queries, session IDs or image
payloads persisted locally. Frame counts are actual emitted live_frame events (deduped
by hclient), not simulated footage. Tasks retain all normal safety guardrails.

| Task | Adapter/policy | Frames | Final observed host/path | Checkpoint | hclient status | reason_code |
|---|---|---:|---|---|---|---|
| Hotel Milan | hotel-bb-com | 7 | www.hotel-bb.com/checkout/ (beyond, not checkpoint) | no | blocked | provider_error |
| Hotel Amsterdam | ihg-com | 9 | www.ihg.com/hotels/gb/en/find-hotels/select-enhance-stay | yes | ready_for_payment | null |

Both runs were strictly sequential. GET /api/v2/sessions/quota returned available=3
before each; exactly one session was created for each, and explicit cleanup
returned HTTP204 before the next run. Elapsed: Milan 290.5s; Amsterdam 72.2s.

Amsterdam: this is a genuine hclient ready_for_payment return at the configured
IHG checkpoint, not merely a page visit or synthetic status. Runtime handoff
matched the same public checkpoint host/path; no booking/payment is claimed.

Milan: /checkout/ is a new distinct observed path, but the run did not return
READY or match the configured extras/review pattern. The generic provider_error
does not establish whether guest details, a site error or incomplete evidence
caused the stop. Ordinary Chrome GET of /checkout/ without H's selection state
redirected to /en, so it could not verify a post-selection/pre-personal-data
boundary. **Do not promote /checkout/ to a checkpoint on this evidence.** No
pattern had changed at that time and no extra H reproduction was run. The safety
correction above now forbids checkout explicitly. A stateful boundary review
is still required; task guardrails prohibit personal data, consent and forms,
but these summary-only measurements are not an audit of every hosted action.

# R5-02 step 4 hotel retry — 2026-11-09

No second NL/CH provider added in this bounded retry. Scandic website terms
permit printing individual pages but otherwise require written permission
for copying/reproduction; `/en/hotels` redirected to the destinations index, not
a dated NL/CH result. H10 legal notice reserves protected elements/reproduction;
the captured hotel catalogue lists European cities but no NL/CH destination was
established. An attempted hotel index returned its not-found page, not rates.

Novum legal notice requires prior consent for reproduction/distribution and
processing of protected content. Its hotel list loaded; many Book links go to IHG,
others to onepagebooking.com. This does not establish a distinct reviewed Novum
checkout, nor extend Novum's terms to the third-party engine. No adapter added.

Leonardo's reviewed 2026 disclaimer PDF again produced no readable browser text.
A March20–22/one-adult Rembrandtpark property URL
rendered **9 Nov–10 Nov, 1 Room, 2 Guests**, ignoring requested query values. This
is a date/party mismatch, not an executable dated link. No review renewal or adapter.

B&B `/en/terms-of-use` intellectual-property clauses were reread, retaining the
existing private in-session owner rule without claiming an automation license.
The actual Netherlands index `/en/netherlands/hotels-netherlands` lists one hotel,
Amsterdam-Zaandam, described as outside Amsterdam (about 30 minutes by bus).
Zaandam is neither the confirmed race city nor the currently reviewed Amsterdam
hotel gateway; no silent nearby-city substitution was added. The Swiss country
index loaded, but B&B is already an existing Swiss provider, not a distinct new
second site. No new dated selected room/rate checkpoint was established.

# R5-02 step 3 hotel research — 2026-11-09

**Not completed:** no second executable reviewed hotel provider was added for
NL or CH. Existing IHG coverage for Amsterdam/Den Haag and existing Swiss
B&B/IHG regional coverage remain unchanged; this is not a two-provider claim.

- Meininger `/en/imprint/`, including public collapsed copyright sections, was
  reread. It prohibits reproduction/utilisation in other publications without
  express agreement, not an affirmative automation license. Existing owner-rule
  status is unchanged. Its dated Amsterdam booking target on
  `mmb.meininger-hotels.com` returned ERR_TOO_MANY_REDIRECTS. No adapter or
  extension to that host added; do not work around the redirect failure.
- Radisson `/en-us/terms-and-conditions` reread: personal/non-commercial viewing
  and downloading are distinguished from copying/reproduction requiring
  permission. Scope remains materially ambiguous. A dated one-adult Amsterdam
  room-display attempt showed no rendered results, not proof of availability.
  No adapter or policy upgrade.
- NH Amsterdam March 20–22 2027 one-adult attempt returned Spanish no-availability
  text plus a required consent overlay with only Yes, I accept visible. No
  consent accepted and no NL adapter added. Existing NH paths still require
  BLOCKED consent_required at that overlay. NH was not globally demoted in the
  registry; whether to prioritize IHG over it remains a follow-up decision.
- Novum, Scandic and H10 were not fully reverified this handoff; Melia's existing
  deep-link restriction and Motel One/Hilton prohibitions are unchanged.

# R5-02 step 2 browser observations — 2026-11-09

**IHG Amsterdam, 20–22 March 2027, one adult:** selected Kimpton De Witt via
public Select Hotel → first room View Prices → Flexible Saver Select. The selected
room was 1 Double City Single. Observed www.ihg.com host/path progression:

1. `/hotels/gb/en/find-hotels/hotel-search`
2. `/hotels/gb/en/find-hotels/select-roomrate`
3. `/hotels/gb/en/find-hotels/select-enhance-stay` (**Add Extras**)

The last path confirms the existing IHG checkpoint expression. Stopped there;
did not add extras, click No thanks/skip, open guest details or accept the cookie
banner. The Add Extras page did not display a complete selected-room/date/party/
full-stay-total summary in the visible content, so this is path verification,
NOT complete READY evidence. Screenshot (in-session only):
`/home/ubuntu/scratch/r5-ihg-rate-selection.png` (captured at Add Extras).

**NH Lisbon, 20–22 March 2027, one adult:**
www.nh-hotels.com `/es/booking/step1-rates` rendered six room categories for NH
Collection Lisboa Liberdade. A blocking Cookie consent overlay had only **Yes,
I accept** and Configuration. Configuration opened cookie categories with another
Yes, I accept control and no visible reject/necessary-only/close control. Stopped
without selecting room/rate or accepting consent. The guessed step2 extras/services
checkpoint remains **unverified**. Screenshots (in-session only):
`/home/ubuntu/scratch/r5-nh-rates.png`,
`/home/ubuntu/scratch/r5-nh-consent-blocked.png`.

**B&B Milan, 20–22 March 2027, one adult:** rejected optional cookies; selected
the first Single Room FLEX public rate. The selection summary showed Single Room,
one adult, FLEX, 2 nights, exact stay dates and full total EUR238.00. Stopped at
the Book now boundary; did not click it or submit any form. Host/path remained
www.hotel-bb.com `/en/hotel/milano-sant-ambrogio` before AND after selection, with
no fragment change. The guessed `/booking/extras|review` path was not observed.
Screenshot (in-session only): `/home/ubuntu/scratch/r5-bb-selected.png`.

As with Vueling/NS, the B&B selected checkpoint is a state on the same URL as
the initial unselected page. After integrating R5-01, matching that hotel page
would force an answer prematurely. No separate safe path/query was observed;
Book now is the next boundary and was not clicked. The distinct extras/review
pattern is retained as **unverified**, not as selected-stop coverage. The earlier
requires_selection field was removed; P11 does not support it.
No account, personal data, consent acceptance, booking or payment occurred.

# R5-02 offline checkpoint additions (2026-11-09)

Every hotel adapter now carries checkpoint patterns. All are case-insensitive
unquoted path/query searches, prefixed with a negative lookahead excluding the shared unsafe
expression documented in site-policy.md, and end with `(?:[/?#]|$)`.

| Adapter | Checkpoint path expression | Evidence status |
| --- | --- | --- |
| IHG (both adapters) | `/select-enhance-stay` | Observed URL in prior R3/R4 navigation below; complete READY evidence still unverified. |
| NH | `/booking/step2-(?:extras|services)` | **Guessed, unverified.** Only step1-rates is documented below. This is a prospective post-room/rate checkpoint, not an observed route. |
| B&B (all fixed properties) | `/booking/(?:extras|review)` | **Guessed, unverified.** Selected room/rate state was observed on the unchanged property page; no distinct review URL verified. |

No live runs in R5-02 step 1. Guessed routes do not authorize navigation or prove
that these pages exist. Earlier guest/consent/form boundaries still block.
Hotel tasks use 60 steps and require an immediate terminal answer on checkpoint,
READY only with complete selected evidence, otherwise BLOCKED unsafe_claim.
Swiss regional hotel gateway mappings and geographic limitations are documented
in site-policy.md. They have no live inventory verification.

# Hotel site evidence: R2-02 (supersedes R1-06)

The R1 "assumed" rows (Accor default, Hilton homepage) are **withdrawn**. Accor is explicitly
denied in `docs/site-policy.json`. Hilton is prohibited by its terms ("You will not use any robot,
spider, other automatic device..."). See `docs/evidence/site-policy.md` for every reviewed terms URL and quote.

## Executable hotel adapters (reviewed 2026-11-08, expire 2027-02-06)

| Adapter | Policy | Destinations with reviewed public IDs | Deep link (observed vs unverified) |
|---|---|---|---|
| NH Hotels `www.nh-hotels.com/es/booking/step1-rates` | allowed_owner_rule (no agent clause; copying restricted) | Lisbon (PT11.LIBER) | **Observed** 2026-11-08: Lisbon 13→15 Mar 2027, 1 adult, 6 room categories with prices, no login/captcha/form submission. |
| IHG `www.ihg.com/redirect?path=rates` | allowed_owner_rule | Lisbon (LISPO) | **Observed** 2026-11-08: Lisbon 13→15 Mar 2027, 1 adult, 8 room options. Month is zero-based (`022027` = March 2027). |
| Meliá `www.melia.com/en/booking/destination-results` | allowed_owner_rule | Lisbon | **Observed** 2026-11-08: 3 hotels for 13→15 Mar 2027, 1 adult. The cookie banner was left untouched. |

Adapters are tried in registry order. A destination without reviewed place IDs raises `ValueError`
("no policy-reviewed hotel site for this trip"), and the step is blocked with a manual handoff. There is no
silent fallback. Other hotel chains whose terms show no prohibition (Radisson, Barceló, Leonardo, Meininger,
a&o, Scandic, H10, RIU, Iberostar, Catalonia, Eurostars, Novum, B&B, Premier Inn) are policy-allowed. However,
they have **no verified deep link** yet, so they are not executable. Unverified: the pass-2 research found no
complete destination+dates+party result URL for them.

## Task contract

- The deep link encodes the confirmed `arrival_date`/`departure_date`, travelers and destination. The builder
  never uses today/default dates or swaps the dates. Arrival must be ≤ race date < departure, and `nights` must match.
- Ready = a **selected available room and rate** showing the exact stay, party and total price, before guest data.
  The results list, a homepage or an unselected room are not ready. Blocked = no inventory, wrong dates, login,
  captcha, consent, a payment/guest form, or a redirect off `allowed_hosts`.
- `max_steps` = 80. `expected` and `allowed_hosts` come from the reviewed policy.

## Not yet observed

No live H hotel run has happened in R2-02. Room/rate selection and the correct-date safe stop are
**unverified** until R2-03's no-share runtime runs the integrated tree. Unit tests prove task construction only.

## Round 3 (R3-01)

### Live check 2026-11-09

One real H hotel session, concurrent with the single transport session; **two total H runs,
no retries**. Owner-approved read/prepare-only instructions, 40-step cap. Case: Milano
Marathon, Milan, Italy, race 2027-04-04; from Paris, stay 2027-04-03..05, 2 nights,
1 traveler, EUR450 whole-stay budget. Secret supplied only through exec environment;
no session/share/trace URLs, tokens or personal data logged or added to this repository.

- Task: `ihg-com`, public host `www.ihg.com`. Start template:
  `https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest={city_query}%2C%20{country}&qCiD={arrival_day}&qCiMy={arrival_monthyear0}&qCoD={departure_day}&qCoMy={departure_monthyear0}&qAdlt={travelers}&qChld=0&qRms=1`.
  Filled query: Milan/Italy, day 03/month-year 032027 to day 05/month-year 032027, 1 adult.
- Counts: **11 step_progress events, 10 frames**. Progress count is the exposed client
  count (session-start plus observation events), **not** an independently measured H
  action/step count; the runner does not return that metric. Maximum allowed steps: 40.
- Final runner status: **failed**, exact reason **“H session failed”**. Reason-code-like
  classification: **session_failed**. No safe final public site URL retained by the
  strict public-URL filter; no opaque booking/session URL is reproduced.
- Last two real frames reviewed: IHG **“Add Extras / Upgrade your room”**, showing an
  optional next-tier room for +39 EUR/night; then an almost empty IHG page. Neither frame
  establishes exact stay, selected room/rate and whole-stay total. **Not READY**; operational
  outcome is a blocked handoff due to session failure, not evidence of no inventory.
- In-session-only images outside the repo:
  `/home/ubuntu/r3live-hotel-last-1.png`, `/home/ubuntu/r3live-hotel-last-2.png`.
  The throwaway runner and sanitized count/result summary are also outside the repo.

The task prohibited forms, login, consent acceptance, booking, payment and personal data.
No such action is evidenced by the retained frames or sanitized result. Action traces were
not retained, so this is not an independent audit of every browser action or proof of a
safe pre-payment selection. No new attempt was made after the two-run cap was used.

### STEP 3b follow-up — 2026-11-09

- **2026-11-09 — www.hotel-bb.com** — verified template:
  `https://www.hotel-bb.com/en/hotel/freiburg-nord?arrival_date={arrival_mdy_slash}&departure_date={departure_mdy_slash}&rooms={travelers}&destination={place_name}`.
  Freiburg/Freiburg im Breisgau map to Freiburg-Nord. January 9–11 2027, **1 adult**:
  page shows **B&B HOTEL Freiburg-Nord**, **Tullastraße 87c, 79108 Freiburg, Germany**,
  **“1 room | 1 adult | From 09 Jan. 2027 to 11 Jan. 2027”** and double/twin rooms with
  public SUPERSAVER €108.15 and FLEX €119.70, date-by-date prices and Select controls.
  No room/rate selected; no booking, forms, login or consent acceptance. This is an
  in-city rate list, **not** selected-room or safe-stop evidence. Screenshot in-session
  only: `/home/ubuntu/r3b-bb-freiburg-1.png`.
- B&B terms reread at `https://www.hotel-bb.com/fr/conditions-utilisation`, especially
  sections 5, 7, 15. No express robot/agent/scraping ban found; section 15 restricts
  reproduction/copying/code downloading and exploitation without permission. Existing
  owner-rule decision retained; review 2026-11-09, expiry 2027-02-07, in-session screenshots.
- **One adult only:** the attempted public search query `rooms[0][adults]=2` still
  displayed **1 adult**. No two-person capability claimed. Adapter `traveler_counts:[1]`
  safely excludes larger parties; they retain IHG fallback and its in-city limitation.
  Lookup-table requirement restricts this fixed-property URL to the verified Freiburg aliases.
- Actual empty-search text observed: **“No hotels match your search criteria.”** on
  `/en/search` with Freiburg/date/room parameters. This is a rejected search encoding,
  not proof Freiburg-Nord was sold out; no property-specific sold-out message observed here.
- **2026-11-09 — Premier Inn rejected**, Freiburg City Süd property with
  `INdd=09&INmm=01&INyy=2027&OUTdd=11&OUTmm=01&OUTyy=2027&NIGHTS=2&ADULT1=1&CHILD1=0&ROOMS=1`:
  in-city address and **1 Erwachsener, 1 Zimmer**, but no exact-date room/rate result list.
  No adapter added. Stopped after the second hotel candidate succeeded for one adult.
- No additional Lausanne candidate verified in this time box; previous IHG neighboring-city
  limitation remains. Do not describe Lausanne as verified in-city hotel inventory.

Research date: **2026-11-09**. Normal Chrome via Playwright/CDP, **not H**. Only public URLs
were opened/read. No search forms, account creation, consent acceptance, guest details or bookings.
Cookie banners were left untouched. No captcha or login wall on the accepted search/rate pages.
The NH cookie overlay remained visible; no consent was accepted. These are search/rate-page
observations, **not selected-room/selected-rate safe-stop or H success evidence**.

### Verified templates

**IHG-city** (`www.ihg.com`, query-only placeholders; generic, restricted to IT/PT/ES/CH/DE):

```text
https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest={city_query}%2C%20{country}&qCiD={arrival_day}&qCiMy={arrival_monthyear0}&qCoD={departure_day}&qCoMy={departure_monthyear0}&qAdlt={travelers}&qChld=0&qRms=1
```

Each dated line below uses **IHG-city** above, check-in **2027-01-09**, check-out **2027-01-11**,
tested separately for **1 and 2 adults**, one room. The URL uses `qCiMy=qCoMy=002027`
(January is zero-based); the rendered search header showed `09/01/2027 → 11/01/2027`
and `1 Room, 1 Guest` / `1 Room, 2 Guests`. Redirect remained on `www.ihg.com`, at
`/hotels/gb/en/find-hotels/hotel-search`. These links require no reviewed place IDs.

| Date | Chain/host + template | Destination shown | Observed results / limitation |
| --- | --- | --- | --- |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Milan, Italy | 10 hotels; Hotel Indigo Milan and Holiday Inn Milan, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Lisbon, Portugal | 16 hotels; Convent Square Lisbon and Holiday Inn Express Lisbon, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Valencia, Spain | 2 hotels; Holiday Inn Express Valencia, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Zurich, Switzerland | 8 hotels; Ruby Mimi Hotel Zurich and Crowne Plaza Zurich, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Geneve, Switzerland | 4 hotels; Ruby Claire Hotel Geneva and InterContinental Geneve, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Lausanne, Switzerland | 18 hotels, but visible properties were in Geneva (~31 miles away), **not proof of an available Lausanne hotel**. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Freiburg im Breisgau, Germany | 1 hotel, Holiday Inn Express Ringsheim (~17.66 miles away), **not an available Freiburg city hotel**. |

The latter two links preserve the destination, dates and party, but cannot be called successful
in-city hotel preparation. Adapter instructions explicitly require checking the actual hotel's
city and blocking rather than substituting Geneva/Ringsheim. Generic free-text search does not
guarantee inventory or reviewed successful hotels in every city in those countries, nor coverage
outside these five verified countries. Other country codes remain unsupported.

- **2026-11-09 — IHG-city empty/error observation**: `Longyearbyen, Norway`, January 9–11,
  2 adults: `0 Hotel Found. An error has occurred. Please contact your nearest reservation office
  and a representative will be able to assist you.` Norway is not in the adapter's country list.
  This is an observed error/empty response, **not a clean sold-out inventory message**.

No clean sold-out IHG message was established for an otherwise working city search. See the
registry's blocked evidence; any
empty result, mismatched dates/party, unavailable matching-city hotel, captcha, login, consent,
form submission or unreviewed redirect is a blocker.

Screenshots of the rendered search headers (both party sizes for all seven cities):
`/home/ubuntu/r3-hotel-ihg-{Milan,Lisbon,Valencia,Zurich,Geneva,Lausanne,Freiburg-im-Breisgau}-{1,2}.png`.
These in-session screenshots are outside the repository and must not be published.

**NH-rates** (`www.nh-hotels.com`, existing Lisbon adapter retained ahead of IHG):

```text
https://www.nh-hotels.com/es/booking/step1-rates?destinationId={place_name}&fini={arrival_dmy_slash}&fout={departure_dmy_slash}&gvoucher=false&hotelId={place_id}&nadults1={travelers}&nbabies1=0&nchilds1=0&pcode=
```

- **2026-11-09 — NH / www.nh-hotels.com / NH-rates**: Lisbon, `PT11.LIBER`,
  `2027-01-09..2027-01-11`, separately **1 and 2 adults**. NH Collection Lisboa Liberdade,
  `Jan 9-Jan 11`, `1 adulto / 1 habitación` / `2 adultos / 1 habitación`, six available
  room categories with prices. Existing Lisbon/Lisboa/Lisbonne place aliases retained.
- **2026-11-09 — NH / www.nh-hotels.com / NH-rates**, supplemental verified property:
  Milan, `ITMI.TOURI`, `2027-01-09..2027-01-11`, separately **1 and 2 adults**.
  NH Collection Milano Touring, exact dates/party, eight/five available room categories with
  prices respectively. Not added as a new place adapter, to leave generic IHG first for Milan.
  Screenshot: `/home/ubuntu/r3-hotel-nh-milan-2.png` (in-session only, not for publication).
- **2026-11-09 — NH no-inventory observation**: same Milan property/dates, **9 adults**,
  `Lo sentimos, no hay disponibilidad para estas fechas`; followed by
  `Recomendamos cambiar las fechas o buscar una alternativa en estos hoteles` and
  `Modificar fechas`. No form was submitted or dates changed.

### Terms reread and rejected candidates

- **2026-11-09 — NH**: reread `https://www.nh-hotels.com/en/legal-notice`, sections 2
  (User Responsibilities), 3 (Monitoring), 9 (Intellectual Property). Copying/use/load restrictions
  remain; no express bots/agents/scraping prohibition found. Retain the existing owner's
  read-only rule, not a claim of express contractual permission.
- **2026-11-09 — IHG**: reread `https://www.ihg.com/content/gb/en/customer-care/tc.html`,
  LIMITED LICENCE TO VIEW AND COPY, PROHIBITED CONDUCT and INTELLECTUAL PROPERTY RIGHTS.
  Non-commercial individual use/copying restrictions remain; no express bots/agents/scraping
  prohibition found. Retain the existing owner's read-only rule and in-session-only screenshots.
- **2026-11-09 — Meliá**: Lisbon results with exact January 9–11 dates and 1/2 adults did render
  two available hotels and prices. A property showed `This hotel has no availability on this date`.
  However, rereading `https://www.melia.com/en/legal-notice`, section 5 Links, found:
  “No deep-links or IMG or image links, nor frames with website pages will be allowed without
  the express permission of Meliá.” **Executable adapter withdrawn**, not replaced. No express
  automated-agent prohibition found; retain the existing policy decision only for ordinary
  read-only navigation, not permission to issue booking deep links.
- **2026-11-09 — NH generic routes**: `/en/booking/step1-hotels` and other guessed routes
  returned 404 / NoSuchKey; rejected. Only the reviewed Lisbon property adapter remains executable.
- **2026-11-09 — Radisson**: tested Lausanne route rendered “Sorry, something went wrong.
  This is almost certainly not the page you were looking for.” Rejected; no adapter added.
- **2026-11-09 — B&B Hotels**: Lausanne Crissier showed Jan 9–11, two nights, room/rate prices,
  but tested party parameters did not reliably change **1 adult** to 2. Rejected; no adapter added.
  A deliberately wrong date encoding showed “This hotel is fully booked for these dates.” and
  “This hotel is fully booked from 01 Sep. 2027 to 01 Nov. 2027 for 1 room · 1 adult.”
  That is not evidence for January availability or a working two-adult adapter.

NH/IHG/Meliá review dates refreshed to 2026-11-09, expiry 2027-02-07. No prohibited
chain was relaxed. Accor remains denied. No H sessions were created in this research.

## R4-02 normal-Chrome research — 2026-11-09 (offline, no H)

Public deep-link checks used 2027-01-09 to 2027-01-11, one adult, one room.
Terms and authorization caveats are recorded in site-policy.md. No selected
room/rate, guest-details boundary or new READY state was reached in this research.

### IHG extension

Verified the existing public template (values URL-encoded):
`https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest={city},%20{country}&qCiD=09&qCiMy=002027&qCoD=11&qCoMy=002027&qAdlt=1&qChld=0&qRms=1`.
It redirects to /hotel-search. January is month 00, not 01. Rendered date/party
controls were inspected as well as result text, not inferred from URL parameters.

| Query | Rendered result | Decision |
| --- | --- | --- |
| Amsterdam, NL | 16 hotels, public From prices | Add NL search coverage; check actual property city |
| Den Haag, NL | 10 hotels, public From prices | Search coverage, not every result in Den Haag |
| Brussels, BE | 16 hotels, public From prices | Add BE |
| Vienna, AT | 10 hotels, public From prices | Add AT |
| Prague, CZ | 2 hotels, public From prices | Add CZ |
| Paris, FR | 21 hotels, public From prices | Add FR |
| London, GB | 93 hotels, public From prices | Add GB |
| Barcelona, ES | 10 hotels with prices | Existing country, reviewed query |
| Rome, IT | 8 hotels with prices | Existing country, reviewed query |
| Seville, ES | 10 results; first Jerez de la Frontera 79.37 km away, neighboring-country warning | NO demonstrated in-city inventory; must block if no matching city property |
| Savognin, CH | AlpenGold Davos Dorf, 30.92 km away, From USD541 | NO demonstrated in-city inventory |
| Grindelwald, CH | 31 results; first Kriens 48.92 km away, neighboring-country warning | NO demonstrated in-city inventory |
| Sierre, CH | Crans-Montana 5.44 km and Sion 14.64 km; one link leaves IHG | NO demonstrated in-city inventory; unreviewed external host remains forbidden |

These are all search-list observations, not selected full-stay totals or promises
of availability within EUR450. A successful offline build for a mountain town or Seville
does not permit a distant hotel to pass the unchanged strict city check.

### B&B fixed-property extension (one adult ONLY)

Public pattern:
`https://www.hotel-bb.com/en/hotel/{literal-property-slug}?arrival_date=01%2F09%2F2027&departure_date=01%2F11%2F2027&rooms=1&destination={reviewed-name}`.
Property slugs are literal paths, not user-filled path parameters. Each adapter is
restricted to its reviewed city aliases and country. Existing Freiburg-Nord stays intact.
Two-adult encoding remains unverified; no larger party is added.

| Property slug | Destination value | Exact-date, one-adult result |
| --- | --- | --- |
| milano-sant-ambrogio | milano-sant-ambrogio | Milan public room/rate list and Select controls |
| paris-porte-des-lilas | Paris | Paris public room/rate list and Select controls |
| bruxelles-centre-gare-midi | bruxelles-centre-gare-midi | Brussels public room/rate list and Select controls |
| wien-hbf | wien-hbf | Vienna public room/rate list, Room Only public EUR110 / cancellable EUR130 displayed |
| prague-city | prague-city | Prague public room/rate list, CZK3264 displayed |
| birmingham-centre | birmingham-centre | Birmingham public room/rate list and Select controls |
| valencia-ciudad-de-las-ciencias | same slug | Guessed property returned 404; NOT wired |

Each successful property showed `1 room | 1 adult | From 09 Jan. 2027 to 11 Jan. 2027`.
Displayed prices are observations of public rate cards, not verified whole-stay
selected totals. Member prices/sign-in were not used; Select forms were not submitted.
B&B supplies a second site for sampled IT/FR/BE/AT/CZ/GB cities, not all cities in
those countries. Birmingham is NOT a London hotel. No NL second-site link verified.
B&B country/city directories were read to identify properties (Netherlands, Vienna,
Prague, Brussels, Birmingham); directory pages alone were not made executable.

### Rejected hotel trials

All attempts below used the same January dates and one adult unless noted.

- NH /es/booking/step1-rates with `destinationId={city}&fini=09/01/2027&fout=11/01/2027&gvoucher=false&hotelId={id}&nadults1=1&nbabies1=0&nchilds1=0&pcode=`:
  Barcelona ESBA.CALDE, Valencia ESVL.COVAL, Seville ESSE.CONSE, Amsterdam NLAM.ZUID,
  The Hague NLZH.DENHA, Rome ITRM.LEONA, Brussels BEBR.ATL, Vienna AT09.WIEN,
  Prague CZPR.PRAGU, Paris FR75.CHAMP, London GBLO.WLOND.
  All showed `Lo sentimos, no hay disponibilidad para estas fechas`; some did show
  the named property and Jan 9–Jan 11/one adult, others only an empty shell.
  No rate-list proof: none of these guessed mappings added. Existing Lisbon remains.
- Radisson /en-us/search?searchTerm=Amsterdam&checkInDate=2027-01-09&checkOutDate=2027-01-11&adults[]=1&children[]=0:
  not-found/search UI rather than applied-date rates; no adapter.
- Meininger public booking attempt on mmb.meininger-hotels.com: ERR_TOO_MANY_REDIRECTS;
  no challenge bypass or cookie manipulation; no adapter.
- Scandic /en/book?checkin=2027-01-09&checkout=2027-01-11&adults=1&city=Amsterdam:
  PAGE NOT FOUND and default Nov 9–10 controls; no adapter.
- H10 attempted booking route redirected /en/not-found (Error 404); no adapter.
- Catalonia /en/search?destination=Barcelona&arrival=2027-01-09&departure=2027-01-11&adults=1:
  login/cookie UI, no verified exact-date public rate list; commercial hyperlink
  permission also unresolved; no adapter.
- Leonardo /amsterdam?arrival=2027-01-09&departure=2027-01-11&adults=1:
  city hotel list/prices, but Nov 9–10 and 1 Room, 2 Guests remained in controls.
  Query ignored, not an exact-date adapter; no adapter.
- Barceló attempted booking URL returned 404; no verified public pattern retained.

### IHG READY instruction correction

The R3 navigation reached Add Extras / select-enhance-stay after room/rate selection
and then ran out of steps; it did NOT prove a completed READY stop. The new registry
evidence and hotel task instructions say to STOP and report READY immediately on that
review page ONLY when selected room AND rate, matching city, exact dates, party and
full-stay total are all visible, before guest details. Earliest safety boundary still
wins. A page title, result list or partial summary is insufficient. Other hotels use
their own selected-room review boundary, not an invented IHG page.

## Authorized live smoke — 2026-11-09

Direct app runner: `runai.agents.hclient.HAgentRunner` (also used by
`providers.LiveRunner`). Dates 2027-01-15 to 2027-01-17, one adult, EUR450, origin Paris.
The secret was bound only through exec env, never printed. Read/prepare-only instructions
forbid payment, booking, form submission, login, personal data, consent and captcha bypass.
Steps are maximum reported provider `metrics.steps`; frames are deduplicated emitted
`live_frame` events, counted in memory then discarded, not saved screenshots.
No private H session/share URLs, tokens or screenshots were recorded. Frames were not
independently visually reviewed.

| Date | Adapter/policy | Public requested start URL | Final status | Reason code | Last observed stage/page | Provider steps | Emitted frames |
|---|---|---|---|---|---|---:|---:|
| 2026-11-09 | ihg-com / Barcelona free-text | https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest=Barcelona%2C%20ES&qCiD=15&qCiMy=002027&qCoD=17&qCoMy=002027&qAdlt=1&qChld=0&qRms=1 | failed | step_limit | Add Extras: https://www.ihg.com/hotels/gb/en/find-hotels/select-enhance-stay | 40 | 10 |

The returned error was `H step limit reached`, not READY. The observed URL and
coarse answer-stage category indicated Add Extras. This proves reaching the checkpoint,
NOT a successful stop, matching room/rate/city/dates/party/total, or a verified handoff.

Follow-up instruction refinement in hotel.py and IHG success_evidence: select-enhance-stay
is terminal; inspect the selection summary once, then finish READY only with all required
evidence, otherwise BLOCKED unsafe_claim immediately. Never add extras, navigate back or
keep browsing. This is not a demonstrated fix; why the agent did not finish at the
checkpoint is not established from retained safe metadata. No rerun: all three allowed
sessions were exhausted. Post-refinement user-facing behavior remains visually unverified.

## Rebased R4-01 integration review — 2026-11-09 (offline only)

No additional live runs. The failed/step_limit result above remains unchanged.
R4-01 HAgentRunner.run now consumes P7 alternatives; our hotel tasks already match
the exact ten base fields, at most two distinct-policy alternatives and no nesting.
A generated Milan hotel task was passed through the actual run consumer with synthetic
_attempt responses and the real alternative policy gate: blocked/no_inventory primary
advanced to its IHG alternative, emitted Essai d'un autre site and returned the synthetic
ready result without network calls. This is compatibility evidence, NOT hotel live success.

R4-01 converts failed/interrupted sessions after reviewed progress to blocked/
session_failed and preserves the last reviewed public URL. That condition can now
trigger P7 alternatives. It does not change the historical IHG step_limit result into
READY, nor verify the refined Add Extras stop instruction. No applicable new live
evidence or independent visual check was obtained.

## R7-03 hotel offline coverage — 2026-11-09

Added owner-rule policies r7-booking-hotel, r7-hilton-hotel and r7-accor-hotel,
reviewed 2026-11-09, expiring 2027-02-07. Authorization is the owner decision in
docs/handoff/lift-site-exclusions.md, not permission granted by these sites.
Booking/Hilton cover IT, DE, NL, PT, ES, CH, FR, BE, AT, GB, CZ. Accor is
Milan-only: the loader forbids path placeholders, so its destination path is static
and a reviewed place-name lookup gates it to Milan/Milano.

Templates:
- Booking: https://www.booking.com/searchresults.html?ss={city_query}%2C%20{country}&checkin={arrival_date}&checkout={departure_date}&group_adults={travelers}&no_rooms=1&group_children=0
- Hilton: https://www.hilton.com/en/search/?query={city_query}%2C%20{country}&arrivalDate={arrival_date}&departureDate={departure_date}&numAdults={travelers}&numRooms=1
- Accor: https://all.accor.com/ssr/app/accor/hotels/milan-italy?destination={place_name}&dateIn={arrival_date}&dateOut={departure_date}&compositions={travelers}

Selection checkpoints (case-insensitive unquoted path + query):
- Booking: ^/book\.html(?:[/?]|$)
- Hilton: ^/en/book/reservation/review(?:[/?]|$)
- Accor: ^/ssr/app/accor/booking/review(?:[/?]|$)

These are conservative PROVISIONAL patterns, not observed live stops. No pattern
matches search results or an unselected hotel/list page. Standard guest-form,
checkout, pay/payment, confirmation and card-details navigation is blocked without
a profile. With a usable guest profile, tasks contain field names only, separate
guest prefill patterns and payment/card-details stop patterns; terms, marketing,
submissions and payment entry remain forbidden. P14 runtime enforcement belongs
to R7-01 and was not proven by these offline task-builder checks.

Anonymous curl HEAD/GET of the Accor Milan URL returned HTTP 200 and an SSR shell
(base href /ssr/, dateIn/dateOut state keys). This does NOT establish date/party
hydration, inventory, room selection or a checkout boundary. No forms, consent or
H sessions were used. Booking/Hilton rendering and every checkpoint need later
live validation. Visually unverified; no site screenshots recorded.

Checks after fixing conservative beyond-pattern coverage:
```
uv run ruff check .
All checks passed!
uv run pytest -q
2307 passed, 1 warning in 63.45s (0:01:03)
uv run pytest -q tests/test_agent_hotel.py tests/test_site_policy.py
563 passed in 2.12s
```
The warning is the existing Starlette httpx TestClient deprecation.
Initial full-suite check found 13 failures because new beyond-patterns omitted
generic guest/checkout/pay boundaries; fixed the shard, not shared tests.
No configured pre-commit file or active pre-commit hook is present.
