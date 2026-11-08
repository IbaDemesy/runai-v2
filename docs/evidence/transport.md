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
