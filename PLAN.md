# Frozen target — not a verified live journey

Promise: « Dis-moi ta course, je prépare tout le déplacement ».
Target: Milano Marathon, assumed race date 4 April 2027, Paris–Milano,
3–5 April 2027, two nights, one adult, synthetic total budget EUR 600.
Race date and availability must be verified before live execution.
Sites: official Milano Marathon (registration target Njuko if officially linked),
Accor Milan, Trenitalia. No substitute platform without a scope decision.

## Five steps
1. User describes the race; show the framing (race/date/origin/nights/budget).
   Bootstrap stores the request but uses fixed synthetic framing, not extraction.
2. User validates framing and reviews the three-site plan.
3. User explicitly confirms; no provider execution before confirmation.
4. Registration, hotel and train runners prepare in parallel; expose status by polling.
5. Each stops before payment or any earlier consent/commitment; hand over a URL.
   In demo/replay these URLs are official homepages, NOT prepared checkout sessions.
   `ready_for_payment` is a simulated terminal state, not a live success claim.

## Evidence boundary
Old RunAI docs report Njuko success on another race, Accor contact-details access,
and specify Milan/Trenitalia as a target. They do not prove this full journey.
The old demo replay was synthetic. This repository contains a fresh synthetic trace.
T04/T05/T06 each require a first verified live run with date, start/end URLs,
observed stop state and redacted public evidence; failure is reported, not fabricated.
Never use Booking, TAP, or captcha workarounds as shortcuts.

## Not now
Coach, 3D flyover, quotes engine, Telegram, PDF/ICS, Strava, accounts, payments,
multi-city planning, arbitrary races, autonomous self-repair, production persistence.
