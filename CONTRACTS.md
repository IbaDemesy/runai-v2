# Contracts

Executable source: runai/models.py; Pydantic v2, extra fields forbidden.
OpenAPI: /docs. Provider protocols: runai/providers.py.

- Framing: race, race_date, origin_city, nights (1–14), budget_eur (>0).
- JourneyPlan: framing, departure, return_date, sites keyed by Kind.
- Kind: registration | hotel | transport.
- StepResult: kind, status (ready_for_payment | failed), summary, handoff_url,
  error, synthetic, payment_executed (literal false).
- Event: sequence, type (confirmed | step_started | step_finished), kind,
  message, synthetic. Ordered per mission, no external provider evidence implied.
- Mission: id, mode, synthetic, description, plan, confirmed, status, results, events.
- SearchProvider.search(Framing) -> JourneyPlan (async).
- AgentRunner.run(Kind, JourneyPlan) -> StepResult (async).
- VoiceProvider.transcribe(bytes) -> str (async).

## HTTP
POST /api/missions {description, mode?}: 201, fixed framing, no agents yet.
POST /api/missions/{id}/reply {framing}: acknowledge frozen framing; 422 if changed.
POST /api/missions/{id}/confirm {confirmed:true}: await three concurrent runners.
GET /api/missions/{id}: poll status, results and ordered events during preparation.
404 unknown mission; 422 invalid input; 400 missing explicit confirmation;
409 already confirmed; 501 unavailable live search (missing implementation/key).
Runner failures produce failed StepResults rather than success fallbacks.

## Planned contract evolution (T02/T03/T07/T08; not implemented yet)
- RaceOption: id, race name, edition, distance_km, official race_date,
  official_url, registration_url if verified, source URLs, retrieved_at,
  synthetic. Unknown or conflicting dates are explicit, never guessed facts.
- Suggestion: id, label, action/value, provenance (source | suggested_default),
  source URLs if factual. Chips select an option or answer the current question.
- GuidedTurn: assistant message, candidate options, suggestions, at most one
  focused question, partial framing, selected option, confirmation_required.
  Origin/nights/budget defaults are editable and distinct from official facts.
- SearchProvider discovery accepts vague intent before complete Framing exists;
  T03 supplies official race candidates to T02's guided assistant. Demo uses
  labelled synthetic candidates; no-results/conflicts/errors ask one useful
  follow-up, never require the runner to know the official date.
- AgentLiveFrame: mission_id, kind, sequence, observed_at, mode, synthetic,
  frame_url or real public live_view_url/share_url, step message, availability.
  Extend events with live_frame/live_view_available/step_progress in T07/T08.
  Serve only scrubbed, authorized public URLs/frames, no private H session URLs.
  Record frames for replay, label replay/synthetic provenance and original time;
  missing frames show unavailable, not animated or fabricated live footage.
- T03 defines shared adapter interface/export and registry hooks in
  runai/adapters/__init__.py and providers.py. T04/T05/T06 implement isolated
  modules against it; T07 integrates without forcing cross-ticket file edits.
  Voice adapters/UI module are isolated by T09; T08 owns app/UI wiring.
- Existing HTTP/schema notes above describe bootstrap only. T02/T03 document
  their guided-turn requests/responses here; T07/T08 document frame polling or
  streaming. Plan confirmation remains mandatory before H actions.

## Safety and limitations
In-memory store, single process, no restart durability or authentication.
No purchase/submit API exists. Live adapters must enforce pre-consent stops in
their actual browser tools; a result schema alone is not a live safety boundary.
Replay schema_version 1: provenance synthetic, results array with all three kinds.
Homepage handoffs carry no prepared cart; no invented live view URLs.
