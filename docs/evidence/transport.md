# PR44 review correction — SBB URL checkpoint disabled — 2026-11-09

Supersedes earlier /en/offer checkpoint claims; earlier smoke tables remain
historical observations. Step 6 Geneva's /en/offer URL already contained
retDay/retMoment/retTime/retTrip while its last frame still showed **Select return
ticket**, an outbound-only CHF54.40 subtotal and no selected return fare.
Return-connection parameters do not prove return-ticket selection. No retained
observed URL state distinguishes complete round-trip fare selection from that
outbound offer; do not guess a stronger query regex.

Every SBB adapter now uses the existing never-match `(?!)` sentinel for
url_patterns, disabling URL-triggered force_answer. Registry and runner require
nonempty lists, so an empty list would reject tasks rather than disable only
the trigger. All beyond boundaries, including shop onboarding, are unchanged.
Agent answers still undergo evidence validation; this does not promise READY
without a verified checkpoint. No shared runtime/contract edits or live runs.
Offline regressions reject bare /en/offer, outbound trip, return date, and the
observed combination of return parameters on every SBB adapter.

# R6-02 step 6 SBB-primary / reviewed shop smokes — 2026-11-09

Only shop.sbb.ch was added as an explicitly owner-reviewed same-operator SBB
host; restrictions/expiry unchanged. NS moved unchanged behind SBB into the
transport fragment. Geneva–Zurich is SBB primary, NS P7 alternative through
registry order, not a selection-code special case. Earlier runs below remain
historical evidence; no core runtime files were edited.

Real pipeline on the post-step-5 rebased runtime: trip → transport.build_task →
hclient._policy → unmodified HAgentRunner.run/task, max_steps 60, 2027-01-09 to
2027-01-11, one adult, EUR800. Four creations, including one automatic fallback,
quota available>0 immediately before each; HTTP204 cleanup before next creation.

| Route | Provider / frames | Final pipeline status / reason | Honest last visible stop state | Checkpoint / beyond matched during smoke |
|---|---|---|---|---|
| Geneva–Zurich | SBB 13; NS not attempted | blocked / date_mismatch | /en/offer, round-trip heading Jan 9/11, one full-price adult, 2nd class, outbound supersaver CHF54.40, 08:05–10:56. **Select return ticket** still visible; no selected-return fare/full-trip total established. | Yes / No |
| Paris–Milan | SBB 36; Vueling fallback 0 | blocked / provider_error | Shop onboarding visibly **SwissPass login / Purchase as a guest**, with login and guest-choice controls. No distinct shop fare summary or selected round trip; fallback had no frames/observed URL. | No / No |
| Lyon–Milan | SBB 47; no fallback | blocked / date_mismatch | Full-fare outbound Frecciarossa 09:31–14:11 preview, from CHF73; **Select tickets** visible. No return selection/round-trip total. | No / No |

Status/reason are actual runner outputs, not relabelled visual interpretations.
Geneva's heading visibly has the requested dates; date_mismatch does **not**
establish a visibly incorrect date there. Checkpoint match is not READY: return
fare was still pending. No run establishes completed round-trip preparation.

Scrubbed observed path/query sequences; `same` carries preceding public state,
all unlisted query values removed rather than inferred:

```text
Geneva–Zurich (www.sbb.ch):
/en?stops=Genève_I8501008~Zürich+HB_I8503000&day=2027-01-09&time=08_00&moment=dep
→ same + reduction=[redacted]
→ same + retDay=[redacted]&retMoment=[redacted]&retTime=[redacted]
→ same + trip=[redacted]
→ /en/plan/return (reversed stops, day=2027-01-09, time=08_05, preceding opaque keys)
→ same + retTrip=[redacted]
→ /en/offer (original stops, day=2027-01-09, time=08_05, preceding opaque keys)

Paris–Milan (www.sbb.ch unless noted):
/en?stops=Paris+Gare+de+Lyon_I8768600~Milano+Centrale_I8301700&day=2027-01-09&time=08_00&moment=dep
→ same + reduction=[redacted]
→ same + day2=[redacted]&time2=[redacted]&moment2=[redacted]
→ /en
→ /en (original stops, day=2026-11-09, time=07_05, moment=dep)
→ same with day=2027-01-09
→ same + reduction=[redacted]
→ same + trip=[redacted]
→ shop.sbb.ch/customer/en/alw/onboarding?su=[redacted]&cu=[redacted]

Lyon–Milan (www.sbb.ch):
/en?stops=Lyon+Part+Dieu_I8772319~Milano+Centrale_I8301700&day=2027-01-09&time=08_00&moment=dep
→ same + reduction=[redacted]
→ same with stops reversed
→ original stop order restored
→ /en
→ /en (original stops, day=2026-11-09, time=07_10, moment=dep)
→ same with day=2027-01-09
→ same + reduction=[redacted]
→ same + return=[redacted]
→ /en
→ /en (original stops, day=2026-11-09, time=07_11, moment=dep)
→ same with day=2027-01-09
→ same + reduction=[redacted]
→ same + trip=[redacted]
```

Paris/Lyon temporarily reset to today's date before restoring Jan 9; Lyon also
temporarily reversed the route. Neither is accepted as requested-date/route
preparation. The observer retained frames/locations, not a full action audit;
instructions forbid forms, personal data, consent acceptance, booking/payment,
but retained evidence does not independently certify every runtime action.

No new shop fare-summary path, so /en/offer remains unchanged; the conditional
offer-path rerun was not triggered. After classifying Paris's frame, exact
`^/customer/en/alw/onboarding(?:[?;]|$)` became a SBB beyond boundary, not a
checkpoint. This hardening is offline-tested only, not live-rerun; the table
truthfully records the old pattern's non-match. No additional run forced success.

All four creations received HTTP204 cleanup. Final organization quota:
`limit=3, active=1, available=2` (organization-wide; ownership of the remaining
active session is unknown). No claim of organization-wide active=0. Frames and
scrubbed harness artifacts remain outside the repository; no private IDs/URLs.

# R6-02 step 5 real-pipeline checkpoint smokes — 2026-11-09

Each route used the real `trip -> transport.build_task -> hclient._policy ->
HAgentRunner.run(task, event_cb)` pipeline. Travel January 9–11, 2027, race
January 10, one adult, EUR800 budget; max_steps 60. Tasks and runner were not
modified for probes: P7 alternatives/retries remained enabled. Each creation
was quota-gated with available > 0, and each preceding own session had cleanup
HTTP204 before the next creation. Shared organization active counts can include
other sessions. Last frames and detailed harness results stayed outside the
repository. No H URLs, session IDs, token values or screenshots are included.

## Per-route results

Frames are genuine deduplicated live-frame events, split by attempted provider.
Status/reason below is the **final unmodified runner result**, not a relabelled
visual assessment or a guessed per-attempt result.

| Route / run | Provider attempts / frames | Final status / reason | Honest last visible state / stop | Checkpoint / beyond matched |
| --- | --- | --- | --- | --- |
| Paris–Milan | SBB 10; Vueling 0 | blocked / provider_error | SBB connection preview, 1 Full fare, Jan 9, 2nd class from CHF88; Select tickets visible. Navigation to unreviewed shop.sbb.ch blocked before a frame there. Vueling fallback produced no frame. No selected return/total. | no / no |
| Paris–Amsterdam | NS 8 | blocked / provider_error | Inbound fare-selection panel, Jan 9/11, 1 passenger, EUR89 header; Continue to final check still visible. Not a verified final review/checkpoint. | no / no |
| Geneva–Zurich, original guess | NS 10; SBB 15 | failed / timeout | NS Check your trip showed both Jan 9/11 Full-flex legs, 1 passenger, EUR179.60; Enter your details unclicked. SBB reached /en/offer, adult Jan 11 return offer CHF52, Total return journey CHF106.40; Continue unclicked. Old guessed checkpoint did not match. | no / no |
| Lyon–Milan | SBB 8; Vueling 0 | blocked / provider_error | SBB Jan 9 direct Frecciarossa 09:31–14:11 preview, 2nd class from CHF73, Select tickets visible. Unreviewed shop redirect blocked before a frame there; Vueling fallback no frame. No selected return/total. | no / no |
| Geneva–Zurich, corrected checkpoint, one rerun | NS 10; no fallback | failed / unsafe_claim | NS Check your trip: Jan 9 06:35–09:28 Genève–Zürich HB and Jan 11 06:32–09:25 return, 1 passenger, 2nd class Full-flex, EUR179.60. Enter your details remained unclicked. Unchanged results path; corrected SBB checkpoint not exercised. | no / no |

International SBB redirects were to `shop.sbb.ch/customer/en/alw/onboarding`,
with `su`/`cu` values redacted. That host is not in SBB's reviewed scopes. The
runner's host gate blocks before rendering/interacting there, then its existing
P7 path can replace the route's final result with Vueling's provider_error.
The table does not claim a login/passenger page was reached: no frame there was
retained. No scope was broadened and no onboarding URL was promoted to READY.

## Observed path/query sequences (opaque values removed)

- Paris/Lyon–Milan SBB: `/en?stops=<public mapped stops>&day=2027-01-09&time=08_00&moment=dep`
  → same plus `reduction=[redacted]` → same plus `trip=[redacted]`
  → `shop.sbb.ch/customer/en/alw/onboarding?su=[redacted]&cu=[redacted]`.
  Vueling: no public observed URL/frame.
- Both NS routes: `/en/traintickets-v3/` throughout. No distinct path/query was
  observed, even when Geneva–Zurich displayed its selected-trip review pane.
  Fragment changes are not a path/query checkpoint and were not retained.
- Geneva–Zurich SBB fallback: `/en?...` → plus `reduction` → plus
  `retDay`, `retMoment`, `retTime` → plus `trip` → `/en/plan/return?...`
  (reversed public stations) → plus `retTrip` → `/en/offer?...`.
  Query includes the public mapped stations, January 9 outbound date and times;
  opaque trip/return-trip values and other retained values are redacted. This
  is evidence of UI-generated return parameters, **not** validation of a new
  direct-link contract. The configured start link still has no return/party
  parameters; instructions now explicitly say *start link*.

## Checkpoint correction and remaining safety limits

SBB's guessed buying/pages/offerte path was replaced with the observed exact
`/en/offer` path (query allowed). The initial last frame establishes that this
is a fare/ticket-selection surface, not start/results or a connection preview.
It does not alone establish all READY evidence. Tests exclude `/en`, `trip=`
preview, `/en/plan/return`, old guessed paths, `/en/offers`, nested login and
unsafe explicit query states; passenger/login/pay/checkout remain beyond-only.
NS's distinct overview/review guess is unchanged: do not broaden it to its
shared results path merely because a safe selected-trip pane is visible.

The single authorized Geneva–Zurich rerun ended at NS with `failed/unsafe_claim`;
the existing runner does not try P7 alternatives for that result. Therefore the
corrected SBB pattern was **not live-matched on rerun**. It is grounded in the
first run's observed /en/offer frame/path and offline tests, not a successful
runtime READY. No extra SBB-only run was substituted for the real primary.
The reason code is reported as returned; it does not prove a booking or payment
occurred. The retained observations/frame establish a safe review surface, not
a complete audit of actions or the model's answer.

No beyond-pattern URL was observed in any of the five runs. Tasks forbid
consent acceptance, personal data, submissions, login, booking and payment.
The harness records observations and last frames, not a complete action audit;
it cannot independently certify every runtime action. Visible passenger-detail
entry/Continue buttons are not authorization to open the next page. Coverage
still means route-scoped render evidence, not guaranteed checkout preparation.

Eight session creations total, including automatic fallbacks; all cleaned up
HTTP204. Final organization quota: `limit=3, active=0, available=3`.

Evidence version boundary: these live smokes preceded the requested rebase onto
origin/main `b9a6fb685dae3c3073c3a421e089331bfecb6b01`, which brought upstream H
runtime changes. The rebase was conflict-free and the new tree passed lint and
2091 tests, but no post-rebase live sessions were authorized/run here. Do not
present the pre-rebase statuses as observed acceptance of the updated runtime.

# R6-02 transport render gate — 2026-11-09

This section supersedes historical coverage claims below. Owner-rule authorization
and an executable URL do not establish that H can render priced results.
Transport adapters may carry optional `h_render_verified_at: "YYYY-MM-DD"`.
It must be a valid canonical ISO date, no later than the current UTC date;
malformed/future values fail registry validation closed. It is transport-only.
The date records a route-scoped dated-results render, **not** READY, full-adult
pricing, selected return travel, an independently audited action trace, or
affirmative provider authorization. It does not renew the entry's terms review.

Verified candidates rank before unverified candidates, preserving the existing
mode/registry order within each group. A route without a verified candidate has
no primary: `select_adapters` raises the existing no-coverage ValueError and
`coverage('transport', ...)` returns `covered=False, policy_ids=[]`. Unverified
candidates can only be P7 alternatives behind a verified primary. Other kinds
retain their existing policy gate. Distinct-policy cap remains three tasks.

## Scoped registry and coverage

- SBB's existing `sbb-ch` review moved, unchanged in date/scope/automation, from
  the base document into `docs/site-policy.d/transport.json`. No duplicate ID.
  One-adult rail adapters carry the date only for Paris–Milan, Lyon–Milan,
  Geneva–Milan and Geneva–Zurich. Paris–Zurich and Geneva–Lucerne are unwitnessed
  alternatives, never primaries without another verified provider on that route.
- NS Paris–Amsterdam is separated from the Den Haag gateway mapping. Only the
  Amsterdam place set and Geneva–Zurich adapter carry the date. Brussels–Amsterdam,
  Paris–Barcelona, other NS routes and Den Haag remain unverified. Gateway-city
  task/verifier behavior is retained, but gateway coverage is not inferred from
  a different route's render evidence.
- No date is attached to Vueling or CP. Paris–Milan now chooses SBB before the
  unverified Vueling alternative; Geneva–Zurich chooses NS then SBB.
- Covered eval routes: Paris–Milan, Lyon–Milan, Geneva–Zurich, Paris–Amsterdam.
  Geneva–Milan is also covered. Eval gaps: Paris–Lisbon/Zurich/Barcelona/Madrid,
  Brussels–Amsterdam and Geneva–Lucerne. Historical Vueling-only routes below
  are no longer reported covered.

## Public URL shapes and limitations

```text
SBB: https://www.sbb.ch/en?stops={origin_station_name}_I{origin_station_code}~{station_name}_I{station_code}&day={arrival_date}&time=08_00&moment=dep
NS: https://www.nsinternational.com/en/traintickets-v3/#/search/{origin_station_code}/{station_code}/{arrival_ymd}?pax=A&inboundDate={departure_ymd}
CP: https://www.cp.pt/pt/resultado-pesquisa?departureStation={origin_place_id}&arrivalStation={place_id}&startDate={arrival_date}&endDate={departure_date}&passageiros={travelers}&selectedClass=2
Vueling: https://tickets.vueling.com/booking/flightSearch?o={origin_iata}&d={iata}&dd={arrival_date}&rd={departure_date}&adt={travelers}&chd=0&inf=0&c=en-GB&cur=EUR
Legacy SBB: https://www.sbb.ch/en/buying/pages/fahrplan/fahrplan.xhtml?suche=true&von=Gen%C3%A8ve&nach=Z%C3%BCrich%20HB&datum=09.01.2027&zeit=08%3A00&an=false&reisedatumRueckfahrt=11.01.2027&anzahlErwachsene=1
SWISS: https://www.swiss.com/booking/flight-search?tripType=R&flight1=PAR.GVA.2027-01-09&flight2=GVA.PAR.2027-01-11&adults=1
Aer Lingus: https://www.aerlingus.com/booking/flight-search/?origin=CDG&destination=DUB&departureDate=2027-01-09&returnDate=2027-01-11&adults=1
```

SBB stop search verified 8768600 Paris Gare de Lyon, 8772319 Lyon Part Dieu,
8301700 Milano Centrale; domestic IDs are 8501008 Genève, 8503000 Zürich HB,
8505000 Luzern. Template substitutions percent-encode names (including spaces
and accents); `%20` and the manually tested `+` have the same decoded value.
SBB's current query honors the outbound date but has **no return/party URL
parameters**. Normal Chrome and H defaulted to one Half Fare Travelcard. Tasks
therefore require 1 adult without reduction/Half-Fare, outbound plus return on
the departure date, both selected fares and total, and a stop before passenger
details/login/payment. If safe selection controls are unavailable, block; never
submit a search/personal-data form or claim reduced outbound prices as READY.
NS keeps safe fragment retention and existing reviewed gateway semantics.

## Dated render observations (steps 1–3)

All observations below: 2026-11-09; outbound January 9, 2027, return January 11
where supported. Start-page tasks forbade interactions; selection research
allowed only necessary/reject cookies and safe connection/fare selection. Last
frames remained outside the repository. No screenshots, private URLs or session
IDs are included. Runtime classifications can differ from visible state.

The public-template column refers to the shapes above, with arrival 2027-01-09,
departure 2027-01-11, one adult, and each row's mapped stations/airports.

| Provider / route | Public template | Frames | Observed state | Observed host/path change |
| --- | --- | ---: | --- | --- |
| CP Porto–Lisbon, step 1 | CP | 1 | Frame received; not retained/classified | Not established |
| Vueling ORY–Barcelona baseline | Vueling | 0 | Runtime `consent_required`; visual wall unverified | No public final observation |
| SBB Geneva–Zurich, legacy URL | Legacy SBB | 1 | Cookie/timetable shell, wrong date 09.11.2026; no fares | `www.sbb.ch` timetable surface |
| SWISS Paris–Geneva | SWISS | 1 | Cloudflare verification/bot wall | `www.swiss.com` booking surface |
| Aer Lingus CDG–Dublin, old URL | Aer Lingus | 1 | Sparse broken/loading surface, no fares | `www.aerlingus.com` booking surface |
| NS Paris–Amsterdam | NS | 2 | Jan 9 outbound fares EUR48/66.90/101.90/41/33 | `/en/traintickets-v3/`, unchanged |
| NS Brussels–Amsterdam | NS | 2 | Correct route/dates/party; connections-loading error | Same unchanged NS path |
| NS Paris–Barcelona | NS | 1 | Cookie wall; route/dates behind it, no readable fares | Same unchanged NS path |
| NS Geneva–Zurich | NS | 2 | Jan 9 outbound connections EUR89.80 | Same unchanged NS path |
| CP Porto–Lisbon, step 2 | CP | 2 | Correct route/date/class; no results for selected filters | `/pt/resultado-pesquisa`, unchanged |
| SBB Geneva–Zurich, current query | SBB | 1 | Correct date/times; price placeholders, no numeric prices | `/en`, unchanged |
| SBB Geneva–Lucerne | SBB | 1 | Correct date; loading skeleton and cookie banner | `/en`, unchanged |
| SBB Paris–Zurich | SBB | 2 | Correct date; direct TGV timetable/cookie wall, no numeric prices | `/en`, unchanged |
| SBB Paris–Milan | SBB | 3 | Correct date; CHF117.30/88/71 connection prices | `/en`, unchanged |
| SBB Lyon–Milan | SBB | 3 | Correct date; direct FR CHF73; alternatives 85.30/89/72 | `/en`, unchanged |
| SBB Geneva–Milan | SBB | 3 | Correct date; CHF82.50/60.70/51.30; direct EC64 | `/en`, unchanged |
| SBB Geneva–Zurich selection research | SBB | 4 | Connection preview, 2nd class from CHF29.80; Select tickets still present | `/en?...` → same query plus `trip=[redacted]` |
| NS Paris–Amsterdam selection research | NS | 10 | Both Jan 9/11 Mid-flex legs selected, 1 passenger, EUR89; Enter your details unclicked | `/en/traintickets-v3/`, unchanged |

Three-frame start-page probes were intentionally cancelled at the third frame;
their `failed/provider_error` is not a render failure. SBB selection ended
`login_required`, but the retained frame was connection preview, not proof of a
login page. NS selected review ended `provider_error`, not runtime READY. No
passenger/login/payment URL was observed. Path auditing in steps 1–2 did not
retain queries/fragments; step 3 retained scrubbed path+query, not fragments.
The retained records are not complete runtime action audits.

Execution caveats: step 1 Vueling unexpectedly retried once without a separate
quota check. Later launchers disabled retries and quota-gated each creation.
Step 2's initial response-hook bug consumed three sessions with no valid frames;
those attempts are not provider-render evidence. Cleanup returned HTTP204.
Step 4 is offline implementation only; no new live sessions.

## Unwired candidates and checkpoint uncertainty

Trenitalia/Le Frecce: public form uses POST; candidate white-label URL stayed
loading in Chrome. Italo: booking links found but no complete dated fare GET.
Renfe: public code exposes a fallback search endpoint, not a verified dated GET.
SNCB: international booking uses b-europe.com. These booking hosts, plus
ventas.ouigo.com, are outside current reviewed scopes;
policy was not broadened. Iberia/Volotea: no validated dated party fare link.
Aer Lingus's different `/app/plan/plan` query still showed an empty form behind
consent in Chrome. Official OUIGO España dated deep-link shape was found, but
the Madrid–Barcelona candidate showed an error in Chrome; no H probe. ITA and
other prohibited providers remain excluded. Marketing/timetable pages are not
fare preparation evidence. The older SNCB handoff/registry discrepancy remains
historical; no international booking authorization is inferred from it.

SBB's P11 ticket-offer guess is
`/en/buying/pages/(offerte|angebot)/(offerte|angebot).xhtml`, **not live verified**.
Neither `/en?...` nor `/en?...&trip=...` matches it. `trip` proves connection
preview only. NS retains its existing unverified overview/review guess; actual
selected review stayed on the results path. Neither is a proven READY URL.
Both providers merge defensive path-boundary and explicit step/stage/screen/page
query patterns for passenger/login/payment/checkout. Bare `guests=1` and `pax=A`
do not trigger those boundaries. The same defensive boundaries are merged into
legacy CP/Vueling checkpoints, without changing their guessed ready paths, so
alternatives also stop at login. Ready patterns exclude nested login or explicit
personal-details navigation state even under a guessed review/offer path.
Actual beyond-page URLs are unobserved; do not
visit passenger details just to discover them. Next step must validate guesses
live or document failure, never broaden READY to shared results or previews.

# R5-02 step 5 live transport smokes — 2026-11-09

Merged HAgentRunner.run with branch build_task output, alternatives removed only
to keep each invocation single-task. Paris origin, March20–22 2027, race March21,
one adult, EUR600 budget; same external launcher and summary-only privacy method
as the hotel smokes. No synthetic provider or direct raw-session navigation used.
NS start fragments retain the normal P12 keep_fragment flag. Frame counts below
are actual deduplicated live_frame emissions, not raw observation counts.

| Task | Adapter/policy | Frames | Final observed host/path | Checkpoint | hclient status | reason_code |
|---|---|---:|---|---|---|---|
| Paris–Barcelona | ns-international | 10 | www.nsinternational.com/en/traintickets-v3/ | no | blocked | sold_out |
| Paris–Milan | vueling-com | 0 | unavailable (no public final URL) | no | blocked | provider_error |
| Paris–Amsterdam | ns-international | 7 | www.nsinternational.com/en/traintickets-v3/ | no | failed | unsafe_claim |

Paris–Barcelona: quota available=3 before starting, exactly one session created,
explicit cleanup HTTP204; elapsed239.7s. sold_out is the actual runtime
classification, not an independently verified inventory claim from these
summary-only measurements. No READY and no distinct safe path/query checkpoint
were established. Existing unverified overview/review pattern remains unchanged.

Paris–Milan: quota available=3, one session created, cleanup HTTP204; elapsed14.3s.
No frame or public final URL was emitted. The merged runtime returned
provider_error, not unreviewed_redirect. This is consistent with the corrected
browser-startup/blank-observation classification, but this summary does not expose
the underlying raw Chrome observation or prove a DNS/TLS/bot-wall cause. The
underlying Vueling load failure remains unresolved. No new scope/checkpoint
was inferred from absence of public observations.

Paris–Amsterdam: quota available=3, one session created, cleanup HTTP204;
elapsed169.0s. Real runtime returned failed/unsafe_claim, not READY. Last public
host/path still the NS root, not the configured overview/review boundary.
This safety failure needs review before retry; these scrubbed summary-only
measurements do not establish that any payment or booking actually happened.
Code inspection shows this reason is assigned by _UnsafeClaim, reached through
_payment_claim checks on hosted events/answers. That predicate also accepts
form_submitted, terms_accepted, account_created and personal_data_entered
admissions, not only payment/booking. Thus the verified evidence is a runtime
claim-gate failure, not a verified executed transaction. The triggering payload
and actual hosted action were not retained or independently audited. Runtime
owner review is needed; hclient's documented non-interceptable hosted-tool limit
means prompt guardrails and cancellation alone are not deterministic prevention.

# R5-02 step 4 second-provider research — 2026-11-09

No new adapter met the full dated round-trip + party + safe checkpoint standard
in this additional bounded pass. The 21-row matrix below is unchanged: 20 covered,
Geneva–Lucerne still a gap; second sites only for Paris–Barcelona/Geneva. Existing
matrix tests continue to describe this state, rather than asserting invented
coverage. No policy was upgraded and no new host scope was added.

Terms reread before considering each candidate:
- SBB `/en/meta/legallines/legal-information.html`: individual pages may be saved
  with copyright notices retained; public/commercial use needs written consent.
  Existing owner-rule read/prepare-only status is not affirmative authorization.
- Trenitalia Italian site-use terms reached; French official portal now redirects
  to trenitalia.fr. Its `/les-mentions-legales/` was read separately: private use
  of protected elements only, other reproduction requires agreement. No scope
  extension from the Italian review was assumed.
- TAP user-conduct clauses explicitly prohibit manual/automatic scripts, robots,
  scraping/crawling and automatic interaction/collection. **Still prohibited**;
  no booking attempt or adapter, despite Paris–Lisbon/Porto candidate priority.
- SWISS copyright page retains written-consent restrictions. Iberia legal notice
  allows private/non-commercial download, not public/commercial exploitation.
  Volotea terms reserve content rights and require prior written consent for
  use/reproduction; membership fare trials may create accounts/renewal charges.
  No memberships, consent or account flow touched. Existing owner rules unchanged.
- Renfe public legal paragraphs were reread, including reproduction/use limits
  and contracted-service exception. OUIGO España explicitly restricts copying and
  third-party profit-making use. Neither review supplies a verified Lyon–Barcelona
  result link. Spanish-only destination pages do not establish a Paris cross-border
  route; no route was inferred from destination-country coverage alone.

**SBB additional finding:** public GET timetable with `suche=true`, `von=Genève`,
`nach=Luzern`, `datum=20.03.2027`, `zeit=08:00`, `an=false` rendered March 20
departures including 08:05 and 08:54 with ticket-purchase controls. This is NOT a
verified round-trip party total. The page carries a reCAPTCHA notice; no challenge
was handled. Inspection showed purchase controls inside forms with PrimeFaces
AJAX handlers. **They were not clicked.**
This is a verified next-action form boundary, not proof that no alternative public
GET ticket link exists. Geneva–Zurich and Paris–Zurich/Lucerne dated timetable
GETs rendered the timetable shell; no complete round-trip/one-adult fare and safe
distinct checkpoint were established. SBB remains unwired, Geneva–Lucerne open.

Trenitalia's dated Paris Gare de Lyon–Milano Centrale reservation candidate
returned a shell/error, not dated one-adult round-trip fare results.
The official French `/reservation/` path is an assistance/group-reservation page,
not a dated fare result, even with date/party query parameters. No search submitted.
SWISS `/booking/flight-selection` dated candidate returned requested-page-not-found;
homepage loaded but does not count as coverage. Iberia's dated candidate returned
Not Found. Volotea
`/en/booking/select-flight/` dated candidate returned its 404 page. These failed
candidate URL shapes do not prove the carriers lack working booking flows; no
safe dated deep link was established within this pass, so no adapters were added.

# R5-02 step 3 coverage — 2026-11-09

The table is adapter-level coverage for **one adult**, not proof of selected
round-trip checkout or H success. Dates and the default adult age category must
match on the live page. Existing train-before-flight ordering makes NS primary
over Vueling wherever both have an executable reviewed adapter.

| Origin | Race city | Primary | P7 alternative | Gateway / limit |
|---|---|---|---|---|
| Paris | Milan | Vueling | none verified | MXP |
| Paris | Lisbon | Vueling | none verified | LIS |
| Paris | Barcelona | NS International | Vueling | Paris Gare de Lyon–Barcelona Sants |
| Paris | Valencia | Vueling | none verified | VLC |
| Paris | Seville | Vueling | none verified | SVQ |
| Paris | Madrid | Vueling | none verified | MAD |
| Paris | Rome | Vueling | none verified | FCO |
| Paris | Amsterdam | NS International | none verified | Amsterdam Centraal |
| Paris | Den Haag | NS International | none verified | Amsterdam; onward transfer excluded |
| Paris | Lyon | NS International | none verified | Paris Gare de Lyon–Lyon Part Dieu |
| Paris | Porto | Vueling | none verified | ORY–OPO via BCN |
| Paris | Berlin | NS International | none verified | Paris Nord–Berlin Hbf |
| Paris | Geneva | NS International | Vueling | Paris Gare de Lyon–Genève |
| Paris | Zurich | Vueling | none verified | ORY–ZRH via BCN |
| Paris | Stoos | Vueling | none verified | Zurich; onward transfer excluded |
| Paris | Morschach | Vueling | none verified | Zurich; onward transfer excluded |
| Paris | Brunnen | Vueling | none verified | Zurich; onward transfer excluded |
| Brussels | Amsterdam | NS International | none verified | Brussels Midi–Amsterdam Centraal |
| Geneva | Zurich | NS International | none verified | Genève–Zürich HB |
| Geneva | Lucerne | **gap** | none verified | SBB timetable is not a verified fare deep link |
| Lyon | Barcelona | Vueling | none verified | LYS–BCN; NS timetable lacked prices |

20/21 requested pairs have adapter coverage. One route gap remains: Geneva–Lucerne.
**Shortfall:** two distinct reviewed sites are wired only for Paris–Barcelona and
Paris–Geneva. Research did not establish safe executable second sites elsewhere;
this is not a claim that no such provider exists. Coverage does not imply a
verified URL checkpoint: NS and Vueling share the unresolved boundary gap below.

### New dated normal-Chrome result evidence

NS public template (safe fragment retained by P12):
`https://www.nsinternational.com/en/traintickets-v3/#/search/{origin}/{destination}/{YYYYMMDD}?pax=A&inboundDate={YYYYMMDD}`.
Observed January 9–11 2027 with one Adult (26–59 years), public outbound fares and
times on each wired route: FRPLY→FRLPD (Lyon), FRPLY→ESBST (Barcelona),
FRPLY→CHGVA (Geneva), FRPNO→DEBHF (Berlin), BEBMI→NLASC (Amsterdam),
CHGVA→CHAJD (Zurich). Station labels and dates were displayed; these are not
selected round-trip totals. Paris–Zurich and Lyon–Barcelona returned route/times
but no clearly captured fare, so no new NS adapters were wired for those pairs.
March Paris–Zurich remained loading; not evidence of inventory.

Vueling retained public flightSearch template with o=ORY, d=OPO or ZRH,
dd=2027-03-20, rd=2027-03-22, adt=1, chd=0, inf=0, c=en-GB, cur=EUR.
Both loaded selectFlight lists with Return / 1 Adult, matching destination and
outbound/return public EUR fares via BCN. Selecting the first safe outbound
confirmed Sat 20 Mar, ORY→OPO 07:00–21:15 and ORY→ZRH 07:00–20:25, still on
selectFlight. Return calendar included Mon 22 Mar; no passenger details opened.
One-adult limits are explicit for every new adapter; other party sizes fail
closed where no prior verified adapter supports them. Tiny-town gateway routes
reuse that Zurich search, not a claim that Zurich is the race town or that the
local rail/bus/funicular transfer is included.

### Candidate terms and unsuccessful research (not adapters)

- NS disclaimer and Vueling terms reread before extending their existing owner-rule
  adapters: copyright reservations are not affirmative automation permission;
  retain in-session-only screenshots, no forms/accounts/consent/payment.
- SBB public timetable at `www.sbb.ch/en/buying/pages/fahrplan/fahrplan.xhtml`
  showed Genève→Luzern on January 9 2027, times and “Tickets purchase available”.
  A reCAPTCHA notice was present; no captcha was touched and no round-trip
  one-adult public fare deep link was established. No SBB adapter added.
- SNCB copyright declaration reread at
  `www.belgiantrain.be/en/support/customer-service/copyright-declaration`:
  using/reproducing/displaying site components requires prior written permission.
  Keep prohibited; no booking research or adapter.
- TAP `/en-ca/legal-info/terms-and-conditions` reread: copyright/content require
  written authorization and user-conduct obligations include automated mechanisms.
  Keep prohibited; no booking research or adapter.
- Iberia legal notice expanded and reread: personal use, restrictions on
  exploitation/reproduction/distribution/modification/public communication and
  commercial use remain materially ambiguous. A dated /gb/flight-search attempt
  returned 404; no adapter added.
- OUIGO France legal page and España `/es/informacion-legal` reached; no new
  authorization decision. España dated public `_deeplink/journey-search`
  attempt returned “Ha ocurrido un error…”, not date/party results. No adapter.
- Renfe legal link showed only the cookie layer in the captured state. Italo
  legal headings loaded but clause bodies were not established. CP aviso-legal
  public sections reserve protected signs/reproduction. These partial reads do
  not authorize new scopes or adapters. Existing CP adapter is unchanged.
- Volotea, SWISS and the remaining Italian deep-link candidates were not fully
  reverified in this handoff. No guessed adapters or policy upgrades added.
- SNCF Connect, easyJet, Transavia and Eurowings stay prohibited. No captcha,
  bot wall, private data, consent acceptance or form submission was bypassed.

# R5-02 step 2 observations — 2026-11-09

**R5-01 integration correction:** H's browser showed a Chrome internal error
page (chromewebdata), which pre-R5-01 hclient classified as an unreviewed redirect
before any frame. R5-01 now treats browser-internal URLs as blank observations,
fixing that classification, NOT the underlying page-load failure. A post-merge
H live smoke is still needed; no second H session was run in this handoff.
The original round-4 raw URLs remain unavailable, so their exact network failures
are not independently identified by this one-session reproduction.

## Vueling: exactly one quota-gated H probe

Terms reread in normal Chrome at www.vueling.com,
`/en/customer-services/website-conditions-of-use`: all ten legal accordions.
Section 1 still limits the stated Website to pages served by www.vueling.com;
sections 2/7 restrict commercial copying/exploitation. No express robots/agents
prohibition found. Existing owner-rule ambiguity remains, not express permission.
No new company host was observed, so no navigation scope was widened.

Probe script outside the repository: `/home/ubuntu/scratch/vueling_probe.py`.
Used H API v2 with hclient GUARDRAILS, ORY–BCN, 20–22 March 2027, one adult;
initial page read only, no clicks or typing, max_steps=3. Quota checked before
creation; exactly one session created and deleted. Only scrubbed locations and
operational status logged; no key, session ID, query or private URL logged:

```text
quota available 3
observation host chromewebdata path withheld
terminal completed
cleanup HTTP 204
```

This is a Chrome-internal error location, NOT evidence of a new Vueling company
host or of a bot/captcha wall. The browser network error subtype was not retained,
so DNS/TLS/connection failures and bot denial cannot be distinguished. No second
session was run. Normal Chrome loaded tickets.vueling.com `/booking/selectFlight`
from the same ORY–BCN template and dates, without a bot wall. This countercheck
disproves a universal same-template redirect/block in normal Chrome, not an H-only
network or bot failure. Do not call the historical round-4 cause confirmed.

Reachable classification chain in hclient: observation_event metadata.url is
passed through clean_url/scrub_url; non-HTTP(S) returns None; _reviewed rejects it;
_attempt raises unreviewed_redirect before the observation screenshot is emitted.
An offline control confirmed internal Chrome error URLs are rejected while the
normal Vueling selection URL is reviewed. This explains how the newly observed
H error would produce unreviewed_redirect/zero frames. The original round-4 raw
observation URLs were not available here, so identity with those failures remains
unverified. No bot-wall evidence justifies making Vueling fallback-only yet.

## Actual selected states in normal Chrome

**Vueling:** tickets.vueling.com `/booking/selectFlight` remained unchanged from
the initial list through outbound selection, return selection and Fly Light bundle
selection. Outbound 20 March 2027 07:00 ORY–08:40 BCN; return 22 March 05:50
BCN–07:40 ORY; selected Fly Light; full-party total EUR120.98. Stopped before the
CONTINUE control; no passenger page opened. Public selection controls were buttons
outside forms. The guessed selectFare/fareSelection/review URL was not observed.
Screenshot (in-session only): `/home/ubuntu/scratch/r5-vueling-selected.png`.

**NS International:** www.nsinternational.com `/en/traintickets-v3/` with public
fragment route `#/search/FRPNO/NLASC/20270320/1055/1420` remained unchanged from
outward selection through return selection and the final **Check your trip** pane.
One adult, Paris Nord–Amsterdam Centraal 20 March 10:55–14:20, return 22 March
07:10–10:35; both 2nd class Mid-flex, full total EUR90.00. Stopped before **Enter
your details**. Cookie choice Decline only. No carrier-host navigation, personal
data or form submission. Screenshot (in-session only):
`/home/ubuntu/scratch/r5-ns-final-check.png`.

There is NO distinct selected-review URL for either observed flow. URL-only
immediate-stop matching would also stop an earlier unselected state. The NS
fragment is moreover removed by scrub_url both at session startup and observation
cleaning. Direct offline output for the observed NS URL:

```text
NS scrubbed host/path: https://www.nsinternational.com/en/traintickets-v3/
NS retained fragment: False
existing NS overview pattern matches cleaned: False
```

Matching only `/en/traintickets-v3/` cannot distinguish blank search, results,
selected fare or final check. Preserving the fragment alone is insufficient:
the final-check pane did not change the fragment. A state-aware checkpoint
contract/runtime change is needed; hclient/scrub are outside this ticket's scope.
After the R5-01 merge, first-match force_answer makes these shared URLs unsafe
checkpoint patterns. requires_selection was removed. Distinct Vueling
selectFare/fareSelection/review and NS traintickets-v3 overview/review patterns
remain **unverified** and deliberately do not match initial/shared result pages.
There is no verified deterministic URL checkpoint for these flows. A fresh
Vueling check again selected both legs and Fly Light (EUR120.98) on selectFlight
with no query. The following visible stage is DETAILS, before SEATS/LUGGAGE/EXTRAS;
Continue exposes no safe destination URL in its button markup. It was not clicked
because passenger details are the next indicated boundary. No pre-personal-data
post-selection distinct path/query was established. Screenshot (in-session only):
`/home/ubuntu/scratch/r5-vueling-selected-recheck.png`.

P12 now preserves the reviewed NS start fragment with keep_fragment=true; direct
_safe_start_fragment returned True. The prior fragment-loss startup limitation
below is historical, not the merged runtime behavior. Final NS pane still leaves
the fragment unchanged, so preserving it does not solve checkpoint detection.

# R5-02 offline checkpoint additions (2026-11-09)

All transport adapters carry independent task/P7 checkpoint metadata; 60 steps.
Patterns are unquoted path/query case-insensitive searches with a negative lookahead excluding
the generic unsafe expression in site-policy.md and `(?:[/?#]|$)` suffix.

| Adapter | Checkpoint expression | Evidence status |
| --- | --- | --- |
| Vueling (all route variants) | `/booking/(?:selectFare|fareSelection|review)` | **Guessed, unverified.** Selected state stayed on selectFlight; no distinct safe path/query was observed. |
| NS International | `/en/traintickets-v3/(?:overview|review)` | **Guessed, unverified.** Selected Check your trip pane kept the same path/fragment; search fragment cannot be matched by P11. |
| CP | `/pt/(?:resumo-viagem|resumo-compra)` | **Guessed, unverified.** Public results are documented, selected round-trip review URL is unknown. |

On matching the checkpoint, stop and answer immediately: READY with complete
two-leg evidence, otherwise BLOCKED unsafe_claim. Never navigate beyond patterns.
No live provider called in this step; guessed paths are not authorization or proof
of real stops. Reviewed Den Haag via Amsterdam exposes expected.gateway_city
Amsterdam while preserving the original race city, including aliases. Onward
transfer remains excluded. Runtime gateway support is inherited from R5-01.

# Transport site evidence: R2-02 (supersedes R1-06)

The R1 heuristic routing (country rail sites + Google Flights fallback) is **withdrawn**. Prohibited by their
terms (reviewed 2026-11-08): Google Travel/Flights, Skyscanner, Kayak, Omio, Trainline, SNCF Connect,
Eurostar, BlaBlaCar, Ryanair, easyJet, TAP, Lufthansa, Air France, ITA, KLM, Transavia, Wizz Air, Eurowings,
Rome2rio, Busbud and **FlixBus**. FlixBus's booking conditions have no robot clause, but its separate Online
Terms of Use (pass 2) prohibit "deep-link, screen-scrape, robot, crawl...", so it is denied.

## Executable transport adapters

| Adapter | Policy | Coverage | Deep link |
|---|---|---|---|
| CP `www.cp.pt/pt/resultado-pesquisa` | allowed_owner_rule | Portugal domestic, reviewed station IDs (Lisbon 94-31039, Porto 94-2006, ...) | **Observed** 2026-11-08: Lisbon–Porto journeys and fares on 2026-11-23. For March 2027 the site showed "Não foram encontrados resultados" (sales horizon not open). That is reported as **blocked/no inventory**, never as ready. The round-trip `endDate` parameter is **unverified**. |

Policy-allowed but **not executable** because no public GET deep link is verified: Trenitalia and Renfe (flows
appear POST-based), SBB (result URL format unverified), Italo, ÖBB, SNCB, NS International, Ouigo, ALSA,
SWISS, Aegean, Volotea, Iberia, Aer Lingus. Routes without an adapter raise `ValueError` and are blocked
honestly. This includes Paris→Milan and every cross-border trip as of this review.

## Task contract

- Ready = a selected viable **outbound and return** fare, with the outbound arriving by `arrival_date`, the return
  on `departure_date`, the right route and party and a total price, before passenger data. Unselected results, a
  one-way fare or a homepage are not ready. Unreviewed redirects (carrier/OTA) are blocked.
- `max_steps` = 80. `expected` and `allowed_hosts` come from the reviewed policy.

## Not yet observed

No live H transport run has happened in R2-02. The selected round-trip fare is **unverified**.

## Round 3 (R3-01)

Research date: **2026-11-09**. Normal Chrome through Playwright/CDP, **not H**. Public GET
URLs only; no forms filled/submitted, login, personal data, bookings or consent acceptance.
The Vueling legal-page cookie banner was rejected to read its accordions. No flight/fare was
selected. Search results are **not** selected-round-trip or pre-passenger safe-stop evidence.

### Verified Vueling template

**VY-RT**, host `tickets.vueling.com`:

```text
https://tickets.vueling.com/booking/flightSearch?o={origin_iata}&d={iata}&dd={arrival_date}&rd={departure_date}&adt={travelers}&chd=0&inf=0&c=en-GB&cur=EUR
```

The compact query keys matter: `origin`, `destination`, `departureDate`, `returnDate` and `ADT`
were ignored, leaving a blank/stale search. The working link redirects on the same host to
`/booking/selectFlight`, rendering separate **OUTBOUND** and **RETURN** lists and
`Return • 1 Adult` / `Return • 2 Adults`. Active date tabs, not surrounding suggested days,
were checked: **Sat 9 Jan** outbound and **Mon 11 Jan** return for **2027-01-09..11**.
The public app's query parser also supplied the compact key names; no search was submitted.

Every dated line below uses **VY-RT**, the above January 9–11 2027 stay and **1 adult**.
Counts are visible priced options on the selected day, not selected or reserved flights.
The real empty-leg message is **“NO FLIGHTS ON THIS DAY. NO WORRIES, YOU STILL HAVE PLENTY
TO PICK FROM.”** Date tabs also show **“No flights”**. This is `no_inventory`; never change
the dates to a suggested day. No captcha or login wall on these result pages.

| Date | Host/template | Tested route (reviewed airport mapping) | Page showed outbound / return |
| --- | --- | --- | --- |
| 2026-11-09 | tickets.vueling.com / VY-RT | Paris ORY → Milan MXP | Correct headings, party and active dates; 8 / 10 priced options, mostly BCN connections. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Paris ORY → Lisbon LIS | Correct headings, party and active dates; 6 / 10 priced options via BCN. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Paris ORY → Valencia VLC | Correct headings, party and active dates; 2 / 3 priced options, direct flights. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Paris ORY → Zurich ZRH | Correct headings, party and active dates; 7 / 6 priced options via BCN; some outbound options arrived +1 day and must be rejected. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Lyon LYS → Milan MXP | Correct headings, party and active dates; 2 outbound options, return empty with the real no-flights message above: **no_inventory**. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Lyon LYS → Lisbon LIS | Correct headings, party and active dates; 2 outbound options, return empty with the real no-flights message above: **no_inventory**. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Lyon LYS → Zurich ZRH | Correct headings, party and active dates; 1 outbound option, return empty with the real no-flights message above: **no_inventory**. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Bruxelles BRU → Milan MXP | Correct headings, party and active dates; 1 / 4 priced options. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Bruxelles BRU → Lisbon LIS | Correct headings, party and active dates; 2 / 3 priced options. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Bruxelles BRU → Valencia VLC | Correct headings, party and active dates; 1 / 1 priced option. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Bruxelles BRU → Zurich ZRH | Correct headings, party and active dates; 2 / 2 priced options. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Bruxelles BRU → Basel BSL (Freiburg airport fallback) | Correct BASEL headings, party and active dates; outbound empty with the real no-flights message above, 2 return options: **no_inventory**. This is not a flight to Freiburg city or an included onward transfer. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Genève GVA → Milan MXP | Correct headings, party and active dates; 2 / 1 priced options. |
| 2026-11-09 | tickets.vueling.com / VY-RT | Genève GVA → Lisbon LIS | Correct headings, party and active dates; 2 / 1 priced options. |

- **2026-11-09 — tickets.vueling.com / VY-RT — Paris ORY → Milan MXP, 2027-01-09..11,
  2 adults**: active dates match; `Return • 2 Adults`, 8 outbound / 10 return priced options.
- **2026-11-09 — tickets.vueling.com / VY-RT — Paris ORY → Lisbon LIS, 2027-01-09..11,
  2 adults**: active dates match; `Return • 2 Adults`, 6 outbound / 10 return priced options.
- **2026-11-09 — tickets.vueling.com / VY-RT — Paris ORY → Valencia VLC, 2027-01-09..11,
  2 adults**: active dates match; `Return • 2 Adults`, 2 outbound / 3 return priced options.
- **2026-11-09 — tickets.vueling.com / VY-RT — Paris ORY → Zurich ZRH, 2027-01-09..11,
  2 adults**: active dates match; `Return • 2 Adults`, 7 outbound / 6 return priced options.
- **2026-11-09 — tickets.vueling.com / VY-RT — Paris ORY → Milan MXP, 2027-04-09..11,
  1 adult**: active **Fri 9 Apr / Sun 11 Apr**, 10 outbound / 10 return priced options.
  April 2027 is already on sale here, **not** evidence of a flight sales-horizon failure.
- **2026-11-09 — tickets.vueling.com / VY-RT — Paris ORY → Milan MXP, 2028-01-09..11,
  1 adult**, beyond the currently displayed flight availability: active **Sun 9 Jan /
  Tue 11 Jan**, both legs show **“NO FLIGHTS ON THIS DAY. NO WORRIES, YOU STILL HAVE
  PLENTY TO PICK FROM.”** Report `no_inventory`; the site did not distinguish sold-out
  inventory from a not-yet-open sale horizon.

The registry has four flight adapters to avoid implying every Cartesian route works:
Paris/Bruxelles → MXP/LIS/VLC/ZRH; Lyon → MXP/LIS/ZRH; Genève → MXP/LIS;
Bruxelles → BSL. Reviewed aliases share the verified code, not a guessed city code:
Milan/Milano, Lisbon/Lisboa/Lisbonne, Valencia/València, Zurich/Zürich,
Bruxelles/Brussels/Brussel, Genève/Geneva/Genf/Ginevra and Freiburg/Freiburg im Breisgau.
No unverified Porto/Madrid/Barcelona/Geneva-destination routes were added just to enlarge a table.

### Terms and host review

- **2026-11-09 — Vueling**, `https://www.vueling.com/en/customer-services/website-conditions-of-use`:
  all ten accordions reread in the browser (especially 01, 02, 05 and 07). No express
  robots/agents/scraping prohibition found. Section 02 restricts commercial copying/reuse;
  section 07 reserves content rights and restricts use to the user's own needs. Section 01
  says the Website only encompasses pages served by `www.vueling.com`. The public
  `tickets.vueling.com` booking footer links to this same notice, but the narrow scope wording
  leaves applicability **ambiguous**, not express contractual authorization. Retain the
  existing owner's read-only rule and include only that observed booking host. Review date
  2026-11-09, expiry 2027-02-07; screenshots in-session only. No forms/accounts/consent/payment.
- **2026-11-09 — Deutsche Bahn review attempted**:
  `https://www.bahn.de/agb`, `https://www.bahn.de/nutzungsbedingungen` and
  `https://int.bahn.de/en/terms-of-use` all returned **Access Denied**. The tested
  `int.bahn.de/en/buchung/fahrplan/suche` Paris–Freiburg fragment link also returned Access Denied.
  No captcha bypass or repeated access attempts. **No readable terms; no finding about an
  express agent prohibition is possible.** New `bahn-de` entry is **ambiguous**, screenshot
  scope **none**, no adapter, dated 2026-11-09 and expiring 2027-02-07. It is not owner-authorized.
- **2026-11-09 — SWISS copyright reread**, `https://www.swiss.com/ch/en/terms-conditions/copyright`:
  content may not be used/duplicated/reproduced without written consent. No adapter was verified
  or added, and the existing entry was not refreshed. This is not evidence SWISS serves BSL.

### Rejected candidates and remaining gaps

- **2026-11-09 — Vueling / VY-RT**: Paris ORY→BSL and CDG→BSL (CDG also tested with 2 adults),
  Lyon→VLC/BSL and Genève→VLC/ZRH/BSL returned the search form with blank dates or a stale
  previous route rather than matching round-trip results. **Rejected, no adapters for these
  pairs.** Form redirects are `date_mismatch`, not a fabricated no-inventory message.
- **2026-11-09 — Vueling guessed legacy routes**: `/en/book-your-flight/select-flights` showed
  “OH DEAR, THIS PAGE SEEMS TO BE ON HOLIDAY!”; `tickets.vueling.com/booking/FlightSearch.aspx`
  redirected to manage/findBooking and asked for booking code/name. Rejected; no personal data entered.
- **2026-11-09 — SWISS guessed GET routes**: `/xx/en/booking/flight-information` and
  `/booking/flight-search` rendered page-not-found messages with the supplied route/date parameters.
  Rejected; no working round-trip booking URL or Basel service established.
- **2026-11-09 — Iberia**: `/flight-search-engine/` and `/web/dispatchFlightSearch.do` with
  Paris–Milan round-trip parameters returned Not Found; rejected. The homepage flight form is POST;
  it was not filled/submitted. No adapter added or policy entry refreshed.
- **2026-11-09 — SBB**: `/en?date=2027-01-09&moment=DEPARTURE&stops=...` showed the homepage,
  not a dated round trip; legacy `/en/buying/pages/fahrplan/fahrplan.xhtml?suche=true&von=Paris&nach=Zürich&datum=09.01.2027&returnDate=11.01.2027&adults=1`
  dropped its query and did not preserve the confirmed round trip. Rejected; no adapter added.
- **2026-11-09 — ÖBB**: the homepage's public ticket target was `shop.oebbtickets.at`, not the
  currently reviewed `tickets.oebb.at`; the observed form contained only an outbound date/time.
  No verified public round-trip link; no form submission or new-host authorization.
- **2026-11-09 — NS International**: `/en/traintickets?origin=FRPAR&destination=DEFRI&outboundDate=2027-01-09&inboundDate=2027-01-11&adults=1`
  redirected to `/en/traintickets-v3/#/search` and lost route/dates. Rejected.
- **2026-11-09 — Aer Lingus**: `/booking/flight-search/` with route/date/party query showed
  “Sorry, we couldn't find this page.” Rejected.
- **2026-11-09 — Aegean**: `/booking/flight-search/` on `en.aegeanair.com` with route/date/party
  query showed “Seems this page has taken off!” Rejected; that subdomain was not authorized.
- Volotea homepage was inspected without form interaction; no round-trip results URL was
  established. Trenitalia, Italo, Renfe, Ouigo, SNCB and CP were not newly verified this round.
  The preexisting CP adapter remains unchanged; its return parameter remains unverified as noted above.

**Minimum Paris→Freiburg is still unmet.** No verified round-trip rail adapter was found.
Vueling provides verified round-trip parameter preservation for **14/20** requested combinations,
of which **4** had a missing leg on the tested stay (all three Lyon routes and Bruxelles→BSL).
The other **6** remain fail-closed; no unverified lookup pair is registered to conceal these gaps.
No prohibited entry was relaxed. No selected fare, passenger-details stop or H success was observed.

### In-session screenshot evidence

Not for publication or repository inclusion:

```text
/home/ubuntu/r3-transport-vueling-{ORY,LYS,BRU,GVA}-{MXP,LIS,VLC,ZRH,BSL}-1.png
/home/ubuntu/r3-transport-vueling-ORY-{MXP,LIS,VLC,ZRH}-2-2027-01-09.png
/home/ubuntu/r3-transport-vueling-ORY-MXP-1-2027-04-09.png
/home/ubuntu/r3-transport-vueling-ORY-MXP-1-2028-01-09.png
```

The first pattern denotes only the 14 rendered result pairs listed above, not all 20 combinations.
The two-adult Valencia and January-2028 empty-leg screenshots were also visually inspected.

### STEP 3b — focused follow-up, 2026-11-09

Time-boxed to three candidates for Paris→Freiburg: Vueling, SWISS, SBB. Normal Chrome/CDP,
no H, forms, consent acceptance, login, booking or personal data. No adapter added.

- **2026-11-09 — tickets.vueling.com / VY-RT**, ORY→BSL, January 9–11 2027, 1 adult:
  again redirected to `/booking/flightSearch`, showing stale ORY→MXP and blank dates.
  No connecting itinerary or correct Basel result was rendered. The earlier CDG attempts
  also failed. This is date/route mismatch, not verified no-inventory.
- **2026-11-09 — www.swiss.com**:
  `https://www.swiss.com/fr/en/book-and-manage/destination?OriginCode=CDG&DestinationCode=BSL&OutboundDate=2027-01-09&InboundDate=2027-01-11&Adults=1&Cabin=E&tripType=RETURN`
  displayed Paris Charles de Gaulle→Basel Euroairport and a one-stop route summary, but
  ignored the dates: **“Lowest available fares…1 Adult, Economy, 14 Days”** and
  **“Showing prices in EUR for a round trip of 14 days”**, November/December calendar.
  Rejected. This establishes a public BSL route summary, **not** a January 9–11 offer.
  No substitution of ZRH for Freiburg.
- **2026-11-09 — www.sbb.ch**:
  `https://www.sbb.ch/en/buying/pages/fahrplan/fahrplan.xhtml?suche=true&von=Gen%C3%A8ve&nach=Z%C3%BCrich%20HB&datum=09.01.2027&zeit=08%3A00&an=false&reisedatumRueckfahrt=11.01.2027&anzahlErwachsene=1`
  rendered **Genève→Zürich HB**, **Sat, 09.01.2027. Departure 08:00**, outbound trains
  08:05→10:56 CHF29.80 and 08:35→11:28 CHF34.40. **No displayed return or party**, despite
  the proposed return/traveler parameters. Only per-connection purchase controls; they
  were not activated because the round-trip/traveler state was unverified and form
  submission is prohibited. The browser drops the query after loading the outbound state;
  this alone is not a failure to prefill, correcting the overly broad STEP 3 rejection.
- **2026-11-09 — www.sbb.ch**, same legacy template with `von=Paris&nach=Basel%20SBB`,
  January 9–11 2027, proposed 1 adult: **Paris→Basel SBB**, correct outbound date, TGV
  10:22→13:26 CHF47.00 and 12:22→15:26 CHF42.00. Again **no return date or party** displayed.
  Outbound timetable success is insufficient for an executable round-trip adapter.
- The new SBB homepage `stops`/`date`/`time` query was also checked for Genève→Zurich;
  it displayed the homepage, not a round-trip ticket offer. No readable no-inventory
  message was shown by these SBB checks; none is invented.

**Acceptance-critical Paris→Freiburg remains unresolved** after the agreed time box.
No new rail adapter, no SWISS adapter, no broader lookup pairs. Lausanne was not tested
as an alternative rail destination because the observed SBB link still lacks a return/party.

### Live check 2026-11-09

One real H transport session, concurrent with the single hotel session; **two total H runs,
no retries**. Owner-approved read/prepare-only instructions, 40-step cap. Case: Milano
Marathon, Milan, Italy, race 2027-04-04; Paris origin, outbound 2027-04-03, return
2027-04-05, 1 traveler, EUR450 round-trip budget for the whole party.

- Task: `vueling-com`, mode **flight**, public host `tickets.vueling.com`. Start template:
  `https://tickets.vueling.com/booking/flightSearch?o={origin_iata}&d={iata}&dd={arrival_date}&rd={departure_date}&adt={travelers}&chd=0&inf=0&c=en-GB&cur=EUR`.
  Reviewed pair ORY→MXP, April 3–5 2027, 1 adult; this is not a new live result-page success.
- Counts: **1 step_progress event** (session started), **0 frames**. The client exposes
  progress events, not the underlying H action/step count. Maximum allowed steps: 40.
- Final runner status **blocked**; exact reason **“Site policy unavailable or destination
  not authorized”**; reason-code-like **policy_denied**. No final public site URL retained.
- The client started the H session, then its policy/sensitive-observation gate stopped it
  before any reviewed frame was emitted. The sanitized result does **not** disclose the
  triggering URL or distinguish host/path rejection from a sensitive page/title. Do not
  label this a confirmed redirect, login wall, captcha or no-inventory result.
- **Not READY**: no selected outbound/return fare, party total or passenger-data safe stop
  was observed. No screenshot can be supplied for this run because zero frames arrived.

The secret was supplied only through exec environment. No H session/share/trace URLs,
tokens, personal data or raw provider responses were retained. The task prohibited all
forms, login, consent acceptance, booking, payment and personal data. No action trace
was retained, and no claim of an independently audited safe stop is made. No retries.

## R4-02 normal-Chrome research — 2026-11-09 (offline, no H)

Terms checks are in site-policy.md; all 14 requested allowed-but-unwired IDs exist.
No prohibited host was authorized. Public navigation and read-only inspection only;
no search submissions, passenger details, consent acceptance, payment or captcha bypass.
January trials use outbound 2027-01-09 / return 2027-01-11, one adult.

### Vueling verified additions

Pattern:
`https://tickets.vueling.com/booking/flightSearch?o={origin_iata}&d={iata}&dd=2027-01-09&rd=2027-01-11&adt=1&chd=0&inf=0&c=en-GB&cur=EUR`.

The following rendered /booking/selectFlight with both route headers, Return • 1 Adult,
active Sat 9 Jan and Mon 11 Jan tabs and public SELECT FLIGHT FOR EUR fares:
ORY–BCN, ORY–SVQ, ORY–FCO, ORY–MAD, CDG–GVA, LYS–BCN, GVA–BCN.
Examples: ORY–BCN EUR47 outbound / EUR33 return cards; LYS–BCN EUR42 / EUR34;
GVA–BCN EUR37 / EUR84; CDG–GVA EUR328 / EUR98. These are unselected leg
prices, NOT prepared round-trip totals or claims they fit the budget.
New mappings are restricted to the verified origin/destination pairs and one adult.

LYS–VLC, GVA–VLC, ORY–AMS, ORY–GVA and CDG–AMS reset to /booking/flightSearch
with blank/stale dates rather than a verified exact-date list: NOT wired.
CDG–BLQ showed both date tabs but no outbound flight on Jan 9 (return EUR103);
not wired as a new fare-list adapter. Florence was not verified and not added.
Use Paris CDG specifically for Geneva, ORY for the other new Paris routes.
Existing Paris Milan/Lisbon/Valencia/Zurich mappings and prior reviewed origins remain.

READY is the fare-selection page with outbound AND return selected, exact dates, party,
fare and full round-trip total visible; STOP and report READY immediately before
passenger details. This research verified lists, NOT that selected safe stop.
No-flights date tabs, nearby dates, missing return, wrong arrival day, login, captcha,
consent or a required form submission must block rather than become READY.

### NS International: new reviewed rail deep link

Verified:
`https://www.nsinternational.com/en/traintickets-v3/#/search/FRPNO/NLASC/20270109?pax=A&inboundDate=20270111`.

Rendered Paris Gare du Nord → Amsterdam Central, Sat 09 Jan / Mon 11 Jan, one Adult
(26–59 years), outbound departures/arrivals and EUR fares (e.g. 07:23→10:50 EUR48,
09:24→12:50 EUR41/EUR33). Return date appears in the search summary; a selected return
and its fare were NOT observed. Default age category must match; otherwise block.
pax=A encodes one adult, so traveler_counts=[1]; not a universal party-count mapping.
Rail remains preferred before flight, using the existing mode ordering.

Den Haag explicitly maps to this same reviewed Amsterdam Centraal gateway, with
`via: Amsterdam Centraal (onward Den Haag transfer not included)`. expected.city stays
Den Haag. Per the follow-up brief, READY covers the round trip to/from this reviewed
gateway; the onward local transfer is out of scope and must be mentioned in the final
report, never claimed as booked or included. Never substitute a non-reviewed gateway.
H client's city verification is untouched and currently does NOT support this gateway
semantics: Amsterdam-only page evidence cannot match expected.city Den Haag.

The initial guessed NS format with both dates as path segments reset to blank search;
using inboundDate in the fragment query fixed Amsterdam. A guessed NLGVC destination
first appeared to retain Amsterdam due to SPA hash state; a fresh navigation disproved
it and reset to blank search. Direct Den Haag code NOT added. No stale SPA state is
counted as verification.

NS-specific READY: journey/fare review after selecting BOTH outward and return,
showing routes, exact dates, party and full round-trip price, before opening passenger
details. STOP immediately there. That selected review was not observed; EUR0.00 and
an unselected outbound list are NOT READY. Never follow a link to a prohibited carrier
host, even when its name appears in an NS-sold train offer.

### Unwired transport research / blockers

| Policy | Public trial / discovery | Result |
| --- | --- | --- |
| trenitalia-com | www.trenitalia.com/en.html, inspect public booking links | Homepage/search controls, no verified dates+party round-trip fare deep link. Not wired. |
| italotreno-com | biglietti.italotreno.com/en/booking/ricerca-treni?osc=Milano&dsc=Roma&jt=roundtrip&od=09%2F01%2F2027&id=11%2F01%2F2027&adt=1&yng=0&chd=0&snr=0&inf=0&pet=0&lang=en&startSearch=true | Redirect /booking/ricerca retained dates but no stations/fares. Not wired. |
| sbb-ch | www.sbb.ch/en?date=2027-01-09&moment=DEPARTURE&stops=[{"value":"Zürich HB"},{"value":"Grindelwald"}] (URL-encoded) | Homepage timetable UI, no applied-date round-trip fare list/party. No domestic Swiss adapter. |
| renfe-com | /es/en homepage and /es/en/viajar/prepara-tu-viaje/billetes-ave-y-larga-distancia | Latter unavailable/404; no dated party fare link verified. Not wired. |
| ouigo-france | www.ouigo.com/ and public links | Root redirected /es/; no verified French dated party fare link. Not wired. |
| ouigo-espana | ventas.ouigo.com/es-ES/_deeplink/journey-search?target=calendar&origin=7117000&destination=7161200&outboundDate=2027-01-09&inboundDate=2027-01-11&passengers[0][type]=A&passengers[0][disability_type]=NH; also Madrid–Barcelona trial | Dates/one traveler/route shell rendered, but remained Cargando without fares; one guessed destination was Murcia, not intended city. Neither wired. |
| sncb-nmbs | www.belgiantrain.be/en | “We need to verify that you are not a robot.” Stopped, no bypass, no adapter. |
| alsa-com | /en/web/bus/home → /en/, public link discovery | Homepage/cookie UI; no verified dated party round-trip deep link. Not wired. |
| swiss-com | /booking/flight-search?tripType=R&flight1=PAR.GVA.2027-01-09&flight2=GVA.PAR.2027-01-11&adults=1 | “The requested page could not be found”; homepage also inspected. No adapter. |
| volotea-com | /en/, public link discovery | No verified dated party fare link; not wired. No exact-date fare-list trial established. |
| iberia-com | /us/, public link discovery | No verified dated party fare link; not wired. No exact-date fare-list trial established. |
| aegean | en.aegeanair.com/, public link discovery | No verified dated party fare link; incomplete website-use terms review. Not wired. |
| aerlingus-com | /html/en-US/home.html, public link discovery | No verified dated party fare link; incomplete current terms response. Not wired. |

No domestic Spain/Italy adapter was added: public searches above did not establish
a trustworthy round-trip fare list with dates and party. Zurich/Geneva to Savognin,
Grindelwald and Sierre remain blocked with no reviewed route. This is an explicit
gap, not an airport fallback or invented nearest-station mapping. Lyon/Genève to
Valencia likewise remain blocked, while Barcelona works. ÖBB/bahn.de were not
retested this handoff; previous Cloudflare/Access Denied evidence is not new evidence.

### Follow-up verifier inspection — 2026-11-09

Actual app path: app.prepare → providers.LiveRunner → agents.hclient.HAgentRunner.
There is no runai/hclient.py. Two independent read-only integration limitations:
1. _verified compares page city to expected.city. Controlled complete synthetic gateway
   evidence fails for Den Haag but passes for Amsterdam with all other inputs equal.
   This does not authorize inventing Den Haag page evidence or modifying expected.city.
2. HAgentRunner cleans start_url with scrub_url, which drops the NS public search fragment:
   `https://www.nsinternational.com/en/traintickets-v3/#/search/FRPNO/NLASC/20270115?pax=A&inboundDate=20270117`
   becomes `https://www.nsinternational.com/en/traintickets-v3/`. The offline adapter and
   policy checks do not prove that the live runner preserves routing. No hclient/scrub
   edit was made; no form submission or unreviewed routing workaround is authorized.

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
| 2026-11-09 | vueling-com / ORY–BCN | https://tickets.vueling.com/booking/flightSearch?o=ORY&d=BCN&dd=2027-01-15&rd=2027-01-17&adt=1&chd=0&inf=0&c=en-GB&cur=EUR | blocked | unreviewed_redirect | First unreviewed/non-public observation; no reviewed final page retained | 0 | 0 |
| 2026-11-09 | ns-international / Paris–Amsterdam | https://www.nsinternational.com/en/traintickets-v3/#/search/FRPNO/NLASC/20270115?pax=A&inboundDate=20270117 | failed | step_limit | NS booking surface: https://www.nsinternational.com/en/traintickets-v3/ | 40 | 9 |

Vueling returned `Site policy unavailable or destination not authorized`. The first
observation failed the reviewed-public-URL gate; its destination was not retained.
This does NOT establish a particular external redirect, captcha, inventory failure
or provider-page cause. No policy scope was broadened.

NS returned `H step limit reached`. The runner demonstrably removes the public routing
fragment before session creation, so the actual cleaned initial URL is
https://www.nsinternational.com/en/traintickets-v3/ . The last retained cleaned path
does not distinguish an unselected list from a selected journey. No selected round-trip
review or READY was verified. Start-URL fragment removal is confirmed; its contribution
to the final step limit is not independently established from the retained metadata.
Hclient/scrub were read-only and remain unchanged.

Instruction refinement in NS blocked_evidence: at the first loaded booking page,
missing/reset route, dates or party must stop BLOCKED date_mismatch immediately.
Never fill/submit search forms, reconstruct routing or keep browsing to the step limit.
This is not live-retested and does not repair fragment removal. Gateway-city verification
is a separate blocker for Den Haag. A separately scoped hclient/scrub contract change is
needed, not invented Den Haag evidence, loosened city checks or widened provider policy.

## Rebased R4-01 integration review — 2026-11-09 (offline only)

Rebased without conflicts onto origin/main `26be977847f5acf23924ce19bf3890e3346f3e50`,
including R4-01/#28 and R4-03/04/05. The live table above remains historical:
no additional H sessions were started and no old outcome was upgraded.

- Actual module remains runai.agents.hclient, not runai/hclient.py. LiveRunner passes
  the complete builder task to HAgentRunner.run; app uses LiveRunner without stripping
  alternatives. CONTRACTS P7 and the consumer agree with our existing ten-field task
  shape, at most two alternatives, independent expected, no nested alternatives.
- Startup observations whose URL is missing, empty or about:blank are now skipped
  before the reviewed-URL gate. Three startup blank observations or 45 seconds without
  reviewed progress yield provider_error, not unreviewed_redirect. Genuine foreign
  redirects still fail closed. tests/test_hclient.py covers Vueling blank startup then
  reviewed completion, bounded blank startup and blank followed by an unreviewed URL.
  This fixes the reported about:blank mechanism offline; historical smoke metadata did
  not retain the rejected URL, so neither its precise cause nor live Vueling success
  is newly proven. No new live runs were authorized.
- _verified still compares verification.city with expected.city via _matches_expected;
  there is no reviewed gateway/via lookup or new gateway-aware city rule. The controlled
  builder regression rejects Amsterdam for expected Den Haag, accepts the same evidence
  with expected Amsterdam, and accepts the literal city text Den Haag via Amsterdam
  through the pre-existing substring match. That last synthetic acceptance is not proof
  of independently verified gateway evidence or permission to invent race-city evidence.
- NS start_url still passes through scrub_url, which removes the public routing fragment.
  R4-01's startup fix does not repair this separate integration limitation.
- Rebuilt all 23 original city/origin matrix rows: 23 hotels and 12 supported transports;
  the 11 intentionally uncovered transport pairs still fail closed. All 37 primary/
  alternative candidates passed exact P7 keys, complete expected fields, evaluate_url
  and the rebased hclient._policy. Existing coverage is unchanged:
  `{'covered': True, 'policy_ids': ['vueling-com']}` for Barcelona from Paris.

## R7-02 — transport route render and selected checkpoints (2026-11-09)

Owner-lifted `allowed_owner_rule` permits read/prepare-only research; it is not
provider authorization or proof of checkout readiness. No private H URLs/IDs,
screenshots, tokens or passenger values retained. Dates 2027-01-29 → 2027-01-31,
one adult unless stated. Raw H research used one session at a time, checked quota
before each, rejected cookies and deleted each session (HTTP204). Round two:
18 completed sessions, maximum 11 actual steps; final quota active=0/available=3.
Image-event counts are observations, not independently reviewed screenshots.

| Route / site | H fares / steps | Observed result mode |
|---|---|---|
| Paris→Milan / Omio | yes / 5 (round one) | train, EUR99/EUR169 outbound |
| Paris→Berlin / Omio | yes / 4 | train, EUR80/EUR89 |
| Paris→Lisbon / Omio | yes / 5, plus 5 for flight tab | bus EUR60/EUR99; Ryanair BVA→LIS EUR48 outbound, round trip from EUR136 |
| Paris→Zurich / Omio | yes / 6 | bus; Air France flight EUR70 outbound, round trip from EUR139 |
| Paris→Madrid / Omio | yes / 4 | train EUR108/EUR116 |
| Lyon→Milan / Omio | yes / 4 | train EUR78/EUR98 |
| Brussels→Berlin / Omio | yes / 4 | train EUR70 |
| Geneva→Barcelona / Omio | yes / 6 | bus; easyJet flight EUR41/EUR58 |
| Paris→Milan, two adults / Omio | yes / 5 | UI showed 2 adults, EUR198/EUR338 versus one-adult EUR99/EUR169 |
| Paris→The Hague / Omio | nearby only / 4 | train actually ends Rotterdam Centraal (+21km); NOT verified literal Hague coverage |
| Paris→Milan / Google Flights | yes / 4 | round-trip lists EUR48/EUR49 |
| Paris→Berlin / Google Flights | yes / 3 | round-trip lists EUR88/EUR89 |
| PAR→LIS / Google Flights | yes / 2 | round-trip lists EUR136 Transavia / EUR159 TAP; IATA wording succeeds |
| Paris→Valencia / Google Flights | yes / 3 (round one) | round-trip lists EUR45/EUR80 |
| Geneva→Barcelona / Google Flights | yes / 2 | round-trip lists EUR68/EUR102 |
| ORY→LIS / TAP | yes / 3 (round one) | outbound economy EUR87.47/EUR97.47 |
| Paris→Berlin / corrected Trainline | no / 4 | error and temporary bot restriction; dropped |

Omio public name-based entry:
`https://www.omio.com/links/626fa8a9-f982-43d0-ace9-9a13f6b14612?departurePosTerm={origin}&arrivalPosTerm={destination}&departureDate={out_ISO}&returnDate={back_ISO}&adults={adults}`.
The UUID is Omio's public published redirect identifier, not an H ID. All three
mode tabs appeared. Results paths are
`/app/search-frontend/results/{id}/train`, `/bus` or `/flight`.
List prices are outbound or advertised round-trip-from prices, not selected totals.
Airport substitutions such as Beauvais must be disclosed. The Hague is unverified;
Den Haag Centraal is an untested next-probe search name. No Rotterdam gateway
is approved by this change.

| Deep flow | Observed paths in order | Selected total / safe stop |
|---|---|---|
| Omio Paris→Milan, 10 steps | `/app/search-frontend/results/{id}/train` → `/app/search-frontend/results/{id}/train/{id}/inbound` → `/app/search-frontend/journey/train/{id}/{id}/{id}/{id}` → `/app/search-frontend/booking/{id}/passenger-details` | EUR248 on Customise your trip (journey/train); EUR99 outbound + EUR149 return. Passenger page reached with no typing. |
| Google Paris→Valencia, 5 steps | `/travel/flights` → `/travel/flights/search` → `/travel/flights/booking` | EUR45 selected round trip; stopped at booking options, no airline click-through. |
| TAP ORY→LIS, 11 steps | `/booking/flights` through both selections → `/booking/review-your-trip` | EUR158.35 selected round trip; stopped at login/register or guest-continuation gate. Passenger path unobserved; login is not proven mandatory. |

Only Omio **rail** summary shape is observed; bus/flight selected-summary shapes
remain unverified. Its no-profile checkpoint is the selected journey prefix,
never results or outbound-only inbound lists. Passenger prefill is opt-in,
field-names-only P14 metadata; final post-prefill checkpoint remains `(?!)`
until a permitted live probe observes it. No passenger values were entered in
research. Google/TAP do not advertise prefill.

Hosts observed: Omio **www.omio.com** only, including passenger page; Google
**consent.google.com/m** (reject only) and **www.google.com**; TAP
**booking.flytap.com**. Google selected search/booking query keys `tfs,tfu`;
entry keys `hl,q`. No airline or booking-partner host was visited or authorized
as a Google navigation target.

New verified adapters are split by actual origin/destination observations.
Paris→Brunnen/Stoos/Lucerne uses reviewed **Zurich gateway** evidence, excludes
onward transfer and preserves race city. Google others and broad Omio inventory
remain undated alternatives pending route probes. SBB/NS prior evidence remains
unchanged. SBB must FIRST set 1 adult without reduction before reading fares;
Top offers/travelcard/Half-Fare/GA purchase path tokens are blocked, ordinary
`/en/offer` is not. Those purchase tokens are defensive boundaries, not new live
path observations.

Offline adapter construction does not establish product H READY or integrated
live success. No product UI visual check or new H run was performed for code.

## Round 3 — coverage closure and synthetic prefill probe (2026-11-09)

Dates Jan29→Jan31 2027, 1 adult. **30 sequential H sessions**, quota before every
creation (available3), DELETE HTTP204 after each; 29 render probes and one 23-step
synthetic passenger probe. No screenshots downloaded/saved. All 29 render probes
reported prices and matching dates/return/adult; these are priced result lists,
NOT selected round-trip checkout evidence. H answer reports plus image-bearing
event counts, not independently human-reviewed screenshots.

Start URLs used the exact registry formatter `site_policy._candidates` that
build_task uses (undated primary gaps initially cannot build_task). After dating,
the same Omio start URLs are produced by build_task. Paris/Lyon initial Den Haag
Centraal probes preceded the gateway change: Paris again priced Rotterdam only;
Lyon showed Hague bus prices and nearby Amsterdam flights. Adopted explicit
Rotterdam gateway uniformly and repeated Paris/Lyon against the exact Rotterdam
start URL. Brussels/Geneva Hague probes already used that updated URL. The Hague
race city stays unchanged; onward Rotterdam→The Hague transfer is excluded.

Added Geneva→Zurich to establish the exact shared Zurich gateway URL. Also probed
Paris→Amsterdam and Geneva→Milan on Omio so expanding adults1..4 does not rely
on SBB/NS adapters that remain limited to one adult. Google fallback was not
needed: every requested route had priced Omio results (Hague via disclosed gateway).

| Route / run | Site | Priced results | Steps/images | Mode / examples |
|---|---|---|---|---|
| brussels-amsterdam | Omio | yes | 4/4 | Trains; €29/€62/€100 |
| brussels-barcelona | Omio | yes | 4/4 | Buses; €41/€57/€26 |
| brussels-lisbon | Omio | yes | 4/4 | Flights; €50/€99/€70 |
| brussels-madrid | Omio | yes | 4/4 | Flights; €60/€74/€81 |
| brussels-milan | Omio | yes | 6/6 | Flights; €56/€27/€37 |
| brussels-the-hague | Omio | yes | 4/4 | Trains; €29/€90 |
| brussels-valencia | Omio | yes | 5/5 | Flights; €75/€39/€78 |
| brussels-zurich | Omio | yes | 4/4 | Trains; €156/€164 |
| geneva-amsterdam | Omio | yes | 4/4 | Trains; €92/€85/€77 |
| geneva-berlin | Omio | yes | 5/5 | Trains; €60/€51/€77 |
| geneva-lisbon | Omio | yes | 4/4 | Flights; €64/€128/€67 |
| geneva-madrid | Omio | yes | 5/5 | Flights; €39/€62/€46 |
| geneva-milan | Omio | yes | 4/4 | Buses; €22/€29 |
| geneva-the-hague | Omio | yes | 8/8 | Trains; €92/€77/€85 |
| geneva-valencia | Omio | yes | 4/4 | Buses; €51/€62/€79 |
| geneva-zurich | Omio | yes | 5/5 | Trains (initially), Flights (checked); €61/€119/€164 |
| lyon-amsterdam | Omio | yes | 6/6 | Flights; selected EUR264 |
| lyon-barcelona | Omio | yes | 4/4 | Trains; €65/€24/€42 |
| lyon-berlin | Omio | yes | 6/6 | Flights; €49/€57/€167 |
| lyon-lisbon | Omio | yes | 5/5 | Flights; €62/€63/€70 |
| lyon-madrid | Omio | yes | 6/6 | Flights; €39/€63/€66 |
| lyon-rotterdam | Omio | yes | 4/4 | Trains; €99/€107 |
| lyon-the-hague | Omio | yes | 6/6 | Flights; €48/€54/€126 |
| lyon-valencia | Omio | yes | 5/5 | Trains; €59/€67 |
| lyon-zurich | Omio | yes | 5/5 | Buses; €36/€46/€87 |
| paris-amsterdam | Omio | yes | 6/6 | Flights; €33/€37/€27 |
| paris-barcelona | Omio | yes | 4/4 | Trains; €69/€31/€40 |
| paris-rotterdam | Omio | yes | 4/4 | Trains; €33/€26/€86 |
| paris-the-hague | Omio | yes | 6/6 | Trains; €33/€44/€37 |
| prefill | Omio | yes | 23/23 | deep passenger flow; selected EUR264 |

### Prefill path result: final sentinel retained

Observed sequence, all www.omio.com, IDs scrubbed:
1. `/app/search-frontend/results/{id}/train`
2. `/app/search-frontend/results/{id}/train/{id}/inbound`
3. `/app/search-frontend/journey/train/{id}/{id}/{id}/{id}`
4. `/app/search-frontend/booking/{id}/passenger-details` — final observed page.

Selected round-trip total EUR264. Required fields reported: given name, family
name, email, phone, **birth date**, **country/region of residence**. Optional:
loyalty-card type/number. H reported entering only the five authorized synthetic
identity fields (names, email, phone, birth date); country was not supplied in
the authorized identity. No real personal values, final submission or purchase
was permitted. Do not retain synthetic values in evidence.

**No post-passenger page observed.** H returned blocker=null but stopped on the
passenger form after23 steps, rather than reaching extras/seats/insurance/payment/
terms. This is an incomplete probe, NOT a successful final checkpoint or a
confirmed login/captcha block. Country was reported required and not entered;
whether that was the actual navigation blocker is unverified (no action audit
retained). Do not infer any final path. Keep prefill url_patterns=`(?!)`, retain
observed passenger prefill_patterns, add birth_date/country to authorized field
names to reflect the reported required form. A future probe needs explicit
authorization for a synthetic residence country before attempting continuation.

### Safety and scope caveats

H was instructed to reject cookies and never accept optional categories.
Most reports say Deny All. Lyon→Berlin's cookie answer ambiguously calls
performance/functional/analytics necessary while also claiming rejection; no
action audit retained, so **that report does not independently establish safe
cookie rejection**. Do not claim every cookie action was verified. Fare rendering
itself was reported with actual numeric prices and matching dates.

Geneva→Madrid flights suggested a cheaper **Lyon** departure as well as a genuine
GVA→MAD EUR52 option; bus Geneva→Madrid EUR39 also rendered. Never substitute an
unreviewed origin airport. Brussels flight results may include Charleroi/Bergamo;
actual airports must be disclosed. No additional navigation hosts observed beyond
www.omio.com. No captcha or login reported in these probes.

Registry date covers only observed route sets, plus identical reviewed Zurich
and Rotterdam gateway URLs. Omio verified for47/48 eval combinations; Paris→Valencia
retains verified Google primary. No one-adult route gaps remain. All48 also build
for adults1..4 after the explicitly requested expansion; this is NOT a claim that
3/4 adults were independently live-probed. SBB/NS unchanged. Google plural query
uses adult for1, adults for2..4. Unsupported counts remain blocked.

# R7-02 final authorized live step — 2026-11-09

## Synthetic passenger retry: no final checkpoint observed

One quota-checked sequential raw H session; cleanup HTTP204. Paris→Milan,
2027-01-29→31, one adult, up to45 steps. Actual37 steps,31 image-bearing
observations. Only explicitly authorized synthetic passenger fields were permitted;
no terms/newsletter/insurance/account choices or final submissions authorized.
H reports Deny All and entering all six required field names: given name, family
name, email, phone, birth date, country/region of residence. Additional newly
authorized nationality/gender/address fields were not reported required or entered.
No identity values are retained here.

Observed public paths (www.omio.com; opaque IDs replaced):
`/app/search-frontend/results/{id}/train` →
`/app/search-frontend/results/{id}/train/{id}/inbound` →
`/app/search-frontend/journey/train/{id}/{id}/{id}/{id}` →
`/app/search-frontend/booking/{id}/passenger-details`.

H returned total265.00 (currency not specified in its answer), blocker=null,
final_page_type=passenger-details. **It again stopped on the passenger form,
not on a post-passenger boundary.** All reported required fields were entered
this time, so the earlier missing-country hypothesis does not explain this run.
No login/captcha or other concrete blocker was reported. Actual reason for the
premature completion is unknown; no complete action audit retained. Do not
invent extras/payment paths. Omio prefill sentinel `(?!)` and six observed
required field names remain unchanged. No successful P14 final checkpoint claim.

## Product-pipeline acceptance: zero READY, core preflight blocker

Real trip dict → transport.build_task → hclient._policy → unmodified
HAgentRunner.run, no runner_profile, one adult, EUR800 budget, Jan29/31 travel
and explicitly synthetic race-like Jan30 date (not a sourced real race).
Original max_steps60 retained; automatic alternatives retained, not manually
stripped or promoted. Routes invoked in requested order; Geneva→Barcelona added
because fewer than two READY. These are actual runner outputs, not raw-probe
success relabelled as pipeline success.

| Route | Provider | Status | reason_code | Steps / frames | Stop host/path | Checkpoint matched | Total seen |
|---|---|---|---|---|---|---|---|
| Paris→Milan | Omio | failed | provider_error | 0 / 0 | none | no | none |
| Paris→Berlin | Omio | failed | provider_error | 0 / 0 | none | no | none |
| Paris→Lisbon | Omio | failed | provider_error | 0 / 0 | none | no | none |
| Paris→Brunnen via Zurich | Omio | failed | provider_error | 0 / 0 | none | no | none |
| Geneva→Barcelona | Omio | failed | provider_error | 0 / 0 | none | no | none |

Every runner error: `Invalid H task or provider response`. **No pipeline H
session was created**, so there were no provider steps/images/selected totals.
The runner's preflight failed before the harness's quota-before-every-creation
hook and POST. Explicit smoke-level quota on Geneva showed available3; the
synthetic retry was quota-checked before creation. No overlapping owned sessions.

### Verified causal chain, not an inferred provider failure

- Actual builder outputs use Omio's published public /links/{public-affiliate-id}
  URL. hclient._policy accepts every task. No profile metadata is involved.
- Direct diagnostic: `scrub_url(task["start_url"]) is None`.
- Disproof check: removing every query parameter still returns None, whereas
  `https://www.omio.com/links` survives unchanged. Not a date/adult/query issue.
- The public affiliate UUID matches scrub._OPAQUE_PATH and does not match
  scrub._PUBLIC_SLUG. scrub_url's segment gate returns None before query parsing.
- HAgentRunner._attempt computes clean_url(start_url), then its public-HTTPS
  check raises ValueError for None **before POST /sessions**. Its ValueError
  handler produces exactly the observed failed/provider_error message.
- HAgentRunner.run retries alternatives only when status=blocked with selected
  reason codes. Here status=failed, so the retained alternatives never execute.

This verifies the core scrub/start-URL gate for these exact tasks; it is NOT an
Omio inventory, consent, checkpoint, date, network or quota failure. No H request
was made that could test those hypotheses. No same-input live retries or
primary-ranking changes were used to manufacture success. Fix requires a narrow,
reviewed public-link exception in hclient/scrub (outside this ticket's allowed
files), and potentially separate public selected-path handling if opaque selected
IDs are rejected later; that latter possibility has NOT been live-tested here.

**Acceptance target >=2 verified READY is unmet (0/5).** Raw render/selected-flow
research remains separate historical evidence. No hclient/scrub edits, encoding
bypass, policy widening or fabricated READY. Recommend core owner fix the known
public-link handling, then rerun the same builder pipeline before integrated
acceptance. No UI changes or independent screenshot visual review.

# R8-02 transport update — 2026-11-09

## Real builder smoke, not a readiness claim

Paris→Valencia, outbound 2027-01-28, return 2027-01-30, one adult, EUR800;
synthetic race date January 29. `build_task` → unmodified `HAgentRunner.run`,
420-second timeout, alternatives removed to keep one owned session. A fake
profile was supplied in memory; this Google adapter has no authorized passenger
prefill fields, and no profile values were placed in task instructions.

Quota immediately before the run: limit3/active0/available3. One session created;
no concurrent owned session, no screenshots/frames saved. The first local harness
invocation failed validation (`trip.race is required`) before creating a session;
it is not counted as a live run. A subsequent quota check after completion was
limit3/active1/available2; organization-wide ownership is not exposed by quota.
No other session was cancelled.

Actual result: **blocked / unsafe_claim**. Last public stop:
`www.google.com/travel/flights/booking`. Last reported step57. Client diagnostic:
`verify_failed: ["checkpoint_pattern"]`. H reached a booking path, but the
retained public URL did not satisfy the selected-itinerary `tfs` checkpoint.
Do not infer whether the browser lacked tfs or scrub removed it: that link has
not been discriminated. No independent visual review, selected total, final
payment boundary or successful profile prefill is claimed. No new verification
dates were assigned from this failed run.

## Coverage, dependencies and remaining blockers

The historical R7 48-case matrix (which includes Lucerne, The Hague, Stoos and
Amsterdam, but NOT Frankfurt, Rome or Seville) now has an explicit test with a
synthetic Omio scrub exemption: verified primary and runnable alternative in
every case. Runtime scrub is imported lazily, and no exemption means no Omio
candidate is emitted. The test helper no longer claims every arbitrary route
is covered merely because Omio's public link becomes runnable.

The ticket's revised 48-case destination list is NOT the historical matrix.
Measured one-adult/90-day revised coverage: without the core exemption 9/48
verified primaries, 7 with alternatives; with the actual R8-01 scrub module
36/48 primaries, all36 with alternatives. Frankfurt, Rome and Seville lack
dated H evidence for all four origins (12 gaps). Their Google and Omio links
are registered only as UNVERIFIED candidates; no dates were fabricated.
Paris→Frankfurt therefore still fails closed. Lyon→Zurich works with Omio's
existing dated R7 evidence and the core exemption; without it the route remains
blocked. No new SBB/TGV Lyria Lyon→Zurich verification was obtained. Only the
Paris→Valencia alternative requested smoke was run; no live Omio exemption was
installed, and no unavailable primary was forcibly promoted for a smoke.

Google's checkpoint now requires a nonempty `tfs` query parameter on booking,
not bare booking or results. Cheapest reasonable economy/outbound-then-return
selection and copying the full booking URL are explicit. Existing Omio selected
rail-summary checkpoint and SBB return-leg checkpoint remain unchanged. Omio's
post-prefill final checkpoint is still the fail-closed `(?!)`: historical probes
above never observed a safe post-passenger/pre-payment page. This ticket does
NOT claim that unresolved P14 acceptance is fixed; Google still cannot prefill
passenger forms without navigating to unreviewed airline/partner hosts.

## Horizon source and limitations

Per-adapter caps: Google330, TAP330, Vueling330 days; Omio180, SBB180,
NS180, CP180 days. These are conservative application eligibility assumptions,
not provider promises of actual inventory. Google330 and rail120–180 follow the
R8-02 owner brief; Omio180 is a local six-month cap for mixed rail/flight
inventory, not a claim every Omio carrier opens at180 days. The corresponding
provider help-page fetches (Omio advance booking and SBB point-to-point tickets)
were unavailable in this environment, so an authoritative carrier-specific
source remains outstanding. Do not present these caps as live inventory proof.

Horizon filtering occurs before the distinct-policy cap and verified-primary
selection. Beyond all eligible verified candidates' horizons the builder returns
a public prefilled search handoff and `preflight_block`. This main's ReasonCode
lacks `not_yet_bookable`, so it uses the requested `no_inventory` compatibility
fallback; it automatically selects the new code when core adds it. Main's
hclient does NOT consume preflight_block yet: tests assert builder output only,
not no-H-POST behavior. Do not execute these blocked tasks until R8-01 P15 lands.

# R7-02 scrub-stable Google workaround — 2026-11-09

Supersedes earlier broad **runnable** coverage claims. Registry render evidence
is retained; registry-level coverage is not proof that the runtime can preserve
a deep link. transport.build_task now filters candidates BEFORE the distinct-policy
cap and verified-primary selection: exact scrub_url(start_url)==start_url, with
only the existing validated keep_fragment exception. No verified stable primary
means ValueError. Unverified alternatives are never promoted to compensate.

## Implementation and current runnable coverage

- Generic English month-name date variant mon_d_yyyy (e.g. Jan29 2027 with spaces
  between month/day/year), plus adult_phrase (one adult,2 adults,etc.).
- Optional strictly validated query_encoding=form canonicalizes only query
  encoding with urlencode/quote_plus; default percent behavior is unchanged.
- Optional nonnegative integer priority, default0. Google priority1 outranks Omio
  only within the existing verified/non-last-resort tiers. It cannot promote an
  unverified or last-resort primary. Existing rail-first default is preserved.
- Google q now uses month-name dates and + encoding. It survives scrub intact.
- Omio remains dated in the registry but its public affiliate UUID still fails
  scrub, so no Omio task is emitted on this core. No hclient/scrub edits.
- TAP dotted depDate/retDate are removed by scrub, so TAP is filtered.
- SBB retains all query keys but percent-space encoding is normalized to + by
  scrub; exact equality fails, so its current URLs are filtered. No SBB/NS
  registry or review changes were made in this workaround.

Exactly7/48 eval combinations have a runnable verified primary for ONE adult:
- Paris→Milan, Berlin, Lisbon, Valencia: Google Flights.
- Paris→Amsterdam: NS International (validated public fragment retained).
- Geneva→Barcelona: Google Flights.
- Geneva→Zurich: NS International.
- Lyon: none; Brussels: none.

For2..4 adults, exactly the five Google routes above remain runnable. The two NS
routes retain their original one-adult restriction. All other eval combinations,
including all Brunnen/Stoos/Lucerne gateways and The Hague, fail closed pending
R7-01's reviewed Omio scrub exemption (or new verified stable-provider evidence).
Passing the start guard is not a promise that later selected-path privacy gates
or checkout verification will pass. Tests condition Omio inclusion on actual
scrub behavior, so they also support the future exemption without hard-coding
Omio as permanently blocked. Prefill final sentinel remains (?!) unchanged.

## Actual product-pipeline smokes

Real trip dict → build_task → _policy → unmodified HAgentRunner.run; no profile,
one adult, EUR800 budget, Jan29→31 2027 and explicitly synthetic race-like Jan30
date. Provider max_steps60 unchanged. Alternatives retained as built (only
Paris→Berlin had a stable NS alternative; no fallback actually ran). All runs
used the new q wording, not a separately navigated raw probe.

Public stop for every actual smoke: **www.google.com/travel/flights/booking**.
Observed chain: consent.google.com/m → www.google.com/travel/flights →
/travel/flights/search → /travel/flights/booking. No airline click-through
reported. Hclient checkpoint patterns matched booking and did not match beyond.

| Route | Provider | Actual status | reason_code | Steps / image-bearing observations | Checkpoint | Total evidence |
|---|---|---|---|---|---|---|
| Paris→Milan | Google | ready_for_payment | null | 3/4 | yes | Client verification passed; numeric amount not retained by initial observer |
| Paris→Berlin | Google | ready_for_payment | null | 3/4 | yes | Client verification passed; numeric amount not retained by initial observer |
| Paris→Lisbon | Google | blocked | checkpoint_unverified | 3/4 | yes | Amount not retained; verification failures only handoff_observed |
| Geneva→Barcelona, first actual run | Google | blocked | checkpoint_unverified | 5/6 | yes | Amount not retained; verification failures only handoff_observed |
| Geneva→Barcelona, allowed retry | Google | ready_for_payment | null | 3/4 | yes | EUR68 selected round trip; outbound/return/selected=true; exact dates/adult/cities verified |

**3 routes reached client-verified READY.** READY here is the actual unmodified
client classification, not independent screenshot review or a purchase claim.
The retry recorded verification fields matching Geneva/Barcelona, Jan29/31,
one adult, selected both legs, next boundary booking options, total EUR68, and
scrubbed handoff URL equality true. Raw query values/opaque IDs are not retained.

### Failures, instrumentation correction and retry limits

Three initial Milan/Berlin/Lisbon attempts were invalidated by a scratch observer
bug: raw checkpoint strings were passed to _checkpoint_matches instead of
compiled patterns, causing the HTTP response hook to raise and the runner to
report failed/provider_error, H run or event consumer failed, at consent.google.com/m.
Those are harness failures, NOT provider failures. Fixed the observer with
hclient._checkpoint(candidate), without modifying hclient, and reran each once.

The real Lisbon and first Geneva runs then reached booking but failed only
handoff_observed: the core compares scrub_url(answer.handoff_url) with the
observed URL. Other client verification checks passed. The exact omitted/different
parameter in those answers was not retained, so no specific URL mutation is
claimed. Google instructions now say to copy the exact current public browser
URL including public locale/currency/query parameters, without reconstructing
or truncating it; private session links/tokens remain forbidden. A test pins
this instruction. Geneva's single permitted retry passed with that instruction.
Lisbon was NOT run a third time: its two session creations were already used
by the instrumentation failure and corrected attempt. Do not relabel its
checkpoint_unverified as READY.

Eight session creations total across the four routes; at most two per route.
Quota was checked before every smoke and every session creation, available>=1.
One owned session at a time; every owned session DELETE returned HTTP204 before
the next creation. Some blocked runs issued redundant idempotent DELETE calls.
Organization active1/available2 appeared between some runs; ownership of that
organization-wide session was unknown, and no other session was cancelled.
No saved screenshots, profile values, private H IDs/URLs or query values in
evidence. Frames above count image-bearing observation events, not deduplicated
emitted frames. Full action audit/independent visual consent review unavailable;
guardrails forbid acceptance, personal data, login, purchase and final submission.

## Checks on the workaround

`uv run ruff check . && uv run pytest -q &&
uv run pytest -q tests/test_agent_transport.py tests/test_site_policy.py`:

```text
All checks passed!
2638 passed, 1 warning in 78.09s (0:01:18)
788 passed in 2.99s
```

Existing Starlette/httpx deprecation only. New tests cover all48×four party
counts with explicit runnable sets and conditional Omio support, every emitted
start URL's scrub stability, form-encoded month dates/party wording, filtering
before the three-policy cap, no unverified promotion, malformed encoding/priority,
month boundary examples, and profile unit behavior through a clearly synthetic
stable Omio test link. These synthetic unit links are not production/live evidence.

## 2026-11-09 — runner-equivalent preflight correction (supersedes 7/48)

The equality guard above was stricter than the runner and incorrectly removed
SBB. `HAgentRunner._attempt` in `runai/agents/hclient.py` calls its nested
`clean_url` (scrub_url; also rejects the configured API key) then requires
`_public_https(start_url)` before POST /sessions. It does NOT require raw/clean
equality. `_policy` checks both raw start_url and fallback_url for public HTTPS
and reviewed permission/scope. Builders have no API-key input and emit only
registry-derived public URLs, not credentials or profile values.

The candidate guard now reuses hclient._public_https on both raw and scrubbed
URLs. Existing select_adapters policy evaluation supplies the review/scope gate;
generated fallback_url is exactly start_url. Safe NS fragments retain the
existing keep_fragment handling. Public URL normalization is not rejection.

SBB's percent-space to plus normalization retains all decoded query values,
including day. Its adapter templates/counts/verification dates are unchanged.
TAP would also pass the actual preflight, but dotted depDate/retDate values were
lost during scrub. Its template now emits ISO dates that survive unchanged.
Offline source check of TAP's public frontend bundle: deeplink depDate/retDate
pass through INDRA_formatDateParam, which calls dateService.INDRA_formatDate
with DDMMYYYY; that service uses Moment(input).parseZone().locale(...).format(...).
ISO-8601 input is supported by that parser. This is source/URL-preservation
evidence, NOT new H-render evidence for the ISO-formatted TAP link.

### Current runnable H-render-verified primaries (one adult): 9/48

| Origin | Destinations and primary |
| --- | --- |
| Paris | Milan, Berlin, Lisbon, Valencia: Google Flights; Amsterdam: NS |
| Lyon | Milan: SBB |
| Geneva | Milan, Zurich: SBB; Barcelona: Google Flights |
| Brussels | None |

All other 39 eval combinations still raise before H. Adults2..4: only the five
Google routes above (5/48); SBB/NS/TAP remain one-adult-only. SBB is restored as
Paris→Milan alternative; TAP as Paris→Lisbon alternative. Geneva→Zurich now ranks
SBB before NS, as the registry already specified. Google remains first for all
five verified Google routes, including the Milan/Berlin READY smokes. Omio's
public UUID still scrubs to None and is skipped; broad coverage still depends on
the R7-01 scrub exemption. Tests remain conditional on actual scrub behavior.

No new live runs. Added synthetic MockTransport tests of unmodified
HAgentRunner.run: SBB, NS and TAP reach POST /sessions with the expected
normalized start URL (NS's safe fragment retained); TAP retains both ISO dates.
The mock deliberately returns HTTP400 after capturing POST: no session or live
READY result is claimed. Existing three Google READY routes remain historical
evidence; nothing here upgrades Lisbon's checkpoint_unverified result.

Correction checks (same configured Starlette/httpx deprecation):

```text
uv run ruff check . && uv run pytest -q
All checks passed!
2816 passed, 1 warning in 98.88s (0:01:38)
```
