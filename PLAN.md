# Generic live race journey — not yet verified live

Promise: « Dis-moi ta course, je prépare tout le déplacement ».
Product goal: guide the user to any race and prepare its registration, hotel and
transport live, using official sources and explicit confirmation. Milan is the
first evaluation case, not a product restriction or hard-coded execution path.
First evaluation: Milano Marathon, assumed race date 4 April 2027, Paris–Milano,
3–5 April 2027, two nights, one adult, synthetic total budget EUR 600.
Race date and availability must be verified before live execution.
First-evaluation sites: official Milano Marathon (Njuko if officially linked),
Accor Milan, Trenitalia. For other races, discover official registration and
appropriate authorized hotel/transport options dynamically. Unsupported sites,
unavailable inventory or captcha produce an honest blocker/human handoff, never
fabricated live success. Verify additional races, destinations and dates as evals.

## Five steps
1. Start with a guided chat, not a form: accept vague wishes such as a spring
   marathon in Italy or the Milan marathon. Propose races, editions, distances
   and official dates sourced through Linkup; never ask the user to know these.
   Bootstrap still uses fixed synthetic framing until T02/T03 deliver this.
2. Ask at most one focused question at a time, with clickable suggestion chips.
   Suggest origin, nights and budget as editable defaults, not sourced facts.
   Fill the rest from sources; show provenance and an attractive three-site plan.
   Discovery and execution support the selected race, not only Milan.
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
and specify Milan/Trenitalia as a target. They do not prove this generic journey.
The old demo replay was synthetic. This repository contains a fresh synthetic trace.
T04/T05/T06 each require a first verified live run with date, start/end URLs,
observed stop state and redacted public evidence; failure is reported, not fabricated.
Never use Booking, TAP, or captcha workarounds as shortcuts.

## Not now
Coach, 3D flyover, quotes engine, Telegram, PDF/ICS, Strava, accounts, payments,
multi-city itineraries, autonomous self-repair, production persistence.
Generic race discovery and live preparation are in scope; purchasing is not.

## Continuous improvement loop
Continue small agent tickets and review/merge cycles until the guided product
works live beyond a single demo case. Maximize parallel independent sessions,
each with its own branch/PR and non-overlapping file scope; integrate completed
work only with green CI and reviewed evidence. Re-evaluate multiple races after
integration, record actual failures and open focused follow-up tickets. A passing
synthetic demo or one successful Milan run does not satisfy generic live readiness.
Live runs still require approval, applicable site authorization and pre-payment
stops; continuous coding does not authorize spending or bypassing safeguards.

## Agent delivery topology
One session = one agent = one ticket branch = one PR. T03 prepares shared
adapter interfaces and registry wiring before T04/T05/T06 run in parallel.
T09 may run alongside T03–T06 in isolated voice files. These parallel tickets
write docs/handoff/Txx.md, not shared HANDOFF.md. T07 integrates adapters and
replay; T08 integrates chat, voice and live-view UI after both T07 and T09.
