# Frozen target — not a verified live journey

Promise: « Dis-moi ta course, je prépare tout le déplacement ».
Target: Milano Marathon, assumed race date 4 April 2027, Paris–Milano,
3–5 April 2027, two nights, one adult, synthetic total budget EUR 600.
Race date and availability must be verified before live execution.
Sites: official Milano Marathon (registration target Njuko if officially linked),
Accor Milan, Trenitalia. No substitute platform without a scope decision.

## Five steps
1. Start with a guided chat, not a form: accept vague wishes such as a spring
   marathon in Italy or the Milan marathon. Propose races, editions, distances
   and official dates sourced through Linkup; never ask the user to know these.
   Bootstrap still uses fixed synthetic framing until T02/T03 deliver this.
2. Ask at most one focused question at a time, with clickable suggestion chips.
   Suggest origin, nights and budget as editable defaults, not sourced facts.
   Fill the rest from sources; show provenance and an attractive three-site plan.
   Discovery may propose other races, but execution remains frozen to Milan.
3. User explicitly confirms the plan; no H preparation before confirmation.
   Read-only discovery may run beforehand. No silent date/edition substitution.
4. Registration, hotel and train runners prepare in parallel. A polished dark,
   responsive chat UI shows three side-by-side agent panels on desktop (stacked
   on mobile), real H live view/share embeds or streamed screenshots and step
   logs. If unavailable/blocked, say so and offer a genuine public link.
   Replay shows recorded frames with provenance, never fake live activity.
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
multi-city execution, arbitrary-race execution, autonomous self-repair,
production persistence. Race discovery/proposals are in scope; booking them is not.

## Agent delivery topology
One session = one agent = one ticket branch = one PR. T03 prepares shared
adapter interfaces and registry wiring before T04/T05/T06 run in parallel.
T09 may run alongside T03–T06 in isolated voice files. These parallel tickets
write docs/handoff/Txx.md, not shared HANDOFF.md. T07 integrates adapters and
replay; T08 integrates chat, voice and live-view UI after both T07 and T09.
