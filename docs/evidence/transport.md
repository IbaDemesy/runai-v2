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
