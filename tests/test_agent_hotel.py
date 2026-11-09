import re
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
from test_site_policy import TODAY, assert_task_policy, distinct_entry, entry, registry

from runai.agents.hotel import build_task
from runai.agents.site_policy import evaluate_url, load_registry

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
    assert task["max_steps"] == 40
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
        build_task(trip(city="Unknown City", country="NZ"), today=TODAY)


@pytest.mark.parametrize("city,country", [
    ("Milan", "Italy"), ("Lisbon", "Portugal"), ("Valencia", "Spain"),
    ("Zurich", "Switzerland"), ("Geneva", "Switzerland"), ("Lausanne", "Switzerland"),
    ("Freiburg im Breisgau", "Germany"),
])
@pytest.mark.parametrize("travelers", [1, 2])
def test_committed_seven_city_exact_date_links(city, country, travelers):
    data = trip(city=city, country=country, travelers=travelers,
                arrival_date="2027-01-09", departure_date="2027-01-11",
                race_changes={"race_date": "2027-01-10"})
    task = build_task(data, today=date(2026, 11, 9))
    url = task["start_url"]
    decision = evaluate_url(url, "hotel", today=date(2026, 11, 9))
    assert decision["allowed"]
    assert urlsplit(url).hostname in task["allowed_hosts"] == decision["allowed_hosts"]
    query = parse_qs(urlsplit(url).query)
    if task["site_name"] == "nh-hotels-com":
        assert city == "Lisbon"
        assert query["destinationId"] == ["Lisbon"]
        assert query["hotelId"] == ["PT11.LIBER"]
        assert query["fini"] == ["09/01/2027"]
        assert query["fout"] == ["11/01/2027"]
        assert query["nadults1"] == [str(travelers)]
        assert "fini=09%2F01%2F2027&fout=11%2F01%2F2027" in url
    elif task["site_name"] == "hotel-bb-com":
        assert city in {"Freiburg im Breisgau", "Milan"} and travelers == 1
        destination = "Freiburg-Nord" if city == "Freiburg im Breisgau" else "milano-sant-ambrogio"
        assert query == {"arrival_date": ["01/09/2027"], "departure_date": ["01/11/2027"],
                         "rooms": ["1"], "destination": [destination]}
        assert "arrival_date=01%2F09%2F2027&departure_date=01%2F11%2F2027" in url
    else:
        assert task["site_name"] == "ihg-com"
        assert query == {
            "qDest": [f"{city}, {country}"], "qCiD": ["09"], "qCiMy": ["002027"],
            "qCoD": ["11"], "qCoMy": ["002027"], "qAdlt": [str(travelers)],
            "qChld": ["0"], "qRms": ["1"],
        }
        assert "qCiD=09&qCiMy=002027&qCoD=11&qCoMy=002027" in url
        assert f"qAdlt={travelers}" in url
        assert "no hotel in the confirmed city" in task["instructions"]
    assert task["expected"]["origin_city"] == "Paris"
    assert task["expected"]["travelers"] == travelers
    assert task["expected"]["arrival_date"] == "2027-01-09"
    assert task["expected"]["departure_date"] == "2027-01-11"


def test_committed_accor_stays_denied():
    assert not evaluate_url("https://all.accor.com/", "hotel", today=TODAY)["allowed"]


@pytest.mark.parametrize("city", ["Freiburg", "FREIBURG IM BREISGAU"])
def test_freiburg_one_adult_only_uses_reviewed_in_city_hotel(city):
    one = build_task(trip(city=city, country="DE", travelers=1), today=TODAY)
    assert one["site_name"] == "hotel-bb-com"
    two = build_task(trip(city=city, country="DE", travelers=2), today=TODAY)
    assert two["site_name"] == "ihg-com"


def test_melia_deep_links_withdrawn_after_terms_reread():
    melia = next(e for e in load_registry() if e["id"] == "melia-com")
    assert melia["adapters"] == []


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
    for rule in ("Never fill or submit any form", "solve captchas", "log in",
                 "never accept optional consent", "Never change the dates"):
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
    codes = set(re.findall(r"report BLOCKED ([a-z_]+)", instructions))
    assert codes == {
        "no_site_coverage", "policy_denied", "date_mismatch", "no_inventory", "sold_out",
        "login_required", "captcha", "consent_required", "unreviewed_redirect", "over_budget",
        "step_limit", "session_failed", "timeout", "unsafe_claim", "provider_error",
    }
    assert "reviewed selection page" in task["success_signal"]
    assert "full-stay total for the whole party" in task["success_signal"]
    assert "before guest details, personal data or payment" in task["success_signal"]
    assert "report BLOCKED unsafe_claim" in task["success_signal"]
    assert set(task) == KEYS and task["max_steps"] <= 40
    assert task["fallback_url"] == task["start_url"]
    assert urlsplit(task["fallback_url"]).hostname == "www.hotels.example"
    assert urlsplit(task["fallback_url"]).path not in ("", "/")


def test_budget_caps_selected_rate():
    task = build_task(trip(city="Lisbon", country="Portugal"), today=TODAY)
    assert "EUR 600" in task["instructions"] and "over_budget" in task["instructions"]

@pytest.mark.parametrize("city,country", [
    ("Milan", "IT"), ("Barcelona", "ES"), ("Lisbon", "PT"), ("Valencia", "ES"),
    ("Seville", "ES"), ("Zurich", "CH"), ("Geneva", "CH"), ("Amsterdam", "NL"),
    ("Den Haag", "NL"), ("Rome", "IT"), ("Savognin", "CH"), ("Grindelwald", "CH"),
    ("Sierre", "CH"), ("Brussels", "BE"), ("Vienna", "AT"), ("Prague", "CZ"),
    ("Paris", "FR"), ("London", "GB"), ("Birmingham", "GB"),
])
def test_r4_committed_hotel_matrix_and_policy(city, country, monkeypatch):
    task = build_task(trip(city=city, country=country, travelers=1, budget_eur=450,
                          arrival_date="2027-01-09", departure_date="2027-01-11",
                          race_changes={"race_date": "2027-01-10"}), today=TODAY)
    assert_task_policy(task, monkeypatch)
    assert task["expected"]["city"] == city
    alternatives = task.get("alternatives", [])
    assert len(alternatives) <= 2
    assert len({t["site_name"] for t in [task, *alternatives]}) == 1 + len(alternatives)
    assert set(task) - {"alternatives"} == KEYS
    for alternative in alternatives:
        assert set(alternative) == KEYS
        assert alternative["expected"] == task["expected"]
    if city in {"Milan", "Lisbon", "Brussels", "Vienna", "Prague", "Paris", "Birmingham"}:
        assert alternatives
    if city in {"Amsterdam", "Den Haag", "London"}:
        assert "alternatives" not in task
    for candidate in [task, *alternatives]:
        if candidate["site_name"] == "ihg-com":
            assert "select-enhance-stay" in candidate["success_signal"]
            assert "STOP" in candidate["instructions"] and "READY immediately" in candidate["instructions"]
            assert "no hotel in the confirmed city" in candidate["instructions"]


def test_hotel_alternatives_limit_skip_denied_expired_and_do_not_mutate(monkeypatch):
    items = [distinct_entry(n) for n in range(6)]
    items[1]["automation"] = "prohibited"
    items[2]["expires_at"] = "2026-11-08"
    items[0]["adapters"] *= 2
    reg = registry(*items)
    task = build(trip(), reg)
    assert [a["site_name"] for a in task["alternatives"]] == ["site3", "site4"]
    assert all(set(a) == KEYS for a in task["alternatives"])
    assert_task_policy(task, monkeypatch, reg)
    task["alternatives"][0]["expected"]["city"] = "Changed"
    assert task["expected"]["city"] == "Milan"
    one = build(trip(), registry(items[0], items[1], items[2]))
    assert set(one) == KEYS
