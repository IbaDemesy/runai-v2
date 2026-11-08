import pytest
from test_site_policy import TODAY, registration_entry, registry

from runai.agents.registration import build_task

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts"}


def _trip(**race):
    base = {
        "name": "Example Marathon", "edition": "2027", "distance_label": "Marathon 42.195 km",
        "distance_km": 42.195, "race_date": "2027-04-11", "date_status": "official",
        "city": "Example City", "country": "Germany",
        "official_url": "https://www.example-marathon.test/",
        "registration_url": "https://in.njuko.com/example-marathon-2027",
    }
    base.update(race)
    return {"race": base, "origin_city": "Paris", "travelers": 1, "nights": 2,
            "budget_eur": 600, "arrival_date": "2027-04-10", "departure_date": "2027-04-12"}


def build(data, reg=None):
    return build_task(data, today=TODAY, registry=registry() if reg is None else reg)


def test_reviewed_registration_url():
    task = build(_trip())
    assert set(task) == KEYS
    assert task["kind"] == "registration"
    assert task["start_url"] == "https://in.njuko.com/example-marathon-2027"
    assert task["fallback_url"] == "https://www.example-marathon.test/"
    assert task["max_steps"] == 80
    assert task["allowed_hosts"] == ["in.njuko.com", "www.example-marathon.test"]
    assert task["expected"]["race_date"] == "2027-04-11"
    assert task["expected"]["race_name"] == "Example Marathon"
    for text in ("2027 edition on 2027-04-11", "Marathon 42.195 km", "date_mismatch",
                 "unreviewed_redirect", "account_required=False", "hint",
                 "first personal-data page without touching it"):
        assert text in task["instructions"]
    for text in ("lottery", "sold out", "account login", "captcha", "consent"):
        assert text in task["success_signal"]


def test_falls_back_to_reviewed_official_url():
    task = build(_trip(registration_url="https://unreviewed.example/reg"))
    assert task["start_url"] == "https://www.example-marathon.test/"


@pytest.mark.parametrize("race", [
    {"registration_url": "https://in.njuko.com/other-race", "official_url": None},
    {"registration_url": None, "official_url": "https://unknown-race.example/"},
])
def test_unreviewed_registration_blocks(race):
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build(_trip(**race))


def test_observation_does_not_authorize():
    reg = registry(registration_entry(automation="ambiguous"))
    with pytest.raises(ValueError):
        build(_trip(), reg)


def test_committed_registry_blocks_unknown_race():
    with pytest.raises(ValueError):
        build_task(_trip(registration_url="https://register.random-race.example/2027",
                         official_url="https://random-race.example/"), today=TODAY)


def test_committed_owner_rule_platform_allows_other_njuko_event():
    task = build_task(_trip(registration_url="https://in.njuko.com/random-race-2027",
                            official_url="https://random-race.example/"), today=TODAY)
    assert task["start_url"] == "https://in.njuko.com/random-race-2027"
    assert "in.njuko.com" in task["allowed_hosts"]


@pytest.mark.parametrize("race", [
    {"race_date": "2026-10-01"}, {"race_date": None}, {"date_status": "conflicting"},
    {"edition": "2026"}, {"distance_label": "", "distance_km": None},
    {"registration_url": "http://in.njuko.com/x", "official_url": None},
    {"registration_url": None, "official_url": None}, {"registration_url": 5},
    {"city": ""},
])
def test_rejects_stale_or_incomplete_race(race):
    with pytest.raises(ValueError):
        build(_trip(**race))


def test_rejects_trip_dates_outside_race():
    data = _trip()
    data.update(arrival_date="2027-04-12", departure_date="2027-04-13", nights=1)
    with pytest.raises(ValueError):
        build(data)


def test_origin_optional_for_registration():
    data = _trip()
    del data["origin_city"]
    assert build(data)["expected"]["origin_city"] is None


@pytest.mark.parametrize("value", [None, {}, [], "race"])
def test_empty_or_invalid(value):
    with pytest.raises(ValueError):
        build(value if value != {} else {"race": {}})


def test_guardrails():
    task = build(_trip())
    for item in ("personal data", "account login", "medical", "consent", "payment",
                 "captcha", "any form submission", "redirect"):
        assert any(item in s for s in task["stop_before"])
    for item in ("Never type personal data", "submit a form", "bypass a captcha"):
        assert item in task["instructions"]
