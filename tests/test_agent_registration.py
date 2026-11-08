import re

import pytest

from runai.agents.registration import build_task


def _trip(**race):
    base = {
        "name": "Example Marathon",
        "edition": "2027",
        "distance_label": "Marathon 42.195 km",
        "race_date": "2027-04-11",
        "city": "Example City",
        "country": "Exampleland",
        "official_url": "https://www.example-marathon.test/",
        "registration_url": "https://in.njuko.com/example-marathon-2027",
    }
    base.update(race)
    return {
        "race": base,
        "origin_city": "Paris",
        "travelers": 1,
        "nights": 2,
        "budget_eur": 600,
        "arrival_date": "2027-04-10",
        "departure_date": "2027-04-12",
    }


KEYS = {
    "kind", "site_name", "start_url", "instructions",
    "stop_before", "success_signal", "fallback_url", "max_steps",
}


def test_uses_registration_url():
    task = build_task(_trip())
    assert set(task) == KEYS
    assert task["kind"] == "registration"
    assert task["start_url"] == "https://in.njuko.com/example-marathon-2027"
    assert task["fallback_url"] == "https://www.example-marathon.test/"
    assert task["site_name"] == "in.njuko.com"
    assert task["max_steps"] > 0
    assert "Marathon 42.195 km" in task["instructions"]
    assert "Example Marathon 2027" in task["instructions"]


@pytest.mark.parametrize("missing", [None, "", "  "])
def test_falls_back_to_official_url(missing):
    task = build_task(_trip(registration_url=missing))
    assert task["start_url"] == "https://www.example-marathon.test/"
    assert task["site_name"] == "example-marathon.test"


def test_missing_both_urls_raises():
    with pytest.raises(ValueError):
        build_task(_trip(registration_url=None, official_url=None))


@pytest.mark.parametrize("trip", [{}, {"race": None}, {"race": {}}, {"race": "x"}])
def test_missing_race_raises(trip):
    with pytest.raises(ValueError):
        build_task(trip)


@pytest.mark.parametrize(
    "field,url",
    [
        ("registration_url", "http://in.njuko.com/x"),
        ("official_url", "http://www.example-marathon.test/"),
        ("registration_url", "javascript:alert(1)"),
        ("official_url", "ftp://example.test/"),
        ("registration_url", "https://"),
    ],
)
def test_non_https_rejected(field, url):
    with pytest.raises(ValueError):
        build_task(_trip(**{field: url}))


def test_stop_rules_and_no_personal_data():
    trip = _trip()
    task = build_task(trip)
    text = task["instructions"].lower()
    for word in ["personal data", "login", "account", "medical", "consent", "payment",
                 "captcha", "submit", "never pay", "closed", "sold out", "not yet open",
                 "blocked"]:
        assert word in text, word
    for rule in task["stop_before"]:
        assert rule in task["instructions"]
    assert not re.search(r"[\w.+-]+@[\w-]+\.\w+", task["instructions"])
    assert "Paris" not in task["instructions"]
    assert "600" not in task["instructions"]


RACES = [
    ("Wizz Air Milano Marathon", "Milano", "Italy", "https://www.milanomarathon.it/",
     "https://in.njuko.com/wizz-air-milano-marathon-20271776152378557"),
    ("BMW Berlin-Marathon", "Berlin", "Germany", "https://www.bmw-berlin-marathon.com/",
     None),
    ("Zurich Marató de Barcelona", "Barcelona", "Spain", "https://www.zurichmaratobarcelona.es/",
     "https://inscripciones.rpmsports.es/es/evento/zurich-marato-barcelona-2027/my-registration"),
]


@pytest.mark.parametrize("name,city,country,official,registration", RACES)
def test_generic_across_races(name, city, country, official, registration):
    task = build_task(_trip(name=name, city=city, country=country,
                            official_url=official, registration_url=registration))
    assert task["start_url"] == (registration or official)
    assert name in task["instructions"]
    assert city in task["instructions"]
    others = [r[0] for r in RACES if r[0] != name]
    assert not any(o in task["instructions"] for o in others)
    if "Milano" not in name:
        assert "milan" not in task["instructions"].lower()


def test_login_wall_is_blocked_not_ready():
    signal = build_task(_trip())["success_signal"]
    ready, blocked = signal.split("BLOCKED:")
    assert "login" not in ready.lower()
    assert "login" in blocked.lower()
    assert "captcha" in blocked.lower()
