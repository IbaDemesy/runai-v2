# Registration path evidence (R2-02, supersedes R1-05 "assumed" claims)

Dated 2026-11-08. Terms reviews: see `docs/evidence/site-policy.md` and `docs/site-policy.json`.
Observations come from R1-05's public anonymous fetches (2026-11-08, no forms, no login).
**No live H registration run has been made in R2-02**: live smokes wait for the R2-03 no-share runtime.

## What the builder does now (`runai/agents/registration.py`)
- Validates a sourced race: confirmed/official future `race_date`, edition year matching the date,
  distance, city, country. Stale, conflicting or missing data → `ValueError` (blocked).
- Calls `evaluate_url(registration_url, "registration")`, then the official URL. Only an allowed
  policy decision makes the start URL. Unreviewed hosts block. Platforms are not trusted by name.
- `registration_info()` access observations (account/captcha) are copied as source-only
  metadata and **never** grant permission.
- Instructions: select the exact edition/date/distance; stop untouched at the first personal-data page;
  BLOCKED on account wall, lottery-only, closed/sold-out, captcha, earlier consent, date/distance mismatch,
  or redirect to a host outside `allowed_hosts`. `max_steps` 80.

## Reviewed vs observed vs unverified
| Race / platform | Terms decision (2026-11-08) | Access observation | Unverified |
|---|---|---|---|
| Milano Marathon 2027 → `in.njuko.com/wizz-air-milano-marathon-20271776152378557` | `allowed_read_only` (Njuko application CGU: no automation/copy restriction found); organizer `milanomarathon.it` terms not reviewed → start directly on the Njuko event page | Observed (R1-05): no captcha marker in shell HTML; JS app | Ticket list, open/sold-out status, first personal-data page |
| Other Njuko events (`in.njuko.com`) | `allowed_owner_rule` (corporate notice limits reproduction; ambiguous) | none | everything |
| ENDU (`endu.net`, `rrtm.endu.net` for Rome) | `allowed_owner_rule`; organizer `runromethemarathon.com` not reviewed → denied | none | everything |
| Ahotu, Race Result, Sportstiming, Raceroster | `allowed_owner_rule` (no automation clause found / ambiguous) | none | everything |
| Berlin (SCC) | `prohibited` | Observed (R1-05): lottery + `login.scc-events.com` login wall | n/a: blocked |
| Active, Eventbrite, Athlinks, Let's Do This, Datasport | `prohibited` | n/a | n/a: blocked |
| Barcelona (RPM Sports) | unknown → denied (terms not reviewed) | Observed (R1-05): reCAPTCHA script | n/a: blocked |
| Lisbon half (`maratonaclubedeportugal.com`) | unknown → denied (terms not fetched) | none | n/a: blocked |

No account is created automatically and no platform is guaranteed to accept agents.
