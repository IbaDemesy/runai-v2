from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
from test_site_policy import TODAY, entry, registry

from runai.agents.hotel import build_task

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts"}


def trip(**changes):
    race = {
        "id": "r", "name": "Example Marathon", "edition": "2027", "distance_km": 42.195,
        "distance_label": "Marathon", "race_date": "2027-04-04", "date_status": "official",
        "city": changes.pop("city", "Milan"), "country": changes.pop("country", "Italy"),
        "official_url": "https://www.example-marathon.test/", "registration_url": None,
        "source_urls": [], "retrieved_at": "2026-11-08", "synthetic": False,
    }
    race.update(changes.pop("race_changes", {}))
    return {"race": race, "origin_city": "Paris", "travelers": 2, "nights": 2,
            "budget_eur": 600, "arrival_date": "2027-04-03", "departure_date": "2027-04-05",
            **changes}


def build(data, reg=None):
    return build_task(data, today=TODAY, registry=registry() if reg is None else reg)


@pytest.mark.parametrize("city,country", [
    ("Milan", "Italy"), ("Lisbon", "Portugal"), ("München", "Germany"), ("Lisboa", "PT"),
])
def test_deep_link_encodes_exact_stay(city, country):
    task = build(trip(city=city, country=country))
    assert set(task) == KEYS
    query = parse_qs(urlsplit(task["start_url"]).query)
    assert query == {"city": [city], "in": ["2027-04-03"], "out": ["2027-04-05"],
                     "adults": ["2"]}
    assert task["start_url"].isascii()
    assert task["fallback_url"] == task["start_url"]
    assert task["max_steps"] == 80
    assert task["allowed_hosts"] == ["secure.hotels.example", "www.hotels.example"]
    assert task["site_name"] == "example-hotels"
    assert task["expected"] == {
        "kind": "hotel", "race_name": "Example Marathon", "race_date": "2027-04-04",
        "distance_km": 42.195, "city": city, "country": country, "origin_city": "Paris",
        "arrival_date": "2027-04-03", "departure_date": "2027-04-05", "travelers": 2,
    }
    for text in ("check-in 2027-04-03", "check-out 2027-04-05", "2 adults", "EUR 600",
                 "date_mismatch", "unreviewed_redirect", "www.hotels.example",
                 "Rate page shows dates", "No rooms message", "NOT ready"):
        assert text in task["instructions"]
    assert "room and rate" in task["success_signal"]
    assert "today" not in task["start_url"]


def test_non_ascii_city_percent_encoded():
    task = build(trip(city="Zürich São", country="Germany"))
    assert "Z%C3%BCrich%20S%C3%A3o" in task["start_url"]


def test_unsupported_destination_blocks_without_fallback():
    with pytest.raises(ValueError, match="no policy-reviewed hotel"):
        build(trip(city="Reykjavik", country="Iceland"))
    with pytest.raises(ValueError, match="unknown destination"):
        build(trip(country="Atlantis"))


@pytest.mark.parametrize("reg", [
    registry(entry(automation="ambiguous")), registry(entry(screenshot_scope="unclear")),
    registry(entry(expires_at="2026-11-08")), {"schema_version": 1, "entries": []},
    {"schema_version": 1, "entries": [entry(adapters=[])]}, {"bad": True},
])
def test_policy_gaps_block(reg):
    with pytest.raises(ValueError):
        build(trip(), reg)


def test_committed_registry_blocks_destination_without_reviewed_adapter():
    with pytest.raises(ValueError, match="no policy-reviewed hotel"):
        build_task(trip(), today=TODAY)


@pytest.mark.parametrize("city", ["Lisbon", "Lisboa", "LISBONNE"])
def test_committed_registry_lisbon_uses_reviewed_deep_link_with_exact_stay(city):
    task = build_task(trip(city=city, country="Portugal"), today=TODAY)
    assert task["start_url"].startswith("https://www.nh-hotels.com/es/booking/step1-rates?")
    assert "fini=03%2F04%2F2027&fout=05%2F04%2F2027" in task["start_url"]
    assert "nadults1=2" in task["start_url"]
    assert task["allowed_hosts"] == ["nh-hotels.com", "www.nh-hotels.com"]
    assert task["expected"]["arrival_date"] == "2027-04-03"


@pytest.mark.parametrize("changes", [
    {"arrival_date": "2027-04-05", "departure_date": "2027-04-03"},
    {"departure_date": "2027-04-03"}, {"arrival_date": "not-a-date"},
    {"departure_date": "2027-02-30"}, {"arrival_date": 123},
    {"arrival_date": "2027-04-05", "departure_date": "2027-04-06", "nights": 1},
    {"nights": 3}, {"travelers": 0}, {"travelers": True}, {"travelers": "2"},
    {"budget_eur": 0}, {"budget_eur": "600"}, {"budget_eur": float("nan")},
    {"race_changes": {"race_date": None}}, {"race_changes": {"race_date": "2026-11-01"}},
    {"race_changes": {"date_status": "conflicting"}},
    {"race_changes": {"edition": "2026"}},
    {"arrival_date": "2026-11-08", "departure_date": "2027-04-05", "nights": None},
])
def test_rejects_wrong_dates_and_inputs(changes):
    with pytest.raises(ValueError):
        build(trip(**changes))


def test_date_mismatch_negative_case():
    """Race on 2027-04-04 but the stay is a week later: never silently shifted."""
    with pytest.raises(ValueError, match="race date"):
        build(trip(arrival_date="2027-04-10", departure_date="2027-04-12"))


@pytest.mark.parametrize("key", ["race", "origin_city", "arrival_date", "departure_date"])
@pytest.mark.parametrize("value", [None, "", " "])
def test_missing_fields(key, value):
    with pytest.raises(ValueError):
        build(trip(**{key: value}))
    data = trip()
    del data[key]
    with pytest.raises(ValueError):
        build(data)


@pytest.mark.parametrize("key", ["city", "country"])
def test_missing_race_location(key):
    data = trip()
    data["race"][key] = " "
    with pytest.raises(ValueError):
        build(data)


def test_empty_and_invalid():
    for value in ({}, [], "Milan", None):
        with pytest.raises(ValueError):
            build(value)


def test_defaults_and_stops():
    data = trip(arrival_date=date(2027, 4, 3), departure_date=date(2027, 4, 5))
    del data["travelers"], data["budget_eur"]
    task = build(data)
    assert "1 adults" in task["instructions"]
    assert "No budget supplied" in task["instructions"]
    for rule in ("guest details", "login", "payment", "captcha", "any form submission",
                 "cookie consent acceptance"):
        assert any(rule in s for s in task["stop_before"])
    for rule in ("never fill or submit any form", "solve captchas", "log in",
                 "never accept optional consent", "Never change the dates"):
        assert rule in task["instructions"]


def test_budget_caps_selected_rate():
    task = build_task(trip(city="Lisbon", country="Portugal"), today=TODAY)
    assert "EUR 600" in task["instructions"] and "over_budget" in task["instructions"]
