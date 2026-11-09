import copy
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from test_site_policy import TODAY, registry, transport_entry

from runai.agents.transport import build_task

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts"}


def trip(**changes):
    race = {
        "id": "r", "name": "Example Half", "edition": "2027", "distance_km": 21.0975,
        "distance_label": "Half marathon", "race_date": "2027-03-21", "date_status": "official",
        "city": changes.pop("city", "Lisbon"), "country": changes.pop("country", "Portugal"),
        "official_url": "https://www.example-half.test/", "registration_url": None,
        "source_urls": [], "retrieved_at": "2026-11-08", "synthetic": False,
    }
    race.update(changes.pop("race_changes", {}))
    return {"race": race, "origin_city": "Porto", "travelers": 2, "nights": 2,
            "budget_eur": 400, "arrival_date": "2027-03-20", "departure_date": "2027-03-22",
            **changes}


def build(data, reg=None):
    return build_task(data, today=TODAY, registry=registry() if reg is None else reg)


@pytest.mark.parametrize("origin,city,country", [
    ("Porto", "Lisbon", "Portugal"), ("Paris", "Milan", "Italy"), ("Zürich", "Berlin", "DE"),
])
def test_round_trip_deep_link(origin, city, country):
    task = build(trip(origin_city=origin, city=city, country=country))
    assert set(task) == KEYS
    assert parse_qs(urlsplit(task["start_url"]).query) == {
        "from": [origin], "to": [city], "out": ["2027-03-20"], "ret": ["2027-03-22"],
        "pax": ["2"],
    }
    assert task["start_url"].isascii()
    assert task["max_steps"] == 40
    assert task["allowed_hosts"] == ["tickets.rail.example"]
    assert task["expected"]["origin_city"] == origin
    assert task["expected"]["kind"] == "transport"
    for text in ("arriving on or before 2027-03-20", "return departing on",
                 "2027-03-22", "date_mismatch", "unreviewed_redirect", "one-way",
                 "Unselected result lists or a homepage are NOT ready",
                 "Selected outbound and return", "No connections message"):
        assert text in task["instructions"]
    assert "selected outbound" in task["success_signal"]


def test_origin_country_override_and_unknown_origin():
    task = build(trip(origin_city="Smallville", origin_country="France"))
    assert "Smallville" in task["start_url"]
    with pytest.raises(ValueError):
        build(trip(origin_city="Smallville"))
    with pytest.raises(ValueError):
        build(trip(origin_country="Narnia"))


def test_unsupported_route_blocks_honestly():
    with pytest.raises(ValueError, match="no policy-reviewed transport"):
        build(trip(origin_city="London"))
    with pytest.raises(ValueError, match="no policy-reviewed transport"):
        build(trip(city="Reykjavik", country="Iceland"))


@pytest.mark.parametrize("reg", [
    registry(transport_entry(automation="prohibited")),
    registry(transport_entry(screenshot_scope="none")),
    registry(transport_entry(reviewed_at="2025-01-01", expires_at="2025-06-01")),
    registry(transport_entry(purposes=["hotel"])),
])
def test_policy_gaps_block(reg):
    with pytest.raises(ValueError):
        build(trip(), reg)


def test_committed_registry_blocks_unreviewed_transport():
    for data in (trip(origin_city="London"), trip(origin_city="Paris",
                 city="Reykjavik", country="IS")):
        with pytest.raises(ValueError):
            build_task(data, today=TODAY)


def test_committed_registry_portugal_rail_round_trip_deep_link():
    task = build_task(trip(), today=TODAY)
    assert task["start_url"] == (
        "https://www.cp.pt/pt/resultado-pesquisa?departureStation=94-2006"
        "&arrivalStation=94-31039&startDate=2027-03-20&endDate=2027-03-22"
        "&passageiros=2&selectedClass=2"
    )
    assert "Não foram encontrados resultados" in task["instructions"]


@pytest.mark.parametrize("changes", [
    {"arrival_date": "2027-03-22", "departure_date": "2027-03-20"},
    {"arrival_date": "2027-03-21", "departure_date": "2027-03-21"},
    {"arrival_date": "2027-03-22", "departure_date": "2027-03-24", "nights": 2},
    {"travelers": 0}, {"travelers": 12}, {"budget_eur": -5},
    {"race_changes": {"race_date": "2025-03-21"}},
    {"race_changes": {"date_status": "unknown", "race_date": None}},
    {"origin_city": " "},
])
def test_rejects_invalid(changes):
    with pytest.raises(ValueError):
        build(trip(**changes))


def test_missing_and_empty():
    for value in ({}, None, []):
        with pytest.raises(ValueError):
            build(value)
    data = trip()
    del data["departure_date"]
    with pytest.raises(ValueError):
        build(data)


def test_guardrails():
    task = build(trip())
    for rule in ("passenger details", "login", "payment", "captcha", "any form submission"):
        assert any(rule in s for s in task["stop_before"])
    for rule in ("Never fill or submit any form", "solve captchas", "reseller"):
        assert rule in task["instructions"]


def test_numbered_prompt_p4_reasons_and_early_inventory_stop():
    task = build(trip())
    instructions = task["instructions"]
    assert instructions.startswith("1. DATE CHECK first:")
    assert [int(n) for n in re.findall(r"^(\d+)\.", instructions, re.MULTILINE)] == list(range(1, 9))
    assert "Within your first ~10 steps" in instructions
    assert "report BLOCKED no_inventory immediately — do not wander until the step limit" in instructions
    assert "Never change the dates or submit search forms" in instructions
    assert "STOP on any other host" in instructions
    assert set(re.findall(r"report BLOCKED ([a-z_]+)", instructions)) == {
        "no_site_coverage", "policy_denied", "date_mismatch", "no_inventory", "sold_out",
        "login_required", "captcha", "consent_required", "unreviewed_redirect", "over_budget",
        "step_limit", "session_failed", "timeout", "unsafe_claim", "provider_error",
    }
    assert "reviewed selection page" in task["success_signal"]
    assert "full round-trip total" in task["success_signal"]
    assert "before passenger details, personal data or payment" in task["success_signal"]
    assert "report BLOCKED unsafe_claim" in task["success_signal"]
    assert set(task) == KEYS and task["max_steps"] <= 40
    assert task["fallback_url"] == task["start_url"]
    assert urlsplit(task["fallback_url"]).hostname == "tickets.rail.example"
    assert urlsplit(task["fallback_url"]).path not in ("", "/")


@pytest.mark.parametrize("rail_covers", [True, False])
def test_train_preferred_and_flight_fallback_with_reviewed_destination(rail_covers):
    flight = transport_entry(id="flight")
    flight["scopes"] = [{"host": "tickets.flight.example", "path_prefix": "/"}]
    flight["adapters"][0].update({
        "mode": "flight", "places": {"Lisbon": {"iata": "LIS"}},
    })
    flight["adapters"][0]["url_template"] = flight["adapters"][0]["url_template"].replace(
        "tickets.rail.example", "tickets.flight.example",
    ) + "&airport={iata}"
    rail = copy.deepcopy(flight)
    rail["id"] = "rail"
    rail["scopes"] = [{"host": "tickets.rail.example", "path_prefix": "/"}]
    rail["adapters"][0].update({
        "mode": "rail", "origin_countries": ["PT"] if rail_covers else ["CH"],
        "places": {"Lisbon": {"station_name": "Lisboa Santa Apolónia", "station_code": "LIS"}},
        "url_template": flight["adapters"][0]["url_template"].replace(
            "airport={iata}", "station={station_code}",
        ).replace("tickets.flight.example", "tickets.rail.example"),
    })
    reg = registry(flight, rail)
    original = copy.deepcopy(reg)
    task = build(trip(), reg)
    assert reg == original
    assert task["site_name"] == ("rail" if rail_covers else "flight")
    assert ("round-trip train" if rail_covers else "round-trip flight") in task["instructions"]
    destination = "Lisbon via Lisboa Santa Apolónia, LIS" if rail_covers else "Lisbon via LIS"
    assert destination in task["instructions"]
    assert set(task) == KEYS


def test_flight_airport_mapping_keeps_expected_city():
    flight = transport_entry()
    flight["adapters"][0].update({
        "mode": "flight", "places": {"freiburg im breisgau": {"iata": "BSL"}},
    })
    flight["adapters"][0]["url_template"] += "&airport={iata}"
    task = build(trip(city="Freiburg im Breisgau", country="DE"), registry(flight))
    assert "Freiburg im Breisgau via BSL" in task["instructions"]
    assert task["expected"]["city"] == "Freiburg im Breisgau"
    assert "airport=BSL" in task["start_url"]
