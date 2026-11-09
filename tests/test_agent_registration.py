import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from test_site_policy import TODAY, registration_entry, registry

from runai.agents import site_policy
from runai.agents.registration import build_task, policy_view, registration_coverage
from runai.agents.site_policy import evaluate_url

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts", "alternatives"}


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
    assert task["fallback_url"] == task["start_url"]
    assert task["max_steps"] == 40
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
    {"distance_label": "Marathon", "distance_km": None}, {"distance_km": "42.195"},
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


def test_ultra_distance_is_accepted():
    data = _trip(distance_km=1000.0, distance_label="1000 km ultra")
    assert "1000 km ultra" in build(data)["instructions"]


def _organizer(**changes):
    base = registration_entry(
        id="example-organizer", automation="allowed_owner_rule",
        scopes=[{"host": "www.example-marathon.test", "path_prefix": "/"}],
        navigation_hosts=["in.njuko.com"], registration_observations=[],
        adapters=[{
            "kind": "registration",
            "race_match": {"name_patterns": [r"example\s+marathon"], "countries": ["DE"]},
            "url_template": "https://in.njuko.com/example-marathon-2027?d={race_date}",
            "success_evidence": "Participant form for the 2027 marathon.",
            "blocked_evidence": "Registrations closed or sold out.",
            "platform_hosts": ["in.njuko.com"],
        }],
    )
    base.update(changes)
    return base


def _njuko(**changes):
    return registration_entry(**{
        "id": "njuko-platform", "automation": "allowed_owner_rule",
        "scopes": [{"host": "in.njuko.com", "path_prefix": "/"}],
        "registration_observations": [], **changes,
    })


def test_adapter_first_and_platform_hosts():
    reg = registry(_organizer(), _njuko())
    task = build(_trip(registration_url=None), reg)
    assert task["start_url"] == "https://in.njuko.com/example-marathon-2027?d=2027-04-11"
    assert task["allowed_hosts"] == ["in.njuko.com"]
    assert "Participant form for the 2027 marathon." in task["instructions"]
    assert task["max_steps"] < 40 + 1


def test_organizer_official_url_navigates_to_platform():
    reg = registry(_organizer(adapters=[]), _njuko())
    task = build(_trip(registration_url=None), reg)
    assert task["start_url"] == "https://www.example-marathon.test/"
    assert task["allowed_hosts"] == ["in.njuko.com", "www.example-marathon.test"]


def test_unreviewed_navigation_host_is_dropped():
    reg = registry(_organizer(adapters=[], navigation_hosts=["unknown-platform.example"]))
    task = build(_trip(registration_url=None), reg)
    assert task["allowed_hosts"] == ["www.example-marathon.test"]


@pytest.mark.parametrize("trip_change", [
    {"name": "Other Race"}, {"country": "Italy"},
])
def test_adapter_needs_name_and_country_match(trip_change):
    reg = registry(_organizer(), _njuko())
    task = build(_trip(registration_url=None, **trip_change), reg)
    assert task["start_url"] == "https://www.example-marathon.test/"


def test_adapter_with_unreviewed_platform_is_skipped():
    task = build(_trip(registration_url=None), registry(_organizer()))
    assert task["start_url"] == "https://www.example-marathon.test/"


def test_prohibited_organizer_adapter_is_not_used():
    reg = registry(_organizer(automation="prohibited", screenshot_scope="none"), _njuko())
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build(_trip(registration_url=None), reg)


def test_expired_organizer_adapter_is_not_used():
    reg = registry(_organizer(expires_at="2026-11-08", reviewed_at="2026-08-01"), _njuko())
    with pytest.raises(ValueError):
        build(_trip(registration_url=None), reg)


@pytest.mark.parametrize("adapter_change", [
    {"url_template": "https://evil.example/x"},
    {"url_template": "https://in.njuko.com/{race_date}"},
    {"url_template": "https://in.njuko.com/x?{unknown}"},
    {"url_template": "http://in.njuko.com/x"},
    {"race_match": {"name_patterns": []}},
    {"race_match": {"name_patterns": ["("]}},
    {"race_match": {"name_patterns": ["x"], "countries": ["germany"]}},
    {"success_evidence": ""},
    {"platform_hosts": ["*.njuko.com"]},
])
def test_malformed_adapter_fails_closed(adapter_change):
    organizer = _organizer()
    organizer["adapters"][0].update(adapter_change)
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), registry(organizer, _njuko()))


def test_conflicting_scope_decisions_fail_closed():
    reg = registry(_organizer(), _njuko(), _njuko(id="njuko-denied", automation="prohibited"))
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), reg)


def test_instructions_prevent_false_booking_verdict():
    task = build(_trip())
    for text in ("/book, /checkout or /register is NOT a booking",
                 "no payment, booking or submission was made", "registration_closed",
                 "sold_out", "login_required", "consent_required", "Iscriviti", "Inscrições",
                 "Inscriptions", "under 40 steps"):
        assert text in task["instructions"]
    assert "no payment, booking or submission was made" in task["success_signal"]


FRAGMENT = Path(__file__).resolve().parents[1] / "docs" / "site-policy.d" / "registration.json"
MERGED_TODAY = date(2026, 11, 9)


def _merged():
    base = json.loads(site_policy.REGISTRY_PATH.read_text(encoding="utf-8"))["entries"]
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))
    assert fragment["schema_version"] == 1
    return {"schema_version": 1, "entries": base + fragment["entries"]}


def _race_trip(name, date_, km, city, country, official=None, registration=None, edition="2027"):
    arrival = (date.fromisoformat(date_) - timedelta(days=1)).isoformat()
    departure = (date.fromisoformat(date_) + timedelta(days=1)).isoformat()
    return {"race": {
        "name": name, "edition": edition, "distance_km": km, "race_date": date_,
        "date_status": "official", "city": city, "country": country,
        "official_url": official, "registration_url": registration,
    }, "origin_city": "Paris", "travelers": 1, "nights": 2, "budget_eur": 600,
        "arrival_date": arrival, "departure_date": departure}


SHOWCASE = [
    (("Wizz Air Milano Marathon", "2027-04-04", 42.195, "Milano", "Italy",
      "https://www.milanomarathon.it/"),
     "https://in.njuko.com/wizz-air-milano-marathon-20271776152378557", "in.njuko.com"),
    (("EDP Meia Maratona de Lisboa", "2027-03-07", 21.0975, "Lisboa", "Portugal",
      "https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/"),
     "https://meia-maratona.inscricoes.maratonaportugal.com/default.aspx?prova_id=3769",
     "meia-maratona.inscricoes.maratonaportugal.com"),
    (("Mein Freiburg Halbmarathon", "2027-04-04", 21.0975, "Freiburg", "Germany",
      "https://mein-freiburgmarathon.de/"),
     "https://mein-freiburgmarathon.de/lauf/halbmarathon/anmeldung/", "mein-freiburgmarathon.de"),
    (("Mein Freiburg Marathon", "2027-04-04", 42.195, "Freiburg", "Germany",
      "https://mein-freiburgmarathon.de/"),
     "https://mein-freiburgmarathon.de/lauf/marathon/anmeldung/", "mein-freiburgmarathon.de"),
    (("Jungfrau-Marathon", "2027-09-11", 42.195, "Interlaken", "Switzerland",
      "https://www.jungfrau-marathon.ch/"),
     "https://www.jungfrau-marathon.ch/de/anmeldung.html", "www.jungfrau-marathon.ch"),
    (("Padova Marathon", "2027-04-18", 42.195, "Padova", "Italy", "https://padovamarathon.com/"),
     "https://www.endu.net/events/padovamarathon/book", "www.endu.net"),
    (("Run Rome The Marathon", "2027-03-14", 42.195, "Roma", "Italy",
      "https://www.runromethemarathon.com/"), "https://rrtm.endu.net/", "rrtm.endu.net"),
    (("Generali Genève Marathon", "2027-05-09", 42.195, "Genève", "Switzerland",
      "https://www.generaligenevemarathon.com/"),
     "https://in.njuko.com/generali-geneve-marathon-2027-1782304695994", "in.njuko.com"),
]


@pytest.mark.parametrize(("race", "start", "platform"), SHOWCASE)
def test_merged_registry_covers_showcase_races(race, start, platform):
    reg = _merged()
    task = build_task(_race_trip(*race), today=MERGED_TODAY, registry=reg)
    assert task["start_url"] == start
    assert platform in task["allowed_hosts"]
    assert task["max_steps"] <= 40
    review = evaluate_url(start, "registration", today=MERGED_TODAY,
                          registry=policy_view(reg)[0])
    assert set(task["allowed_hosts"]) <= set(review["allowed_hosts"])  # H client subset check


def test_merged_organizer_official_url_reaches_platform():
    trip = _race_trip("Zurich Maratón de Sevilla", "2027-02-21", 42.195, "Sevilla", "Spain",
                      "https://www.zurichmaratonsevilla.es/")
    task = build_task(trip, today=MERGED_TODAY, registry=_merged())
    assert task["start_url"] == "https://www.zurichmaratonsevilla.es/zms-inscripciones"
    assert "in.njuko.com" in task["allowed_hosts"]


@pytest.mark.parametrize("race", [
    ("10K Valencia Ibercaja", "2027-01-10", 10.0, "Valencia", "Spain",
     "https://10kvalencia.com/", "https://registration.10kvalencia.com/inscripcion/x/"),
    ("Swiss Canyon Trail", "2027-06-05", 51.0, "Couvet", "Switzerland",
     "https://www.swisscanyontrail.com/"),
    ("NN Marathon Rotterdam", "2027-04-11", 42.195, "Rotterdam", "Netherlands",
     "https://nnmarathonrotterdam.nl/",
     "https://in.njuko.com/nn-marathon-rotterdam-20271784203024537/w/x"),
    ("ASICS Marathon de Paris", "2027-04-04", 42.195, "Paris", "France",
     "https://www.asicsmarathondeparis.com/"),
    ("Run in Lyon", "2027-10-03", 42.195, "Lyon", "France", "https://www.runinlyon.com/",
     "https://in.timeto.com/x"),
    ("Zurich Marató Barcelona", "2027-03-14", 42.195, "Barcelona", "Spain",
     "https://zurichmaratobarcelona.es/"),
    ("Lausanne Marathon", "2027-10-24", 42.195, "Lausanne", "Switzerland",
     "https://www.lausanne-marathon.com/", "https://onreg.datasport.com/lausanne-marathon-2027"),
    ("Unknown Hill Race", "2027-05-01", 10.0, "Bern", "Switzerland", "https://hill-race.example/"),
])
def test_merged_registry_blocks_prohibited_or_unreviewed(race):
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build_task(_race_trip(*race), today=MERGED_TODAY, registry=_merged())


def test_merged_registry_still_needs_distance():
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", None, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    with pytest.raises(ValueError, match="distance"):
        build_task(trip, today=MERGED_TODAY, registry=_merged())


def test_merged_registry_expires_fail_closed():
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", 42.195, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    with pytest.raises(ValueError):
        build_task(trip, today=date(2027, 2, 6), registry=_merged())


def test_fragment_entries_are_dated_unique_and_documented():
    base = json.loads(site_policy.REGISTRY_PATH.read_text(encoding="utf-8"))["entries"]
    fragment = json.loads(FRAGMENT.read_text(encoding="utf-8"))["entries"]
    base_ids = {e["id"] for e in base}
    base_scopes = {(s["host"], s.get("path_prefix", "/")) for e in base for s in e["scopes"]}
    evidence = (FRAGMENT.parents[1] / "evidence" / "registration.md").read_text(encoding="utf-8")
    for e in fragment:
        assert e["id"] not in base_ids
        assert not {(s["host"], s.get("path_prefix", "/")) for s in e["scopes"]} & base_scopes
        reviewed, expires = date.fromisoformat(e["reviewed_at"]), date.fromisoformat(e["expires_at"])
        assert 0 < (expires - reviewed).days <= 90
        assert e["purposes"] == ["registration"]
        assert e["terms_urls"] and all(u.startswith("https://") for u in e["terms_urls"])
        assert e["screenshot_scope"] == ("in_session_only" if e["automation"].startswith(
            "allowed") else "none")
        assert f"`{e['id']}`" in evidence
    text = FRAGMENT.read_text(encoding="utf-8")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    assert "token" not in text.lower()


def test_load_registry_merges_fragments_when_available():
    merged = site_policy.load_registry()
    if not any(e["id"] == "milanomarathon-it" for e in merged):
        pytest.skip("site_policy.load_registry fragment merging (R3-01) not on main yet")
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", 42.195, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    assert build_task(trip, today=MERGED_TODAY)["start_url"].startswith("https://in.njuko.com/")


def test_edition_specific_adapter_skips_other_editions():
    trip = _race_trip("Wizz Air Milano Marathon", "2028-04-02", 42.195, "Milano", "Italy",
                      "https://www.milanomarathon.it/", edition="2028")
    task = build_task(trip, today=MERGED_TODAY, registry=_merged())
    assert task["start_url"] == "https://www.milanomarathon.it/"
    assert "2027" not in task["start_url"]


def test_adapter_fallback_keeps_sourced_race_url():
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", 42.195, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    task = build_task(trip, today=MERGED_TODAY, registry=_merged())
    assert task["start_url"].startswith("https://in.njuko.com/")
    assert task["fallback_url"] == "https://www.milanomarathon.it/"


@pytest.mark.parametrize("bad", [["not-an-entry"], [{"id": "x", "scopes": ["host"]}]])
def test_malformed_registry_entries_fail_closed_as_value_error(bad):
    reg = _merged()
    reg["entries"] = reg["entries"] + bad
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", 42.195, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    with pytest.raises(ValueError, match="registry"):
        build_task(trip, today=MERGED_TODAY, registry=reg)


def _with_availability(**availability):
    organizer = _organizer()
    organizer["adapters"][0]["availability"] = {
        "status": "open", "observed_at": "2026-11-08",
        "source": "https://in.njuko.com/example-marathon-2027", "note": "Open.", **availability}
    return registry(organizer, _njuko())


def _coverage(race=None, reg=None, today=TODAY):
    race = _trip(registration_url=None)["race"] if race is None else race
    return registration_coverage(race, today=today, registry=reg)


def test_coverage_reports_fresh_open_availability():
    assert _coverage(reg=_with_availability()) == {
        "covered": True, "status": "open", "policy_id": "njuko-platform",
        "observed_at": "2026-11-08", "prohibited": False}


@pytest.mark.parametrize(("observed", "status"), [
    ("2026-10-01", "unknown"), ("2027-01-01", "unknown"), ("2026-10-19", "open"),
])
def test_coverage_availability_older_than_21_days_is_unknown(observed, status):
    result = _coverage(reg=_with_availability(observed_at=observed), today=date(2026, 11, 9))
    assert result["covered"] is True
    assert result["status"] == status


def test_coverage_without_adapter_or_observation_is_unknown():
    result = _coverage(_trip()["race"], reg=registry())
    assert result["covered"] is True and result["status"] == "unknown"
    assert result["observed_at"] is None


@pytest.mark.parametrize("status", ["sold_out", "closed"])
def test_sold_out_or_closed_still_builds_with_reason_first(status):
    task = build(_trip(registration_url=None), _with_availability(status=status))
    code = "sold_out" if status == "sold_out" else "registration_closed"
    first = task["instructions"].splitlines()[0]
    assert first.startswith("AVAILABILITY FIRST") and "first 5 steps" in first
    assert f"BLOCKED {code}" in first
    assert _coverage(reg=_with_availability(status=status))["status"] == status


def test_open_availability_adds_no_reason_first():
    task = build(_trip(registration_url=None), _with_availability())
    assert task["instructions"].startswith("Goal:")


@pytest.mark.parametrize("bad", [
    {"status": "maybe"}, {"status": None}, {"observed_at": "yesterday"}, {"observed_at": 20261108},
    {"source": "http://in.njuko.com/x"}, {"source": None}, {"note": 5},
])
def test_malformed_availability_fails_closed(bad):
    reg = _with_availability(**bad)
    with pytest.raises(ValueError, match="registry"):
        build(_trip(registration_url=None), reg)
    assert _coverage(reg=reg)["covered"] is False


def test_malformed_availability_object_fails_closed():
    organizer = _organizer()
    organizer["adapters"][0]["availability"] = "open"
    assert _coverage(reg=registry(organizer, _njuko()))["covered"] is False


def test_platform_adapter_with_organizer_path_lists_alternatives():
    task = build(_trip(), registry(_organizer(), _njuko()))
    assert task["start_url"].startswith("https://in.njuko.com/example-marathon-2027?d=")
    assert task["alternatives"] == ["https://in.njuko.com/example-marathon-2027",
                                    "https://www.example-marathon.test/"]
    assert "https://www.example-marathon.test/" in task["instructions"]
    for url in task["alternatives"]:
        assert evaluate_url(url, "registration", today=TODAY,
                            registry=registry(_organizer(), _njuko()))["allowed"]


def test_no_adapter_means_no_alternatives():
    assert build(_trip())["alternatives"] == []


UNCOVERED = {"covered": False, "status": "unknown", "policy_id": None, "observed_at": None,
             "prohibited": False}


@pytest.mark.parametrize("race", [
    None, {}, [], "race", {"race_date": "not-a-date"}, {"race_date": None},
    {**_trip()["race"], "race_date": "2026-01-01"}, {**_trip()["race"], "distance_km": None},
    {**_trip()["race"], "registration_url": 5},
])
def test_coverage_never_raises_on_malformed_race(race):
    assert registration_coverage(race, today=TODAY, registry=registry()) == UNCOVERED


@pytest.mark.parametrize("reg", [{"entries": "x"}, {"schema_version": 1, "entries": [1]}, 5])
def test_coverage_never_raises_on_malformed_registry(reg):
    assert _coverage(_trip()["race"], reg=reg) == UNCOVERED


def test_coverage_bad_today_uses_current_date():
    result = registration_coverage(_trip()["race"], today="2026-11-09", registry=registry())
    assert set(result) == set(UNCOVERED)


MILAN = ("Wizz Air Milano Marathon 2027", "2027-04-04", 42.195, "Milano", "Italy",
         "https://www.milanomarathon.it/")
LISBON_HALF = ("EDP Meia Maratona de Lisboa 2027", "2027-03-07", 21.0975, "Lisboa", "Portugal",
               "https://maratonaclubedeportugal.com/corrida-marco/edp-meia-maratona-de-lisboa/")
BARCELONA_HALF = (
    "Mitja Marató Barcelona 2027", "2027-02-14", 21.0975, "Barcelona", "Spain",
    "https://www.mitjamarato.barcelona/",
    "https://inscripciones.rpmsports.es/es/evento/hyundai-mitja-marato-barcelona-by-brooks-2027")
IRONTRAIL = ("Swiss Irontrail 2027 T78", "2027-08-14", 78.0, "Davos", "Switzerland",
             "https://www.irontrail.ch/", "https://onreg.datasport.com/de/swiss-irontrail-2027")
DEN_HAAG = ("NN CPC Loop Den Haag 2027", "2027-03-14", 21.1, "Den Haag", "Netherlands",
            "https://nncpcloopdenhaag.nl/")
VALENCIA_10K = ("10K Valencia Ibercaja", "2027-01-10", 10.0, "Valencia", "Spain",
                "https://10kvalencia.com/", "https://registration.10kvalencia.com/inscripcion/x/")


def _merged_coverage(race):
    return registration_coverage(_race_trip(*race)["race"], today=MERGED_TODAY,
                                 registry=_merged())


def test_merged_coverage_milan_open():
    result = _merged_coverage(MILAN)
    assert result["covered"] is True and result["status"] == "open"
    assert result["prohibited"] is False and result["observed_at"] == "2026-11-09"


def test_merged_coverage_lisbon_half_sold_out_still_builds():
    assert _merged_coverage(LISBON_HALF)["covered"] is True
    assert _merged_coverage(LISBON_HALF)["status"] == "sold_out"
    task = build_task(_race_trip(*LISBON_HALF), today=MERGED_TODAY, registry=_merged())
    assert task["instructions"].startswith("AVAILABILITY FIRST")
    assert "BLOCKED sold_out" in task["instructions"].splitlines()[0]


@pytest.mark.parametrize("race", [VALENCIA_10K, BARCELONA_HALF, IRONTRAIL])
def test_merged_coverage_prohibited_registration_is_not_covered(race):
    result = _merged_coverage(race)
    assert result["covered"] is False and result["prohibited"] is True
    assert result["policy_id"] and result["status"] == "unknown"
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build_task(_race_trip(*race), today=MERGED_TODAY, registry=_merged())


@pytest.mark.parametrize("race", [BARCELONA_HALF, IRONTRAIL])
@pytest.mark.parametrize("registration_url", [None, "", "https://in.njuko.com/example-2027"])
def test_prohibited_registration_flow_cannot_start_on_organizer(race, registration_url):
    trip = _race_trip(*race)
    trip["race"]["registration_url"] = registration_url
    coverage = registration_coverage(trip["race"], today=MERGED_TODAY, registry=_merged())
    assert coverage["covered"] is False
    assert coverage["prohibited"] is True
    assert coverage["policy_id"] in {"mitjamarato-barcelona", "irontrail-ch"}
    with pytest.raises(ValueError, match="denied"):
        build_task(trip, today=MERGED_TODAY, registry=_merged())


def test_merged_den_haag_builds_on_reviewed_njuko_with_sold_out_first():
    reg = _merged()
    task = build_task(_race_trip(*DEN_HAAG), today=MERGED_TODAY, registry=reg)
    assert task["start_url"].startswith("https://in.njuko.com/nn-cpc-loop-den-haag-")
    assert task["instructions"].startswith("AVAILABILITY FIRST")
    assert "https://nncpcloopdenhaag.nl/" in task["alternatives"]
    assert _merged_coverage(DEN_HAAG)["status"] == "sold_out"


def test_merged_coverage_unknown_race():
    race = ("Unknown Hill Race", "2027-05-01", 10.0, "Bern", "Switzerland",
            "https://hill-race.example/")
    assert _merged_coverage(race) == UNCOVERED


def test_merged_every_start_and_alternative_url_passes_policy():
    reg = _merged()
    view = policy_view(reg)[0]
    for race in [MILAN, LISBON_HALF, DEN_HAAG] + [r for r, _, _ in SHOWCASE]:
        task = build_task(_race_trip(*race), today=MERGED_TODAY, registry=reg)
        for url in [task["start_url"], *task["alternatives"]]:
            assert evaluate_url(url, "registration", today=MERGED_TODAY,
                                registry=view)["allowed"], url
        assert _merged_coverage(race)["covered"] is True
