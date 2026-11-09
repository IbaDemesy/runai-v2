# Checkout safety correction — 2026-11-09

Every hotel/transport adapter's shared beyond expression and ready-pattern
exclusion now use:
```regex
guest|passenger|/pax|payment|/pay|checkout|/book(?:ing)?/confirm
```
The legacy task fallback uses the same beyond expression. Checkout and guest
forms are forbidden boundaries, not selected-stop success evidence. Regression
tests use the actual unquoted path/query matcher, including encoded checkout,
confirmation paths and unsafe query values on otherwise-ready paths. Existing
task/alternative start URLs match neither ready nor beyond patterns. No runtime
or registration adapter changes, and no live retest in this safety-fix step.

# P11/P12 integration correction — 2026-11-09

Merged origin/main containing R5-01 and reread CONTRACTS.md P11/P12 and hclient
_checkpoint/_checkpoint_matches/force_answer. Patterns match the **unquoted path
+ '?' + query**, never host or fragment. On the first matching observation the
runtime emits the frame and requests force_answer (60-second answer deadline).
Beyond patterns take precedence and cancel with policy_denied. The earlier
requires_selection proposal is removed: the runtime does not implement it.
Neither checkpoint list may match a task's start path/query or an unselected page.
Primary and alternative task tests exercise these boundaries with the merged
runtime helpers, not a separate guessed matcher.

IHG Add Extras is a verified distinct checkpoint. Vueling selectFlight, NS
traintickets-v3 and B&B hotel pages are shared selected/unselected URLs and MUST
NOT be checkpoint patterns. Their remaining distinct review/extras patterns are
explicitly unverified gaps, not claims of successful deterministic stopping.
Their tasks still instruct an immediate safe answer after selection, never
opening passenger/guest details or submitting a form to reach an invented URL.
NH's post-rates pattern remains unverified; required consent means stop with
BLOCKED consent_required.

P12: NS tasks set keep_fragment=true only when both scrub_url of a synthetic
public fragment URL and scrub_text preserve the route/query unchanged, and the
fragment-less URL survives scrubbing unchanged. The merged runtime independently
rechecks this. Direct check of the reviewed NS route returned True from
_safe_start_fragment. Observations still have no fragment for checkpoint matching.
Gateway verification now accepts expected.city OR expected.gateway_city, not a
third city; all dates, party and selection checks remain required.

# R5-02 offline checkpoint contract (2026-11-09)

Optional adapter `checkpoint` has non-empty string lists `url_patterns` and
`beyond_patterns`. Load compiles each regex with IGNORECASE to validate it and
retains plain strings for task JSON. Match using re.search on unquoted path/query
as specified in the integration correction above.
Missing is compatible; malformed, empty, non-string or invalid regex fails closed.
Legacy adapters without this metadata receive an impossible `(?!)` ready pattern
and the generic unsafe boundary; this is not evidence of a selected review page.
Hotel/transport tasks and P7 alternatives carry independent copies. A checkpoint
requires an immediate answer: READY only with complete evidence, else BLOCKED
unsafe_claim. Never navigate beyond; all earlier safety boundaries still win.
The hclient runtime is inherited unchanged from the R5-01 origin/main merge.

All checkpoint patterns exclude URLs containing the shared beyond expression:
`guest[-_/ ]?(?:details|info)|passenger|/pax|payment|/pay`.
Unknown/expired/prohibited policy reviews and Accor remain denied.

City aliases are accent/case-insensitive for countries, place IDs and URL queries.
Expected race/origin strings remain unchanged. Reviewed regional hotel bases:
Stoos/Morschach → Lucerne (Lake Lucerne regional lodging base), Savognin → Chur
(regional transport/lodging base), Grindelwald → Interlaken (valley gateway).
These are desk-reviewed geographic allowances within Switzerland, not observed
hotel inventory, proximity guarantees or included transfers. Search only that
gateway; a property outside both race city and gateway blocks date_mismatch.
No wider neighboring-city substitution is allowed. Transport `via` exposes its
reviewed gateway city without replacing expected.city; the merged P12 runtime
accepts it with the same dates/party/selection requirements. No runtime edits here.

# Site policy review: R2-02

Machine-readable registry: `docs/site-policy.json`, enforced by `runai/agents/site_policy.py`
(`evaluate_url`, `registration_info`). Every H navigation is gated on it before a session starts.

## Review method (2026-11-08)

- Fetched each site's official terms of use/legal notice (HTTP/browser, read-only) on 2026-11-08 UTC,
  quoted the relevant clauses and classified them. robots.txt was **not** used as authorization.
- Reviews expire after 90 days (`expires_at` 2027-02-06). Expired, unknown, future-dated, malformed
  or out-of-purpose scopes fail closed. Host/path matching is exact (no wildcard, no suffix allow);
  only explicit **prohibitions** extend to subdomains (deny-by-suffix).
- Screenshot/live-view scope is a separate field: `in_session_only` means frames are shown to the
  requesting user during the run and are not published as H traces. It does not waive copyright/terms.
- `registration_observations` (account wall/captcha, with source and date) are observations, never permission.

## Decision rule

- `prohibited`: terms explicitly forbid robots/scraping/automated access or reuse → **denied**, including subdomains.
- `allowed_owner_rule`: terms reviewed, no explicit agent prohibition, but materially ambiguous
  (personal non-commercial use/copying clauses, or simply no clause found). **Lead/owner decision, 2026-11-08**:
  "ambiguous (no explicit prohibition found) = ALLOWED, with a dated note citing the terms URL"; read/prepare only,
  stop before payment, no account. The ticket text asked for ambiguous scopes to fail closed; this owner
  override is deliberate and recorded here. `evaluate_url` returns a reason saying so.
- `allowed_read_only`: reviewed terms with no restriction found for that exact scope (Milano Marathon 2027 Njuko event).
- Sites with no review (unknown) remain **denied**: the pinned R2-05 contract requires unknown → `allowed=False`,
  and builders cannot do a network terms check in CI. Unsupported destinations/routes raise `ValueError` and
  the step is shown as blocked with a manual handoff. There is no silent fallback to Accor, Omio or a homepage.
- Accor (`accor.com`, incl. `all.accor.com`, `ibis.accor.com`) is **explicitly denied** as ticket requirement,
  even though its legal conditions have no robot clause (reproduction limited to personal use).

## Reviewed sites

| Registry id | Purpose | Decision | Terms URL | Sections reviewed | Key quote (verbatim, truncated) |
|---|---|---|---|---|---|
| `accor` | hotel | prohibited | https://all.accor.com/a/en/information/legal-conditions.html | COPYRIGHT; database reproduction and commercial use | No element found on all.accor.com may be copied, reproduced, modified, reissued, loaded, altered, transmitted or distributed in any way whatsoever or in any for |
| `hilton-com` | hotel | prohibited | https://www.hilton.com/en/p/site-usage-agreement/ | III. RESTRICTIONS ON USE OF MATERIALS; site-use restrictions | You will not use any robot, spider, other automatic device, or manual process to monitor or copy the Site or the contents or information (including the Informat |
| `booking-com` | hotel | prohibited | https://www.booking.com/content/terms.html | A15. Intellectual property rights (including automated assistants and booking agents) | Whether or not you have a commercial purpose, you’re not allowed to access, monitor, copy, scrape/crawl, download, reproduce, or otherwise use anything on our P |
| `hotels-com` | hotel | prohibited | https://www.hotels.com/legal/terms | Your use of our Service (restricted activities) | access, monitor or copy any content on our Service using any robot, spider, scraper or other automated means or any manual process |
| (none: expedia.com) | - | **unknown → denied** | https://www.expedia.com/lp/b/terms-of-service | not fetched | curl HTTP 429; browser human-verification wall. Terms not fetched; search snippets not used as quotations. |
| `marriott-com` | hotel | prohibited | https://www.marriott.com/about/terms-of-use.mi | 4.B Restrictions; 7.A Intellectual Property | use robots, spiders, or other automatic or high-volume methods or devices, or manual processes to access, search, retrieve, index, monitor, scrape, copy or coll |
| `ihg-com` | hotel | allowed_owner_rule | https://www.ihg.com/content/gb/en/customer-care/tc.html | LIMITED LICENCE TO VIEW AND COPY; PROHIBITED CONDUCT | LIMITED LICENCE TO VIEW AND COPY. The content and information displayed on this Site (“IHG Materials”) is the property of SCH and/or other parties. The download |
| `hrs-com` | hotel | prohibited | https://www.hrs.com/en/termsandconditions | A18. Use of the HRS Internet Portal | The use of the HRS Internet Portal and its contents is only permitted for the individual inquiry of Accommodation bookings. Automated inquiries are not permitte |
| (none: trivago.com) | - | **unknown → denied** | https://www.trivago.com/en-US/st/terms-of-service | not fetched | curl/browser access denied (HTTP 403). Official search snippet not treated as fetched terms. |
| `kayak-com` | hotel, transport | prohibited | https://www.kayak.com/terms-of-use | 4. Play nice on the playground; 6.1 Our content | Scrape, harvest, deep-link to, train AI on, or otherwise use automated tools on our Site without our written permission. |
| `agoda-com` | hotel | prohibited | https://www.agoda.com/info/termsofuse.html | 1.3 (Platform use restrictions) | 1.3.4 use manual or automated software or processes to monitor, copy, extract, export or otherwise scrape any material displayed on our Platform, including text |
| `hostelworld-com` | hotel | prohibited | https://www.hostelworld.com/legal/hostel-terms-and-conditions/ | 7.4 (restricted use of website/content); 3.20 (currency information) | (a) access, monitor, reproduce, distribute, transmit, broadcast, display, sell, license, copy or otherwise exploit any content, information and software of the  |
| `airbnb-com` | hotel | prohibited | https://www.airbnb.com/help/article/2908 | 11.1 Rules; 22.9 Airbnb Platform Content | Do not use bots, crawlers, scrapers, or other automated means to access or collect data or other content from or otherwise interact with the Airbnb Platform. |
| `nh-hotels-com` | hotel | allowed_owner_rule | https://www.nh-hotels.com/en/legal-notice | User obligations; Intellectual Property | Reproduce the Content; |
| `melia-com` | hotel | allowed_owner_rule | https://www.melia.com/en/legal-notice | Intellectual property; use of website content | Any reproduction, copy, dissemination, distribution, public communication, transformation or modification, unless there is permission from the legal owner or le |
| `hotel-bb-com` | hotel | allowed_owner_rule | https://www.hotel-bb.com/fr/conditions-utilisation | Propriété intellectuelle | Toute reproduction, représentation, utilisation ou modification, par quelque procédé que ce soit et sur quelque support que ce soit, de tout ou partie du Site e |
| `motel-one-com` | hotel | prohibited | https://www.motel-one.com/en/terms-of-use/ | V) Your rights, items 1–9 | MO grants you a personal, non-exclusive, non-transferable, royalty-free license to access and use the Websites/Application and the content in accordance with th |
| `accor` | hotel | prohibited | https://all.accor.com/a/en/information/legal-conditions.html | COPYRIGHT; database reproduction and commercial use | No element found on all.accor.com may be copied, reproduced, modified, reissued, loaded, altered, transmitted or distributed in any way whatsoever or in any for |
| `premierinn-com` | hotel | allowed_owner_rule | https://www.premierinn.com/gb/en/terms/terms-of-use.html | 5. Your use of the site; 7. Intellectual property rights | Nothing in these terms and conditions grants or is intended to grant any right, title or interest in the website or any intellectual property rights contained t |
| (none: book.d-edge.com) | - | **unknown → denied** | not located | not fetched | Optional booking engine: attempted official D-EDGE legal-notice route returned 404; engine-specific terms not located wi |
| (none: reservations.travelclick.com) | - | **unknown → denied** | not located | not fetched | Optional engine: public booking shell fetched but no general engine terms discovered; no booking form used. |
| `trenitalia-com` | transport | allowed_owner_rule | https://www.trenitalia.com/it/informazioni/termini-e-condizioni-di-utilizzo-sito-trenitalia.html | Proprietà intellettuale; Utilizzo del Sito. Divieti. | Ogni diritto sui contenuti (a titolo puramente esemplificativo e non esaustivo : testi, immagini, segni distintivi, file audio e video e architettura del Sito)  |
| `italotreno-com` | transport | allowed_owner_rule | https://www.italotreno.com/en/copyright-legal-notes | 7 Site Restrictions | Italo S.p.A. grants the User a limited right for the sole purpose of accessing and using the Site for personal, non-commercial motives and in full compliance wi |
| `sbb-ch` | transport | allowed_owner_rule | https://www.sbb.ch/en/meta/legallines/legal-information.html | Use of the SBB Websites | The information and services contained on the Websites are supplied by SBB solely for private use and for information purposes. |
| `sncf-connect-com` | transport | prohibited | https://www.sncf-connect.com/statics/cgv/cgv-fr-fr.pdf | Article 2.1 (site access/use; automated processes and extraction) | Sont notamment interdits, sans autorisation écrite préalable de SNCF Connect, le recours à tout procédé automatisé, robot, logiciel, script ou dispositif analog |
| (none: bahn.de) | - | **unknown → denied** | https://int.bahn.de/en/terms-of-use | not fetched | curl and browser HTTP 403/access denied. Official search snippets not quoted as fetched text. |
| `renfe-com` | transport | allowed_owner_rule | https://grupo.renfe.com/es/es/informacion-legal/renfe---operadora/nuestra-web | Propiedad intelectual e industrial | Su uso, reproducción, distribución, comunicación pública, puesta a disposición, transformación o cualquier otra actividad similar o análoga queda totalmente pro |
| `cp-pt` | transport | allowed_owner_rule | https://www.cp.pt/info/pt/aviso-legal | Direitos de autor / utilização do sítio (aviso legal) | A reprodução, transferência, distribuição ou armazenamento dos conteúdos do Website, sem a prévia autorização, por escrito, da CP é proibida para qualquer outro |
| `thetrainline-com` | transport | prohibited | https://www.thetrainline.com/terms | 12.2 Using Trainline | Use any device, software, automated agents, scripts or routine to hack, or attempt to hack, into or interfere with our booking service or the security of our we |
| `omio-com` | transport | prohibited | https://www.omio.com/terms-of-use | 7. Intellectual Property | The use of any automated system, tool, or software to access, extract, or collect data from Omio’s website or mobile applications, including through scraping or |
| (none: flixbus.com) | - | **unknown → denied** | https://www.flixbus.com/general-terms-business-and-booking-conditions | not fetched | Business/booking conditions fetched; no customer robot/scraping/copying clause found in this document. Mention of automa |
| `google-travel-google-terms` | transport | prohibited | https://policies.google.com/terms | Using Google services: respecting others; abuse restrictions | using automated means to access content from any of our services in violation of the machine-readable instructions on our web pages (for example, robots.txt fil |
| `skyscanner-net` | transport | prohibited | https://www.skyscanner.net/terms-of-service | Using our Services; intellectual property | You also agree not to use any unauthorised automated computer program, software agent, bot, spider or other software or application to scan, copy, index, sort o |
| `ryanair-com` | transport | prohibited | https://www.ryanair.com/us/en/lp/legal/terms-of-use | Permitted use; screen scraping; intellectual property | Use of any automated system or software, whether operated by a third party or otherwise, to extract any data from this website for commercial purposes (“screen  |
| `easyjet-com` | transport | prohibited | https://www.easyjet.com/en/help-centre/policy-terms-and-conditions/acceptable-use-policy | Acceptable use policy (extraction, re-utilisation and screen scraping) | d) not to gather, extract, reproduce, re-utilise and/or display on any other website, app or other online service, any material on or from our Channels, specifi |
| `vueling-com` | transport | allowed_owner_rule | https://www.vueling.com/en/customer-services/website-conditions-of-use | 02. User obligations; 07. Intellectual and industrial property | Reproduce, duplicate, copy, sell, re-sell or exploit for commercial purposes, totally or partially, the content of the Website. |
| `flytap-com` | transport | prohibited | https://www.flytap.com/en-ca/legal-info/terms-and-conditions | 3. Copyright; Website use obligations | i. not use manual or automatic software, devices, scripts, robots or backdoors or other means or procedures that aim to access, "scrape", "crawl" or "spider" an |
| `lufthansa-com` | transport | prohibited | https://www.lufthansa.com/us/en/terms-of-use | 3.5 (commercial reproduction; robots and automatic mechanisms) | 3.5 You must not reproduce information from the Lufthansa website for commercial purposes. This also includes providing prices for Lufthansa flights on another  |
| `airfrance-com` | transport | prohibited | https://wwws.airfrance.us/information/legal/edito-preambule | Intellectual property; Conditions of use of our websites | Accordingly, without our prior written authorization, any use of processes, systems, or devices such as screen scraping, robots, software, automated or manual p |
| `ita-airways-com` | transport | prohibited | https://www.ita-airways.com/us/en/legal/terms-and-conditions-of-use.html | Site Content / intellectual property; obligations and prohibited use | use the deep-link, page-scrape, chatbot, spider, or any algorithm or other automated or manual process to acquire, copy or monitor the Site or its Content or po |
| (none: swiss.com) | - | **unknown → denied** | not located | not fetched | Official legal index fetched, but candidate terms route failed (403/404). Actual applicable use terms URL not verified o |
| `eurostar-com` | transport | prohibited | https://www.eurostar.com/uk-en/website-terms-and-conditions | 5 (copyright/trademarks); website-use restrictions (screen scraping) | not to use automated systems or software to extract data from Eurostar’s website for commercial purposes (‘screen scraping’) and you acknowledge that screen scr |
| `blablacar` | transport | prohibited | https://legal.blablacar.com/en-gb/terms-and-conditions/ | 6 Non-commercial purpose; 11 Intellectual property (Platform use) | extracting or attempting to extract (in particular by using data scraping bots or any other similar data collection tool) a substantial part of the data of the  |
| `njuko-com-njuko-net` | registration | allowed_owner_rule | https://njuko.com/fr/legal-notices.html | 5. Propriété intellectuelle et contrefaçons | njuko SAS est propriétaire des droits de propriété intellectuelle et détient les droits d'usage sur tous les éléments accessibles sur le site, notamment les tex |
| `ahotu-com` | registration | allowed_owner_rule | https://help.ahotu.com/article/53-terms-of-service | 14. Intellectual property | All content on our Websites, including but not limited to text, graphics, logos, images, audio clips, digital downloads, data compilations, and software, is the |
| `my-raceresult-com` | registration | allowed_owner_rule | https://my.raceresult.com/imprint/termsofuse | Allgemeine Nutzungsbedingungen §§1–6 |  |
| `endu-net` | registration | allowed_owner_rule | https://www.endu.net/en/terms | 3. User guidelines (IP/content restrictions) | Copying, reproducing, extracting, recording or making available to the public any part of the services offered by ENDU, or any other action carried out using th |
| `active-com` | registration | prohibited | https://passport.active.com/waiver?waiverId=1673924&waiverLocale=en_US | 2. Code of Conduct; 3. Ownership and Restrictions on Use; 11. Suspected Violation | use any robot, bot, spider, offline reader, site search/retrieval application or other manual or automatic device or process to retrieve, index, data mine, scra |
| `eventbrite-com` | registration | prohibited | https://www.eventbrite.com/help/en-us/articles/251210/eventbrite-terms-of-service/ | 13. Scraping or Commercial Use of Site Content is Prohibited | You have no right to use, and you agree not to use, any Site Content for your own commercial purposes. You have no right to, and you agree not to, scrape, crawl |
| `sportstiming-dk` | registration | allowed_owner_rule | https://www.sportstiming.dk/terms | Handelsbetingelser / Terms and conditions |  |
| (none: chronotrack.com) | - | **unknown → denied** | not located | not fetched | ChronoTrack-specific website terms not located within time box; separately fetched Athlinks terms are reported separatel |
| `athlinks-com` | registration | prohibited | https://www.athlinks.com/terms | Prohibited Uses; Intellectual Property Rights | Use any robot, spider or other automatic device, process or means to access the Athlinks Sites for any purpose, including monitoring or copying any of the mater |
| (none: Wiclax / UTS) | - | **unknown → denied** | not located | not fetched | Wiclax official homepage fetched but no official usage terms located. UTS identity/relationship was not verified; no inv |
| `raceroster-com` | registration | allowed_owner_rule | https://raceroster.com/legal/tos-for-event-registrants | 3.1 The Services | Notwithstanding the foregoing, you shall not, and shall not permit anyone else to, directly or indirectly: (i) modify, reproduce or otherwise create derivatives |
| (none: letsdoitregistration) | - | **unknown → denied** | not located | not fetched | Requested name could not be resolved confidently to an official platform. Let’s Do This is a possible intended service a |
| `letsdothis-com` | registration | prohibited | https://www.letsdothis.com/terms | Participant Terms: Your use of the Services; automated access/content restrictions | use, or cause others to use, any automated system or software to extract LDT Content or data from the Services; |
| `datasport-com` | registration | prohibited | https://datasport.com/en/terms-and-conditions | 6.1 Use of myDatasport; 6.2 Use of other Datasport Services | The athlete may only use myDatasport manually and only in the manner intended. The use of mechanisms, software or other scripts that burden the myDatasport plat |
| (none: mikatiming.com) | - | **unknown → denied** | not located | not fetched | Official Impressum fetched, but no usage terms located; an imprint is not presented as fetched Terms of Use. |
| `milano-marathon-2027-njuko` | registration | allowed_read_only | https://in.njuko.com/wizz-air-milano-marathon-20271776152378557 | Njuko platform Conditions Générales (footer modal), sections 1–12 |  |
| `endu-net` | registration | allowed_owner_rule | https://www.endu.net/en/terms | ENDU T&C §3. User guidelines | Copying, reproducing, extracting, recording or making available to the public any part of the services offered by ENDU, or any other action carried out using th |
| (none: Lisbon Half Marathon registration host) | - | **unknown → denied** | not located | not fetched | Official event registration link leads to meia-maratona.inscricoes.maratonaportugal.com/default.aspx?prova_id=3767. Publ |
| `berlin-marathon-registration-host` | registration | prohibited | https://www.generali-berlin-marathon.com/fileadmin/media/content/AGB/general_terms_and_conditions_SCC_events.pdf | SCC EVENTS General Terms §12 Lists of Results | The list of results may be accessed and viewed solely for private informational purposes. Any reproduction, storage, distribution, making available to the publi |
| (none: bestwestern.com) | - | **unknown → denied** | https://www.bestwestern.com/en_US/legal/terms-of-use.html | not fetched | Pass 2. Official URL found; curl 403 and browser blank. Search snippets were NOT used as fetched quotations. Deep-link:  |
| `bestwestern-it` | hotel | prohibited | https://www.bestwestern.it/best-western-italia/termini-e-condizioni/default-eng.asp | License and Site Access | Best Western International grants you a limited license to access and make personal use of this site and not to download (other than page caching) or modify it, |
| (none: bestwestern.fr) | - | **unknown → denied** | https://www.bestwestern.fr/mentions.jsp | not fetched | Pass 2. Correct official legal route retried: curl 403 and browser blank. A careers-site result was rejected as inapplic |
| (none: bestwestern.de) | - | **unknown → denied** | not located | not fetched | Pass 2. Legal notice and linked terms index fetched, but these are company details/booking-document links; website-use t |
| `radissonhotels-com` | hotel | allowed_owner_rule | https://www.radissonhotels.com/en-us/site-usage | Use of Site / Contents | Radisson Hospitality authorizes you to view and download a single copy of the Contents solely for your own lawful, personal, non-commercial use if you include t |
| `barcelo-com` | hotel | allowed_owner_rule | https://www.barcelo.com/en-us/general-information/legal-notice/ | Intellectual and industrial property | Any use and/or exploitation will require prior authorization from BARCELÓ HOTEL GROUP, which may be managed through the content use licensing website www.barcel |
| `leonardo-hotels` | hotel | allowed_owner_rule | https://static.leonardo-hotels.com/image/7d32669cbd6c57631ca08c5ead753923_Disclaimer%202026.pdf | Disclaimer (Benelux); Intellectual property | Unauthorized or illegal use of the content or parts of it do infringe the intellectual property rights. Permission to use the displayed content or parts of it a |
| `room-mate` | hotel | prohibited | https://room-matehotels.com/downloads/paginas-legales/roommate_terms_of_use_en.pdf | 4 User obligations; 5 Intellectual property | Our services are solely for personal and non -commercial use. Accordingly, it is forbidden to resell, deep link, use, copy, monitor (for example, spiders, scrap |
| `pestana-com` | hotel | prohibited | https://www.pestana.com/en/terms-conditions | Website Terms of Use: access; reservation interface license | The User must not, under any circumstances, access the Services by any other means other than the interface made available by Pestana Management, or access (or  |
| `vilagale-com` | hotel | prohibited | https://www.vilagale.com/pt-pt/aviso-legal/ | Aviso legal: utilização do site | O usuário deste site não poderá utilizar qualquer software ou aplicação que interfira com o normal funcionamento do mesmo. Não poderá utilizar qualquer aplicaçã |
| `meininger-hotels-com` | hotel | allowed_owner_rule | https://www.meininger-hotels.com/en/imprint/ | Disclaimer & imprint §3 Copyright and trademark rights | The copyright for items created by the author himself lies solely with the author of the site. The reproduction or utilisation of such graphics, audio documents |
| `aohostels-com` | hotel | allowed_owner_rule | https://www.aohostels.com/en/imprint/ | Imprint: Copyright | Contents and works created by the site operators on these websites are subject to German copyright. The reproduction, adaptation, distribution or any kind of ut |
| `generator` | hotel | prohibited | https://staygenerator.com/information/terms-and-conditions | Use of Site; Intellectual Property | You agree that you will not (a) interfere or disrupt the Site, (b) use or attempt to use any robot, spider, automatic device, or automatic or manual process to  |
| `marriott-com` | hotel | prohibited | https://www.marriott.com/about/terms-of-use.mi | 4.B Restrictions; 7.A Intellectual Property | use robots, spiders, or other automatic or high-volume methods or devices, or manual processes to access, search, retrieve, index, monitor, scrape, copy or coll |
| `motel-one-com` | hotel | prohibited | https://www.motel-one.com/en/terms-of-use/ | V) Your rights | 9) use robots or other automated devices to search or monitor the Websites/Application. |
| `scandichotels-com` | hotel | allowed_owner_rule | https://www.scandichotels.com/en/customer-service/policies/website-terms | 2.2 Copyright | 2.2 You may print out individual pages from the website. Otherwise, you may not copy, reproduce, publish, upload, send, transfer or distribute any material or a |
| `nh-hotels-com` | hotel | allowed_owner_rule | https://www.nh-hotels.com/en/legal-notice | User obligations; Intellectual Property | Copy the Content; |
| (none: hyatt.com) | - | **unknown → denied** | https://help.hyatt.com/en/hyatt-terms.html | not fetched | Pass 2. curl 403 on terms/home; browser blank. Actual contents unavailable, not inferred from unrelated Hyatt products.  |
| `wyndhamhotels-com` | hotel | prohibited | https://www.wyndhamhotels.com/wyndham/about-us/terms-of-use | 5. Use of Web Services; prohibited activities | (i) use any robot, spider, intelligent agent, meta-searching or other automatic device, or manual process to search, monitor or copy the Web Services’ pages, or |
| (none: choicehotels.com) | - | **unknown → denied** | https://www.choicehotels.com/legal/terms-of-use | not fetched | Pass 2. curl 403 and browser blank. No fetched terms quotations. Deep-link: no complete format verified. No forms submit |
| `novum-hotels-com` | hotel | allowed_owner_rule | https://www.novum-hotels.com/en/legal-notice | Legal notice: Copyright | Without consent, only the private, non-commercial use of content and structural elements without their processing in each case one workplace is permitted. |
| `marriott-com` | hotel | prohibited | https://www.marriott.com/about/terms-of-use.mi | 4.B Restrictions; 7.A Intellectual Property | use robots, spiders, or other automatic or high-volume methods or devices, or manual processes to access, search, retrieve, index, monitor, scrape, copy or coll |
| `melia-com` | hotel | allowed_owner_rule | https://www.melia.com/en/legal-notice | Legal notice: intellectual property and content use | The total or partial reproduction of any services or content of the website is not permitted. |
| `h10hotels-com` | hotel | allowed_owner_rule | https://www.h10hotels.com/en/legal-notice | Legal notice: Intellectual and industrial property | The reproduction, transformation, distribution, public communication and, in general, any other form of use, partial or total, of the elements referred to in th |
| `riu-com` | hotel | allowed_owner_rule | https://www.riu.com/en/corporate/legal-notice | Legal notice: Obligations of users; Intellectual property | Ultimately, users who access this website may view the content and, where applicable, make authorised private copies, provided that the reproduced elements are  |
| `iberostar-com` | hotel | allowed_owner_rule | https://www.iberostar.com/en/legal-notice/ | Intellectual/industrial property | Unless authorized by the owner of the Website or, where appropriate, by third-party owners of the relevant rights, or unless legally permitted, the user may not |
| `cataloniahotels-com` | hotel | allowed_owner_rule | https://www.cataloniahotels.com/en/legal/disclaimer | Legal disclaimer: Intellectual and industrial property | The website and its contents, including the designs, texts, graphic displays, logos, icons, buttons, as well as the software, trade names, brands, works, illust |
| `eurostarshotels-com` | hotel | allowed_owner_rule | https://www.eurostarshotels.com/aviso-legal.html | Aviso legal: propiedad intelectual | El código fuente, los diseños gráficos, la información y contenidos que aparecen en esta web están protegidos por derechos de propiedad intelectual e industrial |
| `oebb` | transport | allowed_owner_rule | https://www.oebb.at/en/rechtliches/nutzungsbedingungen | Use rights; Intellectual property | Information, brand names and other contents may not be modified, copied, duplicated, sold, leased, complemented or utilised in any other way without our prior w |
| `sncb-nmbs` | transport | allowed_owner_rule | https://www.belgiantrain.be/en/support/customer-service/copyright-declaration | Copyright Statement | For this reason, NMBS/SNCB-NMBS prohibits any visitor to this site from using, reproducing, displaying, making public, modifying, deleting, adapting, etc., eith |
| `ns-international` | transport | allowed_owner_rule | https://www.nsinternational.com/en/disclaimer-ns | Disclaimer NS: Copyright | The copyright for the content, the appearance, the design and the software of this website is vested in NS. Here, NS means NS-Groep NV and/or one of its subsidi |
| `ouigo-france` | transport | allowed_owner_rule | https://www.ouigo.com/infos-legales | Crédits et droits de reproduction | SNCF Voyageurs SA concède à l'Utilisateur, le droit d'utiliser le Site pour ses besoins strictement personnels, à l'exclusion de toute utilisation lucrative. So |
| `ouigo-espana` | transport | allowed_owner_rule | https://www.ouigo.com/es/informacion-legal | Información legal: propiedad intelectual | Entre otras cosas, se prohíbe al Usuario copiar, reproducir, representar, modificar y/o usar, o transferir, de cualquier manera y para cualquier propósito, todo |
| (none: iryo.eu) | - | **unknown → denied** | not located | not fetched | Pass 2. curl robot/security wall on candidate legal path; browser renders official home/statement, not usable website te |
| `italotreno-com` | transport | allowed_owner_rule | https://www.italotreno.com/en/copyright-legal-notes | 7 Site Restrictions | Italo S.p.A. grants the User a limited right for the sole purpose of accessing and using the Site for personal, non-commercial motives and in full compliance wi |
| `flixbus-website-terms` | transport | prohibited | https://www.flixbus.com/online-terms-of-use | License; prohibited uses / technological means | Non-private or commercial use of the Site and Materials is not permitted. Use of any information on the Site for the purpose of reselling tickets is prohibited. |
| `alsa-com` | transport | allowed_owner_rule | https://www.alsa.com/en/legal-notice | Industrial and Intellectual Property Rights | All contents, elements, designs, and applications housed on this Website, regardless of their format or characteristics, and all Industrial and Intellectual Pro |
| (none: RegioJet) | - | **unknown → denied** | not located | not fetched | Pass 2. Official home/documents route fetched only JS shell/consent interface; website-use terms not obtained. No captch |
| (none: Westbahn) | - | **unknown → denied** | not located | not fetched | Pass 2. Official imprint fetched but contains company details, not website-use/copying terms; tariff/transport index not |
| (none: Deutsche Bahn) | - | **unknown → denied** | https://www.bahn.de/nutzungsbedingungen | not fetched | Pass 2. Both German bahn.de website/app terms and English int.bahn.de terms retried by curl/browser: 403 Access Denied.  |
| `swiss-com` | transport | allowed_owner_rule | https://www.swiss.com/ch/en/terms-conditions/copyright | Copyright information | The copyright to the content of the www.swiss.com website belongs exclusively to Swiss International Air Lines AG and such content may not be used, duplicated o |
| `eurowings-com` | transport | prohibited | https://www.eurowings.com/en/legal-information/terms-of-use.html | 2 Copyright; 3.5 Commercial reproduction | 3.5 You may not reproduce data from the website for commercial purposes. This includes quoting prices for Eurowings flights on another website or another online |
| `wizz-air` | transport | prohibited | https://filemanager-cdn.mziq.com/published/f33cff8c-9600-4e77-8b65-b797eb10bc4e/c578cc53-0644-4cae-acb5-383b8daa8be8_website_terms_and_conditions_en_d150c153_9446_4acf_b707_5bd246326d18.pdf | 3 Permitted use; 4 Copyright | without Wizz Air’s prior written consent, use any automated system, algorithm or software to monitor, extract, search or copy any material or data (in whole or  |
| `transavia` | transport | prohibited | https://www.transavia.com/en-EU/conditions/services-access-and-distribution/ | Services Access and Distribution Policy §§1–2; 8.4 | 2.2. Professional Users are not permitted to use the Consumer Channels for commercial purposes. This includes accessing, collecting, querying, extracting, or ot |
| `aegean` | transport | allowed_owner_rule | https://en.aegeanair.com/conditions-notices/conditions-notices/ | Copyright and Trademark Notice / website use terms | All contents of the Web site are Copyright © 2000 Aegean Airlines S.A. and/or its suppliers, Βuilding 57, Athens Internantional Airport, Artemida, Spata, Attiki |
| `airbaltic-com` | transport | prohibited | https://www.airbaltic.com/en/rules-and-regulations/terms-of-use | Permitted use §6; Intellectual property | You may not use any automated system or software, whether operated by a third party or otherwise, to extract any data from airBaltic website (“screen scraping”) |
| `volotea-com` | transport | allowed_owner_rule | https://www.volotea.com/en/legal-conditions/terms-of-use/ | Intellectual property / website content | Access to the Website does not grant the User any rights over its contents, which may not be used, reproduced, distributed, amended, publicly disseminated, tran |
| `iberia-com` | transport | allowed_owner_rule | https://www.iberia.com/us/informacion-legal/ | Propiedad Intelectual e Industrial | El contenido de este website puede ser descargado al terminal del usuario (download), siempre que sea para su uso privado y sin ningún fin comercial; por lo tan |
| `aerlingus-com` | transport | allowed_owner_rule | https://www.aerlingus.com/localized/en/modals/terms-of-use.html | Terms of Use: Internet bookings; Conditions of Carriage |  |
| `klm` | transport | prohibited | https://www.klm.com/information/legal/website-terms-use | Reservation features; Intellectual property | User represents that he shall not for direct or indirect commercial use reproduce, use, block, overwrite, copy, distribute, retrieve or monitor any content of t |
| `brusselsairlines-com` | transport | prohibited | https://www.brusselsairlines.com/gb/en/legal-notices/terms-of-use | Use of Website | By using this Website you agree not to use any robot, spider, other automatic device, or manual process to monitor or copy web pages from the Website or any con |
| `rome2rio-com` | transport | prohibited | https://www.rome2rio.com/terms-of-use/ | Prohibited activities | You agree not to engage in any of the following prohibited activities: (i) copying, distributing, or disclosing any part of the Service in any medium, including |
| `busbud-com` | transport | prohibited | https://www.busbud.com/en/terms-of-use/ | Restrictions on use of Website | Access, monitor or copy any software, content or information of the Website using any robot, spider, scraper or other automated means or any manual process for  |

Unknown → denied rows are terms that could not be fetched (bot walls, timeouts, or not located), so no policy exists for them.
Full quotes and fetch notes: research log kept outside the repo; quotes above are copied verbatim from the fetched pages.

## R4-02 offline review — 2026-11-09

Authority: direct owner-assigned R4-02 brief (queue update is a separate PR).
Normal Chrome, CDP localhost:29229; public navigation/read-only DOM inspection.
No H runs, accounts, personal data, bookings, payment, consent acceptance, captcha bypass
or search-form submissions. No screenshots committed. Rate lists are not READY.

All requested candidate IDs already exist in the main registry. No duplicate IDs or
new scopes/fragments were needed; registration.json is untouched. Existing prohibited
policies, including SNCF Connect, Trainline, Omio, Eurostar, Air France, easyJet,
Ryanair, KLM, Accor and Booking, were not relaxed. A train sold on allowed NS pages
may name Eurostar, but that does not authorize navigating to Eurostar's prohibited host.

### Current terms checked

Official URLs remain in each entry's terms_urls. The following are dated observations,
not a finding that silence about robots constitutes permission. Owner-rule entries
retain their existing narrowly read-only authority and in-session-only screenshots.
For readable reviews below, reviewed_at is 2026-11-09 and expires_at is 2027-02-07;
the three incomplete reviews explicitly do NOT renew prior authorization.

| Policy | Official section read / result |
| --- | --- |
| ihg-com | /content/gb/en/customer-care/tc.html: Authorised Users, LIMITED LICENCE TO VIEW AND COPY, PROHIBITED CONDUCT, IP. Non-commercial individual use; copying/retransmission restricted. No express robot/agent prohibition found. |
| nh-hotels-com | /en/legal-notice: User Responsibilities, Monitoring, IP. Copying/commercial use restricted; no express robot prohibition found. |
| hotel-bb-com | /fr/conditions-utilisation: 5 Access, 7 Services, 15 IP. Reproduction/code downloading/commercial exploitation restricted; no express robot prohibition found. |
| radissonhotels-com | /en-us/site-usage: contents, restricted use. Copying/commercial reuse and damaging access restricted; no express robot prohibition found. |
| meininger-hotels-com | /en/imprint/: Copyright and trademark rights. Rights reserved; no express robot prohibition found in this imprint (not comprehensive express automation permission). |
| scandichotels-com | /en/customer-service/policies/website-terms: 2 IP, 6 Automatically gathered information. Printing individual pages allowed; other copying needs written permission. No express robot prohibition found. |
| h10hotels-com | /en/legal-notice: IP and unlawful use. Rights reserved; no express robot prohibition found. |
| cataloniahotels-com | /en/legal/disclaimer: 3 IP. Personal/private use only; commercial third-party hyperlinks need consent. No express robot prohibition found, but commercial deep-link authority unresolved: no adapter. |
| leonardo-hotels | Linked Disclaimer 2026.pdf produced no readable browser text; /terms checked but no complete current authorization established. Prior review NOT renewed, no adapter. |
| barcelo-com | /en-us/general-information/legal-notice/: IP. Content use/exploitation needs prior authorization; no express robot prohibition found. No adapter. |
| trenitalia-com | /it/informazioni/termini-e-condizioni-di-utilizzo-sito-trenitalia.html: Utilizzo del Sito/Divieti and IP. Hidden accordion text also read. Personal/non-commercial access, saving extracts permitted; copying/distribution restricted. No express robot prohibition found. |
| italotreno-com | /en/copyright-legal-notes: 3 Access, 7 Site Restrictions, 8 Copyright, 13 Links; accordion text read. Personal/non-commercial access, downloading/copying restricted. No express robot prohibition found. |
| sbb-ch | /en/meta/legallines/legal-information.html: Restrictions on access, Use. Individual pages may be saved; public/commercial use needs written consent. No express robot prohibition found. |
| renfe-com | grupo.renfe.com/es/es/informacion-legal/renfe---operadora/nuestra-web: IP. Use/reproduction restricted except authorized or contracted services. No express robot prohibition found. |
| ouigo-france | /infos-legales: credits/reproduction, 5 IP. Reproduction and unauthorized downloading restricted. No express robot prohibition found. |
| ouigo-espana | /es/informacion-legal: IP and use. Copying restricted, third-party profit-making use excluded. No express robot prohibition found. |
| ns-international | /en/disclaimer-ns: information, availability, copyright, third-party links, reference to transport conditions. Copyright reserved; no express robot prohibition found. Not a comprehensive express automation licence. |
| sncb-nmbs | /en/support/customer-service/copyright-declaration: use/reproduction/display requires written permission. No express robot prohibition found in notice. Public booking visit hit robot challenge: no adapter. |
| alsa-com | /en/legal-notice: use/IP. Restrictions remain; no express robot prohibition found. No adapter. |
| swiss-com | /ch/en/terms-conditions/copyright: content use/duplication/reproduction needs written permission. No express robot prohibition found in this copyright page, not express authorization. No adapter. |
| volotea-com | /en/legal-conditions/terms-of-use/: IP, prohibited/non-permitted use. Reuse restrictions; no express robot prohibition found. No adapter. |
| iberia-com | /us/informacion-legal/: responsibility/IP (including additional page text inspection). Rights reserved; no express robot prohibition found in inspected content. No adapter. |
| aegean | /conditions-notices/conditions-notices/ mainly carriage/baggage conditions, not complete current website-use authorization. Prior review NOT renewed, no adapter. |
| aerlingus-com | /localized/en/modals/terms-of-use.html rendered only worldwide booking-facility availability. Complete current terms unverified; prior review NOT renewed, no adapter. |
| vueling-com | /en/customer-services/website-conditions-of-use: existing ten-section review retained. Copyright/commercial-copying limits and www-versus-tickets scope ambiguity remain; existing owner rule, not express authorization. New exact-date airport-pair checks below. |

No newly inspected text established an express robots/automation prohibition. This
does not relax any prohibited host or erase copying/commercial-use restrictions.
Unwired sites remain unwired even when their owner-rule review remains valid.
Other candidate chains not listed here (e.g. a&o, Novum, RIU, Iberostar, Eurostars)
were not newly researched or wired; their existing reviews were not refreshed.

### Coverage semantics and limitations

Coverage means a reviewed executable search URL, NOT local inventory or a safe selected
checkout. IHG can build small-town searches which return only distant hotels; the
existing city-verification gate is unchanged and those results cannot qualify READY.
NS Den Haag explicitly routes via Amsterdam Centraal; no onward transfer is included.
The via field is reviewed routing metadata, never a change to expected.city.

select_adapters reuses the same fail-closed candidate generator, preserves rail-before-flight
ordering and caps output at three distinct policy IDs. Each builder emits at most two
complete alternatives, with the same base task keys and no nested alternatives.
Denied/expired/unreviewed hosts cannot become fallbacks.
