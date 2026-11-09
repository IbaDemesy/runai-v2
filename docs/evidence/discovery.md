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

## R4-04 — 2026-11-09 offline latency/determinism checks (step 3 snapshot)

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

## R4-04 — 2026-11-09 live Linkup-only smoke (step 4)

Two smoke runs total. Both used `PYTHONPATH=.` from the repository root,
`GuideEngine.start` → `runai.app._discovery_hints` →
`runai.discovery.linkup.discover(timeout_s=120)`. The Linkup key was bound
only through the execution environment, never printed or written to disk.
No H calls, race-site interaction, account creation, forms or purchases.
Each run used a fresh cache and executed the requests sequentially in one
process; the fourth request repeated the first. HTTP request hooks counted
actual provider requests, including retries, without logging URLs or headers.

### Run 1 — deep / 15-second attempt cap — failed

2026-11-09T01:32:48Z–01:34:49Z:

| Request | First-reply seconds | Linkup calls | Candidates | Result |
| --- | ---: | ---: | ---: | --- |
| un marathon au printemps en Italie | 30.145 | 4 | 0 | discovery_failed |
| un trail en Suisse cet été | 30.159 | 4 | 0 | discovery_failed |
| le semi de Lisbonne | 30.162 | 4 | 0 | discovery_failed |
| un marathon au printemps en Italie (repeat) | 30.121 | 4 | 0 | discovery_failed |

Cache entries: 0; cache repeat identical: **no** (no candidates, no cache hit).
The repeated ~30-second/four-call pattern is consistent with exhausting two
15-second attempts per query; this first script recorded the guide error,
not individual provider exception types. These failures do not count toward
a successful discovery latency claim. The initial cap was unsuitable.

### Run 2 — standard / 35-second attempt cap — successful sourced replies

Changed query depth to `standard`, retaining structured output and all source,
date, URL and unsafe-response validation. Increased the attempt cap to 35
seconds to avoid the prior overly short deadline; caller-specified shorter
timeouts are still honored. A retry can exceed 35 seconds overall.

2026-11-09T01:35:00Z–01:35:15Z:

| Request | First-reply seconds | Linkup calls | Candidates | Guide error |
| --- | ---: | ---: | ---: | --- |
| un marathon au printemps en Italie | 4.568 | 2 | 2 | none |
| un trail en Suisse cet été | 5.619 | 2 | 4 | none |
| le semi de Lisbonne | 4.586 | 2 | 3 | none |
| un marathon au printemps en Italie (repeat) | 0.014 | 0 | 2 | none |

Cold-request sample p50: **4.586 seconds** across the three distinct requests,
excluding the cache hit. No provider exception was reported in run 2. Cache
entries: 3. Repeat candidate ids identical: **yes**, in the same order:
`wizz-air-milano-marathon-2027`, `run-rome-the-marathon-32nd-edition`.

Returned candidates (source domains only; null/conflicting dates preserved):

| Request | Race | Date | date_status | Source domains | Registration | Hotel | Transport | Origin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Italy | Wizz Air Milano Marathon | 2027-04-04 | official | www.fidal.it, www.milanomarathon.it | unknown | true | true | Paris |
| Italy | Run Rome The Marathon | null | unknown | www.runnersworld.com, www.runromethemarathon.com | unknown | true | false | Paris |
| Switzerland | Stoos-Trail | 2027-07-10 | official | www.stoostrail.ch | unknown | true | false | Paris |
| Switzerland | Scuol trail running event | 2027-06-26 | unverified | guide.swiss-running.ch | unknown | true | false | Paris |
| Switzerland | Klosters trail running event | null | conflicting | guide.swiss-running.ch | unknown | true | false | Paris |
| Switzerland | Churfirsten Trail Run | 2027-08-28 | official | www.churfirstentrailrun.ch | unknown | false | false | Paris |
| Lisbon | Discoveries Lisbon Half Marathon | 2026-11-29 | official | www.discoveries-half-marathon.com | unknown | true | true | Paris |
| Lisbon | Tranquilidade Semi-Marathon des Découvertes (Meia Maratona dos Descobrimentos) | 2026-11-29 | official | www.discoveries-half-marathon.com | unknown | true | true | Paris |
| Lisbon | EDP Lisbon Half Marathon | null | unknown | www.running-portugal.com | unknown | true | true | Paris |

`official` is the discovery normalizer's classification of provider-returned
source dates/hosts, not a separate manual verification of organizer pages.
The two Discoveries names appear to describe the same event; distinct names
were not deduplicated by the current name/edition key. The named Lisbon request
also returned a different Lisbon half, while EDP's date remained unknown;
this is not proof that the intended EDP edition is ready to prepare.
Preparation booleans describe policy adapter coverage, not inventory or
availability. Registration stayed unknown because P8 coverage is unavailable
on this branch. No race was confirmed and nothing was prepared.

This small live sample meets the <=35-second p50 target for these three
requests only; it does not establish sustained throughput, six-concurrent-
search behavior, generic source completeness, or live preparation success.

Post-tuning offline checks:

```text
All checks passed!
1152 passed, 1 warning in 14.33s
```

## 2026-11-09 — R5-04 live smoke

Read-only Linkup through `GuideEngine` → `runai.app._discovery_hints` →
`runai.discovery.linkup.discover`, run from an external scratch script. No H
sessions, confirmation actions, bookings or preparation launches. Only public
race data was recorded. These are discovery-ready drafts, not prepared bookings.

Latest attempt per case below. Steps count **follow-up** user messages/clicks;
add one to include the initial request. Therefore Portugal's first successful
attempt took seven total inputs and missed the <=6-total-input target.

| Case | Attempt | First reply (s) | Follow-ups / total inputs | Ready | Race / date / status | Public source hosts | Origin |
|---|---:|---:|---|---|---|---|---|
| Milan | 3 | 3.47 | 3 / 4 | yes | Wizz Air Milano Marathon / 2027-04-04 / official | runhub.world, www.milanomarathon.it | Paris |
| Barcelona winter half | 1 | 74.78 | 4 / 5 | yes | Hyundai Mitja Marató Barcelona / 2027-02-14 / official | www.mitjamarato.barcelona | Paris |
| Swiss summer trail | 1 | 3.78 | 3 / 4 | yes | Stoos-Trail / 2027-07-10 / official | www.stoostrail.ch | Geneva |
| Netherlands spring 10K | 1 | 8.92 | 4 / 5 | yes | Groet uit Schoorl Run / 2027-02-14 / official | www.groetuitschoorlrun.nl | Paris |
| Portugal spring half | 3 | 72.97 | 6 / 7, stopped | **no** | no selected race | — | — |
| A03 Lisbon → Berlin | 2 | 3.93 | 5 / 6 | yes | GENERALI BERLIN-MARATHON / 2027-09-26 / official | www.bmw-berlin-marathon.com, www.generali-berlin-marathon.com, www.scc-events.com | Paris |
| A08 Milan → Paris | 3 | 0.09 | 3 / 4 | yes | Wizz Air Milano Marathon / 2027-04-04 / official | runhub.world, www.milanomarathon.it | Paris |
| A16 Milan → Lyon → Brussels | 3 | 0.09 | 4 / 5 | yes | Wizz Air Milano Marathon / 2027-04-04 / official | runhub.world, www.milanomarathon.it | Brussels |

No identical consecutive assistant turns in any attempt (comparison used message,
candidate IDs and chip kind/value, excluding turn-specific chip IDs). All cases
stopped without confirmation. A08/A16 reused the in-process live Milan cache;
their first-reply latency is warm-cache latency, not provider network latency.

Initial Milan requests returned empty results twice. Adding year/local city
aliases to named search prompts produced sourced Milan results on attempt 3;
this observation does not isolate the prompt change from provider variability.
A03 initially failed, then reached ready on attempt 2 using a deep official-date
alternative search. New offline regressions cover empty delegated-search
escalation, unknown-date recovery, unverified delegated-search escalation and
the named prompt after app hint mapping. Recovery now prioritizes explicitly
sourced organizer dates; missing dates are never inferred.

Portugal remains a blocker: attempt 1 reached ready after six follow-ups, with
EDP Meia Maratona de Lisboa, 2027-03-07, official, source host
maratonaclubedeportugal.com, Paris origin, and a sold-out/waitlist warning.
Attempt 2 stalled on unverified-only candidates; attempt 3 encountered provider
errors and stopped after six follow-ups despite an intermediate official-date
result. No fourth attempt was made. It is not a repeatable live success.
Netherlands returned a February date after broadening a spring request; readiness
does not establish that the original seasonal preference was satisfied.

Seven of eight latest attempts reached ready, all within six total inputs;
the Portugal case did not. Slow cold responses (~73–75 seconds), fallback-season
quality, and Portugal reliability need follow-up. The successes were collected
across incremental fixes, not a fresh all-eight run on the final revision. This
small sample proves neither generic live readiness nor H preparation. UI
presentation was not visually verified.

## R6-04 — Linkup-only live smoke (2026-11-09)

One complete five-request batch, **05:38:23–05:59:06 UTC** on 2026-11-09,
after `be0e50d`. No second or third batch, no code changes during the smoke.
Real `GuideEngine` → `runai.app._discovery_hints` →
`runai.discovery.linkup.discover(..., timeout_s=120)`, using the environment
credential only. Run from the repository root with `PYTHONPATH=.`. No app
server, H sessions, confirmation, submissions, accounts, consent or purchases.
The runner and scrubbed incremental JSON were kept outside the repository
(`/home/ubuntu/r604_linkup_smoke.py` and
`/home/ubuntu/r604_linkup_smoke_results.json`), not committed.

Each mission cleared the discovery cache before starting. First-reply timing
covers `GuideEngine.start`, including any standard fallback lookup. Every later
input selected exactly the first offered chip, stopping at `ready_to_confirm`
or ten **total inputs including the initial request**. No confirm chip was
clicked. No identical consecutive assistant turns were observed, comparing
message, question, candidate names/dates/distances/statuses and chip kind/value,
excluding transient chip IDs. No sensitive values or raw provider bodies recorded.

### Results

| Initial request | First reply (s) | First candidates | Inputs to ready | Total journey (s) | Final official-date race | Identical consecutive turns |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| I'd love to run a big marathon in Germany next autumn | 7.865 | 1 | 8 | 359.082 | Jungfrau-Marathon, 2027-09-11 (**Switzerland**, not Germany) | 0 |
| un semi-marathon au Portugal | 7.074 | 4 | 5 | 7.095 | Hyundai Porto Half Marathon, 2027-09-19 | 0 |
| un marathon au printemps en Italie | 13.231 | 4 | 9 | 504.777 | Generali Genève Marathon, 2027-05-08 (**Switzerland**, not Italy/Milan) | 0 |
| le marathon de Berlin | 7.933 | 1 | 7 | 148.578 | Generali Genève Marathon, 2027-05-08 (**not Berlin**) | 0 |
| a marathon in October | 13.046 | 2 | 7 | 223.724 | Lausanne Marathon, 2027-10-24 (October retained) | 0 |

**First-reply p95 = 13.231 s**, nearest-rank method:
sort five observations and take `ceil(0.95 × 5) = 5`, the maximum.
All five first replies meet the ≤20 s target; five samples are not a sustained
latency guarantee. All first-reply provider invocations used `standard` (nine
invocations including fallbacks). Later turns used `deep` (17 invocations).
There were 26 guide-level discovery invocations in total, including nine
`DiscoveryTimeout` failures. These are not HTTP-request counts: discovery issues
paired searches and may retry. Later deep calls frequently consumed ~70 s,
so fast first replies did **not** imply fast complete journeys.

### Candidates and public source evidence

Statuses below are exactly the guide's normalized Linkup output, not independent
verification of the pages or race schedules. `official` is the existing
organizer-source/date rule; `unverified` retains a sourced date without qualifying
official evidence. No status/date was manually upgraded. All candidates were
non-synthetic. Listed dates and distances are provider extractions, not guarantees.

1. **Germany/autumn — first reply:** GENERALI BERLIN-MARATHON,
   2027-09-26, 42.195 km, **unverified**. Sources:
   https://www.visitberlin.de/en/event/generali-berlin-marathon-2027,
   https://marathonguide.com/coach/how-to-enter-the-2027-berlin-marathon/,
   https://aims-worldrunning.org/countries/39.html.
   Later Swiss recovery candidates were all **official**:
   - Jungfrau-Marathon, 2027-09-11, 42.195 km:
     https://www.jungfrau-marathon.ch/de/social-wall.html and
     https://www.faernresorts.com/wengen/events-and-packages-wengen/jungfrau-marathon.
   - Lausanne Marathon, 2027-10-24:
     https://en.lausanne-marathon.com/conseils/dates-de-levenement/.
   - SwissCityMarathon – Lucerne, 2027-10-31:
     https://www.swisscitymarathon.ch/en/event-guide/media/facts-and-figures/.

2. **Portugal half — first reply:**
   - Hyundai Porto Half Marathon, 2027-09-19, 21.0975 km, **official**:
     https://www.porto-marathon.com/en/half.html.
   - Lisbonne Marathon Half Marathon (localized display name), 2027-10-10,
     21.0975 km, **official**:
     https://www.running-portugal.com/lisbon/marathon/en/rules.html.
   - Algarve Marathon Half Marathon, 2026-12-06, 21.0975 km, **unverified**:
     https://www.race-calendar.com/algarve-marathon-marina-de-vilamoura-portugal-on-06-december-2026/154458.
   - EDP Lisbonne Half Marathon, 2027-03-07, 21.0975 km, **official**:
     https://www.running-portugal.com/lisbon/lisbonhalf/en/home.html and
     https://maratonaclubedeportugal.com/en/.
   No additional race candidates appeared later. First-chip selection stayed
   on Porto; neither Funchal nor Gaia was returned, and no ping-pong occurred.

3. **Italy/spring — first reply:** all four were **unverified**, 42.195 km:
   - Run Rome The Marathon, 2027-03-14:
     https://www.infront.sport/news/run-rome-the-marathon-confirmed-through-2031-with-2027-race-set-for-14-march
     and https://marathon-index.com/races/rome-marathon/.
   - Milano Marathon, 2027-04-04:
     https://marathon-index.com/races/milan-marathon/.
   - Padova Marathon, 2027-04-18:
     https://marathon-index.com/races/padova-marathon/.
   - Rimini Marathon, 2027-04-25: FIDAL's sourced 2027 marathon/half calendar
     PDF under https://www.fidal.it/upload/files/Organizzazione/2027/.
   Later recovery returned Generali Genève Marathon, 2027-05-08, 42.195 km,
   **official**, https://www.generaligenevemarathon.com/.
   Milan remained unverified and was **not** the final selected race.

4. **Berlin named — first reply:** Berlin Marathon, 2027-09-26, 42.195 km,
   **unverified**, https://www.berlin.de/en/events/september/.
   Later Swiss recovery candidates were all **official**:
   - Generali Genève Marathon, 2027-05-08, 42.195 km:
     https://www.generaligenevemarathon.com/en.
   - OCHSNER SPORT Zürich Marathon, 2027-04-11:
     https://www.zuerichmarathon.ch/marathon-2/marathon.
   - Gornergrat Zermatt Marathon, 2027-07-03:
     https://guide.swiss-running.ch/en/events/6030 and
     https://www.zermattmarathon.ch/en/our-courses/top20run.
   - Jungfrau-Marathon, 2027-09-11:
     https://www.jungfrau-marathon.ch/en/news.html.

5. **October — first reply:**
   - Yorkshire Marathon Festival, 2027-10-24, 42.195 km, **unverified**:
     https://www.timeoutdoors.com/events/marathons/october.
   - 2XU Long Beach Marathon, no confirmed date, 42.195 km, **unknown**:
     https://www.runlongbeach.com/.
   Later recovery returned **official** Lausanne Marathon, 2027-10-24,
   42.195 km, https://fr.lausanne-marathon.com/contact/contact/ and
   https://en.lausanne-marathon.com/info-coureurs/departs-horaires/;
   and **official** SwissCityMarathon – Lucerne, 2027-10-31,
   https://www.swisscitymarathon.ch/faq/.
   This live request found sourced October dates; it did not exercise the
   October-empty/adjacent-month path (covered offline instead).

### Limits, blockers and next steps

Five missions reached the **draft confirmation gate**, not successful H
preparation. Only Portugal and October retained the original race/country/month
intent; Germany, Italy and named Berlin followed first-chip recovery into
Switzerland. Four journeys exceeded the offline six-input target (but all met
this smoke's ten-input limit). In particular, Germany/Italy/Berlin are **not**
successful completions of their original requests.

Final coverage was partial for Jungfrau and Lausanne (registration unknown,
transport false, hotel true) and Porto (registration unknown, hotel/transport
true). Geneva's coverage modules reported registration covered and hotel/transport
true; this is module coverage, not a live browser/preparation result. No H ran.
Milan registration coverage was unknown in its unverified initial candidate,
so this batch does not establish live Milan registration readiness.

The observed limiting chain is direct: standard source rows for Germany,
Italy and Berlin lacked qualifying organizer-date evidence, so the guide kept
them unverified and led with recovery; later deep timeouts and country recovery
produced slow Swiss alternatives. No dates/verification were fabricated to force
the original requests to pass. Recommended follow-up: improve standard-mode
organizer grounding and preserve original country/race through recovery, then
bound later deep-enrichment latency and rerun the five-case batch. Do not claim
generic live readiness or H success from these results. UI was not rendered.
