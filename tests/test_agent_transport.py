import copy
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from test_site_policy import TODAY, assert_task_policy, distinct_entry, registry, transport_entry

from runai.agents import hclient
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
    assert set(task) == KEYS | ({"alternatives"} if rail_covers else set())
    if rail_covers:
        assert [a["site_name"] for a in task["alternatives"]] == ["flight"]


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


@pytest.mark.parametrize("city,country,policy,airport", [
    ("Milan", "IT", "vueling-com", "MXP"), ("Barcelona", "ES", "vueling-com", "BCN"),
    ("Lisbon", "PT", "vueling-com", "LIS"), ("Valencia", "ES", "vueling-com", "VLC"),
    ("Seville", "ES", "vueling-com", "SVQ"), ("Zurich", "CH", "vueling-com", "ZRH"),
    ("Geneva", "CH", "vueling-com", "GVA"), ("Rome", "IT", "vueling-com", "FCO"),
    ("Madrid", "ES", "vueling-com", "MAD"),
    ("Amsterdam", "NL", "ns-international", None), ("Den Haag", "NL", "ns-international", None),
])
def test_r4_paris_routes_and_policy(city, country, policy, airport, monkeypatch):
    task = build_task(trip(city=city, country=country, origin_city="Paris", travelers=1,
                          budget_eur=450, arrival_date="2027-01-09",
                          departure_date="2027-01-11",
                          race_changes={"race_date": "2027-01-10"}), today=TODAY)
    assert task["site_name"] == policy
    assert task["expected"]["city"] == city
    assert_task_policy(task, monkeypatch)
    assert set(task) == KEYS
    if airport:
        query = parse_qs(urlsplit(task["start_url"]).query)
        assert query["o"] == (["CDG"] if city == "Geneva" else ["ORY"])
        assert query["d"] == [airport]
        assert query["adt"] == ["1"]
        assert "both outbound and return fares" in task["instructions"]
    else:
        assert "#/search/FRPNO/NLASC/20270109?pax=A&inboundDate=20270111" in task["start_url"]
        assert "At the first loaded NS booking page" in task["instructions"]
        assert "STOP BLOCKED date_mismatch immediately" in task["instructions"]
    if city == "Den Haag":
        assert "Den Haag via Amsterdam Centraal" in task["instructions"]
        assert "onward Den Haag transfer not included" in task["instructions"]
        assert "without changing the race city in expected" in task["instructions"]
        assert "READY covers the round trip to/from" in task["instructions"]
        assert "mention it in the final report" in task["instructions"]
        assert "Never substitute a non-reviewed gateway" in task["instructions"]


@pytest.mark.parametrize("origin,airport", [("Lyon", "LYS"), ("Genève", "GVA")])
def test_r4_barcelona_supported_valencia_unverified(origin, airport, monkeypatch):
    data = trip(city="Barcelona", country="ES", origin_city=origin, travelers=1)
    task = build_task(data, today=TODAY)
    assert parse_qs(urlsplit(task["start_url"]).query)["o"] == [airport]
    assert_task_policy(task, monkeypatch)
    data["race"]["city"] = "Valencia"
    with pytest.raises(ValueError, match="no policy-reviewed transport"):
        build_task(data, today=TODAY)


@pytest.mark.parametrize("origin", ["Zurich", "Geneva"])
@pytest.mark.parametrize("city", ["Savognin", "Grindelwald", "Sierre"])
def test_r4_unverified_domestic_swiss_routes_fail_closed(origin, city):
    with pytest.raises(ValueError, match="no policy-reviewed transport"):
        build_task(trip(city=city, country="CH", origin_city=origin, travelers=1), today=TODAY)


def test_transport_alternatives_distinct_rail_first_and_policy(monkeypatch):
    items = [distinct_entry(n, "transport") for n in range(6)]
    for item in items:
        item["adapters"][0]["mode"] = "rail"
    items[0]["adapters"][0]["mode"] = "flight"
    items[1]["adapters"] *= 2
    items[2]["automation"] = "prohibited"
    items[3]["expires_at"] = "2026-11-08"
    reg = registry(*items)
    before = copy.deepcopy(reg)
    task = build(trip(), reg)
    assert task["site_name"] == "site1"
    assert [a["site_name"] for a in task["alternatives"]] == ["site4", "site5"]
    assert all(set(a) == KEYS for a in task["alternatives"])
    assert reg == before
    assert_task_policy(task, monkeypatch, reg)
    task["alternatives"][0]["expected"]["city"] = "Changed"
    assert task["expected"]["city"] == "Lisbon"


def test_via_text_not_url_substitution_and_still_requires_reviewed_ids():
    item = transport_entry()
    item["adapters"][0].update(places={
        "Den Haag": {"station_code": "NLASC", "via": "Amsterdam Centraal"},
    })
    item["adapters"][0]["url_template"] += "&station={station_code}"
    task = build(trip(city="Den Haag", country="DE"), registry(item))
    assert task["expected"]["city"] == "Den Haag"
    assert "Den Haag via Amsterdam Centraal" in task["instructions"]
    del item["adapters"][0]["places"]["Den Haag"]["station_code"]
    with pytest.raises(ValueError, match="no reviewed place IDs"):
        build(trip(city="Den Haag", country="DE"), registry(item))


def test_gateway_ready_is_not_supported_by_unchanged_hclient_city_verifier():
    task = build_task(trip(city="Den Haag", country="NL", origin_city="Paris", travelers=1),
                      today=TODAY)
    url = task["start_url"].split("#", 1)[0]
    answer = {"verification": {
        "origin_city": "Paris", "city": "Amsterdam", "arrival_date": "2027-03-20",
        "departure_date": "2027-03-22", "travelers": 1, "fare": "Public round trip",
        "total": "EUR 120", "outbound_selected": True, "return_selected": True,
        "selected": True, "next_safe_boundary": "Passenger details",
    }}
    reviews = [(set(task["allowed_hosts"]), ("/",))]
    assert task["expected"]["city"] == "Den Haag"
    assert not hclient._verified(task, answer, url, url, url, reviews)
    control = copy.deepcopy(task)
    control["expected"]["city"] = "Amsterdam"
    assert hclient._verified(control, answer, url, url, url, reviews)
