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
