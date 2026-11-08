from datetime import date
from pathlib import Path

import pytest

from runai.agents.transport import build_task, select_site


def trip(**changes):
    return {
        "city": "Milan", "country": "Italy", "origin": "Paris",
        "arrival_date": "2027-04-03", "departure_date": "2027-04-05",
        "adults": 2, "budget": "EUR 600", **changes,
    }


@pytest.mark.parametrize("city,country,origin,expected", [
    ("Milan", "Italy", "Paris", "Trenitalia"),
    ("Lisbon", "Portugal", "Porto", "CP"),
    ("Zermatt", "Switzerland", "Zurich", "SBB"),
    ("Reykjavik", "Iceland", "Paris", "Google Flights"),
])
def test_destinations(city, country, origin, expected):
    task = build_task(trip(city=city, country=country, origin=origin))
    assert set(task) == {
        "kind", "site_name", "start_url", "instructions", "stop_before",
        "success_signal", "fallback_url", "max_steps",
    }
    assert task["kind"] == "transport"
    assert task["site_name"] == expected
    assert task["fallback_url"] == task["start_url"]
    assert task["max_steps"] > 0
    for value in (city, country, origin, "2027-04-03", "2027-04-05", "2", "EUR 600"):
        assert value in task["instructions"]
    for forbidden in ("booking.com", "flytap"):
        assert forbidden not in str(task).lower()


@pytest.mark.parametrize("key", ["city", "country", "origin", "arrival_date", "departure_date"])
@pytest.mark.parametrize("value", [None, "", " "])
def test_missing_inputs(key, value):
    with pytest.raises(ValueError):
        build_task(trip(**{key: value}))
    data = trip()
    del data[key]
    with pytest.raises(ValueError):
        build_task(data)


def test_empty_input():
    with pytest.raises(ValueError):
        build_task({})


@pytest.mark.parametrize("changes", [
    {"arrival_date": "not-a-date"}, {"departure_date": "2027-02-30"},
    {"departure_date": "2027-04-03"}, {"departure_date": "2027-04-02"},
    {"arrival_date": 123}, {"adults": 0}, {"adults": True}, {"adults": "2"},
])
def test_invalid_inputs(changes):
    with pytest.raises(ValueError):
        build_task(trip(**changes))


def test_dates_defaults_and_guardrails():
    data = trip(arrival_date=date(2027, 4, 3), departure_date=date(2027, 4, 5))
    del data["adults"]
    del data["budget"]
    task = build_task(data)
    assert "1 adults" in task["instructions"]
    assert "No budget supplied" in task["instructions"]
    data["travelers"] = 3
    assert "3 adults" in build_task(data)["instructions"]
    for rule in ("guest details", "passenger details", "login", "payment", "booking",
                 "account creation", "terms", "cookie consent", "form submission",
                 "personal data", "captcha"):
        assert rule in task["stop_before"]
    for rule in ("Never pay", "book", "create accounts", "accept terms", "cookie consent",
                 "submit forms", "enter personal data", "bypass captchas", "report blocked"):
        assert rule in task["instructions"]
    assert "blocked" in task["success_signal"]
    source = Path(__file__).parents[1] / "runai" / "agents" / "transport.py"
    assert all(term not in source.read_text().lower() for term in ("booking.com", "flytap"))


@pytest.mark.parametrize("country,expected", [
    ("IT", "Trenitalia"), ("CH", "SBB"), ("France", "SNCF Connect"),
    ("Spain", "Renfe"), ("Portugal", "CP"), ("Germany", "DB"),
])
def test_domestic_rule_table(country, expected):
    task = build_task(trip(country=country, origin_country=country))
    assert task["site_name"] == expected
    assert "rail search" in task["instructions"]


@pytest.mark.parametrize("first,second,expected", [
    ("FR", "IT", "Trenitalia"), ("CH", "IT", "Trenitalia"),
    ("FR", "CH", "SBB"), ("DE", "CH", "SBB"), ("DE", "FR", "DB"),
])
def test_cross_border_rules_bidirectional(first, second, expected):
    for source, destination in ((first, second), (second, first)):
        assert select_site(trip(origin_country=source, country=destination))[1] == expected


@pytest.mark.parametrize("changes", [
    {"origin": "Unknown town"}, {"origin_country": "US"},
    {"country": "US", "city": "New York"}, {"origin_country": "PT"},
])
def test_flight_fallback(changes):
    task = build_task(trip(**changes))
    assert task["site_name"] == "Google Flights"
    assert "read-only search only" in task["instructions"]
    assert "do not enter carrier checkout" in task["instructions"]


def test_invalid_explicit_country():
    with pytest.raises(ValueError):
        build_task(trip(origin_country=""))
