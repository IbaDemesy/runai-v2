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

## Safety and limitations
In-memory store, single process, no restart durability or authentication.
No purchase/submit API exists. Live adapters must enforce pre-consent stops in
their actual browser tools; a result schema alone is not a live safety boundary.
Replay schema_version 1: provenance synthetic, results array with all three kinds.
Homepage handoffs carry no prepared cart; no invented live view URLs.
