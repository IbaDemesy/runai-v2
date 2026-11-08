from datetime import date
from pathlib import Path

import pytest

from runai.agents.hotel import build_task, select_site


def trip(**changes):
    return {
        "race": {
            "id": "synthetic-race", "name": "Synthetic race", "edition": 2027,
            "distance_km": 42.195, "distance_label": "marathon",
            "race_date": "2027-04-04", "date_status": "unverified",
            "city": changes.pop("city", "Milan"), "country": changes.pop("country", "Italy"),
            "official_url": "https://example.org", "registration_url": None,
            "source_urls": [], "retrieved_at": "2026-11-08", "synthetic": True,
        },
        "origin_city": "Paris", "travelers": 2, "nights": 2, "budget_eur": 600,
        "arrival_date": "2027-04-03", "departure_date": "2027-04-05", **changes,
    }


@pytest.mark.parametrize("city,country,origin,expected", [
    ("Milan", "Italy", "Paris", "Accor"),
    ("Lisbon", "Portugal", "Porto", "Accor"),
    ("Zermatt", "Switzerland", "Zurich", "Accor"),
    ("Reykjavik", "Iceland", "Paris", "Accor"),
])
def test_destinations(city, country, origin, expected):
    task = build_task(trip(city=city, country=country, origin_city=origin))
    assert set(task) == {
        "kind", "site_name", "start_url", "instructions", "stop_before",
        "success_signal", "fallback_url", "max_steps",
    }
    assert task["kind"] == "hotel"
    assert task["site_name"] == expected
    assert task["fallback_url"] == task["start_url"]
    assert task["max_steps"] > 0
    for value in (city, country, origin, "2027-04-03", "2027-04-05", "2", "EUR 600"):
        assert value in task["instructions"]
    for forbidden in ("booking.com", "flytap"):
        assert forbidden not in str(task).lower()


@pytest.mark.parametrize("key", ["race", "origin_city", "arrival_date", "departure_date"])
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


@pytest.mark.parametrize("key", ["city", "country"])
@pytest.mark.parametrize("value", [None, "", " ", 12])
def test_missing_race_location(key, value):
    data = trip()
    data["race"][key] = value
    with pytest.raises(ValueError):
        build_task(data)
    del data["race"][key]
    with pytest.raises(ValueError):
        build_task(data)


@pytest.mark.parametrize("race", [[], "Milan", 123])
def test_invalid_race(race):
    with pytest.raises(ValueError):
        build_task(trip(race=race))


def test_numeric_budget_and_legacy_keys_do_not_override_contract():
    task = build_task(trip(budget_eur=250.5, adults=9, budget="USD 2", origin="Rome"))
    assert "EUR 250.5" in task["instructions"]
    assert "2 adults" in task["instructions"]
    assert "Paris" in task["instructions"]
    assert "USD" not in task["instructions"]


@pytest.mark.parametrize("changes", [
    {"arrival_date": "not-a-date"}, {"departure_date": "2027-02-30"},
    {"departure_date": "2027-04-03"}, {"departure_date": "2027-04-02"},
    {"arrival_date": 123}, {"travelers": 0}, {"travelers": True}, {"travelers": "2"},
    {"budget_eur": 0}, {"budget_eur": -1}, {"budget_eur": "600"}, {"budget_eur": True},
    {"budget_eur": None}, {"budget_eur": float("inf")}, {"budget_eur": float("nan")},
])
def test_invalid_inputs(changes):
    with pytest.raises(ValueError):
        build_task(trip(**changes))


def test_dates_defaults_and_guardrails():
    data = trip(arrival_date=date(2027, 4, 3), departure_date=date(2027, 4, 5))
    del data["travelers"]
    del data["budget_eur"]
    task = build_task(data)
    assert "1 adults" in task["instructions"]
    assert "No budget supplied" in task["instructions"]
    data["travelers"] = 3
    assert "3 adults" in build_task(data)["instructions"]
    for rule in ("guest details", "passenger details", "login", "payment", "booking",
                 "account creation", "terms", "cookie consent",
                 "form submission",
                 "personal data", "captcha"):
        assert rule in task["stop_before"]
    for rule in ("Never pay", "book", "create accounts", "accept terms", "cookie consent",
                 "Never submit any form", "enter personal data",
                 "bypass captchas", "report blocked", "beyond dismissing"):
        assert rule in task["instructions"]
    for phrase in ("public search controls/result navigation", "read-only",
                   "deep-linked/public result pages", "consent or newsletter",
                   "If viewing results is impossible without a forbidden step"):
        assert phrase in task["instructions"]
    assert "press Search" not in task["instructions"]
    assert "form submission is allowed" not in task["instructions"]
    assert "blocked" in task["success_signal"]
    source = Path(__file__).parents[1] / "runai" / "agents" / "hotel.py"
    assert all(term not in source.read_text().lower() for term in ("booking.com", "flytap"))


def test_chain_selection():
    assert select_site(trip()) == ("Accor", "https://all.accor.com")
    assert select_site(trip(hotel_preference="Hilton")) == (
        "Hilton", "https://www.hilton.com",
    )


@pytest.mark.parametrize("preference", ["booking.com", "unknown", "", None, []])
def test_unsupported_chain(preference):
    with pytest.raises(ValueError):
        build_task(trip(hotel_preference=preference))


def test_hotel_stop_and_unavailable():
    instructions = build_task(trip())["instructions"]
    assert "guest-details page" in instructions
    assert "no availability" in instructions
    assert "within the total budget" in instructions
