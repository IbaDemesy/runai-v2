# Linkup discovery live evidence

## R2-04 step 1 — offline reliability revision (2026-11-08)

No new live requests were made for this revision. Historical batches below are
not verification of the revised prompt. Past-only results are now rejected as
an empty list (the historical past-edition fallback described below is removed).
Official dated candidates sort ahead of unverified/unknown/conflicting ones;
conflicts retain `date_status=conflicting` with no selected date. No dates are
derived from edition/platform URLs, and no next-year date is manufactured.

Deep search and timeout behavior remain unchanged: default 20 seconds, caller
override retained verbatim, and app integration still supplies 120 seconds.
Offline mock requests cover both timeout values. Query/hints use scrubbed,
instruction-filtered JSON inside a delimited data block; source-derived display
text receives the same filtering. Source schemas reject extra fields, dates
require exact ISO dates, and public URLs must survive the shared scrubber.
This is defense in depth, not a claim that provider source extraction is an
independent audit or that arbitrary prompt injection is solved.

Step 1b aligns the pinned observation contract: `registration_access` is None
or exactly `account_required`, `captcha`, `source`, `observed_at`, `note`.
The booleans are nullable; observation time is an ISO date, not a datetime.
The default registry is lazily imported from
`runai.agents.site_policy.registration_info`; missing module/function is unknown.
An injected sync/async callable remains supported. Both receive only the public
registration URL, falling back to the official URL, never the candidate/query.
Accepted evidence requires a public source URL and a non-future observation
date. Missing/invalid evidence or lookup failures remain unknown. Observations
are not permission or guarantees of login-free access; no platform inference,
form submissions or accounts are used.

Offline check: `uv run ruff check . && uv run pytest -q`:

```text
All checks passed!
456 passed, 1 warning in 2.01s
```

The warning is the installed FastAPI/Starlette test-client httpx deprecation,
not a missing project environment. No dependency/configuration files changed.

Verified at 2026-11-08T20:30:24.639875+00:00.

## Verdict and reproduction

- Three verification batches on 2026-11-08, each containing the four required
  queries in parallel; 12 read-only Linkup requests total. No H sessions,
  registration submissions, consent, account creation, bookings or purchases.
- Final implementation uses **deep** structured search. The 20-second default
  timed out for all four queries. Explicit `timeout_s=120` returned sourced
  candidates for all four queries in 30.91–78.85 seconds (batch 2 below).
- A standard-depth experiment was faster (4.02–7.17 seconds) but had materially
  poorer grounding, missing distances and only a past Milan edition despite an
  available future edition. It was rejected; batch 3 is NOT the final code.
- Integration should call `await discover(query, timeout_s=120)` and show an
  honest loading state. The specified public default remains 20 seconds;
  timeout errors never fall back to fabricated or cached success.
- Candidate dates/distances are Linkup extractions, not independently audited
  race guarantees. Unknown/conflicting dates remain explicit; the UI must not
  silently turn them into confirmed dates. The past-edition fallback means
  "no future edition in this response", not proof none exists on the web.
- Official status requires a dated source on the identified organizer host, or
  the exact registration URL linked by a sourced official organizer page.
  Query/fragment-bearing URLs are conservatively omitted to avoid handing out
  session-bearing evidence. No raw provider bodies or credentials are recorded.
- Subsequent offline review hardening also rejects sensitive session/checkout
  path segments and opaque token-like components, and preserves a known distance
  from a more complete duplicate. No additional live batch was performed.

API documentation read before execution:

- https://docs.linkup.so/pages/documentation/endpoints/search/reference
- https://docs.linkup.so/pages/documentation/endpoints/search/overview
- https://docs.linkup.so/pages/documentation/tutorials/structured-output-guide

Request: `POST https://api.linkup.so/v1/search`, bearer credential from the
environment, `depth=deep`, `outputType=structured`, root-object JSON schema string
in `structuredOutputSchema`. No `fromDate` filter: that filters publication dates,
not event dates, and would hide already-published future-edition announcements.

Independent read-only official-page spot checks on 2026-11-08:

- https://www.runromethemarathon.com/en/ announces **14 March 2027**, **42.195 km**.
  The page also retains older 2026 content, which must not be mixed into 2027.
- https://www.milanomarathon.it/en/ announces **4 April 2027**, **42.195 km**.
- https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/
  announces **7 March 2027**, **21 km**.
- https://www.swisscanyontrail.com/en announces a **4–6 June 2027** weekend,
  including a **16K** event. This homepage alone does not establish the exact
  16K start date; batch 2 cites the distance-specific page separately.

## Batch 1 — default 20-second request timeout

Read-only Linkup API search, four requests in parallel. No H/browser sessions or booking actions.

### un marathon au printemps en Italie

Latency: 20.48s. Error: Race discovery timed out. Please try again..

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| No candidates returned | — | — | — | — | — |

### un trail en Suisse cet ete

Latency: 20.28s. Error: Race discovery timed out. Please try again..

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| No candidates returned | — | — | — | — | — |

### le semi de Lisbonne

Latency: 20.23s. Error: Race discovery timed out. Please try again..

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| No candidates returned | — | — | — | — | — |

### Milano Marathon

Latency: 20.19s. Error: Race discovery timed out. Please try again..

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| No candidates returned | — | — | — | — | — |

## Batch 2 — explicit 120-second request timeout

Verified at 2026-11-08T20:31:51.422438+00:00. Read-only API retries after all default-timeout searches timed out.

### un marathon au printemps en Italie

Latency: 59.24s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Run Rome The Marathon | 32nd edition (2027) | 42.195 | 2027-03-14 | official | https://www.runromethemarathon.com/en/ |
| Termal Bologna Marathon | 2027 | 42.0 | 2027-03-07 | official | https://www.bolognamarathon.run/ |
| Wizz Air Milano Marathon | 25th edition (2027) | 42.195 | 2027-04-04 | official | https://www.milanomarathon.it/en/marathon/ |
| PEAK Lake Garda 42 (LG42) | 6th edition (2027) | 42.0 | 2027-04-11 | official | https://lakegarda42.com/en/ |
| Padova Marathon | 27th edition (2027) | 42.195 | 2027-04-18 | official | https://www.padovamarathon.com/ |
| Rimini Marathon | 12th edition (2027) | 42.195 | unknown | conflicting | https://www.riminimarathon.it/ |

- Run Rome The Marathon source URLs: https://www.runromethemarathon.com/wp-content/uploads/2026/04/RRTM27-regolamento-italiano-23-4-2026.pdf, https://www.runromethemarathon.com/en/
- Termal Bologna Marathon source URLs: https://www.bolognamarathon.run/regolamento
- Wizz Air Milano Marathon source URLs: https://www.milanomarathon.it/en/marathon/, https://www.milanomarathon.it/
- PEAK Lake Garda 42 (LG42) source URLs: https://lakegarda42.com/en/, https://lakegarda42.com/it/
- Padova Marathon source URLs: https://padovamarathon.com/padova-marathon-2027-aperte-le-iscrizioni/, https://www.fidal.it/upload/files/Organizzazione/2027/Maratone%20e%20mezze%20maratone/Calendario%20Maratone%20e%20Mezze%20Maratone%202027%20agg.%2029%20settembre.pdf
- Rimini Marathon source URLs: https://www.riminimarathon.it/regolamento-maratona/, https://www.riminimarathon.it/iscrizioni-maratona-rimini/, https://www.fidal.it/upload/files/Organizzazione/2027/Maratone%20e%20mezze%20maratone/Calendario%20Maratone%20e%20Mezze%20Maratone%202027%20agg.%2029%20settembre.pdf

### un trail en Suisse cet ete

Latency: 78.85s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Swiss Canyon Trail | 32e édition (2027) | 16.0 | 2027-06-05 | official | https://www.swisscanyontrail.com/en |
| Trail Verbier St-Bernard by UTMB | 18e édition (2027) | 47.0 | 2027-07-09 | official | https://verbier.utmb.world/ |
| Eiger Ultra Trail by UTMB | 15e édition (2027) | 51.0 | unknown | conflicting | https://eiger.utmb.world/ |
| Sierre-Zinal | 54e édition (2027) | 31.0 | 2027-08-07 | official | https://www.sierre-zinal.com/ |
| SwissPeaks Trail | 2027 | 168.0 | 2027-09-02 | official | https://swisspeaks.ch/ |
| Wildstrubel by UTMB | 2027 | None | unknown | unknown | https://wildstrubel.utmb.world/ |

- Swiss Canyon Trail source URLs: https://www.swisscanyontrail.com/en/pages/16k, https://www.swisscanyontrail.com/en
- Trail Verbier St-Bernard by UTMB source URLs: https://verbier.utmb.world/discover/the-event/concept, https://verbier.utmb.world/races-and-runner/races/list-of-races
- Eiger Ultra Trail by UTMB source URLs: https://eiger.utmb.world/registration, https://eiger.utmb.world/races/E51
- Sierre-Zinal source URLs: https://www.sierre-zinal.com/en/homepage.html
- SwissPeaks Trail source URLs: https://swisspeaks.ch/en/lescourses/100-miles/
- Wildstrubel by UTMB source URLs: https://wildstrubel.utmb.world/

### le semi de Lisbonne

Latency: 70.4s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| EDP Meia Maratona de Lisboa | 2027 (36th edition) | 21.0 | 2027-03-07 | official | https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/ |
| Generali Tranquilidade Meia Maratona dos Descobrimentos | 2026 | 21.0 | 2026-11-29 | official | https://meiamaratonadosdescobrimentos.com/informacoes/ |

- EDP Meia Maratona de Lisboa source URLs: https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/, https://maratonaclubedeportugal.com/wp-content/uploads/Regulamento_EDP_Meia_Maratona_de_Lisboa_MAR2027_PT.pdf
- Generali Tranquilidade Meia Maratona dos Descobrimentos source URLs: https://meiamaratonadosdescobrimentos.com/informacoes/

### Milano Marathon

Latency: 30.91s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Wizz Air Milano Marathon | 25th edition (2027) | 42.195 | 2027-04-04 | official | https://www.milanomarathon.it/en/ |
| Milano Relay Marathon | 2027 | None | 2027-04-04 | official | https://www.milanomarathon.it/en/ |
| Milano Family Run | Third edition (2027) | None | 2027-04-03 | official | https://www.milanomarathon.it/en/ |

- Wizz Air Milano Marathon source URLs: https://www.milanomarathon.it/en/, https://www.milanomarathon.it/en/marathon/, https://www.milanomarathon.it/en/marathon/register/
- Milano Relay Marathon source URLs: https://www.milanomarathon.it/en/, https://www.milanomarathon.it/en/relay-marathon-en/
- Milano Family Run source URLs: https://www.milanomarathon.it/fr/family-run-fr/informations-pratiques-family-run/

## Batch 3 — rejected standard-depth experiment, default 20-second timeout

Verified at 2026-11-08T20:32:18.970217+00:00. Read-only API searches. This experiment was rejected for poor grounding; the final implementation retains deep search as verified in batch 2.

### un marathon au printemps en Italie

Latency: 5.41s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Run Rome The Marathon | 32ª edizione (2027) | 42.195 | unknown | unknown | https://www.runromethemarathon.com/ |
| Cervia Marathon | 1ª edizione (2027) | 42.195 | 2027-03-21 | unverified | https://cerviarun.it/ |

- Run Rome The Marathon source URLs: https://www.runnersworld.com/it/news/a71106184/roma-maratona-corsa-27-marzo-2027-iscrizioni/, https://www.runromethemarathon.com/
- Cervia Marathon source URLs: https://www.ravennatoday.it/sport/prima-cervia-marathon-programma-21-marzo-2026.html, https://www.runnersworld.com/it/eventi/gare/a73592833/calendario-maratone-italia-2027/, https://cerviarun.it/

### un trail en Suisse cet ete

Latency: 7.17s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Swiss Alps 100 Endurance Run | 2027 | None | unknown | unknown | https://www.swissalps100.com/ |
| Swiss Canyon Trail | 2027 | None | 2027-06-04 | unverified | not found |
| Trail Verbier St-Bernard by UTMB | 2027 | None | 2027-07-09 | unverified | not found |
| Engadin Ultra Trail | 2027 | None | 2027-07-16 | unverified | https://engadinultratrail.ch/ |
| Eiger Ultra Trail | 2027 | None | 2027-07-17 | unverified | https://eiger.utmb.world/ |
| Churfirsten Trail Run | 2027 | None | 2027-08-28 | official | https://www.churfirstentrailrun.ch/ |

- Swiss Alps 100 Endurance Run source URLs: https://www.swissalps100.com/
- Swiss Canyon Trail source URLs: https://backmyrun.com/races/swiss-canyon-trail
- Trail Verbier St-Bernard by UTMB source URLs: https://backmyrun.com/races/trail-verbier-st-bernard-by-utmb
- Engadin Ultra Trail source URLs: https://runhub.world/c/ch, https://backmyrun.com/races/engadin-ultra-trail
- Eiger Ultra Trail source URLs: https://runhub.world/c/ch
- Churfirsten Trail Run source URLs: https://www.churfirstentrailrun.ch/, https://backmyrun.com/races/churfirsten-trail-run

### le semi de Lisbonne

Latency: 4.74s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Tranquilidade Semi-Marathon des Découvertes | 13e édition, 2026 | 21.0975 | 2026-11-29 | official | https://www.discoveries-half-marathon.com/fr/infos.html |

- Tranquilidade Semi-Marathon des Découvertes source URLs: https://www.discoveries-half-marathon.com/fr/infos.html, https://www.discoveries-half-marathon.com/fr/inscriptions.html

### Milano Marathon

Latency: 4.02s. Error: none

| Candidate | Edition | Distance (km) | Date | Status | Official URL |
|---|---|---|---|---|---|
| Wizz Air Milano Marathon | 2026 (24th edition) | 42.195 | 2026-04-12 | official | https://www.milanomarathon.it/ |

- Wizz Air Milano Marathon source URLs: https://www.milanomarathon.it/en/the-24th-edition-will-take-place-on-sunday-april-12-2026/, https://www.milanomarathon.it/en/the-date-of-the-next-edition-has-been-confirmed-the-race-will-take-place-on-sunday-april-12-2026/, https://www.mondomilano.it/eventi/sport/milano-marathon-2026, https://www.festivalinitalia.it/en/festival/wizz-air-milan-marathon

## Live Linkup smoke 2026-11-08T21:47:58Z (read-only, no H calls, 3 queries in parallel, deep, timeout 120 s, scrubbed)

Real observed output from one read-only scripted run of `runai.discovery.linkup.discover`
(R2-04 session). Hosts only are recorded below; no keys or private URLs.

### un marathon au printemps en Italie

Hints: distance=marathon, country=Italy. Duration **45.9 s**, no error,
**6 candidates**, all date_status=official and all future at observation time.

| Candidate | Distance (km) | Date | Official/source host | Registration host |
| --- | --- | --- | --- | --- |
| Run Rome The Marathon | null | 2027-03-14 | runromethemarathon.com | join.endu.net |
| Termal Bologna Marathon | null | 2027-03-07 | bolognamarathon.run | — |
| Wizz Air Milano Marathon | 42.195 | 2027-04-04 | milanomarathon.it | — |
| Lake Garda 42 | 42.0 | 2027-04-11 | lakegarda42.com | — |
| Padova Marathon | 42.195 | 2027-04-18 | padovamarathon.com | — |
| Rimini Marathon | 42.195 | 2027-04-18 | riminimarathon.it | — |

registration_access=null (unknown) for all six: site_policy.registration_info
was not on main yet. Registration hosts do not establish access or permission.
A dash means no registration host was supplied in this evidence summary, not
proof that no registration link exists. Null distances remain unknown.

### le semi de Lisbonne

Duration **28.8 s**, **2 candidates**:

| Candidate | Distance (km) | Date | date_status | Source host | Registration host |
| --- | --- | --- | --- | --- | --- |
| Discoveries Lisbon Half Marathon | 21.097 | 2026-11-29 | official | discoveries-half-marathon.com | in.njuko.com |
| EDP Lisbon Half Marathon | 21.097 | 2027-03-07 | unverified | maratonaclubedeportugal.com | — |

The second result's source was not identified as the organizer in this observed
output. Its unverified date **cannot become ready_to_confirm**; do not upgrade
it from historical observations elsewhere in this document.

### a trail in Switzerland this summer

Hints: country=Switzerland. Duration **43.5 s**, **0 candidates**, no error.
This is an honest empty outcome, not permission to invent a race or date.

### Limits and follow-up

Synthetic tests do not prove live readiness. These read-only search results do
not establish registration availability, account/captcha absence, authorization
or prepared checkout states. No H calls were made. Observed latency of roughly
**29–46 s** supports the R2-05 need for background discovery and honest loading
states rather than a shorter timeout or fabricated fallback.

## R3-04 — 2026-11-08 read-only live smoke: "un semi en Espagne"

Run 2026-11-08T23:55:35Z → 23:56:24Z (UTC) through the real guide path:
`GuideEngine.start("un semi en Espagne")` → `runai.app._discovery_hints` →
`runai.discovery.linkup.discover` (Linkup structured search, key from the
environment only, never printed). No H session, no registration/hotel/transport
site was opened. Output below is scrubbed to public organizer hosts and dates.

Parsed hints: `distance=half`, `country=Spain` (the alias "Espagne" now maps to
Spain/ES). One Linkup call, **47.9 s**, 6 raw rows, **4 upcoming candidates**
shown (past-only or unsourced rows dropped). No broadened retry was needed
because the first sourced query was not empty. Reply language `fr`, no error.

| Candidate | Date | date_status | Distance (km) | City | Source hosts (dedup by domain) | Registration host |
| --- | --- | --- | --- | --- | --- | --- |
| Medio Maratón de Sevilla | 2026-12-13 | official | 21.0975 | Seville | mediomaratondesevilla.es, promo.deporticket.com | promo.deporticket.com |
| Media Maratón Ciudad de Getafe | 2027-01-31 | official | 21.0975 | Getafe | mediadegetafe.com | — |
| Hyundai Mitja Marató Barcelona by Brooks | 2027-02-14 | official | 21.0975 | Barcelona | mitjamarato.barcelona | — |
| TotalEnergies Medio Maratón Ciudad de Málaga | 2027-03-07 | official | 21.097 | Málaga | mediamaratonmalaga.com | — |

Chips: four `choose_race` chips (`<name> — <date>`), no "accès inconnu"
suffix. The Seville registration URL was accepted only because it is linked
from the official organizer page and appears in the cited sources; it is a
sourced link, not proof of open registration, authorization or availability.

An earlier same-day diagnostic call (direct `discover`, not through the guide)
returned six Spanish half-marathon candidates (Sevilla, Santa Pola,
Granollers, Getafe, Barcelona, Madrid). Together these show the round-2 "no
race" outcome was not an absence of races. Fixes: country alias
normalisation, distance synonyms in the query (medio maratón / mitja marató /
meia maratona), per-row validation so one malformed row no longer discards the
whole reply, edition year derived from sourced dates, and one broadened
sourced retry (no month window, close distance variants) before any "no race"
answer. Dates still come only from sources; nothing was invented.

## R4-04 — 2026-11-09 offline latency/determinism checks

No live Linkup or H calls were made for this change. The live first-reply p50
target of <=35 seconds is **not measured or established** by these tests.

One discovery now runs its general structured query and an organizer-focused
structured query concurrently, merging rows in request order rather than
completion order. Each query has a 15-second wall-clock budget (or a shorter
caller timeout), including when the app supplies a larger HTTP timeout. A
timeout, connection/transport error, HTTP 429 or HTTP 5xx gets one retry;
other HTTP 4xx and malformed/unsafe responses do not. Two failed attempts can
take about 30 seconds; an engine-level broadened search after an honest empty
result can still increase total first-reply latency. This is not a successful
discovery latency guarantee, and slow providers may now return a timeout.

Nonempty, wholly successful candidate snapshots are cached for 30 minutes,
bounded to 128 normalized-query/hints/date hashes. No credentials form part of
the key. Returned snapshots are defensive copies. Empty, failed and partially
failed searches are not cached. `clear_cache()` resets process-local snapshots;
tests inject the monotonic clock to verify expiry without sleeping.

Offline evidence: barrier-based fake HTTP handlers prove both queries overlap
and preserve result ordering when completion order reverses. Additional fakes
verify wall-clock cancellation, exactly one transient retry, no auth retry,
cache hits/expiry/eviction/isolation and non-caching of empty/error/partial
responses. No partial candidate progress is emitted: the guide/discovery
interface returns a final list/turn, not a partial-turn callback or stream.

Final full offline check:

```text
All checks passed!
1152 passed, 1 warning in 14.12s
```
