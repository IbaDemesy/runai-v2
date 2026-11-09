# Registration path evidence (R2-02, supersedes R1-05 "assumed" claims)

## R8-03 normal-Chrome observations — 2026-11-09

Read-only Chrome walk (cookies refused, nothing typed or submitted, no login, no
waiting list). Public host/path only; no frames or screenshots kept.

| Policy | Requested | Observed host/path | Finding |
|---|---|---|---|
| `r7-lisbon-marathon-2027` | maratonaclubedeportugal.com/maratona-de-lisboa/ | maratonaclubedeportugal.com/en/ (English locale) or same path (Portuguese) | Locale redirect stays on the reviewed host; scope widened to `/` so the run keeps frames. INSCREVA-SE links: meia-maratona.inscricoes.maratonaportugal.com prova_id 3765-3768 (March 2027 half/10k/7k), 3769 half waiting list; no 2027 full-marathon entry link. Bounded no_inventory early stop kept. |
| `r8-zurich-marathon-goactive` | www.zuerichmarathon.ch/ | www.goactive.ch/event/ochsner-sport-zurich-marathon-2027-138 | All "Jetzt anmelden"/"ZUR ANMELDUNG" buttons link to GoActive; Marathon 42.2 km and Halbmarathon 21.1 km shown Sold Out. P15 preflight_block sold_out with the GoActive handoff (no H session). GoActive /login is out of scope. |
| `r7-valencia-marathon-2026` / `-2027` | www.valenciaciudaddelrunning.com/en/marathon/ | /en/marathon/maraton/ (same reviewed prefix) | 2026 edition sold_out (existing dated FAQ evidence) -> preflight_block; 2027 platform still unverified -> bounded no_inventory early stop. |
| `frankfurt-marathon-de` | www.frankfurt-marathon.com/anmeldelink-2027/ | in.motionevents-registrations.com/mainova-frankfurt-marathon-2027-1789303690969?currentPage=select-competition | MAINOVA FRANKFURT MARATHON 2027, 31.10.2027; EINZELANMELDUNG -> currentPage=form_individual-form (empty participant fields, ZURÜCK/WEITER). Task now starts on the provider with max_steps=15. |
| `milanomarathon-it` | in.njuko.com/wizz-air-milano-marathon-20271776152378557 | ?currentPage=select-competition | 04/04/2027, two categories at EUR 114. The recap/cart currentPage value after the form was not reached in Chrome; the profile url_pattern (cart/recap/summary/panier/warenkorb) is provisional until the live smoke below. |

## R7-03 live registration smokes — 2026-11-09

Real `registration.build_task` -> `HAgentRunner.run`, without runner_profile.
Only alternatives were removed to keep each invocation to one reviewed
provider/session; no checkpoint, safety rule or verification gate was relaxed.
The H key was bound through exec environment. Each run had a fresh quota GET
immediately before it: org limit=3, active=1, available=2. Both ran sequentially,
after the Booking hotel smoke, with HTTP204 cancellation/explicit DELETE cleanup
before the next run. Exactly three ticket sessions total; no fourth/retry.

| Race/date/distance | Public requested and final host/path | Quota available | Status | reason_code | Stop evidence | Max reported provider steps | Emitted frames | Elapsed |
|---|---|---:|---|---|---|---:|---:|---:|
| Milano Marathon, 2027-04-04, 42.195km | in.njuko.com/wizz-air-milano-marathon-20271776152378557 | 2 | ready_for_payment | null | First participant personal-data boundary accepted by hclient verification; public handoff same host/path | 5 | 4 | 41.6s |
| NN CPC Loop Den Haag, 2027-03-14, 10km | in.njuko.com/nn-cpc-loop-den-haag-20261784205635566 | 2 | failed | timeout | Same event URL last observed; no verified safe stop or handoff | 27 | 5 | 486.4s |

Milano returned genuine runtime READY with changing/deduplicated live_frame
events and no verify_failed gates. It is not a registration/submission or a
payment claim. Frames were counted then discarded, not independently visually
reviewed; no screenshots were persisted and no comprehensive hosted-action
audit is claimed. The normal instructions stop before personal data, login,
consent, submission or payment; no profile/identity was provided.

CPC did not reproduce the historical `Site blocked preparation` policy denial:
this run reached observed/framed Njuko content but timed out. Sanitized
observation metadata showed only the same public event path, with no recorded
forbidden-title/URL or beyond-pattern trigger. No structured answer or
verification-failure list explains why it stalled; the timeout is not evidence
of sold-out status, the wrong edition, a captcha or consent. The exact UI stage
is unverified because the event is a same-URL flow and frames were not reviewed.
No URL/checkpoint correction was supported; none was made. One of two requested
registration READY results was achieved; the three-run cap is exhausted.

No private H links, queries, session IDs, personal data or image payloads were
retained. Each run created one session and cleanup returned HTTP204 twice
(runner stop plus explicit cleanup).

### Review follow-up: bounded stops survive stale observations

Commit `2dfba91` decouples adapter-level early_stop_reason from the 21-day
availability freshness window. Berlin's account wall and Valencia/Lisbon
unverified entry boundaries retain max_steps=12, first-five-step BLOCKED,
disabled READY checkpoints and no prefill even after observations expire.
Availability coverage still becomes unknown when stale; this does not renew
or promote old observations. Added fresh/day-22 tests for all four explicit
early-stop adapters plus a missing-observation case. Ordinary adapters keep
their existing freshness behavior. No core files or policy shards changed.

Final implementation checks:
```
uv run ruff check .
All checks passed!
uv run pytest -q
2340 passed, 1 warning in 63.08s (0:01:03)
uv run pytest -q tests/test_agent_hotel.py tests/test_agent_registration.py tests/test_site_policy.py
807 passed in 8.73s
```
Warning: existing Starlette httpx TestClient deprecation.

## R6-03 read-only observations and coverage — 2026-11-09

Normal Chrome (the session browser), anonymous, read-only: pages rendered, cookie banners
hidden (never accepted), only public selection buttons clicked, nothing typed or
submitted. No screenshots were kept; no private ids.

| Entry | Country | Observation (2026-11-09) | Checkpoint | Availability |
|---|---|---|---|---|
| `stoos-trail-raceresult` | CH | `my.raceresult.com/422182/registration`: "Stoos Trail 2027, 2027-07-10", ST46/ST24/ST10/Bärglauf, fee window 10/15/2026-11/14/2026; public "Register Now" opens `/422182/registration?regname=Einzel-Anmeldung` with empty Last/First Name, Year, Date of Birth (steps Grunddaten > Überprüfung > Payment) | enabled: `^/422182/registration\?(?:[^#]*&)?regname=` (bare landing has empty query, no match) | open |
| `frankfurt-marathon-de` (new) | DE | official link -> Njuko white-label `in.motionevents-registrations.com/mainova-frankfurt-marathon-2027-...?currentPage=select-competition`: "MAINOVA FRANKFURT MARATHON 2027, DATUM 31.10.2027, 136,00 €, EINZELANMELDUNG"; the public button leads to `currentPage=form_individual-form` (empty Vorname/Nachname/Geburtsdatum, 15-min timer) | Njuko `currentPage=form_individual-form` | open (kids races not open until Feb 2027) |
| `maratonaclubedeportugal-com` | PT | `default.aspx?prova_id=3765..3768` banner: "As provas EDP Meia Maratona de Lisboa, Vodafone 10K e Luso 7K estão esgotadas"; `prova_id=3769` redirects to `waitinglist.aspx` ("Lista de Espera", "Esgotada") | unchanged | sold_out (half); 10K also sold out |
| (none) Porto marathon | PT | `maratonadoporto.com/en/registration-2026/` redirects to rockthesport.com (prohibited), "Registrations closed"; Porto half 19/09/2027 has no registration link | — | not covered |
| TCS Amsterdam | NL | "Registration for the 2027 edition will open on Saturday, December 19" | unchanged | not_open |
| Zurich Maratón Sevilla | ES | 2027 phases: repeaters 9–12 April, waiting list 13–16 April, public from 17 April | unchanged | not_open (Madrid half stays the open ES race) |

Terms: Frankfurt Teilnahmebedingungen, Impressum and Datenschutz plus Njuko legal notices
contain no robot/scraping/automated-agent prohibition; my.raceresult Terms of Use reviewed
again (no bot clause; §3.4 submission = binding offer, so never submit). Berlin, Paris, Lyon,
Valencia 10K, Barcelona, Rotterdam, Datasport and rockthesport stay prohibited/denied.

**Frankfurt blocker:** `runai.agents.scrub.scrub_url` returns None for the white-label path
`/mainova-frankfurt-marathon-2027-1789303690969` (the 13-digit Njuko event id is only exempted
on njuko hosts), so H cannot start there. `registration_coverage` now fails closed
(`covered=false`) when the start URL is not scrub-clean; Frankfurt becomes preparable once
scrub.py adds `in.motionevents-registrations.com` to the Njuko public-id hosts (scope amendment,
not in this ticket's files).

Coverage (offline, `registration_coverage`, today 2026-11-09): fresh open and preparable for
ES (Madrid half), NL (CPC Den Haag 10K/5K), CH (Stoos-Trail, Genève),
IT (Milano, Roma, Bologna, Padova). **PT has no open race on a permitted platform**: Lisbon
half/10K/7K are sold out (waiting list), Porto is on prohibited rockthesport and closed;
no Funchal/Gaia registration page could be found. The guide gets
`registration="sold_out"` for Lisbon and must not rank it preparable.

Availability detection: `availability_from_evidence(text, url)` maps waiting-list /
sold-out words (waiting list, lista de espera, Warteliste, liste d'attente, wachtlijst,
sold out, ausverkauft, complet, esgotado, agotado, uitverkocht) to `sold_out`, closed
wording to `closed`, "will open"/"startet voraussichtlich" to `not_open`. A sourced
`waitinglist.aspx` registration URL makes the task start with AVAILABILITY FIRST
`BLOCKED sold_out`; step 5b tells the agent never to join and to answer only that
registration is unavailable (offline test: such an answer is `sold_out`, not a payment claim).

### R6-03 live H smokes — NOT RUN (2026-11-09)

`HAI_API_KEY` (and `LINKUP_API_KEY`) were absent from this session's environment;
`GET /api/v2/sessions/quota` without a key returned an authorization error. No H session
was started, so no live READY is claimed for Stoos-Trail or Frankfurt; the checkpoints
above are based only on the read-only Chrome observation. Previous verified READY remains
Milan only.

## R5-03 sequential live registration smokes — 2026-11-09 UTC

Runtime: R5-01 PR #33 head `77fd6d5` in a detached, uncommitted throwaway worktree,
overlaid with this ticket's registration builder, registry and tests. The ticket branch
was subsequently rebased onto merged R5-01 at main `ee00d23`. Checkpoint matching uses
the unquoted path + `?` + query, case-insensitively; ENDU/Madrid patterns no longer
require a scheme or host. All four were strictly sequential, single-registration-agent
runs. Harness disabled alternative attempts. Quota GET immediately before each run
reported available slots 3, 2, 3, 2 respectively. No new session began without a slot.

Read/prepare-only guardrails: no typing, accounts, consent, submission or payment
authorized. Frames were counted from real `live_frame` callbacks and not written to disk.
No private H URLs, session IDs, keys or site screenshots are recorded here. Host/path
columns deliberately omit query strings. Checkpoint/beyond flags reflect actual H
observation URLs evaluated by the R5-01 matcher, not the start URL alone. Steps are the
maximum provider-reported step metric; each run issued one `force_answer` request.

| UTC start–finish | Race | Start host/path | Frames | Final host/path | Checkpoint matched | Beyond matched | Status / reason_code | Steps | Honest note |
|---|---|---|---:|---|---|---|---|---:|---|
| 03:16:11–03:17:09 | Milan | in.njuko.com/wizz-air-milano-marathon-20271776152378557 | 4 | in.njuko.com/wizz-air-milano-marathon-20271776152378557 | yes | no | ready_for_payment / null | 8 | Njuko participant-form checkpoint matched; runtime accepted the forced structured answer. READY names a safe untouched-page stop, not a purchase or submitted registration. |
| 03:17:14–03:20:40 | TCS Amsterdam | www.tcsamsterdammarathon.eu/registration | 1 | www.tcsamsterdammarathon.eu/registration | no | no | blocked / provider_error | 57 | Did not return the expected not-open verdict. Official GET observation remains not_open; live run establishes neither a participant page nor successful preparation. |
| 03:20:48–03:25:24 | Stoos-Trail ST24 | my.raceresult.com/422182/registration | 6 | my.raceresult.com/422182/registration | no | no | blocked / provider_error | 57 | Stayed on the public registration route; no distinct personal-data URL established. Disabled checkpoint cannot certify the shell; actual personal-page reach is unverified. |
| 03:25:28–03:25:47 | Movistar Madrid half | www.mediomaratonmadrid.es/en/web-form/34571-general-entry | 1 | www.mediomaratonmadrid.es/en/web-form/34571-general-entry | yes | no | blocked / session_failed | 1 | Observed known personal-data URL; force_answer requested, but session failed. No verified READY claim. |

Outcome: **1 runtime-verified READY out of 4**; two checkpoint URLs matched, no observed
beyond-pattern match. No manual screenshot review or integrated three-agent/UI acceptance
was performed. A final quota GET after all runs reported active=0, available=3. No sessions
from this ticket remain running. Do not reinterpret provider errors as availability verdicts.

## R5-03 offline review — 2026-11-09

Anonymous GETs only: no new H runs, screenshots, form interaction or prepared-registration
claims. Existing live records below are historical and unchanged.

- `movistar-madrid-half`: official organizer-hosted Deporticket form at
  https://www.mediomaratonmadrid.es/en/web-form/34571-general-entry shows the 2027 half
  marathon, 69.00 € and First name / Family name / Date of birth / Gender fields. This
  observed untouched personal-data URL is the checkpoint and scrub-safe start; the long
  `/web-evento/13064-movistar-madrid-medio-maraton-2027` slug does not survive local scrub.
  Reviewed linked `/en/web-legal-notice` §§2–6, 9–10 and embedded processing/consent clauses:
  private viewing permitted, no express automated-navigation ban found. Restricted to the
  organizer-hosted form; this does not authorize external deporticket.com (GET returned 403).
- `stoos-trail-raceresult`: `/anmeldung` embeds Race Result event 422182. Public
  https://my.raceresult.com/422182/registration identifies Stoos Trail 2027 on July 10 in
  Brunnen. Reviewed organizer imprint/privacy, race rules §§5/14, Race Result AGB and
  https://my.raceresult.com/imprint/termsofuse §§1–6 (public event browsing §2;
  submitting registration is a binding contractual offer under §3.4).
  No express automated-navigation ban found; race submission would accept rules, so it is
  forbidden. The JS shell has InStock metadata but no anonymously visible active entry
  control: availability remains **unknown**, not open. Organizer course distances are
  11, 25.6, 46.6 and 13 km. No distinct personal-data URL observed: checkpoint `(?!)` is
  deliberately disabled rather than falsely treating the shell as a participant page.
- `bijlmer-run-atleta-pending`: organizer homepage says “Inschrijving opent: 21 november
  2026” (10K **not_open**). Organizer participation terms reviewed, but Atleta review is
  incomplete. Ambiguous policy, no adapter, no permission to start.

Fresh distance-scoped open observations also recorded for CPC 5/10K (official registration
links; half remains sold_out), Geneva, Rome, Bologna, Padova and Prague. Together with Milan
and Madrid these form eight named open races in five countries (NL, CH, IT, CZ, ES). Geneva
starts on the organizer `/participate` page because its direct Njuko slug fails local scrub.
Rome's page mixes older content: runtime date/edition verification remains mandatory.

Amsterdam is **not_open** (2027 registration opens December 19; current short distance
7.5K, not 8K). Vienna marathon/half are waitlist-only (**sold_out**); Freiburg has no remaining
entry codes (**sold_out**). Jungfrau shows only closed 2026 entry (**unknown** for 2027).
Seville's 2027 page still links a 2026 Njuko slug (**unknown**). Eiger E16 has an active
2027 registration link (**open**, 16 km only), but the external byUTMB host remains
unreviewed and must block navigation there. These are observations, not booking guarantees.

Checkpoint limitations: Njuko shape is based on the historical untouched Milan URL, not a
new event-specific visit. ENDU personal-page patterns are conservative **provisional**;
anonymous catalog/book GETs do not expose the participant URL. Other non-Njuko platforms
without an observed distinct personal-page URL use disabled `(?!)` patterns, explicitly
not success-capable until validated. No provisional pattern is claimed to be observed.

## R4-03 live H registration smokes — 2026-11-09 (UTC 01:32–01:48)

Harness: `runai.agents.registration.build_task` on the committed registry, then
`runai.agents.hclient.HAgentRunner().run(task)` with `HAI_API_KEY` from the environment, agents
in parallel. Pending the R4-01 hclient fallback gate fix, the harness (not product code) set
`fallback_url = start_url`; without it Milan/Geneva/Den Haag are blocked `policy_denied`
before any H session. Read-only: no data typed, no form submitted, no payment. Only status,
reason code, step count and scrubbed final URLs are recorded; no H frames or private session
URLs are committed.

| batch | race | start_url | result / reason_code | steps | actual stop (final URL) |
|---|---|---|---|---|---|
| 1 | Wizz Air Milano Marathon 2027 | https://in.njuko.com/wizz-air-milano-marathon-20271776152378557 | failed / session_failed | 9 | `...?currentPage=form_individual-form`: the Njuko participant form (first personal-data page) was reached; the H session then failed before a verified READY answer, so no success is claimed. |
| 1 | Zurich Maratón de Sevilla 2027 | https://www.zurichmaratonsevilla.es/zms-inscripciones | failed / timeout | 31 | still on `zms-inscripciones`; organizer → Njuko step not reached. |
| 1, 2 | Generali Genève Marathon 2027 | https://in.njuko.com/generali-geneve-marathon-2027-1782304695994 | failed / provider_error (0 H steps, twice) | 0 | none: `scrub_url` rejects the `-2027-1782304695994` path segment as phone-like, so hclient refuses the start URL before a session (hclient/scrub scope, not fixed here). |
| 1, 2 | NN CPC Loop Den Haag 2027 (widget URL) | https://in.njuko.com/nn-cpc-loop-den-haag-20261784205635566/w/6a58d147a44b09c924dbb429 | failed / provider_error (0 H steps) | 0 | none: `scrub_url` rejects the opaque hex `/w/` segment; adapter moved to the event root URL. |
| 3 | NN CPC Loop Den Haag 2027 (root URL) | https://in.njuko.com/nn-cpc-loop-den-haag-20261784205635566 | failed / step_limit | 12 | `...?currentPage=select-competition`: race list (half marathon observed sold out); no sold_out verdict returned before the limit. |
| 3 | Jungfrau-Marathon 2027 | https://www.jungfrau-marathon.ch/de/anmeldung.html | failed / session_failed | 3 | `de/anmeldung.html` (2027 registration not open per observation). |

Honest outcome: 0 verified READY stops. Milan reached the first personal-data page untouched.
Blockers for the next round: H `session_failed`/timeouts, hclient `scrub_url` rejecting real
Njuko event URLs (Geneva, Den Haag widget) and the R4-01 fallback gate.

## R4-03 reviews and availability observations — 2026-11-09

These rows supersede older unknown/status claims below for the named races only.
New reviews expire 2027-02-07 (90 days). Anonymous GET/curl and Chrome only;
cookie banners rejected, no login, account creation, consent acceptance, data entry
or form submission. No H run or pre-payment success is claimed. Existing Valencia,
Barcelona marathon, Paris and Rotterdam denials are unchanged. Adapter identifiers
below are policy entry IDs plus distance (the adapter schema has no separate ID).

| id | decision | terms URL(s) | reviewed sections | reason / clause | registration observation |
|---|---|---|---|---|---|
| `mitjamarato-barcelona` | prohibited for registration, including organizer fallback | https://www.mitjamarato.barcelona/avis-legal/<br>https://web.rockthesport.com/es/documentation/legal-notice | Full organizer Avis Legal: identification, IP, unauthorized use, liability, privacy, jurisdiction; platform extraction paragraph | Organizer has general domestic-use/copyright/load restrictions, not an express automation ban. Platform expressly prohibits “La extracción y uso de elementos del sitio causando o no un perjuicio cualquiera a Nuonet”. | Organizer says “Dorsals esgotats”, 14 February 2027. Anonymous platform GET identifies RockTheSport and says “Inscripciones agotadas”. No adapter: platform denied. Corporate https://www.rpmsports.es/ returned 403; /aviso-legal/ timed out, so corporate host remains unknown. |
| `rpmsports-rockthesport-registration` | prohibited | https://web.rockthesport.com/es/documentation/legal-notice | RockTheSport IP / prohibited extraction; RPM event platform identity | Same extraction clause above; scopes only inscripciones.rpmsports.es, not a conflicting allowance on rockthesport.com. | https://inscripciones.rpmsports.es/es/evento/hyundai-mitja-marato-barcelona-by-brooks-2027 shows 14/02/2027 and sold out. Hidden generic “event ended” modal copy is not reliable edition status. |
| `irontrail-ch` | prohibited for registration, including organizer fallback (Datasport denied) | https://www.irontrail.ch/<br>https://www.irontrail.ch/rennen-info/anmeldung<br>https://www.datasport.com/en/terms-and-conditions/ | Embedded legal/privacy notice including Copyright und Markenrechte; Anmeldung; Datasport athlete automated-procedure clause | Organizer has no express automation clause. Anmeldung explicitly delegates the entire registration process to Datasport and applies its AGB. Datasport: “no crawlers, search robots or other automated procedures may be used in order to review the data stored on myDatasport”. This clause names myDatasport; the existing broader base denial is preserved, not reinterpreted as an allowance for onreg. | Organizer links https://onreg.datasport.com/de/swiss-irontrail-2027; no Mikati​ming link observed. Platform not traversed: availability, login/captcha and first personal-data page unknown. Dates 14–15 August 2027, T78 78 km / T55 55 km / T22 21.6 km / T20 20.2 km. Individual start dates unverified; no adapter. |
| `nncpcloopdenhaag-nl` | allowed_owner_rule | https://nncpcloopdenhaag.nl/wp-content/uploads/sites/50/2026/09/Algemene-voorwaarden-NN-CPC-Loop-den-Haag-2027-Individueel.pdf<br>https://www.golazo.com/privacy-policies/golazo-the-netherlands/<br>https://in.njuko.com/nn-cpc-loop-den-haag-20261784205635566 | Full individual terms, four pages, Articles 1–7 (participation, liability, portrait/privacy, disputes); privacy; event footer CGU | No express automation/extraction/bot clause in individual terms. Unlike Rotterdam, no automated multiple-entry clause. Njuko CGU modal only displays “....”; shared platform authorization comes from existing base Njuko review, not invented event-specific terms. PDF initially returned browser-check HTML; later curl returned PDF and web content extraction returned all four pages. | Chrome: heading “NN CPC Loop Den Haag 2027”, 14-03-2027; NN Halve Marathon €49.50 “uitverkocht”. No login/captcha before selection; rejected cookies using Nee. Half sold out, so first personal-data page not reachable/verified. Adapter `nncpcloopdenhaag-nl` uses the exact Njuko URL in this row; slug has 2026 but visible edition is 2027. Availability sold_out, 2026-11-09, half only. |
| Descobrimentos half | unknown → blocked, no allowed entry or adapter | https://meiamaratonadosdescobrimentos.com/<br>https://meiamaratonadosdescobrimentos.com/informacoes/<br>https://login.plataformaxistarca.pt | Organizer landing/information/footer; platform anonymous landing | No retrievable substantive terms/regulations link found: “REGULAMENTO 2026” is not a linked document in fetched HTML. Registration platform exposes login, account creation and recovery only, no public terms. Cannot authorize organizer/platform from missing terms. | Official date 29 November 2026, 21 km (not a verified 2027 edition). Registration link leads to login wall before participant details. Availability unknown: pricing schedule alone does not prove inventory. No login attempted. |
| Lisbon October marathon 2027 | existing organizer/own-platform allowance unchanged; no new adapter (edition/deep link unverified) | https://maratonaclubedeportugal.com/maratona-de-lisboa/<br>https://maratonaclubedeportugal.com/prova/edp-maratona-de-lisboa-2026/<br>https://rnr.inscricoes.maratonaportugal.com/ | Existing scoped organizer registration pages and own registration landing | Main page title claims 2027 marathon entries open but its actual body is the 7 March half; the marathon-specific published page is still 2026. /prova/edp-maratona-de-lisboa-2027/ returns 404. Do not convert a misleading page title into a 2027 adapter. | Own rnr landing says unavailable/sold out but names EDP Meia/Vodafone/Luso, not a verified 2027 marathon. Availability unknown for October marathon. External course source https://running-portugal.com/lisbon/marathon/en/course.html lists 9 October 2027 marathon, while other listings say 10 October; that host is not reviewed and its registration page still advertises 2026. Exact 2027 date/deep link remains unverified. |
| `milanomarathon-it` existing adapter | allowed_owner_rule unchanged | https://in.njuko.com/wizz-air-milano-marathon-20271776152378557 | Existing reviewed event; availability recheck only | No new policy scope/terms decision. | Chrome: 04/04/2027, two entry categories €114. Rejected cookies; public S'INSCRIRE on foreign non-competitive category reached blank first participant-information page, no login/captcha. Left untouched, never pressed Next. Availability open, 2026-11-09. Some qualifying-time guidance mentions 2026: runtime must verify edition/date again. |
| `maratonaclubedeportugal-com` existing EDP half adapter | allowed_owner_rule unchanged | https://meia-maratona.inscricoes.maratonaportugal.com/default.aspx?prova_id=3769 | Existing observation retained, not re-dated | No new terms decision. | Availability sold_out observed 2026-11-08: Esgotada, waitinglist.aspx. Organizer recheck 2026-11-09 still shows Waiting list. |

Chrome root-URL recheck (2026-11-09): opening https://in.njuko.com/nn-cpc-loop-den-haag-20261784205635566 renders the 2027 event dated 14-03-2027, half marathon uitverkocht, 10/5 km INSCHRIJVEN, no login/captcha. Cookies had already been rejected; no forms touched. Important: Njuko navigation changes the address to the original widget URL https://in.njuko.com/nn-cpc-loop-den-haag-20261784205635566/w/6a58d147a44b09c924dbb429?currentPage=select-competition. The adapter now starts at the root, but a live runtime that rejects that eventual widget URL may still block; root navigation is not proof that the scrubber issue is solved.

### Test source records (only verified dates; not invented 2027 alternatives)

```json
[
 {"name":"Mitja Marató Barcelona 2027","country":"ES","race_date":"2027-02-14","distance_km":21.0975,"official_url":"https://www.mitjamarato.barcelona/","registration_url":"https://inscripciones.rpmsports.es/es/evento/hyundai-mitja-marato-barcelona-by-brooks-2027"},
 {"name":"NN CPC Loop Den Haag 2027","country":"NL","race_date":"2027-03-14","distance_km":21.1,"official_url":"https://nncpcloopdenhaag.nl/","registration_url":"https://in.njuko.com/nn-cpc-loop-den-haag-20261784205635566"},
 {"name":"Meia Maratona dos Descobrimentos 2026","country":"PT","race_date":"2026-11-29","distance_km":21,"official_url":"https://meiamaratonadosdescobrimentos.com/","registration_url":"https://login.plataformaxistarca.pt"},
 {"name":"Wizz Air Milano Marathon 2027","country":"IT","race_date":"2027-04-04","distance_km":42.195,"official_url":"https://www.milanomarathon.it/","registration_url":"https://in.njuko.com/wizz-air-milano-marathon-20271776152378557"},
 {"name":"EDP Meia Maratona de Lisboa 2027","country":"PT","race_date":"2027-03-07","distance_km":21,"official_url":"https://maratonaclubedeportugal.com/","registration_url":"https://meia-maratona.inscricoes.maratonaportugal.com/default.aspx?prova_id=3769"}
]
```

Swiss Irontrail 2027 T78: country CH, distance_km 78, official_url
https://www.irontrail.ch/, registration_url https://onreg.datasport.com/de/swiss-irontrail-2027.
Do not supply a made-up race_date: only the weekend 2027-08-14/15 was verified.
Lisbon October 2027: no source record with a confirmed exact date or registration URL.
Best-effort additional cities were time-boxed out; existing Madrid, Zurich and Lausanne
blocker notes below remain unchanged. No Hamburg/Munich/Eindhoven/Turin/Malaga review claimed.

### Scoped checks

PR #30 safety follow-up: Barcelona half and Irontrail organizer entries are now
prohibited for the registration purpose, not merely their platforms. No organizer-only
start is permitted. Both sourced URLs are checked before choosing an adapter, so an
allowed platform URL cannot override a denied official organizer. CPC availability now
has an explicit `distances_km: [21, 21.0975, 21.1]` scope: half-marathon coverage remains
sold_out, while 5/10 km remain covered with unknown status and no AVAILABILITY FIRST
instruction. Missing scope retains existing behavior; malformed/empty scopes fail closed.

```text
$ uv run ruff check . && uv run pytest -q
All checks passed!
1166 passed, 1 warning in 7.01s
```

`uv run python -c "import json;json.load(open('docs/site-policy.d/registration.json'))" && uv run pytest -q tests/test_site_policy.py tests/test_agent_registration.py 2>&1 | tail -5`

```text
........................................................................ [ 34%]
........................................................................ [ 68%]
...................................................................      [100%]
211 passed in 0.52s
```

Initial run caught the new prohibited RPM entry's screenshot_scope set to
in_session_only instead of none; corrected the entry, then obtained the output above.
Concurrent registration builder/test edits are not authored by this research step.
`git diff --check` produced no output. No pre-commit configuration found.


Dated 2026-11-08. Terms reviews: see `docs/evidence/site-policy.md` and `docs/site-policy.json`.
Observations come from R1-05's public anonymous fetches (2026-11-08, no forms, no login).
**No live H registration run has been made in R2-02**: live smokes wait for the R2-03 no-share runtime.

## What the builder does now (`runai/agents/registration.py`)
- Validates a sourced race: confirmed/official future `race_date`, edition year matching the date,
  distance, city, country. Stale, conflicting or missing data → `ValueError` (blocked).
- Calls `evaluate_url(registration_url, "registration")`, then the official URL. Only an allowed
  policy decision makes the start URL. Unreviewed hosts block. Platforms are not trusted by name.
- `registration_info()` access observations (account/captcha) are copied as source-only
  metadata and **never** grant permission.
- Instructions: select the exact edition/date/distance; stop untouched at the first personal-data page;
  BLOCKED on account wall, lottery-only, closed/sold-out, captcha, earlier consent, date/distance mismatch,
  or redirect to a host outside `allowed_hosts`. `max_steps` 80.

## Reviewed vs observed vs unverified
| Race / platform | Terms decision (2026-11-08) | Access observation | Unverified |
|---|---|---|---|
| Milano Marathon 2027 → `in.njuko.com/wizz-air-milano-marathon-20271776152378557` | `allowed_read_only` (Njuko application CGU: no automation/copy restriction found); organizer `milanomarathon.it` terms not reviewed → start directly on the Njuko event page | Observed (R1-05): no captcha marker in shell HTML; JS app | Ticket list, open/sold-out status, first personal-data page |
| Other Njuko events (`in.njuko.com`) | `allowed_owner_rule` (corporate notice limits reproduction; ambiguous) | none | everything |
| ENDU (`endu.net`, `rrtm.endu.net` for Rome) | `allowed_owner_rule`; organizer `runromethemarathon.com` not reviewed → denied | none | everything |
| Ahotu, Race Result, Sportstiming, Raceroster | `allowed_owner_rule` (no automation clause found / ambiguous) | none | everything |
| Berlin (SCC) | `prohibited` | Observed (R1-05): lottery + `login.scc-events.com` login wall | n/a: blocked |
| Active, Eventbrite, Athlinks, Let's Do This, Datasport | `prohibited` | n/a | n/a: blocked |
| Barcelona (RPM Sports) | unknown → denied (terms not reviewed) | Observed (R1-05): reCAPTCHA script | n/a: blocked |
| Lisbon half (`maratonaclubedeportugal.com`) | unknown → denied (terms not fetched) | none | n/a: blocked |

No account is created automatically and no platform is guaranteed to accept agents.

## R3-02 organizer and registration-platform terms reviews (2026-11-08)

Source: `docs/site-policy.d/registration.json` (reviewed_at 2026-11-08, expires_at 2027-02-06).
Method: anonymous public GET of the listed terms/legal pages and registration landing pages; no cookies
accepted, no login, no form opened or submitted, no personal data. No live H registration session was
run in R3-02 (no evidence of a pre-payment stop is claimed). Base-registry platforms (njuko, endu,
my-raceresult, sportstiming, raceroster, ahotu) are referenced through `platform_hosts`, not duplicated.

| id | decision | terms URL(s) | reviewed sections | reason / clause | registration observation |
|---|---|---|---|---|---|
| `milanomarathon-it` | allowed_owner_rule | https://www.milanomarathon.it/privacy/<br>https://www.milanomarathon.it/wizz-air-milano-marathon/regolamento/ | Privacy policy (full text keyword review); Regolamento landing page; Iscriviti page; footer legal-link search | No website terms of use are published (footer/legal-link search); the reviewed pages contain no robot, scraping or automated-agent prohibition. Iscriviti links to the reviewed Njuko event page (milano-marathon-2027-njuko). Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | Iscriviti links to in.njuko.com 2027 event; Njuko page is a JavaScript app, availability unverified. |
| `maratonaclubedeportugal-com` | allowed_owner_rule | https://maratonaclubedeportugal.com/politica_de_privacidade.pdf<br>https://maratonaclubedeportugal.com/wp-content/uploads/REGULAMENTO_EDP_MEIA-_MARATONA_DE-LISBOA_2027_PT-.docx.pdf | Privacy policy PDF; EDP Meia Maratona de Lisboa 2027 regulamento PDF; footer legal-link search on organizer and inscricoes.maratonaportugal.com | No website terms of use are published (footer/legal-link search); the reviewed pages contain no robot, scraping or automated-agent prohibition. The own-branded inscricoes.maratonaportugal.com service publishes no separate terms. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | 2027 half (prova_id=3769, 21 km) redirects to waitinglist.aspx: Esgotada (sold out); waiting-list form only. |
| `mein-freiburgmarathon-de` | allowed_owner_rule | https://mein-freiburgmarathon.de/impressum/<br>https://my.raceresult.com/imprint/termsofuse | Impressum: Urheberrechte, Hyperlink, Markenzeichen, Haftung, Lizenz/Nutzungsrechte, Recht; RACE RESULT Allgemeine Nutzungsbedingungen (keyword review) | No express automated-access, robot or scraping prohibition in the Impressum or the embedded RACE RESULT terms; general copyright restrictions only. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | Embedded RACE RESULT registration; organizer says entry only with an existing code and codes are allocated. |
| `jungfrau-marathon-ch` | allowed_owner_rule | https://www.jungfrau-marathon.ch/de/impressum.html | Impressum (full text keyword review) | No express robot, scraping or automated-access prohibition in the Impressum. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | Anmeldung says the 2026 online registration is closed; 2027 entry (10/11 Sept 2027) not yet linked. |
| `eiger-utmb-world` | allowed_owner_rule | https://utmb.world/terms-and-conditions | UTMB terms & conditions: Editor information; Intellectual property; Personal data (keyword review) | No express bot or scraping prohibition in the UTMB website terms (broad reproduction limits only). The in.ch.byutmb.world registration host is NOT reviewed: navigation there must stop as unreviewed_redirect. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | adapter: https://eiger.utmb.world/registration |
| `zurichmaratonsevilla-es` | allowed_owner_rule | https://www.zurichmaratonsevilla.es/web-aviso-legal | Aviso legal: conditions of use, intellectual property, liability (full text keyword review) | No express automation or scraping prohibition in the organizer legal notice; registration runs on reviewed Njuko. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | Inscripciones page describes 2027 phases; embedded Njuko link still labelled 2026. |
| `generaligenevemarathon-com` | allowed_owner_rule | https://www.generaligenevemarathon.com/mentions-legales<br>https://www.generaligenevemarathon.com/rules | Mentions légales: 1 Éditeur, 2 Hébergeur, 3 Propriété intellectuelle; rules/CGV landing page | No express automated-access or scraping prohibition in the organizer legal notice; registration runs on reviewed Njuko. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | adapter: https://in.njuko.com/generali-geneve-marathon-2027-1782304695994 |
| `runromethemarathon-com` | allowed_owner_rule | https://www.runromethemarathon.com/privacy-policy-2/ | Privacy policy / Condizioni generali di utilizzo page (privacy text only); homepage footer legal-link search | No website terms of use are published (footer/legal-link search); the reviewed pages contain no robot, scraping or automated-agent prohibition. ISCRIVITI links to the reviewed ENDU host rrtm.endu.net. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | adapter: https://rrtm.endu.net/ |
| `bolognamarathon-run` | allowed_owner_rule | https://www.bolognamarathon.run/regolamento | Regolamento 2027 (full text keyword review); footer legal-link search | No website terms of use are published (footer/legal-link search); the reviewed pages contain no robot, scraping or automated-agent prohibition. ISCRIVITI SU ENDU leads to the reviewed www.endu.net book page. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | adapter: https://www.endu.net/events/bologna-marathon/book |
| `padovamarathon-com` | allowed_owner_rule | https://padovamarathon.com/termini-e-condizioni/ | Condizioni generali di vendita B2C: premises, 1-4 sales/contract, 9 obligations (keyword review) | No express automation, robot or scraping prohibition in the published terms; ISCRIVITI ONLINE leads to the reviewed ENDU host. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | adapter: https://www.endu.net/events/padovamarathon/book |
| `firenzemarathon-it` | allowed_owner_rule | https://www.firenzemarathon.it/regolamento-maratona/ | Regolamento maratona (full text keyword review); footer legal-link search | No website terms of use are published (footer/legal-link search); the reviewed pages contain no robot, scraping or automated-agent prohibition. Registration runs on the reviewed ENDU host. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | ENDU event page shows the 2026 edition; 2027 registration not verified. |
| `vienna-marathon-com` | allowed_owner_rule | https://www.vienna-marathon.com/?go=impressum<br>https://www.hakuapp.com/legal | Organizer Impressum (keyword review); haku Terms of Service for organizers and participants (automated-access keyword review) | No express bot, crawler, scraping or automated-access ban in the organizer Impressum or haku terms. Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | Registration options: waiting list for marathon/half/relay; individual entry for shorter runs. |
| `runczech-com` | allowed_owner_rule | https://www.runczech.com/en/web-information<br>https://www.runczech.com/en/common-general-terms-and-conditions | Web information: Obligations of Users, Limitation of Liability; Common General Terms: formation of contract, RunnersID | No express automation or scraping prohibition in the website-use or general entry terms. Online entry needs a RunnersID account (login wall). Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | Race selection loads anonymously; RunnersID account required to register (report login_required). |
| `tcsamsterdammarathon-eu` | allowed_owner_rule | https://www.tcsamsterdammarathon.eu/general-terms-and-conditions<br>https://do.occdn.net/p/75/f/am26-algemene-voorwaarden-stichtingsevenementen-individueel-en-groepen-eng.pdf<br>https://do.occdn.net/p/75/f/am26-reglement-individueel-en-business-tcsam-eng2.pdf | General terms download page; 2026 individual/group conditions Articles 1-7; 2026 regulations Articles 1-25 | No express automation ban in the published terms and regulations (2026 versions; re-review 2027 terms when released). Allowed read-only by owner rule: no forms, accounts, consent or payment; screenshots in-session only. | 2027 registration opens 19 December 2026. |
| `10kvalencia-com` | prohibited | https://10kvalencia.com/condiciones-generales/<br>https://registration.10kvalencia.com/inscripcion/10k-valencia-ibercaja-by-kiprun-2027/registration-terms | Condiciones de uso de la Web; Normas de uso; Derechos de Propiedad Intelectual e Industrial | Express restriction on automated access/extraction: "Los Contenidos de la Web no se podrán extraer por terceros, ya sea de forma manual o a través de cualquier técnica." Denied; never start or navigate an H agent here. | n/a |
| `valenciaciudaddelrunning-com` | prohibited | https://www.valenciaciudaddelrunning.com/terminos-y-condiciones-vcr/<br>https://www.valenciaciudaddelrunning.com/terminos-y-condiciones-sdc/ | Condiciones de uso de la Web; Normas de uso; Derechos de Propiedad Intelectual e Industrial (Fundación and SD Correcaminos) | Express restriction on automated access/extraction: "Los Contenidos de la Web no se podrán extraer por terceros, ya sea de forma manual o a través de cualquier técnica." Denied; never start or navigate an H agent here. | n/a |
| `swisscanyontrail-com` | prohibited | https://www.swisscanyontrail.com/policies/terms-of-service | Terms of service: Section 12 Prohibited uses | Express restriction on automated access/extraction: "(i) to spam, phish, pharm, pretext, spider, crawl, or scrape;" Denied; never start or navigate an H agent here. | n/a |
| `zurichmaratobarcelona-es` | prohibited | https://zurichmaratobarcelona.es/avis-legal/ | Avis legal: condiciones de acceso y uso; propiedad intelectual | Express restriction on automated access/extraction: "La extracción y uso de elementos del sitio ... (intellectual-property/extraction clause)" Denied; never start or navigate an H agent here. | n/a |
| `rockthesport-com` | prohibited | https://web.rockthesport.com/es/documentation/legal-notice<br>https://web.rockthesport.com/es/documentation/general-terms | Aviso legal: intellectual-property/extraction paragraph; Términos y condiciones | Express restriction on automated access/extraction: "La extracción y uso de elementos del sitio causando o no un perjuicio cualquiera a Nuonet ..." Denied; never start or navigate an H agent here. | n/a |
| `rocknrollmadridrun-com` | prohibited | https://rocknrollmadridrun.com/aviso-legal/ | Aviso legal: intellectual-property/extraction paragraph | Express restriction on automated access/extraction: "La extracción y uso de elementos del sitio causando o no un perjuicio cualquiera a Elipse ..." Denied; never start or navigate an H agent here. | n/a |
| `asicsmarathondeparis-com` | prohibited | https://www.asicsmarathondeparis.com/fr/conditions-generales-dutilisation | Conditions générales d'utilisation: accès et utilisation du site (extraction automatisée) | Express restriction on automated access/extraction: "Vous n'êtes pas autorisé à utiliser, ni à permettre à des tiers d'utiliser, tout système automatisé ou logiciel permettant d'extraire des contenus ou données depuis le Site" Denied; never start or navigate an H agent here. | n/a |
| `hokasemimarathondeparis-com` | prohibited | https://www.hokasemimarathondeparis.com/fr/conditions-generales-dutilisation | Conditions générales d'utilisation: accès et utilisation du site (extraction automatisée) | Express restriction on automated access/extraction: "Vous n'êtes pas autorisé à utiliser, ni à permettre à des tiers d'utiliser, tout système automatisé ou logiciel permettant d'extraire des contenus ou données depuis le Site" Denied; never start or navigate an H agent here. | n/a |
| `runinlyon-com` | prohibited | https://www.runinlyon.com/fr/mentions-legales | CGU: user conduct / prohibited uses | Express restriction on automated access/extraction: "Utiliser un robot, un agent numérique ... ou tout autre dispositif ou processus manuel ou automatisé" Denied; never start or navigate an H agent here. | n/a |
| `timeto-com` | prohibited | https://www.timeto.com/fr/cgu | CGU 4.19 (robots, extraction, CAPTCHA) | Express restriction on automated access/extraction: "Utiliser un robot, un agent numérique ... ou tout autre dispositif ou processus manuel ou automatisé" Denied; never start or navigate an H agent here. | n/a |
| `nnmarathonrotterdam` | prohibited | https://nnmarathonrotterdam.nl/wp-content/uploads/sites/52/2026/10/Algemene-Voorwaarden-NNMR-Pre-registratie-2027.pdf | Algemene voorwaarden pre-registratie 2027: Artikel 2.2, Artikel 4.5 | Express restriction on automated access/extraction: "Meerdere pre-registraties ... met geautomatiseerde middelen (zoals bots of scripts) zijn verboden." Denied; never start or navigate an H agent here. | n/a |
| `nnmarathonrotterdam-2027-njuko` | ambiguous | https://nnmarathonrotterdam.nl/wp-content/uploads/sites/52/2026/10/Algemene-Voorwaarden-NNMR-Pre-registratie-2027.pdf | Algemene voorwaarden pre-registratie 2027: Artikel 2.2, Artikel 4.5 (event-path scope so the Njuko host stays usable for other events) | Express restriction on automated access/extraction: "Meerdere pre-registraties ... met geautomatiseerde middelen (zoals bots of scripts) zijn verboden." Denied; never start or navigate an H agent here. | n/a |

Not added (fail closed as unknown): Lausanne (`onreg.datasport.com` already prohibited in base),
Zurich Marathon (GoActive publishes no reachable terms), Brussels (no terms page found), Paris/Lyon
registration platforms beyond the listed CGU clauses. Valencia, Swiss Canyon Trail, Barcelona, Madrid,
Paris, Lyon and Rotterdam are explicitly denied because their terms forbid automated extraction/bots.
Lisbon half 2027 was observed sold out (Esgotada, waiting list) on 2026-11-08: the agent must report
`sold_out`, not READY.

## R7-03 offline registration coverage — 2026-11-09

Owner-rule scope: docs/handoff/lift-site-exclusions.md overrides the historical
exclusion table above, not any account/consent/submission/payment safety stop.
New entries (reviewed 2026-11-09, expires 2027-02-07):
- `r7-berlin-marathon`: official GENERALI organizer /en/registration/run,
  including www BMW alias scope. Anonymous GET says lottery runs October 1 to
  November 12, 2026, for September 26, 2027; a personal SCC account is required.
  Linked public login URL: https://login.scc-events.com/s/login/?language=en_US.
  Task stops BLOCKED login_required; no ballot, account or login action.
- `r7-valencia-marathon-2026`: official
  https://www.valenciaciudaddelrunning.com/en/marathon/info-registration-2026/.
  Anonymous GET of its linked /en/marathon/faq-valencia-marathon-waiting-list/
  says only unsuccessful ballot entrants are on the waiting list and new
  waiting-list registrations are not accepted. Treat as sold_out, never join.
- `r7-valencia-marathon-2027`: official /en/marathon/ information handoff.
  No verified 2027 entry/platform was found; availability stays unknown, with
  bounded no_inventory task rather than inheriting 2026 sold-out status.
- `r7-lisbon-marathon-2027`: official organizer /maratona-de-lisboa/ handoff.
  Organizer navigation still links the 2026 full marathon; no verified 2027
  full-marathon platform/date was found. Unknown, bounded no_inventory task;
  this does not assert that the full marathon is sold out.

Lisbon HALF: anonymous GET of the existing prova_id=3769 registration URL
again returned waitinglist.aspx, Lista de Espera, Esgotada, 07/03/2027. Bounded
sold_out task checks availability within five steps (max_steps 12), not 60.

CPC edition check: the old observation explicitly records rendered title 2027
and date 14-03-2027 despite the 2026 slug. A new anonymous GET of official
https://nncpcloopdenhaag.nl/inschrijven/10-km-loop/ still links that exact event
with /w/6a58d147a44b09c924dbb429 and 2027 entry deadlines. Do not rewrite the
slug based on its year. Current builder, evaluate_url, scrub and _policy gates
allow it. The historical live denial is not reproduced; session redirect/task
evidence is needed to identify its actual cause. Half remains sold_out;
5/10 km observations remain separate.

Frankfurt builder and _policy allow the reviewed white-label event. scrub_url
still returns None; HAgentRunner cleans start_url then rejects a non-public
result before session creation. Core scrub amendment belongs R7-01.

Stoos anonymous GET still identifies Stoos Trail 2027, 2027-07-10, Brunnen.
The existing observed participant checkpoint is retained; earlier required
consent is an honest blocker, never consent acceptance or invented READY.

All unavailable tasks retain safe official handoffs and bounded steps, but
these are H tasks, NOT pre-H short-circuit results. Core support is required
for a true pre-H result. Profile-bearing normal tasks emit P14 field names only;
actual runtime prefill and new boundary enforcement need R7-01 integration.
No H sessions, personal-data entry, submissions or visual checks performed.

Offline checks after final code/policy edits:
```
uv run ruff check .
All checks passed!
uv run pytest -q
2331 passed, 1 warning in 60.05s (0:01:00)
uv run pytest -q tests/test_agent_hotel.py tests/test_agent_registration.py tests/test_site_policy.py
798 passed in 8.27s
```
The warning is the existing Starlette httpx TestClient deprecation. All ten
generated scenario tasks passed hclient._policy; Frankfurt separately fails
scrub_url, as above. This is offline evidence, not successful preparation.
