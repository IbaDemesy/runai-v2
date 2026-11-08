# Round 2 live acceptance — 2026-11-08, resumed run

**Acceptance remains incomplete: zero complete live successes.** Two real H
confirmations were used, both in Lisbon; neither had three running agents or
three genuine pre-payment stops. The two-country target was not achieved.

Runtime evidence below is from **3e4546b**, after restarting the live server with
the supplied environment keys. The initial 4afda5e attempt still collapsed
suggestion values; 3e4546b fixed that routing blocker. Later commits were not
loaded into the running process, following the lead's no-restart guidance.
Checkout HEAD at close was **3bca0ae**; this is not runtime acceptance of that
revision. No demo/replay evidence is counted.

## Five requested cases

Dates and distances were proposed by the assistant, not supplied by the tester.
Italy, Switzerland, Berlin and Spain were fresh guide-only regressions, without
H confirmations. Their H outcomes remain untested, not inferred from policy.

| Case / assistant-proposed race, date and public source | Registration | Hotel | Transport | Actual overlap / frames | Outcome |
| --- | --- | --- | --- | --- | --- |
| Italy — Padova Marathon, **18 Apr 2027**, 42.195 km; [official announcement](https://padovamarathon.com/padova-marathon-2027-aperte-le-iscrizioni/) | Untested | Untested | Untested | No H launch | Guide-only: distinct IDs and non-first pill routed to Padova. |
| Switzerland — Swiss Canyon Trail, **4 Jun 2027**, distance unknown; [official event](https://www.swisscanyontrail.com/en). Targeted retry: Swiss Canyon Trail 111K, **5 Jun 2027**, 114.2 km; [official distance page](https://www.swisscanyontrail.com/en/pages/111k) | Untested | Untested | Untested | No H launch | Guide gap: original event-level plan exposed Confirm with null distance. Targeted retry routed correctly to a specific sourced distance/date, but did not exercise a null-distance chip question. |
| Lisbon — EDP Lisbon Half Marathon, **7 Mar 2027**, 21.097 km; [official race](https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/). Porto, 2 nights, €750; 6–8 Mar | **Blocked**, task builder rejected plan; no registration URL/reviewed organizer adapter; handoff `maratonaclubedeportugal.com` | **Failed**, `H step limit reached`; handoff `www.nh-hotels.com` | **Failed**, `H session failed`; handoff `www.cp.pt` | Only hotel/rail H sessions overlapped, 22:48:42.205–22:52:54.042 UTC. Frame events/distinct images: registration 0/0, hotel 12/11, rail 3/3 | **Not a success**; no three-agent run or verified successful stop. |
| Berlin (EN) — Berliner Frauenlauf, **22 May 2027**, 10 km; [official organizer calendar](https://www.scc-events.com/en/events/calendar), [registration information](https://www.berliner-frauenlauf.de/en/registration/registration) | Untested | Untested | Untested | No H launch | Guide-only: distinct IDs and non-first pill routed to this sourced women's race. Entrant eligibility was not evaluated. |
| Spain — Marató bp Castelló, **14 Feb 2027**, 42.195 km; [official rules](https://www.maratonbpcastellon.com/reglamento-marato-bp-castello/) | Untested | Untested | Untested | No H launch | Guide-only: distinct IDs and non-first pill routed to Castelló. |

## Additional authorized Lisbon variant

The assistant proposed **Generali Tranquilidade Meia Maratona dos Descobrimentos,
29 Nov 2026, 21 km**, corroborated by the [organizer information](https://meiamaratonadosdescobrimentos.com/informacoes/)
and [official English/Portuguese site](https://www.discoveries-half-marathon.com/pt/infos.html).
The tester selected Porto, 2 nights and €750; the trip was 28–30 Nov.

| Registration | Hotel | Transport | Actual overlap / frames | Outcome |
| --- | --- | --- | --- | --- |
| **Blocked** before H: task builder rejected plan; no registration URL/reviewed organizer adapter. Handoff `meiamaratonadosdescobrimentos.com` | **Blocked** after live browsing: `Site policy or sensitive page blocked this run`; error `Site policy unavailable or destination not authorized`. Handoff `www.nh-hotels.com` | **Failed**: `H step limit reached`. Handoff `www.cp.pt` | Hotel/rail session lifecycles overlapped 22:58:21.526–22:59:38.292 UTC. Frame events/distinct images: registration 0/0, hotel 11/10, rail 6/6 | **Not a success**; no registration session or three verified stops. |

Only two of the three permitted confirmations were used. A third repetitive
Portugal launch was not made, and no unsupported/unsourced plan was forced.

## Live evidence and stop-state limits

Times below are UTC on 2026-11-08. Starts are the post-creation **“H browser
session started”** events, not the core `step_started` events. Ends are the
observed core terminal events; provider-internal active/idle time is unavailable.
Real interleaved changing frames corroborate two concurrent browser sessions,
not three.

| Run / agent | H session started | Terminal event | Frame observations, first–last | Events / distinct image hashes |
| --- | --- | --- | --- | --- |
| EDP / hotel | 22:48:42.205 | 22:55:34.288 | 22:48:53.454–22:50:01.203 | 12 / 11 |
| EDP / transport | 22:48:42.204 | 22:52:54.042 | 22:48:53.823–22:49:04.872 | 3 / 3 |
| Descobrimentos / hotel | 22:58:21.510 | 22:59:38.292 | 22:58:33.809–22:59:33.473 | 11 / 10 |
| Descobrimentos / transport | 22:58:21.526 | 23:04:36.284 | 22:58:32.018–22:58:55.676 | 6 / 6 |

- Registration had no H session or screenshot in either launch.
- The primary NH view progressed to a blank guest-details page, but the provider
  ended at its step limit. A blank form is not a verified hotel pre-payment stop.
- Primary CP reached a search/no-results state. The second CP run displayed
  actual outbound/return fare choices but ended at its step limit. Neither is
  a successful transport preparation.
- All reported `payment_executed` flags were false. The tester did not enter
  personal data, pay, book, create accounts, accept terms/consent, submit
  transaction forms or bypass captchas. Full provider action traces were not
  independently audited; sanitized flags and final pages are not such an audit.
- Public handoffs are genuine organizer/NH/CP pages. No private provider
  session URL, access token or personal data is included here.

## UI and guide checks

- **Passed:** immediate discovery progress/skeletons; chronological questions;
  suggestion pills; UI-entered Porto, two-night and €750 preferences.
- **Passed:** typing `oui` at the primary ready plan did not launch agents;
  only the dedicated confirmation click started preparation.
- **Passed:** corrected EDP suggestion routing, distinct natural IDs, and
  non-first candidate routing in Italy/Berlin/Spain and the targeted Swiss query.
- **Passed:** real hotel/rail images now load and change. The previous
  HTTP-404/zero-frame symptom did not recur in these sessions.
- **Passed:** 1440×900 desktop and 390×844 mobile stage had no horizontal
  overflow; mobile cards stacked and handoffs remained reachable. The UI
  showed screenshots/cards, not prompts, raw JSON or logs.
- **Passed:** missing registration footage was labelled unavailable;
  stale/terminal hotel and rail frames were labelled retained/interrupted or
  stopped, rather than being presented as continuously live.
- **Failed / guide-quality gap:** the exact Swiss prompt produced a short
  “Distance inconnue” label, but proceeded through origin/nights/budget to a
  Confirm button with null numeric distance and an event-start date.
  No H confirmation was made on that plan.
- **Untested live branches:** duplicate-ID `:2` suffix and official-date-without-
  source downgrade were not naturally returned by discovery. The exact single
  sourced numeric-distance question was also not triggered: a targeted retry
  returned separate concrete-distance candidates instead.
- **Historical, not rerun in this resume:** fake-card/email redaction,
  gibberish and past-date recovery, typed preference edits and English `ok`
  confirmation gating. Do not treat those earlier checks as current-HEAD proof.

## Policy and remaining blockers

Applicable policy is [docs/site-policy.json](../site-policy.json): hotel
`nh-hotels-com`, rail `cp-pt`; both allow only `in_session_only` screenshots.
No registration adapter was executed. Reviewed registration platform coverage
does not authorize the two organizer hosts or substitute for a sourced URL.
Blocked/failed statuses were preserved; no policy was bypassed.

Remaining acceptance blockers are the absent registration sessions, hotel/rail
failures or policy stops, and the Swiss event-level/null-distance ready plan.
The later 3bca0ae runtime remains untested. Neither the prior offline pass count
nor these two-browser runs establishes generic live readiness or the required
two-country success target.

## Shareable UI evidence

These are own-app screenshots. Provider image regions in the Lisbon pair are
explicitly withheld, not replaced with simulated footage. The private annotated
recording contains provider views and must not be published in GitHub or this
repository.

| Lisbon desktop — 1440×900 | Lisbon mobile — 390×844 |
| --- | --- |
| ![Lisbon desktop terminal cards, provider regions withheld](https://app.devin.ai/attachments/0fb99f50-6898-4a18-bd1d-5b572d5b264c/lisbon-status-desktop-public.png) | ![Lisbon mobile terminal card, provider region withheld](https://app.devin.ai/attachments/c360a824-454f-41ea-8d69-2f726acb7e44/lisbon-status-mobile-public.png) |

| Swiss exact prompt — null-distance gap | Swiss targeted retry — specific sourced distance |
| --- | --- |
| ![Swiss unknown distance still exposes Confirm](https://app.devin.ai/attachments/9e8692b3-6391-4ca7-b636-5846d5126795/regression-swiss-null-confirm.png) | ![Swiss 111K selection has 114.2 km and 5 June 2027](https://app.devin.ai/attachments/5e31f1b4-db12-416b-9834-ff1d4ffea367/regression-swiss-specific-distance.png) |

[Private Devin session](https://app.devin.ai/sessions/568b25fd08584f2281014745862f60e1).
