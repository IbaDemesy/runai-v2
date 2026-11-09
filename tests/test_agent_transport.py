import copy
import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from test_site_policy import (
    CITY_ALIAS_CASES,
    TODAY,
    assert_task_policy,
    distinct_entry,
    registry,
    transport_entry,
)

from runai.agents import hclient, site_policy
from runai.agents.site_policy import city_name, coverage
from runai.agents.transport import build_task

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts", "checkpoint"}

ROUTE_MATRIX = [
    ("Paris", "Milan", "IT", "sbb-ch", "vueling-com", None),
    ("Lyon", "Milan", "IT", "sbb-ch", None, None),
    ("Geneva", "Milan", "IT", "sbb-ch", None, None),
    ("Paris", "Amsterdam", "NL", "ns-international", None, None),
    ("Geneva", "Zurich", "CH", "sbb-ch", "ns-international", None),
    *[("Paris", city, country, None, None, None) for city, country in [
        ("Lisbon", "PT"), ("Zurich", "CH"), ("Barcelona", "ES"), ("Madrid", "ES"),
        ("Valencia", "ES"), ("Seville", "ES"), ("Rome", "IT"), ("Den Haag", "NL"),
        ("Lyon", "FR"), ("Porto", "PT"), ("Berlin", "DE"), ("Geneva", "CH"),
        ("Stoos", "CH"), ("Morschach", "CH"), ("Brunnen", "CH"),
    ]],
    ("Brussels", "Amsterdam", "NL", None, None, None),
    ("Geneva", "Lucerne", "CH", None, None, None),
    ("Lyon", "Barcelona", "ES", None, None, None),
]


def synthetic_gateway_registry():
    reg = json.loads(site_policy.REGISTRY_PATH.read_text())
    fragment = site_policy.REGISTRY_PATH.parent / "site-policy.d" / "transport.json"
    reg["entries"].extend(json.loads(fragment.read_text())["entries"])
    for item in reg["entries"]:
        if item["id"] == "ns-international":
            for adapter in item["adapters"]:
                if "den haag" in adapter.get("places", {}):
                    adapter["h_render_verified_at"] = "2026-11-09"
    return reg


@pytest.mark.parametrize("origin,city,country,primary,alternative,gateway", ROUTE_MATRIX)
def test_committed_transport_route_matrix(origin, city, country, primary, alternative,
                                          gateway, monkeypatch):
    result = coverage("transport", city=city, origin_city=origin, today=TODAY)
    assert result["covered"] is bool(primary)
    if primary is None:
        assert result["policy_ids"] == []
        with pytest.raises(ValueError, match="no policy-reviewed"):
            build_task(trip(origin_city=origin, city=city, country=country, travelers=1),
                       today=TODAY)
        return
    assert result["policy_ids"][0] == primary
    selected = site_policy.select_adapters(
        "transport", {"city": city, "country": country, "origin_city": origin,
                      "travelers": 1, "arrival_date": "2027-01-09",
                      "departure_date": "2027-01-11"},
        origin_country=site_policy.city_country(origin), today=TODAY, modes=("rail", "flight"),
    )
    assert selected[0][0]["h_render_verified_at"] == "2026-11-09"
    task = build_task(trip(
        origin_city=origin, city=city, country=country, travelers=1,
        arrival_date="2027-01-09", departure_date="2027-01-11",
        race_changes={"race_date": "2027-01-10"},
    ), today=TODAY)
    assert task["site_name"] == primary
    assert task["expected"]["city"] == city
    assert task["expected"].get("gateway_city") == gateway
    if alternative:
        assert alternative in {t["site_name"] for t in task["alternatives"]}
    for candidate in [task, *task.get("alternatives", [])]:
        if candidate["site_name"] == "ns-international":
            assert candidate["keep_fragment"] is True
            assert hclient._safe_start_fragment(candidate["start_url"],
                                                hclient.scrub_url(candidate["start_url"]))
    assert_task_policy(task, monkeypatch)


def test_documented_geneva_lucerne_gap():
    assert not coverage("transport", city="Lucerne", origin_city="Geneva",
                        today=TODAY)["covered"]
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(origin_city="Geneva", city="Lucerne", country="CH", travelers=1),
                   today=TODAY)


@pytest.mark.parametrize("fragment,retained", [
    ("", False),
    ("#/search/FRPNO/NLASC/20270109?pax=A&inboundDate=20270111", True),
    ("#/search/FRPNO/NLASC/20270109?token=private", False),
])
def test_keep_fragment_only_for_unchanged_public_routes(fragment, retained):
    item = transport_entry()
    item["adapters"][0]["url_template"] = "https://tickets.rail.example/results" + fragment
    task = build(trip(), registry(item))
    assert task.get("keep_fragment", False) is retained


@pytest.mark.parametrize("origin,city,country", [
    ("Paris", "Lyon", "FR"), ("Paris", "Porto", "PT"),
    ("Paris", "Stoos", "CH"), ("Brussels", "Amsterdam", "NL"),
    ("Geneva", "Zurich", "CH"),
])
def test_new_route_party_sizes_fail_closed(origin, city, country):
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(origin_city=origin, city=city, country=country, travelers=2),
                   today=TODAY)


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


@pytest.mark.parametrize("alias,canonical,country", CITY_ALIAS_CASES)
def test_transport_alias_tasks(alias, canonical, country):
    reg = registry(transport_entry())
    reg["entries"][0]["adapters"][0]["destination_countries"] = [country]
    reg["entries"][0]["adapters"][0]["places"] = {canonical: {"station_code": "TEST"}}
    reg["entries"][0]["adapters"][0]["url_template"] += "&station={station_code}"
    a = build(trip(city=alias, country=country), reg)
    b = build(trip(city=canonical, country=country), reg)
    assert a["start_url"] == b["start_url"]
    assert a["expected"]["city"] == alias and b["expected"]["city"] == canonical


@pytest.mark.parametrize("city,gateway", [
    ("Bijlmer", "Amsterdam"), ("Amsterdam-Zuidoost", "Amsterdam"),
    ("The Hague", "Amsterdam"), ("Amsterdam", None),
])
def test_alias_gateway_accepts_canonical_transport_evidence(city, gateway):
    reg = synthetic_gateway_registry()
    task = build_task(trip(city=city, country="NL", origin_city="Paris", travelers=1),
                      today=TODAY, registry=reg)
    for candidate in [task, *task.get("alternatives", [])]:
        expected = candidate["expected"]
        assert expected["city"] == city
        if gateway is None:
            assert "gateway_city" not in expected
        else:
            assert expected["gateway_city"] == gateway
            assert hclient._matches_expected("city", gateway, expected["gateway_city"])
        if city == "Bijlmer":
            assert not hclient._matches_expected("city", "Amsterdam", expected["city"])


@pytest.mark.parametrize("city", ["Den Haag", "The Hague", "'s-Gravenhage"])
def test_transport_gateway_city_keeps_race_city(city, monkeypatch):
    reg = synthetic_gateway_registry()
    task = build_task(trip(city=city, country="NL", origin_city="Paris", travelers=1),
                      today=TODAY, registry=reg)
    assert task["expected"]["city"] == city
    assert task["expected"]["gateway_city"] == "Amsterdam"
    assert_task_policy(task, monkeypatch, reg)


@pytest.mark.parametrize("origin,city,country", [
    ("Porto", "Lisbon", "Portugal"), ("Paris", "Milan", "Italy"), ("Zürich", "Berlin", "DE"),
])
def test_round_trip_deep_link(origin, city, country):
    task = build(trip(origin_city=origin, city=city, country=country))
    assert set(task) == KEYS
    assert parse_qs(urlsplit(task["start_url"]).query) == {
        "from": [city_name(origin)], "to": [city_name(city)],
        "out": ["2027-03-20"], "ret": ["2027-03-22"],
        "pax": ["2"],
    }
    assert task["start_url"].isascii()
    assert task["max_steps"] == 60
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


def test_committed_registry_portugal_without_render_evidence_blocks():
    with pytest.raises(ValueError, match="no policy-reviewed transport"):
        build_task(trip(), today=TODAY)


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
    assert set(task) == KEYS and task["max_steps"] == 60
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


@pytest.mark.parametrize("city,country,policy", [
    ("Milan", "IT", "sbb-ch"), ("Amsterdam", "NL", "ns-international"),
])
def test_paris_verified_routes_and_unverified_flight_alternative(city, country, policy,
                                                                 monkeypatch):
    task = build_task(trip(city=city, country=country, origin_city="Paris", travelers=1,
                          arrival_date="2027-01-09", departure_date="2027-01-11",
                          race_changes={"race_date": "2027-01-10"}), today=TODAY)
    assert task["site_name"] == policy
    assert_task_policy(task, monkeypatch)
    if city == "Milan":
        flight = next(t for t in task["alternatives"] if t["site_name"] == "vueling-com")
        query = parse_qs(urlsplit(flight["start_url"]).query)
        assert query["o"] == ["ORY"] and query["d"] == ["MXP"]
        assert query["adt"] == ["1"]
    else:
        assert task["keep_fragment"] is True
        assert "#/search/FRPNO/NLASC/20270109?pax=A&inboundDate=20270111" in task["start_url"]
        assert "At the first loaded NS booking page" in task["instructions"]


@pytest.mark.parametrize("origin", ["Lyon", "Genève"])
@pytest.mark.parametrize("city", ["Barcelona", "Valencia"])
def test_unverified_flight_only_routes_block(origin, city):
    with pytest.raises(ValueError, match="no policy-reviewed transport"):
        build_task(trip(city=city, country="ES", origin_city=origin, travelers=1), today=TODAY)


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


@pytest.mark.parametrize("city,verified", [
    ("Amsterdam", True), ("Den Haag via Amsterdam", True),
    ("Rotterdam", False), ("", False),
])
def test_gateway_city_verifier_requires_reviewed_city_and_checkpoint(city, verified):
    reg = synthetic_gateway_registry()
    task = build_task(trip(city="Den Haag", country="NL", origin_city="Paris", travelers=1),
                      today=TODAY, registry=reg)
    url = task["start_url"].split("#", 1)[0]
    answer = {"verification": {
        "origin_city": "Paris", "city": city, "arrival_date": "2027-03-20",
        "departure_date": "2027-03-22", "travelers": 1, "fare": "Public round trip",
        "total": "EUR 120", "outbound_selected": True, "return_selected": True,
        "selected": True, "next_safe_boundary": "Passenger details",
    }}
    reviews = [(set(task["allowed_hosts"]), ("/",))]
    assert task["expected"]["city"] == "Den Haag"
    assert task["expected"]["gateway_city"] == "Amsterdam"
    assert not hclient._verified(task, answer, url, url, url, reviews)
    synthetic_review_url = url + "review"
    assert hclient._verified(task, answer, synthetic_review_url, synthetic_review_url,
                             synthetic_review_url, reviews) is verified


@pytest.mark.parametrize("origin,origin_stop", [
    ("Paris", "Paris Gare de Lyon_I8768600"), ("Lyon", "Lyon Part Dieu_I8772319"),
    ("Genève", "Genève_I8501008"),
])
def test_sbb_escaped_stations_and_safe_full_adult_round_trip_instructions(origin, origin_stop,
                                                                        monkeypatch):
    task = build_task(trip(origin_city=origin, city="Milano", country="IT", travelers=1),
                      today=TODAY)
    assert task["site_name"] == "sbb-ch"
    query = parse_qs(urlsplit(task["start_url"]).query)
    assert query == {"stops": [origin_stop + "~Milano Centrale_I8301700"],
                     "day": ["2027-03-20"], "time": ["08_00"], "moment": ["dep"]}
    assert task["start_url"].isascii()
    assert "%20" in task["start_url"]
    assert task["expected"]["city"] == "Milano"
    for phrase in ("no return-date or party URL parameters", "necessary-only",
                   "never accept consent", "1 adult without reduction/Half-Fare",
                   "return departing on 2027-03-22", "before passenger details, login or payment"):
        assert phrase in task["instructions"]
    assert task["max_steps"] == 60
    assert_task_policy(task, monkeypatch)


@pytest.mark.parametrize("policy", ["sbb-ch", "ns-international", "cp-pt", "vueling-com"])
def test_transport_checkpoint_guesses_exclude_results_and_benign_party_queries(policy):
    item = next(e for e in site_policy.load_registry() if e["id"] == policy)
    for adapter in item["adapters"]:
        compiled = hclient._checkpoint({"checkpoint": adapter["checkpoint"]})
        values = dict.fromkeys(adapter["uses"], "1")
        values.update(next(iter(adapter["places"].values()), {}))
        values.update(next(iter(adapter["origin_places"].values()), {}))
        start_url = adapter["url_template"].format(**values)
        assert not hclient._checkpoint_matches(compiled, "url_patterns", start_url)
        assert not hclient._checkpoint_matches(compiled, "beyond_patterns", start_url)
        for path in ("/en?stops=x&day=2027-01-09", "/en?stops=x&trip=preview",
                     "/en/traintickets-v3/?pax=A&guests=1"):
            url = "https://example.test" + path
            assert not hclient._checkpoint_matches(compiled, "url_patterns", url)
            assert not hclient._checkpoint_matches(compiled, "beyond_patterns", url)
        for path in ("/en/passenger-details", "/en/login", "/en/payment", "/en/checkout",
                     "/en?step=passenger_details", "/en?screen=payment&pax=A",
                     "/en/traintickets-v3/review/login", "/booking/review/login",
                     "/pt/resumo-compra?step=login",
                     "/en/buying/pages/offerte/offerte.xhtml?screen=personal_details",
                     "/en/offer?screen=personal_details", "/en/offer?step=login"):
            url = "https://example.test" + path
            assert hclient._checkpoint_matches(compiled, "beyond_patterns", url)
            assert not hclient._checkpoint_matches(compiled, "url_patterns", url)
    if policy == "sbb-ch":
        for adapter in item["adapters"]:
            boundary = hclient._checkpoint({"checkpoint": adapter["checkpoint"]})
            for path in ("/customer/en/alw/onboarding",
                         "/customer/en/alw/onboarding?su=redacted&cu=redacted"):
                url = "https://shop.sbb.ch" + path
                assert hclient._checkpoint_matches(boundary, "beyond_patterns", url)
                assert not hclient._checkpoint_matches(boundary, "url_patterns", url)
            for path in ("/customer/en/alw/onboarding-offers", "/en?guests=1&pax=A"):
                assert not hclient._checkpoint_matches(
                    boundary, "beyond_patterns", "https://shop.sbb.ch" + path,
                )
        assert hclient._checkpoint_matches(
            compiled, "url_patterns",
            "https://www.sbb.ch/en/offer?stops=public-stations&trip=synthetic&retTrip=synthetic",
        )
        for path in ("/en?trip=synthetic", "/en/plan/return?trip=synthetic&retTrip=synthetic",
                     "/en/buying/pages/offerte/offerte.xhtml", "/en/offers", "/en/offer/login"):
            assert not hclient._checkpoint_matches(
                compiled, "url_patterns", "https://www.sbb.ch" + path,
            )
