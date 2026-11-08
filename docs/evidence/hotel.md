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
