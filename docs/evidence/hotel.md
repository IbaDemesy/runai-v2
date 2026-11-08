# Hotel site evidence — R1-06

This is an offline task-builder delivery, not evidence of live preparation.
No homepage, robots.txt, terms page, search, inventory or checkout was inspected.
All site-flow claims below are **assumed**, not observed. No live H runs occurred.
An allowlisted official homepage is not permission to automate a site.

| Site | Public flow | Safe stop page | Bot protection / captcha | Automated-agent terms |
| --- | --- | --- | --- | --- |
| Accor — https://all.accor.com | assumed: destination/dates/party search, room and rate selection | assumed: guest-details page; stop earlier at any consent, personal-data/booking submission, login or commitment | assumed: challenges may block; no protection was tested; report blocked and hand off | assumed: permission is unverified; review current applicable terms and obtain authorization before execution |
| Hilton — https://www.hilton.com | assumed: destination/dates/party search, room and rate selection | assumed: guest-details page; stop earlier at any consent, personal-data/booking submission, login or commitment | assumed: challenges may block; no protection was tested; report blocked and hand off | assumed: permission is unverified; review current applicable terms and obtain authorization before execution |

## Local implementation evidence

- Default is Accor worldwide, including Milan, Lisbon, Zermatt and Reykjavik.
  Explicit hilton preference selects only the allowlisted Hilton homepage.
- Budget is a total stay hint, not a nightly allowance. Missing budget requires
  human clarification before choosing a rate. No inventory is invented.
- Public search fields, pressing Search and noncommitting room/rate selection
  are allowed. Submitting personal-data or booking forms remains forbidden.
- No availability, suitable rate, authorization or prepared session is claimed.
- Tests are synthetic offline specifications, not browser evidence.
- Visually unverified. Future authorized evidence must record actual dates,
  public start/end URLs and the observed safe stop or blocker, without personal data.
