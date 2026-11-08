import asyncio
from datetime import date

import pytest
from pydantic import ValidationError

import runai.guide
from runai.guide.engine import GuideEngine
from runai.guide.fake import FakeDiscovery
from runai.guide.types import GuideState, RaceOption


def test_package_public_api():
    assert runai.guide.GuideEngine is GuideEngine
    assert runai.guide.GuideState is GuideState
    assert runai.guide.RaceOption is RaceOption
    assert all(hasattr(runai.guide, name) for name in runai.guide.__all__)


def run(awaitable):
    return asyncio.run(awaitable)


def engine(discover=None):
    return GuideEngine(discover or FakeDiscovery(), today=date(2026, 1, 1))


def invariant(turn):
    assert (turn.message + (turn.question or "")).count("?") <= 1
    assert turn.question or not turn.suggestions
    assert len({s.kind for s in turn.suggestions}) == 1 or all(
        s.kind in {"confirm", "edit", "choose_race", "retry"} for s in turn.suggestions
    )


def click(e, state, turn, index=0):
    invariant(turn)
    return run(e.step(state, {"suggestion_id": turn.suggestions[index].id}))


@pytest.mark.parametrize(
    "query", ["un trail en Suisse cet ete", "a trail in Switzerland this summer"]
)
def test_acceptance_full_conversation(query):
    e = engine()
    state, turn = run(e.start(query))
    assert len(turn.candidates) == 3
    for _ in range(4):
        state, turn = click(e, state, turn)
    invariant(turn)
    assert turn.ready_to_confirm and state.stage == "confirm"
    assert "milan" not in state.draft.race.name.lower()
    assert all(
        state.draft.provenance[f] == "suggested_default"
        for f in ["origin_city", "nights", "budget_eur"]
    )
    assert "unverified" in turn.message or "non vérifiée" in turn.message
    payload = e.trip_payload(state)
    assert set(payload) == {
        "race",
        "origin_city",
        "travelers",
        "nights",
        "budget_eur",
        "arrival_date",
        "departure_date",
    }
    assert payload["arrival_date"] == "2026-07-09"
    assert payload["departure_date"] == "2026-07-11"
    assert GuideState.model_validate(state.model_dump(mode="json")) == state
    state, turn = click(e, state, turn)
    assert state.stage == "confirmed"
    invariant(turn)


def test_named_and_correction_and_bare_answers():
    e = engine()
    state, turn = run(e.start("le semi de Lisbonne"))
    assert state.stage == "origin" and state.draft.race.city == "Lisbon"
    state, turn = run(e.step(state, {"text": "Lyon"}))
    assert state.stage == "nights" and state.draft.provenance["origin_city"] == "user"
    state, turn = run(e.step(state, {"text": "2"}))
    assert state.stage == "budget"
    state, turn = run(e.step(state, {"text": "plutôt 3 nuits"}))
    assert state.stage == "budget" and state.draft.nights == 3
    state, turn = run(e.step(state, {"text": "800"}))
    assert turn.ready_to_confirm and state.draft.budget_eur == 800
    assert state.draft.departure_date == date(2027, 3, 16)


@pytest.mark.parametrize(
    "query,smalltalk,yes,overrides",
    [
        (
            "le semi de Lisbonne",
            "merci bonjour et les chats",
            "oui",
            ["depuis Lyon", "plutôt 3 nuits", "budget 800", "à 2"],
        ),
        (
            "Lisbon half marathon",
            "thanks hello tell me a joke",
            "sounds good",
            ["from Lyon", "actually 3 nights", "800 euros", "2 people"],
        ),
    ],
)
def test_natural_free_text(query, smalltalk, yes, overrides):
    e = engine()
    state, turn = run(e.start(query))
    before = state.draft.model_copy(deep=True)
    state, reply = run(e.step(state, {"text": smalltalk}))
    assert state.draft == before and state.stage == "origin"
    assert reply.question == turn.question and reply.suggestions == turn.suggestions
    for answer in [yes, "ok", "ok"]:
        state, turn = run(e.step(state, {"text": answer}))
        invariant(turn)
    assert turn.ready_to_confirm
    for text in overrides:
        state, turn = run(e.step(state, {"text": text}))
        invariant(turn)
        assert turn.ready_to_confirm
    assert (
        state.draft.origin_city,
        state.draft.nights,
        state.draft.budget_eur,
        state.draft.travelers,
    ) == ("Lyon", 3, 800, 2)
    assert all(
        state.draft.provenance[f] == "user"
        for f in ["origin_city", "nights", "budget_eur", "travelers"]
    )
    state, turn = run(e.step(state, {"text": "non"}))
    assert state.stage == "confirm" and turn.question


def test_empty_no_results_retry_invalid_suggestion():
    calls = []

    async def discover(query, hints):
        calls.append(query)
        if len(calls) == 1:
            raise RuntimeError("private provider details")
        return await FakeDiscovery()(query, hints)

    e = engine(discover)
    state, turn = run(e.start("  "))
    assert not calls and turn.question and turn.suggestions
    state, turn = run(e.step(state, {"text": "un marathon en Italie au printemps"}))
    assert turn.error == "discovery_failed" and turn.suggestions[0].kind == "retry"
    state, turn = click(e, state, turn)
    assert len(calls) == 2 and len(turn.candidates) == 3
    original = state.model_dump(mode="json")
    state, turn = run(e.step(state, {"suggestion_id": "missing"}))
    assert turn.error == "unknown_suggestion" and state.model_dump(mode="json") == original
    e = engine()
    state, turn = run(e.start("gibberish"))
    assert not turn.error and turn.question
    state, turn = run(e.start("a marathon in Norway"))
    assert not turn.candidates and len(turn.suggestions) == 3
    assert "broaden" in turn.message


@pytest.mark.parametrize(
    "status,race_date", [("unknown", None), ("conflicting", "2027-04-01"), ("official", None)]
)
def test_blocked_dates_and_invalid_candidates(status, race_date):
    async def discover(query, hints):
        return [
            {"bad": "row"},
            {"id": "test", "name": "Test", "race_date": race_date, "date_status": status},
        ]

    e = engine(discover)
    state, turn = run(e.start("a marathon"))
    assert len(turn.candidates) == 1
    state, turn = click(e, state, turn)
    assert not turn.ready_to_confirm and any(s.kind == "retry" for s in turn.suggestions)
    assert not any(s.kind == "confirm" for s in turn.suggestions)
    invariant(turn)
    with pytest.raises(ValueError):
        e.trip_payload(state)


def test_new_race_intent_and_all_fields_upfront():
    e = engine()
    state, turn = run(e.start("un marathon en Italie au printemps"))
    state, turn = run(e.step(state, {"text": "le semi de Lisbonne depuis Lyon 3 nuits 800 euros"}))
    assert turn.ready_to_confirm and state.draft.race.city == "Lisbon"
    state, turn = run(e.step(state, {"text": "un trail en Suisse cet été"}))
    assert len(turn.candidates) == 3 and state.draft.race is None


def test_models_forbid_extra_and_fake_unknown():
    with pytest.raises(ValidationError):
        RaceOption(id="a", name="A", date_status="unknown", invented=True)
    rows = run(FakeDiscovery()("ultra Chamonix", {"city": "Chamonix", "distance": "ultra"}))
    assert rows[0]["race_date"] is None and rows[0]["synthetic"]
    assert run(FakeDiscovery()("gibberish", {})) == []


def test_official_date_edit_and_yes_confirmation():
    async def discover(query, hints):
        return [
            {
                "id": "paris",
                "name": "Example race",
                "city": "Paris",
                "race_date": "2027-04-01",
                "date_status": "official",
            }
        ]

    e = engine(discover)
    state, turn = run(e.start("a marathon in Paris"))
    assert state.stage == "origin"
    assert turn.suggestions[0].value != "Paris"
    for _ in range(3):
        state, turn = run(e.step(state, {"text": "ok"}))
    assert turn.ready_to_confirm
    assert "unverified" not in turn.message
    state, turn = run(e.step(state, {"suggestion_id": "edit:nights"}))
    assert state.stage == "nights"
    state, turn = run(e.step(state, {"text": "3 nights"}))
    assert state.draft.nights == 3 and turn.ready_to_confirm
    state, turn = run(e.step(state, {"text": "yes"}))
    assert state.stage == "confirmed"


def test_all_invalid_rows_and_month_change():
    async def discover(query, hints):
        return [{"unknown": True}]

    state, turn = run(engine(discover).start("a marathon in Italy"))
    assert not turn.candidates and not turn.ready_to_confirm
    e = engine()
    state, turn = run(e.start("un trail en Suisse cet été"))
    state, turn = run(e.step(state, {"text": "en juillet"}))
    assert len(turn.candidates) == 1
    assert turn.candidates[0].race_date.month == 7


def test_question_in_free_text_does_not_create_second_question():
    e = engine()
    state, turn = run(e.start("un trail en Suisse cet été ?"))
    invariant(turn)
    state, turn = click(e, state, turn)
    state, turn = run(e.step(state, {"text": "bonjour, ça va ?"}))
    invariant(turn)
    assert state.stage == "origin" and not turn.error


def test_explicit_year_discovery_and_mismatched_candidates():
    state, turn = run(engine().start("Milan marathon 2028"))
    assert state.draft.race.race_date.year == 2028
    assert state.draft.race.edition == "2028"

    async def discover(query, hints):
        assert hints["year"] == 2028
        return [
            {
                "id": "wrong-date",
                "name": "Race",
                "date_status": "official",
                "race_date": "2027-04-01",
                "edition": "2028",
            },
            {
                "id": "wrong-edition",
                "name": "Race",
                "date_status": "official",
                "race_date": "2028-04-01",
                "edition": "2027",
            },
        ]

    state, turn = run(engine(discover).start("Milan marathon 2028"))
    assert not turn.candidates and state.draft.race is None and not turn.ready_to_confirm


def test_new_race_search_resets_hints_but_month_refines():
    e = engine()
    state, turn = run(e.start("un marathon en Italie au printemps 2028"))
    state, turn = run(e.step(state, {"text": "un trail en Suisse"}))
    assert len(turn.candidates) == 3
    assert state.hints == {"distance": "trail", "country": "Switzerland"}
    state, turn = run(e.step(state, {"text": "plutôt en juillet"}))
    assert state.hints["distance"] == "trail" and state.hints["country"] == "Switzerland"
    assert len(turn.candidates) == 1 and turn.candidates[0].city == "Zermatt"
    state, turn = run(e.step(state, {"text": "le semi de Lisbonne"}))
    assert state.draft.race.city == "Lisbon"
    assert "months" not in state.hints and "year" not in state.hints


@pytest.mark.parametrize("answer", ["budget 2028 euros", "2028 €", "2028 eur", "2028"])
def test_budget_is_not_a_race_year(answer):
    calls = []

    async def discover(query, hints):
        calls.append(query)
        return await FakeDiscovery()(query, hints)

    e = engine(discover)
    state, turn = run(e.start("le semi de Lisbonne depuis Lyon 2 nuits"))
    assert state.stage == "budget"
    race = state.draft.race
    state, turn = run(e.step(state, {"text": answer}))
    assert len(calls) == 1 and state.draft.race == race
    assert state.draft.budget_eur == 2028 and turn.ready_to_confirm
    state, turn = run(e.step(state, {"text": "budget 2029 euros"}))
    assert len(calls) == 1 and state.draft.budget_eur == 2029


def test_month_refinement_preserves_explicit_year():
    e = engine()
    state, turn = run(e.start("un trail en Suisse 2028"))
    state, turn = run(e.step(state, {"text": "plutôt en juillet"}))
    assert state.hints["year"] == 2028 and state.hints["months"] == ["2028-07"]
    assert len(turn.candidates) == 1
    assert turn.candidates[0].race_date == date(2028, 7, 10)
    state, turn = run(e.step(state, {"text": "in July 2029"}))
    assert state.hints["year"] == 2029 and state.hints["months"] == ["2029-07"]


def test_winter_months_take_precedence_over_single_year():
    async def discover(query, hints):
        assert hints["year"] == 2028
        assert hints["months"] == ["2028-12", "2029-01", "2029-02"]
        return [
            {
                "id": value,
                "name": "Synthetic winter example",
                "race_date": value,
                "edition": value[:4],
                "date_status": "official",
                "synthetic": True,
            }
            for value in ["2028-12-10", "2029-01-10", "2029-02-10", "2028-06-10", "2029-12-10"]
        ]

    e = engine(discover)
    state, turn = run(e.start("a marathon winter 2028"))
    assert [r.race_date.isoformat() for r in turn.candidates] == [
        "2028-12-10",
        "2029-01-10",
        "2029-02-10",
    ]
    state, turn = click(e, state, turn, 1)
    assert state.draft.race.race_date == date(2029, 1, 10) and state.stage == "origin"


def test_r1_03_race_contract_and_hint_bridge():
    row = {
        "id": "example-2028",
        "name": "Synthetic contract example",
        "edition": "2028",
        "distance_km": 21.1,
        "distance_label": "Semi-marathon",
        "race_date": "2028-03-14",
        "date_status": "official",
        "city": "Lisbon",
        "country": "Portugal",
        "official_url": "https://example.org/race",
        "registration_url": None,
        "source_urls": ["https://example.org/race"],
        "retrieved_at": "2026-01-01T00:00:00Z",
        "synthetic": True,
    }
    assert set(row) == set(RaceOption.model_fields)
    assert RaceOption.model_validate(row).distance_label == "Semi-marathon"
    observed = []

    async def discover(query, hints):
        observed.append(hints)
        return [row]

    e = engine(discover)
    state, turn = run(e.start("le semi de Lisbonne au printemps 2028"))
    hints = observed[-1]
    assert hints["month_from"] == "2028-03" and hints["month_to"] == "2028-05"
    assert hints["year"] == 2028 and hints["race_name"] == "le semi de Lisbonne au printemps 2028"
    assert hints["distance"] == "half" and hints["named"]
    assert hints["months"] == ["2028-03", "2028-04", "2028-05"]
    assert state.draft.race.distance_label == "Semi-marathon"
    state, turn = run(e.step(state, {"text": "un trail en Suisse cet été"}))
    assert observed[-1]["year"] == 2026 and "race_name" not in observed[-1]
    assert not turn.ready_to_confirm
    assert observed[-1]["month_from"] == "2026-06" and observed[-1]["month_to"] == "2026-08"
    assert "year" not in state.hints
    assert all(
        row["distance_label"] for row in run(FakeDiscovery()("trail", {"distance": "trail"}))
    )


def test_named_race_refinement_keeps_base_query_and_race_name():
    observed = []

    async def discover(query, hints):
        observed.append((query, hints.copy()))
        month = hints.get("month_from", "2027-03")
        return [
            {
                "id": "lisbon",
                "name": "Synthetic Lisbon half",
                "city": "Lisbon",
                "race_date": f"{month}-14",
                "date_status": "unverified",
                "synthetic": True,
            }
        ]

    e = engine(discover)
    state, turn = run(e.start("le semi de Lisbonne"))
    state, turn = run(e.step(state, {"text": "plutôt en mai"}))
    query, hints = observed[-1]
    assert query == "le semi de Lisbonne" and hints["race_name"] == query
    assert hints["city"] == "Lisbon" and hints["distance"] == "half" and hints["named"]
    assert hints["month_from"] == hints["month_to"] == "2026-05"
    assert state.query == query and state.draft.race.city == "Lisbon" and turn.candidates
    state, turn = run(e.step(state, {"text": "un marathon à Rome"}))
    assert observed[-1][0] == "un marathon à Rome"
    assert observed[-1][1]["race_name"] == "un marathon à Rome"
