# Registration path evidence (R1-05)

Method: public, anonymous HTTP fetches (`curl`, desktop user agent) of organizer pages on
2026-11-08. No forms submitted, no login, no personal data, no consent accepted. No live H run
was made: R1-02 (H client) is not on main yet. "Observed" = seen in fetched public HTML on that
date; "Assumed" = inferred, must be confirmed by a live H run.

| Race (country) | Official site | Registration path / platform | Safe stop | Blockers |
|---|---|---|---|---|
| Wizz Air Milano Marathon 2027 (IT) | https://www.milanomarathon.it/ | Observed: homepage -> `/wizz-air-milano-marathon/iscriviti/` -> link to Njuko `https://in.njuko.com/wizz-air-milano-marathon-20271776152378557` (HTTP 200) | Assumed: Njuko participant-data step after selecting the race/ticket | Observed: no captcha marker in organizer or Njuko shell HTML. Assumed: Njuko is a JS app (4.9 KB shell), so ticket list/open status needs a browser |
| Generali/BMW Berlin-Marathon (DE) | https://www.berlin-marathon.com/ (observed redirect to `generali-berlin-marathon.com`) | Observed: `/anmeldung/lauf` page describing a "Verlosung" (lottery) and linking to SCC login `login.scc-events.com` | Observed: stop at the SCC login page (login wall) | Observed: lottery-based entry + account login required -> expected BLOCKED (lottery/login wall) |
| Zurich Marató de Barcelona 2027 (ES) | https://www.zurichmaratobarcelona.es/ | Observed: homepage links to RPM Sports `inscripciones.rpmsports.es/.../zurich-marato-barcelona-2027/my-registration` (HTTP 200) | Assumed: first participant-data form on RPM Sports | Observed: Google reCAPTCHA script present on the RPM Sports page -> agent must stop, never solve |
| Valencia Marathon (ES), extra | https://www.valenciaciudaddelrunning.com/ | Observed: links to `info-inscripciones` pages and `tickets.valenciaciudaddelrunning.com` (organizer ticketing) | Assumed: ticket shop customer-data step | Not checked |

Unreachable on 2026-11-08 from this VM (connection failed, not investigated): maratonadelisboa.com.

## Implications for `build_task`
- Organizer site -> officially linked third-party platform is the common pattern (Njuko, RPM
  Sports, organizer ticketing), so instructions allow officially linked platforms generically.
- Login walls, lotteries and captchas are real; they are explicit BLOCKED / stop conditions.
- Candidate sites without observed captcha for live demos: Milano (organizer + Njuko). Terms of
  service of Njuko/organizers regarding automated agents were not reviewed (assumed unknown).
