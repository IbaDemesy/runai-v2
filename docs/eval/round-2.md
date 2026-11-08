# Round 2 live acceptance — 2026-11-08

**Integrated live acceptance: INCOMPLETE. 0/5 complete live successes; the
two-country target is not met.** Guide-only results and started H sessions are
not successful preparation or proof of a pre-payment stop.

## Cases

| Case | Discovery / plan | Observed live acceptance |
| --- | --- | --- |
| Italy | Rome Marathon, 14 Mar 2027; https://www.runromethemarathon.com/ | Guide only; H untested. |
| Switzerland | Swiss Canyon Trail, 4 Jun 2027: event-start date, event runs 4–6 June; distance unspecified. | Guide only; H untested. Warning: duplicate pills and long distance label. |
| Lisbon | EDP Lisbon Half, 7 Mar 2027; origin Porto, 2 nights, €750. | Registration blocked by policy: no sourced `registration_url`; organizer host `maratonaclubedeportugal.com` not reviewed. Hotel (`www.nh-hotels.com`) and transport (`www.cp.pt`) H sessions started, then failed `H HTTP 404`. Zero frames, no three-agent overlap, no pre-payment stop. |
| Berlin (EN) | S25 Berlin 10 km, 18 Apr 2027. | One run's public response omitted source URLs, so the confirm gate refuses it. A direct rerun returned `berlin-laeuft.de` and Davengo URLs. H untested. |
| Spain | Marató BP Castelló, 14 Feb 2027. | A later discovery returned no matches. H untested. |

## Passed checks

- Background discovery returned 202 in approximately 80 ms with truthful progress.
- Chronological questions, suggestion pills, chips and typed edits worked.
- “oui” / “ok” never launched agents; explicit confirmation was required.
- At 1440×900 and 390×844, unavailable frames were shown as unavailable;
  no raw prompt, JSON or log was displayed.
- Fake card/email redaction, gibberish recovery and past-date recovery worked.

## Blockers and next steps

1. `hclient` fetches legacy `/api/v1/trajectories/.../resources` screenshot
   URLs without the bearer, producing 404. Fix requested from R2-03: normalize
   to `/api/v2/sessions/{id}/resources` and retain scoped authentication and
   unauthenticated presigned downloads. See the
   [H resource documentation](https://hub.hcompany.ai/agents-api/sessions/resources).
2. R2-04 guide `_scrub_data` collapses long race IDs; fix PR #16 is open.
3. [Site-policy coverage](../site-policy.json) is limited to Lisbon hotels
   (NH/IHG/Meliá), CP rail and the listed registration platforms. CP March 2027
   inventory was not on sale as of 2026-11-08.
4. Guide quality remains uneven: event-level dates/distances and intermittent
   missing sources prevent reliable complete plans.

After the fixes, repeat integrated live acceptance across the five cases. Count
only genuine, evidenced outcomes; synthetic checks do not establish live success.
