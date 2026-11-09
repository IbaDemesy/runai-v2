import asyncio
import copy
import json
import re
from urllib.parse import parse_qs, urlsplit

import httpx
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
from runai.agents.transport import _candidate_task, build_task

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts", "checkpoint"}

OMIO_START = (
    "https://www.omio.com/links/626fa8a9-f982-43d0-ace9-9a13f6b14612"
    "?departurePosTerm=Paris&arrivalPosTerm=Milan&departureDate=2027-01-29"
    "&returnDate=2027-01-31&adults=1"
)
OMIO_RUNNABLE = hclient._public_https(hclient.scrub_url(OMIO_START))
GOOGLE_SELECTED_URL = (
    "https://www.google.com/travel/flights/booking?tfs="
    "CBwQAhooEgoyMDI3LTAxLTI4agwIAhIIL20vMDVxdGpyDAgDEggvbS8wcjBsbRoo"
    "EgoyMDI3LTAxLTMwagwIAxIIL20vMHIwbG1yDAgCEggvbS8wNXF0akABSAFwAYIB"
    "Cwj___________8BmAEB&tfu=EgYIABAAGAA&hl=en"
)
GOOGLE_VERIFIED = {("Paris", city) for city in ("Milan", "Berlin", "Lisbon", "Valencia")} | {
    ("Geneva", "Barcelona"),
}
NS_RUNNABLE = {("Paris", "Amsterdam")}
SBB_RUNNABLE = {("Lyon", "Milan"), ("Geneva", "Milan"), ("Geneva", "Zurich")}


def runnable_primary(origin, city, travelers=1):
    pair = (city_name(origin), city_name(city))
    if pair in GOOGLE_VERIFIED:
        return "google-travel-google-terms"
    if OMIO_RUNNABLE and pair[0] in {"Paris", "Lyon", "Geneva", "Brussels"} and pair[1] in {
        "Milan", "Berlin", "Lisbon", "Zurich", "Madrid", "Barcelona", "Den Haag",
        "Brunnen", "Stoos", "Lucerne", "Amsterdam", "Valencia",
    }:
        return "omio-com"
    if travelers == 1 and pair in SBB_RUNNABLE:
        return "sbb-ch"
    if travelers == 1 and pair in NS_RUNNABLE:
        return "ns-international"
    return None


def assert_runnable_tasks(task):
    for candidate in [task, *task.get("alternatives", [])]:
        assert candidate["fallback_url"] == candidate["start_url"]
        for key in ("start_url", "fallback_url"):
            url = candidate[key]
            assert hclient._public_https(url)
            assert hclient._public_https(hclient.scrub_url(url))
        if candidate.get("keep_fragment"):
            assert hclient._safe_start_fragment(candidate["start_url"],
                                                hclient.scrub_url(candidate["start_url"]))

ROUTE_MATRIX = [
    ("Paris", "Milan", "IT", "omio-com", "google-travel-google-terms", None),
    ("Lyon", "Milan", "IT", "omio-com", "sbb-ch", None),
    ("Geneva", "Milan", "IT", "omio-com", "sbb-ch", None),
    ("Paris", "Amsterdam", "NL", "omio-com", "ns-international", None),
    ("Geneva", "Zurich", "CH", "omio-com", "ns-international", None),
    ("Paris", "Barcelona", "ES", "omio-com", "google-travel-google-terms", None),
    ("Paris", "Den Haag", "NL", "omio-com", "ns-international", "Rotterdam"),
    *[("Paris", city, country, None, None, None) for city, country in [
        ("Seville", "ES"), ("Rome", "IT"),
        ("Lyon", "FR"), ("Porto", "PT"), ("Geneva", "CH"), ("Morschach", "CH"),
    ]],
    ("Brussels", "Amsterdam", "NL", "omio-com", "google-travel-google-terms", None),
    ("Geneva", "Lucerne", "CH", "omio-com", "google-travel-google-terms", "Zurich"),
    ("Lyon", "Barcelona", "ES", "omio-com", "google-travel-google-terms", None),
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
    assert result["covered"] is bool(runnable_primary(origin, city))
    if primary is None:
        assert result["policy_ids"] == []
        with pytest.raises(ValueError, match="no policy-reviewed"):
            build_task(trip(origin_city=origin, city=city, country=country, travelers=1),
                       today=TODAY)
        return
    runnable = runnable_primary(origin, city)
    if runnable is None:
        with pytest.raises(ValueError, match="no policy-reviewed"):
            build_task(trip(origin_city=origin, city=city, country=country, travelers=1),
                       today=TODAY)
        return
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
    assert task["site_name"] == runnable
    assert_runnable_tasks(task)
    assert task["expected"]["city"] == city
    assert task["expected"].get("gateway_city") == gateway
    for candidate in [task, *task.get("alternatives", [])]:
        if candidate["site_name"] == "ns-international":
            assert candidate["keep_fragment"] is True
            assert hclient._safe_start_fragment(candidate["start_url"],
                                                hclient.scrub_url(candidate["start_url"]))
    assert_task_policy(task, monkeypatch)


def test_geneva_lucerne_uses_rendered_zurich_gateway():
    assert coverage("transport", city="Lucerne", origin_city="Geneva", today=TODAY)["covered"] is (
        OMIO_RUNNABLE
    )
    if not OMIO_RUNNABLE:
        with pytest.raises(ValueError, match="no policy-reviewed"):
            build_task(trip(origin_city="Geneva", city="Lucerne", country="CH", travelers=1),
                       today=TODAY)
        return
    task = build_task(trip(origin_city="Geneva", city="Lucerne", country="CH", travelers=1),
                      today=TODAY)
    assert task["expected"]["city"] == "Lucerne"
    assert task["expected"]["gateway_city"] == "Zurich"
    assert parse_qs(urlsplit(task["start_url"]).query)["arrivalPosTerm"] == ["Zurich"]


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
    reg = copy.deepcopy(registry() if reg is None else reg)
    for entry in reg["entries"]:
        for adapter in entry.get("adapters", []):
            adapter.setdefault("query_encoding", "form")
    return build_task(data, today=TODAY, registry=reg)


@pytest.mark.parametrize("alias,canonical,country", CITY_ALIAS_CASES)
def test_transport_alias_tasks(alias, canonical, country):
    reg = registry(transport_entry())
    reg["entries"][0]["adapters"][0]["destination_countries"] = [country]
    reg["entries"][0]["adapters"][0]["query_encoding"] = "form"
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
        if candidate["site_name"] == "omio-com":
            expected_gateway = "Rotterdam" if city_name(city) == "Den Haag" else (
                city_name(city) if city_name(city) != city else None
            )
            assert expected.get("gateway_city") == expected_gateway
            continue
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
    assert task["expected"]["gateway_city"] == ("Rotterdam" if OMIO_RUNNABLE else "Amsterdam")
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
    ("Milan", "IT", "omio-com"), ("Amsterdam", "NL", "omio-com"),
])
def test_paris_verified_routes_and_unverified_flight_alternative(city, country, policy,
                                                                 monkeypatch):
    task = build_task(trip(city=city, country=country, origin_city="Paris", travelers=1,
                          arrival_date="2027-01-09", departure_date="2027-01-11",
                          race_changes={"race_date": "2027-01-10"}), today=TODAY)
    assert task["site_name"] == runnable_primary("Paris", city)
    assert_task_policy(task, monkeypatch)
    if city == "Milan":
        flight = task
        query = parse_qs(urlsplit(flight["start_url"]).query)
        assert "PAR to MIL" in query["q"][0]
        assert "for one adult" in query["q"][0]
    else:
        task = next(t for t in [task, *task.get("alternatives", [])]
                    if t["site_name"] == "ns-international")
        assert task["keep_fragment"] is True
        assert "#/search/FRPNO/NLASC/20270109?pax=A&inboundDate=20270111" in task["start_url"]
        assert "At the first loaded NS booking page" in task["instructions"]


@pytest.mark.parametrize("origin,city", [
    ("Lyon", "Barcelona"), ("Lyon", "Valencia"), ("Genève", "Valencia"),
])
def test_previously_unverified_routes_now_have_omio_fares(origin, city):
    if not OMIO_RUNNABLE:
        with pytest.raises(ValueError, match="no policy-reviewed"):
            build_task(trip(city=city, country="ES", origin_city=origin, travelers=1), today=TODAY)
        return
    task = build_task(trip(city=city, country="ES", origin_city=origin, travelers=1), today=TODAY)
    assert task["site_name"] == "omio-com"
    assert task["alternatives"]


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
    task = next(t for t in [task, *task.get("alternatives", [])]
                if t["site_name"] == "ns-international")
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
    expected = site_policy.trip_expected(
        trip(origin_city=origin, city="Milano", country="IT", travelers=1), "transport", today=TODAY,
    )
    candidates = site_policy.select_adapters(
        "transport", expected, origin_country=site_policy.city_country(origin), today=TODAY,
    )
    candidate = next(c for c in candidates if c[2]["policy_id"] == "sbb-ch")
    task = _candidate_task(expected, None, *candidate)
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
        for path in ("/en?trip=synthetic", "/en/plan/return?trip=synthetic&retTrip=synthetic",
                     "/en/buying/pages/offerte/offerte.xhtml", "/en/offers", "/en/offer/login"):
            assert not hclient._checkpoint_matches(
                compiled, "url_patterns", "https://www.sbb.ch" + path,
            )


@pytest.mark.parametrize("query", [
    "", "?trip=synthetic", "?trip=synthetic&retDay=2027-01-11",
    ("?stops=public-stations&day=2027-01-09&trip=synthetic&retDay=2027-01-11"
     "&retMoment=dep&retTime=08_00&retTrip=synthetic"),
])
def test_sbb_outbound_offer_never_forces_answer_even_with_return_connection(query):
    item = next(e for e in site_policy.load_registry() if e["id"] == "sbb-ch")
    for adapter in item["adapters"]:
        compiled = hclient._checkpoint({"checkpoint": adapter["checkpoint"]})
        url = "https://www.sbb.ch/en/offer" + query
        assert not hclient._checkpoint_matches(compiled, "url_patterns", url)
        assert not hclient._checkpoint_matches(compiled, "beyond_patterns", url)


R7_DESTINATIONS = {
    "Milan": "IT", "Lisbon": "PT", "Berlin": "DE", "Amsterdam": "NL",
    "The Hague": "NL", "Zurich": "CH", "Brunnen": "CH", "Stoos": "CH", "Lucerne": "CH",
    "Valencia": "ES", "Madrid": "ES", "Barcelona": "ES",
}
R7_ORIGINS = ("Paris", "Lyon", "Brussels", "Geneva")


def allow_public_omio_links(monkeypatch):
    from runai.agents import scrub

    original = scrub.scrub_url

    def clean(url):
        if isinstance(url, str) and url.startswith(
            "https://www.omio.com/links/626fa8a9-f982-43d0-ace9-9a13f6b14612?",
        ):
            return url
        return original(url)

    monkeypatch.setattr(scrub, "scrub_url", clean)


@pytest.mark.parametrize("origin", R7_ORIGINS)
@pytest.mark.parametrize("city,country", R7_DESTINATIONS.items())
def test_r8_historical_48_with_core_omio_exemption(origin, city, country, monkeypatch):
    allow_public_omio_links(monkeypatch)
    task = build_task(trip(origin_city=origin, city=city, country=country), today=TODAY)
    assert coverage("transport", city=city, country=country, origin_city=origin,
                    today=TODAY)["covered"]
    assert task.get("alternatives")
    for candidate in [task, *task["alternatives"]]:
        assert site_policy.transport_url_runnable(candidate["start_url"])
    selected = site_policy.select_adapters(
        "transport", task["expected"], origin_country=site_policy.city_country(origin),
        today=TODAY, modes=("rail", "flight"), url_filter=site_policy.transport_url_runnable,
    )
    assert selected[0][0]["h_render_verified_at"]


def test_r8_without_core_exemption_omio_is_not_emitted(monkeypatch):
    from runai.agents import scrub

    original = scrub.scrub_url
    monkeypatch.setattr(scrub, "scrub_url", lambda url: None if "/links/" in url else original(url))
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(origin_city="Lyon", city="Zurich", country="CH"), today=TODAY)
    assert not coverage("transport", city="Zurich", country="CH", origin_city="Lyon",
                        today=TODAY)["covered"]
    task = build_task(trip(origin_city="Paris", city="Valencia", country="ES"), today=TODAY)
    assert all(t["site_name"] != "omio-com" for t in [task, *task.get("alternatives", [])])


@pytest.mark.parametrize("days,blocked", [(90, False), (400, True)])
def test_r8_booking_horizon(days, blocked):
    from datetime import timedelta
    from typing import get_args

    from runai.models import ReasonCode

    out = TODAY + timedelta(days=days)
    task = build_task(trip(
        origin_city="Paris", city="Valencia", country="ES",
        arrival_date=out.isoformat(), departure_date=(out + timedelta(days=2)).isoformat(),
        race_changes={"race_date": (out + timedelta(days=1)).isoformat(),
                      "edition": str(out.year)},
    ), today=TODAY)
    assert ("preflight_block" in task) is blocked
    if blocked:
        reason = "not_yet_bookable" if "not_yet_bookable" in get_args(ReasonCode) else "no_inventory"
        assert task["preflight_block"] == {
            "reason_code": reason, "summary": "Billets pas encore en vente pour ces dates",
            "handoff_url": task["start_url"],
        }
        assert site_policy.transport_url_runnable(task["preflight_block"]["handoff_url"])


@pytest.mark.parametrize("value", [0, -1, True, "180", 1.5])
def test_r8_invalid_horizon_fails_closed(value):
    reg = registry(transport_entry())
    reg["entries"][0]["adapters"][0]["booking_horizon_days"] = value
    with pytest.raises(ValueError, match="invalid"):
        build_task(trip(), today=TODAY, registry=reg)


def test_r8_horizon_filter_precedes_candidate_cap_and_keeps_verified_primary():
    items = [distinct_entry(i, "transport") for i in range(4)]
    for index, item in enumerate(items):
        item["adapters"][0]["booking_horizon_days"] = 60 if index < 3 else 180
    task = build_task(trip(origin_city="Paris"), today=TODAY, registry=registry(*items))
    assert task["site_name"] == "site3"
    assert "preflight_block" not in task


@pytest.mark.parametrize("origin", R7_ORIGINS)
@pytest.mark.parametrize("city,country", R7_DESTINATIONS.items())
@pytest.mark.parametrize("travelers", [1, 2, 3, 4])
def test_r7_full_origin_destination_matrix(origin, city, country, travelers):
    data = trip(origin_city=origin, city=city, country=country, travelers=travelers)
    primary = runnable_primary(origin, city, travelers)
    if travelers == 1:
        assert coverage("transport", city=city, country=country, origin_city=origin,
                        today=TODAY)["covered"] is bool(primary)
    if primary is None:
        with pytest.raises(ValueError, match="no policy-reviewed"):
            build_task(data, today=TODAY)
        return
    task = build_task(data, today=TODAY)
    selected = site_policy.select_adapters(
        "transport", task["expected"], origin_country=site_policy.city_country(origin),
        today=TODAY, modes=("rail", "flight"),
    )
    assert selected[0][0]["h_render_verified_at"] == "2026-11-09"
    assert not selected[0][0]["last_resort"]
    assert task["site_name"] != "vueling-com"
    assert task["site_name"] == primary
    assert_runnable_tasks(task)
    assert all(t["site_name"] != "vueling-com" for t in task.get("alternatives", []))
    assert task["expected"]["city"] == city
    if city in {"Brunnen", "Stoos", "Lucerne"}:
        assert task["expected"]["gateway_city"] == "Zurich"
    if city == "The Hague":
        assert task["expected"]["gateway_city"] == "Rotterdam"
        assert parse_qs(urlsplit(task["start_url"]).query)["arrivalPosTerm"] == ["Rotterdam"]


def r7_lisbon_task(**changes):
    reg = changes.pop("registry", None)
    return build_task(trip(origin_city="Paris", city="Lisbon", country="PT", travelers=1,
                           arrival_date="2027-01-29", departure_date="2027-01-31",
                           race_changes={"race_date": "2027-01-30"}, **changes), today=TODAY,
                      registry=reg)


def r7_omio_task(**changes):
    reg = synthetic_gateway_registry()
    for entry in reg["entries"]:
        if entry["id"] == "omio-com":
            for adapter in entry["adapters"]:
                adapter["url_template"] = adapter["url_template"].replace(
                    "626fa8a9-f982-43d0-ace9-9a13f6b14612", "public-test-link",
                )
                adapter["priority"] = 2
    return r7_lisbon_task(registry=reg, **changes)


def test_r7_public_templates_dates_party_and_hosts():
    task = r7_lisbon_task()
    google = task
    assert task["site_name"] == "google-travel-google-terms"
    assert_runnable_tasks(task)
    assert "from PAR to LIS on Jan 29 2027 returning Jan 31 2027 for one adult" in parse_qs(
        urlsplit(google["start_url"]).query,
    )["q"][0]
    assert "consent.google.com" in google["allowed_hosts"]
    assert not any("ryanair" in host for host in google["allowed_hosts"])
    assert "+Jan+29+2027+" in google["start_url"]
    assert "exact current public browser URL as handoff_url" in google["instructions"]
    tap = next(t for t in task["alternatives"] if t["site_name"] == "flytap-com")
    assert hclient.scrub_url(tap["start_url"]) == tap["start_url"]
    query = parse_qs(urlsplit(tap["start_url"]).query)
    assert query["depDate"] == ["2027-01-29"]
    assert query["retDate"] == ["2027-01-31"]


@pytest.mark.parametrize("origin,city,country,provider", [
    ("Lyon", "Milan", "IT", "sbb-ch"),
    ("Paris", "Amsterdam", "NL", "ns-international"),
    ("Paris", "Lisbon", "PT", "flytap-com"),
])
def test_restored_links_reach_unmodified_runner_session_post(origin, city, country, provider,
                                                           monkeypatch):
    task = build_task(trip(origin_city=origin, city=city, country=country, travelers=1,
                           arrival_date="2027-01-29", departure_date="2027-01-31",
                           race_changes={"race_date": "2027-01-30"}), today=TODAY)
    task = next(t for t in [task, *task.get("alternatives", [])] if t["site_name"] == provider)
    task = {key: value for key, value in task.items() if key != "alternatives"}
    assert_task_policy(task, monkeypatch)
    clean = hclient.scrub_url(task["start_url"])
    if provider == "sbb-ch":
        assert clean != task["start_url"]
        assert parse_qs(urlsplit(clean).query) == parse_qs(urlsplit(task["start_url"]).query)
        assert parse_qs(urlsplit(clean).query)["day"] == ["2027-01-29"]
    posts = []

    def handle(request):
        if request.method == "GET" and request.url.path.endswith("/sessions/quota"):
            return httpx.Response(200, json={"limit": 3, "active": 0, "available": 3})
        assert request.method == "POST" and request.url.path.endswith("/sessions")
        posts.append(json.loads(request.content))
        return httpx.Response(400, json={"detail": "Synthetic stop after preflight"})

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            runner = hclient.HAgentRunner("synthetic-transport-key", client=client)
            return await runner.run(task)

    result = asyncio.run(execute())
    assert result["status"] == "failed"
    assert len(posts) == 1
    start = posts[0]["overrides"]["agent.environments[kind=web].start_url"]
    assert start == (task["start_url"] if task.get("keep_fragment") else clean)
    if provider == "flytap-com":
        query = parse_qs(urlsplit(start).query)
        assert query["depDate"] == ["2027-01-29"]
        assert query["retDate"] == ["2027-01-31"]


@pytest.mark.parametrize("url,accepted", [
    ("", False),
    ("http://tickets.rail.example/results", False),
    ("https://127.0.0.1/results", False),
    ("https://user@tickets.rail.example/results", False),
    ("https://tickets.rail.example/sessions/private", False),
    ("https://tickets.rail.example/results?from=Paris%20Est", True),
    ("https://tickets.rail.example/results#/search?token=private", True),
])
def test_start_gate_matches_runner_public_https_checks(url, accepted):
    assert site_policy.transport_url_runnable(url) is accepted


@pytest.mark.parametrize("error", [ImportError, RuntimeError])
def test_transport_coverage_and_builder_fail_closed_if_runner_import_fails(monkeypatch, error):
    def unavailable(name):
        raise error("Synthetic missing runner")

    monkeypatch.setattr(site_policy, "import_module", unavailable)
    reg = registry(transport_entry())
    assert not site_policy.transport_url_runnable("https://tickets.rail.example/results")
    assert coverage("transport", city="Milan", country="IT", origin_city="Paris",
                    today=TODAY, registry=reg) == {"covered": False, "policy_ids": []}
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(origin_city="Paris", city="Milan", country="IT"),
                   today=TODAY, registry=reg)
    assert coverage("hotel", city="Milan", today=TODAY, registry=registry())["covered"]


@pytest.mark.parametrize("travelers,phrase", [(1, "one adult"), (2, "2 adults"), (3, "3 adults"),
                                            (4, "4 adults")])
def test_r7_omio_google_party_encoding(travelers, phrase):
    task = build_task(trip(origin_city="Paris", city="Lisbon", country="PT", travelers=travelers),
                      today=TODAY)
    google = task
    query = parse_qs(urlsplit(google["start_url"]).query)
    assert query["q"][0].endswith(f"for {phrase}")
    assert hclient.scrub_url(google["start_url"]) == google["start_url"]


def test_r7_unsupported_party_count_is_not_promoted():
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(origin_city="Lyon", city="Lisbon", country="PT", travelers=5), today=TODAY)


def test_scrub_guard_filters_before_candidate_limit():
    items = [distinct_entry(n, "transport") for n in range(5)]
    for item in items[:3]:
        item["adapters"][0]["url_template"] = item["adapters"][0]["url_template"].replace(
            "/results?", "/sessions/private?",
        )
    task = build_task(trip(), today=TODAY, registry=registry(*items))
    assert task["site_name"] == "site3"
    assert [a["site_name"] for a in task["alternatives"]] == ["site4"]
    assert_runnable_tasks(task)


def test_scrub_guard_does_not_promote_unverified_alternative():
    items = [distinct_entry(n, "transport") for n in range(2)]
    items[0]["adapters"][0]["url_template"] = items[0]["adapters"][0]["url_template"].replace(
        "/results?", "/sessions/private?",
    )
    items[1]["adapters"][0].pop("h_render_verified_at")
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(), today=TODAY, registry=registry(*items))


def test_actual_omio_scrub_gate_is_respected_without_removing_registry_evidence():
    assert any(e["id"] == "omio-com" for e in site_policy.load_registry())
    task = build_task(trip(origin_city="Lyon", city="Milan", country="IT", travelers=1),
                      today=TODAY)
    assert task["site_name"] == ("omio-com" if OMIO_RUNNABLE else "sbb-ch")
    assert any(t["site_name"] == "omio-com" for t in [task, *task.get("alternatives", [])]) is (
        OMIO_RUNNABLE
    )


def test_google_priority_keeps_verified_google_before_runnable_omio():
    reg = synthetic_gateway_registry()
    for entry in reg["entries"]:
        if entry["id"] == "omio-com":
            for adapter in entry["adapters"]:
                adapter["url_template"] = adapter["url_template"].replace(
                    "626fa8a9-f982-43d0-ace9-9a13f6b14612", "public-test-link",
                )
    task = r7_lisbon_task(registry=reg)
    assert task["site_name"] == "google-travel-google-terms"
    assert any(t["site_name"] == "omio-com" for t in task["alternatives"])
    assert_runnable_tasks(task)


@pytest.mark.parametrize("origin", R7_ORIGINS)
def test_r7_swiss_gateway_start_urls_equal_rendered_zurich(origin):
    if not OMIO_RUNNABLE:
        for city in ("Brunnen", "Stoos", "Lucerne"):
            with pytest.raises(ValueError, match="no policy-reviewed"):
                build_task(trip(origin_city=origin, city=city, country="CH", travelers=1),
                           today=TODAY)
        return
    tasks = [build_task(trip(origin_city=origin, city=city, country="CH", travelers=1),
                        today=TODAY) for city in ("Zurich", "Brunnen", "Stoos", "Lucerne")]
    assert len({t["start_url"] for t in tasks}) == 1
    assert all(t["site_name"] == "omio-com" for t in tasks)


@pytest.mark.parametrize("policy,summary,results", [
    ("omio-com", "/app/search-frontend/journey/train/a/b/c/d", [
        "/app/search-frontend/results/id/train", "/app/search-frontend/results/id/train/id/inbound",
        "/app/search-frontend/results/id/flight", "/app/search-frontend/results/id/bus",
    ]),
    ("google-travel-google-terms", "/travel/flights/booking?tfs=public&tfu=public", [
        "/travel/flights", "/travel/flights/search", "/travel/flights/booking?hl=en",
        "/travel/flights/booking?tfs=", "/travel/flights/booking?notfs=public",
    ]),
    ("flytap-com", "/booking/review-your-trip", ["/booking/flights"]),
])
def test_r7_selected_checkpoints_exclude_observed_results(policy, summary, results):
    item = next(e for e in site_policy.load_registry() if e["id"] == policy)
    for adapter in item["adapters"]:
        cp = adapter["checkpoint"]
        assert any(re.search(p, summary, re.IGNORECASE) for p in cp["url_patterns"])
        for path in results:
            assert not any(re.search(p, path, re.IGNORECASE) for p in cp["url_patterns"])
        for path in ("/login", "/account", "/payment", "/passenger-details"):
            assert any(re.search(p, path, re.IGNORECASE) for p in cp["beyond_patterns"])


def test_google_selected_checkpoint_with_realistic_long_tfs():
    from runai.agents import scrub

    item = next(e for e in site_policy.load_registry()
                if e["id"] == "google-travel-google-terms")
    for adapter in item["adapters"]:
        checkpoint = hclient._checkpoint({"checkpoint": adapter["checkpoint"]})
        assert hclient._checkpoint_matches(checkpoint, "url_patterns", GOOGLE_SELECTED_URL)
        clean = scrub.scrub_url(GOOGLE_SELECTED_URL)
        preserved = bool(parse_qs(urlsplit(clean).query).get("tfs"))
        assert hclient._checkpoint_matches(checkpoint, "url_patterns", clean) is preserved
        assert not hclient._checkpoint_matches(
            checkpoint, "url_patterns", "https://www.google.com/travel/flights/booking?hl=en",
        )


@pytest.mark.parametrize("mode", ["train", "bus", "flight"])
def test_omio_results_are_reviewed_navigation_never_selected_checkpoints(mode):
    item = next(e for e in site_policy.load_registry() if e["id"] == "omio-com")
    for suffix in ("", "/outbound-id/inbound"):
        url = ("https://www.omio.com/app/search-frontend/results/"
               f"12345678-abcd-4321-abcd-123456789abc/{mode}{suffix}")
        decision = site_policy.evaluate_url(url, "transport", today=TODAY)
        assert decision["allowed"]
        assert decision["policy_id"] == item["id"]
        assert item["automation"] == "allowed_owner_rule"
        for adapter in item["adapters"]:
            checkpoint = hclient._checkpoint({"checkpoint": adapter["checkpoint"]})
            assert not hclient._checkpoint_matches(checkpoint, "url_patterns", url)
            assert not hclient._checkpoint_matches(checkpoint, "beyond_patterns", url)


@pytest.mark.parametrize("profile", [None, {}, [], {"email": ""}, {"email": "   "},
                                     {"nationality": "FR"}, {"phone": False}])
def test_r7_empty_or_unsupported_profile_keeps_default_stop(profile):
    task = r7_omio_task(runner_profile=profile)
    assert "prefill_fields" not in task
    assert "prefill_patterns" not in task["checkpoint"]
    assert "passenger details / personal data form" in task["stop_before"]
    assert task["checkpoint"]["url_patterns"] == ["^/app/search-frontend/journey/"]


def test_r7_prefill_is_names_only_and_unobserved_final_checkpoint_fails_closed():
    profile = {"full_name": "Test Runner", "given_name": "FixtureGiven", "family_name": "FixtureFamily",
               "email": "test.runner@example.com", "phone": "+33 6 00 00 00 00",
               "birth_date": "1990-01-01"}
    task = r7_omio_task(runner_profile=profile)
    assert task["prefill_fields"] == ["given_name", "family_name", "email", "phone", "birth_date"]
    assert task["prefill_scope"] == "passenger details"
    assert task["checkpoint"]["url_patterns"] == ["(?!)"]
    assert any(re.search(p, "/app/search-frontend/booking/id/passenger-details")
               for p in task["checkpoint"]["prefill_patterns"])
    assert "Runner profile block appended by the system" in task["instructions"]
    assert "Intermediate Continue to the next form page is allowed" in task["instructions"]
    assert "reviewed bus/flight mode tab with fares" in task["instructions"]
    assert "Disclose actual airports, including Beauvais" in task["instructions"]
    assert "Never fill or submit any form" not in task["instructions"]
    assert "Stop before opening passenger details" not in task["instructions"]
    assert "passenger details / personal data form" not in task["stop_before"]
    encoded = json.dumps(task)
    for value in profile.values():
        assert value not in encoded
    assert all("prefill_fields" not in t for t in task.get("alternatives", []))


def test_r7_two_adults_omio_rendered_milan_and_unsupported_route():
    task = build_task(trip(origin_city="Paris", city="Milan", country="IT", travelers=2),
                      today=TODAY)
    assert parse_qs(urlsplit(task["start_url"]).query)["q"][0].endswith("for 2 adults")
    with pytest.raises(ValueError, match="no policy-reviewed"):
        build_task(trip(origin_city="Paris", city="Unknown", travelers=1), today=TODAY)


def test_r7_observed_required_country_is_names_only_prefill():
    task = r7_omio_task(runner_profile={"country": "FixtureResidence"})
    assert task["prefill_fields"] == ["country"]
    assert task["checkpoint"]["url_patterns"] == ["(?!)"]
    assert "FixtureResidence" not in json.dumps(task)


def test_r7_sbb_top_offers_and_travelcard_boundaries():
    item = next(e for e in site_policy.load_registry() if e["id"] == "sbb-ch")
    for adapter in item["adapters"]:
        for path in ("/en/top-offers", "/en/travelcards/half-fare-travelcard.html",
                     "/en/ga-travelcard/purchase"):
            assert any(re.search(p, path, re.IGNORECASE)
                       for p in adapter["checkpoint"]["beyond_patterns"])
        assert not any(re.search(p, "/en/offer", re.IGNORECASE)
                       for p in adapter["checkpoint"]["beyond_patterns"])
