# Owner product feedback

## Round 3: owner hands-on feedback after testing round 1 live (2026-11-09)

Strava-inspired beautiful UX is the #1 criterion, not optional polish.
These owner priorities remain above older scope notes:
- **(a)** ChatGPT/OpenAI-style suggestion pills/cards under the assistant reply,
  not raw buttons.
- **(b)** Each new assistant question BELOW the latest proposals, chronological.
- **(c)** After launch retain three agent cards; below them show ONLY agents
  acting live through the final pre-payment step, with genuine changing live
  screenshots. Never raw task/prompt/JSON/technical logs; at most short friendly
  status lines. Unavailable footage is honest, never simulated live.
- **(d)** Immediate streaming/typing/progress feedback: the first reply took
  ~1 min silently. Use truthful progress, not invented counts.

Exact live success definition: the assistant proposes a sourced race and its
official date; the user never supplies the date and explicitly confirms the
plan. Three H agents (registration/hotel/transport) run LIVE in parallel with
visibly changing frames. Each reaches a verified safe pre-payment stop:
registration at the first personal-data page untouched, hotel with correct
room/rate/dates/party/total, transport with correct outbound/return fares,
dates/party/total. Any earlier mandatory boundary is a blocker, not success;
synthetic, replay or API-only ready states do not count.

Accor is prohibited; the site-policy gate denies Accor and all prohibited
entries. Unknown/expired reviews fail closed before H. Review actual terms;
prefer sites without captchas whose terms allow agents. Never pay, book,
create accounts, accept terms or consent, submit forms, enter personal data
or bypass captchas. Adversarial FR/EN coverage remains >=30 conversations
with safe recovery, no sensitive echo and no unconfirmed launch.

H budget is not a constraint: run agents live in parallel whenever useful.
Round 3 targets >=1 complete live success, ideally Milan and Lisbon; record
all five cases and honest blockers after integration.


Owner feedback outranks older scope notes. Newest first.

## Round 2: hands-on test of the round-1 live build (2026-11-08)

These four points are the top priority for round 2.

- **(a) Suggestions:** make them look like ChatGPT/OpenAI suggestions: elegant,
  clear, clickable pills or cards under the assistant reply, not raw buttons.
- **(b) Chronological thread:** each new assistant question appears BELOW the
  latest proposals, in chat order. Never append it next to the first question
  or change earlier proposals.
- **(c) After launch, show only the agents:** keep the three agent cards. Below
  them the user ONLY SEES THE AGENTS ACTING LIVE (live browser screenshots) up
  to the final pre-payment step. Never show the raw task, prompts, JSON,
  reasoning, tool names or technical logs. At most one short, friendly status
  line per agent.
- **(d) Immediate feedback:** the first reply took about 1 minute with no
  feedback. Show useful progress at once (pending copy, skeletons, real elapsed
  time). Progress must be honest: no invented source counts or percentages.
- Goal: by morning, a fully working, beautiful, near-perfect site.

## Requirements the planner added for round 2

- **Adversarial tests:** keep a table-driven FR/EN suite of at least 30
  conversations. It covers off-topic messages, dodging, mind changes, a race
  that does not exist, past dates, prompt injection and payment or personal
  data, typos and mixed languages, impossible constraints, and confirming too
  early or with a stale plan. Each row checks the reply AND a safe recovery.
  No sentinel personal data may be echoed or stored, and nothing may launch
  without an explicit `confirm` on the current ready plan. Re-run it at the
  final acceptance.
- **Site policy:** Accor is prohibited and denied in `docs/site-policy.json`.
  Every site an agent uses must have a dated review of its actual terms
  (host/path, purpose, screenshot scope, allowed hosts). Unknown, expired,
  denied or unclear entries block before any H session starts. robots.txt is
  not authorization. H trajectories are never published publicly: screenshots
  only.
- **Exact live success definition:** a case succeeds only if all of these hold:
  1. The assistant itself proposes a sourced future race with its official
     date. The user never gives the date.
  2. The user explicitly confirms the plan.
  3. Three live H agents (registration, hotel, transport) run at the same time.
  4. Their screenshots keep changing on the page while they work.
  5. Each one reaches a verified safe pre-payment stop:
     - registration: the edition is selected, and the first personal-data
       page is reached and left untouched;
     - hotel: a room and rate are selected with the correct dates, party and
       total;
     - transport: outbound and return fares are selected with the correct
       dates, party and total.

  Any earlier mandatory safety stop is a blocker, not a success. Synthetic,
  replay or API-only `ready_for_payment` counts never count.

## Standing feedback

- Beautiful, polished UX/UI is the #1 hackathon criterion. The design reference
  is Strava: bold athletic look, orange accent, clean cards, data-rich feel and
  great typography.
- The assistant must feel like ChatGPT: natural free-form conversation in French
  and English, streaming-like replies, chat bubbles, a bottom composer and
  clickable suggestions. Users never need to know race dates or details. The
  assistant proposes a race with its sourced official date, origin, nights and
  budget. The user accepts these defaults in one click or changes them by typing.
- One successful case means the assistant proposes the race, then three H agents
  (bib/registration, hotel and transport) run LIVE in parallel up to the
  pre-payment stop, and the user sees all three working on the page.
- It must work for any race, not just Milan.
- The H API budget is not a constraint.
