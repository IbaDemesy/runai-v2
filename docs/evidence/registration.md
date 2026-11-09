# Registration path evidence (R2-02, supersedes R1-05 "assumed" claims)

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
| `mitjamarato-barcelona` | organizer allowed_owner_rule; registration prohibited | https://www.mitjamarato.barcelona/avis-legal/<br>https://web.rockthesport.com/es/documentation/legal-notice | Full organizer Avis Legal: identification, IP, unauthorized use, liability, privacy, jurisdiction; platform extraction paragraph | Organizer has general domestic-use/copyright/load restrictions, not an express automation ban. Platform expressly prohibits “La extracción y uso de elementos del sitio causando o no un perjuicio cualquiera a Nuonet”. | Organizer says “Dorsals esgotats”, 14 February 2027. Anonymous platform GET identifies RockTheSport and says “Inscripciones agotadas”. No adapter: platform denied. Corporate https://www.rpmsports.es/ returned 403; /aviso-legal/ timed out, so corporate host remains unknown. |
| `rpmsports-rockthesport-registration` | prohibited | https://web.rockthesport.com/es/documentation/legal-notice | RockTheSport IP / prohibited extraction; RPM event platform identity | Same extraction clause above; scopes only inscripciones.rpmsports.es, not a conflicting allowance on rockthesport.com. | https://inscripciones.rpmsports.es/es/evento/hyundai-mitja-marato-barcelona-by-brooks-2027 shows 14/02/2027 and sold out. Hidden generic “event ended” modal copy is not reliable edition status. |
| `irontrail-ch` | organizer allowed_owner_rule; registration blocked by existing Datasport prohibition | https://www.irontrail.ch/<br>https://www.irontrail.ch/rennen-info/anmeldung<br>https://www.datasport.com/en/terms-and-conditions/ | Embedded legal/privacy notice including Copyright und Markenrechte; Anmeldung; Datasport athlete automated-procedure clause | Organizer has no express automation clause. Anmeldung explicitly delegates the entire registration process to Datasport and applies its AGB. Datasport: “no crawlers, search robots or other automated procedures may be used in order to review the data stored on myDatasport”. This clause names myDatasport; the existing broader base denial is preserved, not reinterpreted as an allowance for onreg. | Organizer links https://onreg.datasport.com/de/swiss-irontrail-2027; no Mikati​ming link observed. Platform not traversed: availability, login/captcha and first personal-data page unknown. Dates 14–15 August 2027, T78 78 km / T55 55 km / T22 21.6 km / T20 20.2 km. Individual start dates unverified; no adapter. |
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
