# Transport site evidence — R1-06

Offline task-builder delivery only. No homepage, robots.txt, terms page, search,
fare or checkout was inspected. All site-flow claims are **assumed**, not observed.
No live H runs occurred. These official-site allowlists do not grant automation
authorization; authorization review remains a prerequisite to execution.

| Site | Public flow | Safe stop page | Bot protection / captcha | Automated-agent terms |
| --- | --- | --- | --- | --- |
| Trenitalia — https://www.trenitalia.com | assumed: stations/dates search and fare selection | assumed: before passenger details, login or payment | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |
| SBB — https://www.sbb.ch | assumed: route search and ticket selection | assumed: before passenger details, login or payment | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |
| SNCF Connect — https://www.sncf-connect.com | assumed: route search and fare selection | assumed: before passenger details, login or payment | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |
| Renfe — https://www.renfe.com | assumed: route search and fare selection | assumed: before passenger details, login or payment | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |
| CP — https://www.cp.pt | assumed: route search and ticket selection | assumed: before passenger details, login or payment | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |
| DB — https://int.bahn.de | assumed: route search and fare selection | assumed: before passenger details, login or payment | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |
| Google Flights — https://www.google.com/travel/flights | assumed: read-only round-trip search and carrier links | assumed: search-results carrier handoff, not carrier checkout | assumed: challenges may block; not tested; stop, no workarounds | assumed: permission unverified; review current terms and authorization |

For every site, stop even earlier if continuing requires consent, account
creation, personal-data or booking form submission, or personal data.
Dismissal is not consent acceptance. Public search fields, pressing Search and
noncommitting fare selection are allowed.

## Routing and evidence limitations

Domestic IT/CH/FR/ES/PT/DE uses the country's official rail site. Bidirectional
FR–IT and CH–IT use Trenitalia; FR–CH and DE–CH use SBB; DE–FR uses DB.
Other pairs use read-only flight search. These are heuristics, not observed
timetables: confirm actual routes, service and dates or report blocked.
Explicit origin_country takes priority over the small documented city lookup;
unknown origins default conservatively to flights. Countries accept English
names or two-letter codes. No carrier is automatically selected for flights.

Offline tests cover Milan, Lisbon, Zermatt, Reykjavik, New York, all domestic
operators, bidirectional cross-border rules, unknown origins and guardrails.
They prove task construction only, not inventory, fares, authorization or live
success. Visually unverified. Future approved evidence must record dated public
start/end URLs and actual safe stop or blocker without private session details.
