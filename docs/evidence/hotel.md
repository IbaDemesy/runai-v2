# Hotel site evidence: R2-02 (supersedes R1-06)

The R1 "assumed" rows (Accor default, Hilton homepage) are **withdrawn**. Accor is explicitly
denied in `docs/site-policy.json`. Hilton is prohibited by its terms ("You will not use any robot,
spider, other automatic device..."). See `docs/evidence/site-policy.md` for every reviewed terms URL and quote.

## Executable hotel adapters (reviewed 2026-11-08, expire 2027-02-06)

| Adapter | Policy | Destinations with reviewed public IDs | Deep link (observed vs unverified) |
|---|---|---|---|
| NH Hotels `www.nh-hotels.com/es/booking/step1-rates` | allowed_owner_rule (no agent clause; copying restricted) | Lisbon (PT11.LIBER) | **Observed** 2026-11-08: Lisbon 13→15 Mar 2027, 1 adult, 6 room categories with prices, no login/captcha/form submission. |
| IHG `www.ihg.com/redirect?path=rates` | allowed_owner_rule | Lisbon (LISPO) | **Observed** 2026-11-08: Lisbon 13→15 Mar 2027, 1 adult, 8 room options. Month is zero-based (`022027` = March 2027). |
| Meliá `www.melia.com/en/booking/destination-results` | allowed_owner_rule | Lisbon | **Observed** 2026-11-08: 3 hotels for 13→15 Mar 2027, 1 adult. The cookie banner was left untouched. |

Adapters are tried in registry order. A destination without reviewed place IDs raises `ValueError`
("no policy-reviewed hotel site for this trip"), and the step is blocked with a manual handoff. There is no
silent fallback. Other hotel chains whose terms show no prohibition (Radisson, Barceló, Leonardo, Meininger,
a&o, Scandic, H10, RIU, Iberostar, Catalonia, Eurostars, Novum, B&B, Premier Inn) are policy-allowed. However,
they have **no verified deep link** yet, so they are not executable. Unverified: the pass-2 research found no
complete destination+dates+party result URL for them.

## Task contract

- The deep link encodes the confirmed `arrival_date`/`departure_date`, travelers and destination. The builder
  never uses today/default dates or swaps the dates. Arrival must be ≤ race date < departure, and `nights` must match.
- Ready = a **selected available room and rate** showing the exact stay, party and total price, before guest data.
  The results list, a homepage or an unselected room are not ready. Blocked = no inventory, wrong dates, login,
  captcha, consent, a payment/guest form, or a redirect off `allowed_hosts`.
- `max_steps` = 80. `expected` and `allowed_hosts` come from the reviewed policy.

## Not yet observed

No live H hotel run has happened in R2-02. Room/rate selection and the correct-date safe stop are
**unverified** until R2-03's no-share runtime runs the integrated tree. Unit tests prove task construction only.

## Round 3 (R3-01)

### Live check 2026-11-09

One real H hotel session, concurrent with the single transport session; **two total H runs,
no retries**. Owner-approved read/prepare-only instructions, 40-step cap. Case: Milano
Marathon, Milan, Italy, race 2027-04-04; from Paris, stay 2027-04-03..05, 2 nights,
1 traveler, EUR450 whole-stay budget. Secret supplied only through exec environment;
no session/share/trace URLs, tokens or personal data logged or added to this repository.

- Task: `ihg-com`, public host `www.ihg.com`. Start template:
  `https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest={city_query}%2C%20{country}&qCiD={arrival_day}&qCiMy={arrival_monthyear0}&qCoD={departure_day}&qCoMy={departure_monthyear0}&qAdlt={travelers}&qChld=0&qRms=1`.
  Filled query: Milan/Italy, day 03/month-year 032027 to day 05/month-year 032027, 1 adult.
- Counts: **11 step_progress events, 10 frames**. Progress count is the exposed client
  count (session-start plus observation events), **not** an independently measured H
  action/step count; the runner does not return that metric. Maximum allowed steps: 40.
- Final runner status: **failed**, exact reason **“H session failed”**. Reason-code-like
  classification: **session_failed**. No safe final public site URL retained by the
  strict public-URL filter; no opaque booking/session URL is reproduced.
- Last two real frames reviewed: IHG **“Add Extras / Upgrade your room”**, showing an
  optional next-tier room for +39 EUR/night; then an almost empty IHG page. Neither frame
  establishes exact stay, selected room/rate and whole-stay total. **Not READY**; operational
  outcome is a blocked handoff due to session failure, not evidence of no inventory.
- In-session-only images outside the repo:
  `/home/ubuntu/r3live-hotel-last-1.png`, `/home/ubuntu/r3live-hotel-last-2.png`.
  The throwaway runner and sanitized count/result summary are also outside the repo.

The task prohibited forms, login, consent acceptance, booking, payment and personal data.
No such action is evidenced by the retained frames or sanitized result. Action traces were
not retained, so this is not an independent audit of every browser action or proof of a
safe pre-payment selection. No new attempt was made after the two-run cap was used.

### STEP 3b follow-up — 2026-11-09

- **2026-11-09 — www.hotel-bb.com** — verified template:
  `https://www.hotel-bb.com/en/hotel/freiburg-nord?arrival_date={arrival_mdy_slash}&departure_date={departure_mdy_slash}&rooms={travelers}&destination={place_name}`.
  Freiburg/Freiburg im Breisgau map to Freiburg-Nord. January 9–11 2027, **1 adult**:
  page shows **B&B HOTEL Freiburg-Nord**, **Tullastraße 87c, 79108 Freiburg, Germany**,
  **“1 room | 1 adult | From 09 Jan. 2027 to 11 Jan. 2027”** and double/twin rooms with
  public SUPERSAVER €108.15 and FLEX €119.70, date-by-date prices and Select controls.
  No room/rate selected; no booking, forms, login or consent acceptance. This is an
  in-city rate list, **not** selected-room or safe-stop evidence. Screenshot in-session
  only: `/home/ubuntu/r3b-bb-freiburg-1.png`.
- B&B terms reread at `https://www.hotel-bb.com/fr/conditions-utilisation`, especially
  sections 5, 7, 15. No express robot/agent/scraping ban found; section 15 restricts
  reproduction/copying/code downloading and exploitation without permission. Existing
  owner-rule decision retained; review 2026-11-09, expiry 2027-02-07, in-session screenshots.
- **One adult only:** the attempted public search query `rooms[0][adults]=2` still
  displayed **1 adult**. No two-person capability claimed. Adapter `traveler_counts:[1]`
  safely excludes larger parties; they retain IHG fallback and its in-city limitation.
  Lookup-table requirement restricts this fixed-property URL to the verified Freiburg aliases.
- Actual empty-search text observed: **“No hotels match your search criteria.”** on
  `/en/search` with Freiburg/date/room parameters. This is a rejected search encoding,
  not proof Freiburg-Nord was sold out; no property-specific sold-out message observed here.
- **2026-11-09 — Premier Inn rejected**, Freiburg City Süd property with
  `INdd=09&INmm=01&INyy=2027&OUTdd=11&OUTmm=01&OUTyy=2027&NIGHTS=2&ADULT1=1&CHILD1=0&ROOMS=1`:
  in-city address and **1 Erwachsener, 1 Zimmer**, but no exact-date room/rate result list.
  No adapter added. Stopped after the second hotel candidate succeeded for one adult.
- No additional Lausanne candidate verified in this time box; previous IHG neighboring-city
  limitation remains. Do not describe Lausanne as verified in-city hotel inventory.

Research date: **2026-11-09**. Normal Chrome via Playwright/CDP, **not H**. Only public URLs
were opened/read. No search forms, account creation, consent acceptance, guest details or bookings.
Cookie banners were left untouched. No captcha or login wall on the accepted search/rate pages.
The NH cookie overlay remained visible; no consent was accepted. These are search/rate-page
observations, **not selected-room/selected-rate safe-stop or H success evidence**.

### Verified templates

**IHG-city** (`www.ihg.com`, query-only placeholders; generic, restricted to IT/PT/ES/CH/DE):

```text
https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest={city_query}%2C%20{country}&qCiD={arrival_day}&qCiMy={arrival_monthyear0}&qCoD={departure_day}&qCoMy={departure_monthyear0}&qAdlt={travelers}&qChld=0&qRms=1
```

Each dated line below uses **IHG-city** above, check-in **2027-01-09**, check-out **2027-01-11**,
tested separately for **1 and 2 adults**, one room. The URL uses `qCiMy=qCoMy=002027`
(January is zero-based); the rendered search header showed `09/01/2027 → 11/01/2027`
and `1 Room, 1 Guest` / `1 Room, 2 Guests`. Redirect remained on `www.ihg.com`, at
`/hotels/gb/en/find-hotels/hotel-search`. These links require no reviewed place IDs.

| Date | Chain/host + template | Destination shown | Observed results / limitation |
| --- | --- | --- | --- |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Milan, Italy | 10 hotels; Hotel Indigo Milan and Holiday Inn Milan, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Lisbon, Portugal | 16 hotels; Convent Square Lisbon and Holiday Inn Express Lisbon, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Valencia, Spain | 2 hotels; Holiday Inn Express Valencia, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Zurich, Switzerland | 8 hotels; Ruby Mimi Hotel Zurich and Crowne Plaza Zurich, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Geneve, Switzerland | 4 hotels; Ruby Claire Hotel Geneva and InterContinental Geneve, with From prices. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Lausanne, Switzerland | 18 hotels, but visible properties were in Geneva (~31 miles away), **not proof of an available Lausanne hotel**. |
| 2026-11-09 | IHG / www.ihg.com / IHG-city | Freiburg im Breisgau, Germany | 1 hotel, Holiday Inn Express Ringsheim (~17.66 miles away), **not an available Freiburg city hotel**. |

The latter two links preserve the destination, dates and party, but cannot be called successful
in-city hotel preparation. Adapter instructions explicitly require checking the actual hotel's
city and blocking rather than substituting Geneva/Ringsheim. Generic free-text search does not
guarantee inventory or reviewed successful hotels in every city in those countries, nor coverage
outside these five verified countries. Other country codes remain unsupported.

- **2026-11-09 — IHG-city empty/error observation**: `Longyearbyen, Norway`, January 9–11,
  2 adults: `0 Hotel Found. An error has occurred. Please contact your nearest reservation office
  and a representative will be able to assist you.` Norway is not in the adapter's country list.
  This is an observed error/empty response, **not a clean sold-out inventory message**.

No clean sold-out IHG message was established for an otherwise working city search. See the
registry's blocked evidence; any
empty result, mismatched dates/party, unavailable matching-city hotel, captcha, login, consent,
form submission or unreviewed redirect is a blocker.

Screenshots of the rendered search headers (both party sizes for all seven cities):
`/home/ubuntu/r3-hotel-ihg-{Milan,Lisbon,Valencia,Zurich,Geneva,Lausanne,Freiburg-im-Breisgau}-{1,2}.png`.
These in-session screenshots are outside the repository and must not be published.

**NH-rates** (`www.nh-hotels.com`, existing Lisbon adapter retained ahead of IHG):

```text
https://www.nh-hotels.com/es/booking/step1-rates?destinationId={place_name}&fini={arrival_dmy_slash}&fout={departure_dmy_slash}&gvoucher=false&hotelId={place_id}&nadults1={travelers}&nbabies1=0&nchilds1=0&pcode=
```

- **2026-11-09 — NH / www.nh-hotels.com / NH-rates**: Lisbon, `PT11.LIBER`,
  `2027-01-09..2027-01-11`, separately **1 and 2 adults**. NH Collection Lisboa Liberdade,
  `Jan 9-Jan 11`, `1 adulto / 1 habitación` / `2 adultos / 1 habitación`, six available
  room categories with prices. Existing Lisbon/Lisboa/Lisbonne place aliases retained.
- **2026-11-09 — NH / www.nh-hotels.com / NH-rates**, supplemental verified property:
  Milan, `ITMI.TOURI`, `2027-01-09..2027-01-11`, separately **1 and 2 adults**.
  NH Collection Milano Touring, exact dates/party, eight/five available room categories with
  prices respectively. Not added as a new place adapter, to leave generic IHG first for Milan.
  Screenshot: `/home/ubuntu/r3-hotel-nh-milan-2.png` (in-session only, not for publication).
- **2026-11-09 — NH no-inventory observation**: same Milan property/dates, **9 adults**,
  `Lo sentimos, no hay disponibilidad para estas fechas`; followed by
  `Recomendamos cambiar las fechas o buscar una alternativa en estos hoteles` and
  `Modificar fechas`. No form was submitted or dates changed.

### Terms reread and rejected candidates

- **2026-11-09 — NH**: reread `https://www.nh-hotels.com/en/legal-notice`, sections 2
  (User Responsibilities), 3 (Monitoring), 9 (Intellectual Property). Copying/use/load restrictions
  remain; no express bots/agents/scraping prohibition found. Retain the existing owner's
  read-only rule, not a claim of express contractual permission.
- **2026-11-09 — IHG**: reread `https://www.ihg.com/content/gb/en/customer-care/tc.html`,
  LIMITED LICENCE TO VIEW AND COPY, PROHIBITED CONDUCT and INTELLECTUAL PROPERTY RIGHTS.
  Non-commercial individual use/copying restrictions remain; no express bots/agents/scraping
  prohibition found. Retain the existing owner's read-only rule and in-session-only screenshots.
- **2026-11-09 — Meliá**: Lisbon results with exact January 9–11 dates and 1/2 adults did render
  two available hotels and prices. A property showed `This hotel has no availability on this date`.
  However, rereading `https://www.melia.com/en/legal-notice`, section 5 Links, found:
  “No deep-links or IMG or image links, nor frames with website pages will be allowed without
  the express permission of Meliá.” **Executable adapter withdrawn**, not replaced. No express
  automated-agent prohibition found; retain the existing policy decision only for ordinary
  read-only navigation, not permission to issue booking deep links.
- **2026-11-09 — NH generic routes**: `/en/booking/step1-hotels` and other guessed routes
  returned 404 / NoSuchKey; rejected. Only the reviewed Lisbon property adapter remains executable.
- **2026-11-09 — Radisson**: tested Lausanne route rendered “Sorry, something went wrong.
  This is almost certainly not the page you were looking for.” Rejected; no adapter added.
- **2026-11-09 — B&B Hotels**: Lausanne Crissier showed Jan 9–11, two nights, room/rate prices,
  but tested party parameters did not reliably change **1 adult** to 2. Rejected; no adapter added.
  A deliberately wrong date encoding showed “This hotel is fully booked for these dates.” and
  “This hotel is fully booked from 01 Sep. 2027 to 01 Nov. 2027 for 1 room · 1 adult.”
  That is not evidence for January availability or a working two-adult adapter.

NH/IHG/Meliá review dates refreshed to 2026-11-09, expiry 2027-02-07. No prohibited
chain was relaxed. Accor remains denied. No H sessions were created in this research.

## R4-02 normal-Chrome research — 2026-11-09 (offline, no H)

Public deep-link checks used 2027-01-09 to 2027-01-11, one adult, one room.
Terms and authorization caveats are recorded in site-policy.md. No selected
room/rate, guest-details boundary or new READY state was reached in this research.

### IHG extension

Verified the existing public template (values URL-encoded):
`https://www.ihg.com/hotels/gb/en/find-hotels/hotel/list?qDest={city},%20{country}&qCiD=09&qCiMy=002027&qCoD=11&qCoMy=002027&qAdlt=1&qChld=0&qRms=1`.
It redirects to /hotel-search. January is month 00, not 01. Rendered date/party
controls were inspected as well as result text, not inferred from URL parameters.

| Query | Rendered result | Decision |
| --- | --- | --- |
| Amsterdam, NL | 16 hotels, public From prices | Add NL search coverage; check actual property city |
| Den Haag, NL | 10 hotels, public From prices | Search coverage, not every result in Den Haag |
| Brussels, BE | 16 hotels, public From prices | Add BE |
| Vienna, AT | 10 hotels, public From prices | Add AT |
| Prague, CZ | 2 hotels, public From prices | Add CZ |
| Paris, FR | 21 hotels, public From prices | Add FR |
| London, GB | 93 hotels, public From prices | Add GB |
| Barcelona, ES | 10 hotels with prices | Existing country, reviewed query |
| Rome, IT | 8 hotels with prices | Existing country, reviewed query |
| Seville, ES | 10 results; first Jerez de la Frontera 79.37 km away, neighboring-country warning | NO demonstrated in-city inventory; must block if no matching city property |
| Savognin, CH | AlpenGold Davos Dorf, 30.92 km away, From USD541 | NO demonstrated in-city inventory |
| Grindelwald, CH | 31 results; first Kriens 48.92 km away, neighboring-country warning | NO demonstrated in-city inventory |
| Sierre, CH | Crans-Montana 5.44 km and Sion 14.64 km; one link leaves IHG | NO demonstrated in-city inventory; unreviewed external host remains forbidden |

These are all search-list observations, not selected full-stay totals or promises
of availability within EUR450. A successful offline build for a mountain town or Seville
does not permit a distant hotel to pass the unchanged strict city check.

### B&B fixed-property extension (one adult ONLY)

Public pattern:
`https://www.hotel-bb.com/en/hotel/{literal-property-slug}?arrival_date=01%2F09%2F2027&departure_date=01%2F11%2F2027&rooms=1&destination={reviewed-name}`.
Property slugs are literal paths, not user-filled path parameters. Each adapter is
restricted to its reviewed city aliases and country. Existing Freiburg-Nord stays intact.
Two-adult encoding remains unverified; no larger party is added.

| Property slug | Destination value | Exact-date, one-adult result |
| --- | --- | --- |
| milano-sant-ambrogio | milano-sant-ambrogio | Milan public room/rate list and Select controls |
| paris-porte-des-lilas | Paris | Paris public room/rate list and Select controls |
| bruxelles-centre-gare-midi | bruxelles-centre-gare-midi | Brussels public room/rate list and Select controls |
| wien-hbf | wien-hbf | Vienna public room/rate list, Room Only public EUR110 / cancellable EUR130 displayed |
| prague-city | prague-city | Prague public room/rate list, CZK3264 displayed |
| birmingham-centre | birmingham-centre | Birmingham public room/rate list and Select controls |
| valencia-ciudad-de-las-ciencias | same slug | Guessed property returned 404; NOT wired |

Each successful property showed `1 room | 1 adult | From 09 Jan. 2027 to 11 Jan. 2027`.
Displayed prices are observations of public rate cards, not verified whole-stay
selected totals. Member prices/sign-in were not used; Select forms were not submitted.
B&B supplies a second site for sampled IT/FR/BE/AT/CZ/GB cities, not all cities in
those countries. Birmingham is NOT a London hotel. No NL second-site link verified.
B&B country/city directories were read to identify properties (Netherlands, Vienna,
Prague, Brussels, Birmingham); directory pages alone were not made executable.

### Rejected hotel trials

All attempts below used the same January dates and one adult unless noted.

- NH /es/booking/step1-rates with `destinationId={city}&fini=09/01/2027&fout=11/01/2027&gvoucher=false&hotelId={id}&nadults1=1&nbabies1=0&nchilds1=0&pcode=`:
  Barcelona ESBA.CALDE, Valencia ESVL.COVAL, Seville ESSE.CONSE, Amsterdam NLAM.ZUID,
  The Hague NLZH.DENHA, Rome ITRM.LEONA, Brussels BEBR.ATL, Vienna AT09.WIEN,
  Prague CZPR.PRAGU, Paris FR75.CHAMP, London GBLO.WLOND.
  All showed `Lo sentimos, no hay disponibilidad para estas fechas`; some did show
  the named property and Jan 9–Jan 11/one adult, others only an empty shell.
  No rate-list proof: none of these guessed mappings added. Existing Lisbon remains.
- Radisson /en-us/search?searchTerm=Amsterdam&checkInDate=2027-01-09&checkOutDate=2027-01-11&adults[]=1&children[]=0:
  not-found/search UI rather than applied-date rates; no adapter.
- Meininger public booking attempt on mmb.meininger-hotels.com: ERR_TOO_MANY_REDIRECTS;
  no challenge bypass or cookie manipulation; no adapter.
- Scandic /en/book?checkin=2027-01-09&checkout=2027-01-11&adults=1&city=Amsterdam:
  PAGE NOT FOUND and default Nov 9–10 controls; no adapter.
- H10 attempted booking route redirected /en/not-found (Error 404); no adapter.
- Catalonia /en/search?destination=Barcelona&arrival=2027-01-09&departure=2027-01-11&adults=1:
  login/cookie UI, no verified exact-date public rate list; commercial hyperlink
  permission also unresolved; no adapter.
- Leonardo /amsterdam?arrival=2027-01-09&departure=2027-01-11&adults=1:
  city hotel list/prices, but Nov 9–10 and 1 Room, 2 Guests remained in controls.
  Query ignored, not an exact-date adapter; no adapter.
- Barceló attempted booking URL returned 404; no verified public pattern retained.

### IHG READY instruction correction

The R3 navigation reached Add Extras / select-enhance-stay after room/rate selection
and then ran out of steps; it did NOT prove a completed READY stop. The new registry
evidence and hotel task instructions say to STOP and report READY immediately on that
review page ONLY when selected room AND rate, matching city, exact dates, party and
full-stay total are all visible, before guest details. Earliest safety boundary still
wins. A page title, result list or partial summary is insufficient. Other hotels use
their own selected-room review boundary, not an invented IHG page.
