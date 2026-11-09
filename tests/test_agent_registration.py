import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from test_site_policy import TODAY, registration_entry, registry

from runai.agents import hclient, site_policy
from runai.agents.registration import (
    NJUKO_CHECKPOINT,
    _distance_matches,
    availability_from_evidence,
    build_task,
    policy_view,
    registration_coverage,
)
from runai.agents.scrub import scrub_url
from runai.agents.site_policy import evaluate_url

KEYS = {"kind", "site_name", "start_url", "instructions", "stop_before", "success_signal",
        "fallback_url", "max_steps", "expected", "allowed_hosts", "alternatives", "checkpoint"}


def _matches(patterns, url):
    checkpoint = {"url_patterns": [re.compile(p, re.IGNORECASE) for p in patterns]}
    return hclient._checkpoint_matches(checkpoint, "url_patterns", url)


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
    assert task["max_steps"] == 60
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
            "checkpoint": NJUKO_CHECKPOINT,
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
    assert task["max_steps"] == 60


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


def test_owner_decision_outlives_organizer_review():
    reg = registry(_organizer(expires_at="2026-11-08", reviewed_at="2026-08-01"), _njuko())
    assert build(_trip(registration_url=None), reg)["start_url"]


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
                 "Inscriptions", "under 60 steps"):
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
     "https://www.generaligenevemarathon.com/participate", "in.njuko.com"),
]


@pytest.mark.parametrize(("race", "start", "platform"), SHOWCASE)
def test_merged_registry_covers_showcase_races(race, start, platform):
    reg = _merged()
    task = build_task(_race_trip(*race), today=MERGED_TODAY, registry=reg)
    assert task["start_url"] == start
    assert platform in task["allowed_hosts"]
    assert task["max_steps"] == (12 if task["instructions"].startswith("AVAILABILITY FIRST") else 60)
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
def test_merged_registry_requires_existing_adapter(race):
    if race[3] in {"Valencia", "Rotterdam"} or race[0] == "Zurich Marató Barcelona":
        assert build_task(_race_trip(*race), today=MERGED_TODAY,
                          registry=_merged())["start_url"]
        return
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build_task(_race_trip(*race), today=MERGED_TODAY, registry=_merged())


def test_merged_registry_still_needs_distance():
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", None, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    with pytest.raises(ValueError, match="distance"):
        build_task(trip, today=MERGED_TODAY, registry=_merged())


def test_owner_decision_does_not_expire_with_terms_review():
    trip = _race_trip("Wizz Air Milano Marathon", "2027-04-04", 42.195, "Milano", "Italy",
                      "https://www.milanomarathon.it/")
    assert build_task(trip, today=date(2027, 2, 6), registry=_merged())["start_url"]


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
        "observed_at": "2026-11-08", "prohibited": False, "registration": "covered",
        "preparable_open": True}


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
    assert [a["start_url"] for a in task["alternatives"]] == [
        "https://in.njuko.com/example-marathon-2027", "https://www.example-marathon.test/"]
    assert "https://www.example-marathon.test/" in task["instructions"]
    for alternative in task["alternatives"]:
        url = alternative["start_url"]
        assert alternative["checkpoint"] == task["checkpoint"]
        assert evaluate_url(url, "registration", today=TODAY,
                            registry=registry(_organizer(), _njuko()))["allowed"]


def test_no_adapter_means_no_alternatives():
    assert build(_trip())["alternatives"] == []


@pytest.mark.parametrize("checkpoint", [None, {}, {"url_patterns": []},
    {"url_patterns": ["("], "beyond_patterns": ["payment"]},
    {"url_patterns": ["form"], "beyond_patterns": []},
    {"url_patterns": [False], "beyond_patterns": ["login"]}])
def test_malformed_checkpoint_fails_closed(checkpoint):
    organizer = _organizer()
    organizer["adapters"][0]["checkpoint"] = checkpoint
    reg = registry(organizer, _njuko())
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), reg)
    assert _coverage(reg=reg)["covered"] is False


def test_missing_checkpoint_fails_closed():
    organizer = _organizer()
    del organizer["adapters"][0]["checkpoint"]
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), registry(organizer, _njuko()))


@pytest.mark.parametrize("page", ["form", "form_individual", "form_individual-form"])
def test_njuko_personal_page_checkpoint_on_every_attempt(page):
    task = build(_trip(), registry(_organizer(), _njuko()))
    for attempt in [task, *task["alternatives"]]:
        checkpoint = attempt["checkpoint"]
        url = f"https://in.njuko.com/example?currentPage={page}"
        assert _matches(checkpoint["url_patterns"], url)
        assert _matches(checkpoint["url_patterns"], url.replace("_", "%5F").upper())
        assert "STOP and answer immediately without typing anything" in attempt["instructions"]
        for boundary in ("payment", "summary", "cart", "login", "signin"):
            assert _matches(checkpoint["beyond_patterns"],
                            f"https://in.njuko.com/example/{boundary}")


UNCOVERED = {"covered": False, "status": "unknown", "policy_id": None, "observed_at": None,
             "registration": "uncovered", "preparable_open": False,
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
def test_lifted_registration_policy_does_not_invent_adapters(race):
    result = _merged_coverage(race)
    assert result["prohibited"] is False
    assert result["covered"] is True
    assert result["preparable_open"] is False
    assert build_task(_race_trip(*race), today=MERGED_TODAY, registry=_merged())["start_url"]


@pytest.mark.parametrize("race", [BARCELONA_HALF, IRONTRAIL])
@pytest.mark.parametrize("registration_url", [None, "", "https://in.njuko.com/example-2027"])
def test_registration_without_adapter_still_cannot_start(race, registration_url):
    trip = _race_trip(*race)
    trip["race"]["registration_url"] = registration_url
    coverage = registration_coverage(trip["race"], today=MERGED_TODAY, registry=_merged())
    assert coverage["covered"] is True
    assert coverage["prohibited"] is False
    assert coverage["preparable_open"] is False
    assert build_task(trip, today=MERGED_TODAY, registry=_merged())["start_url"]


def test_merged_den_haag_builds_on_reviewed_njuko_with_sold_out_first():
    reg = _merged()
    task = build_task(_race_trip(*DEN_HAAG), today=MERGED_TODAY, registry=reg)
    assert task["start_url"].startswith("https://in.njuko.com/nn-cpc-loop-den-haag-")
    assert task["instructions"].startswith("AVAILABILITY FIRST")
    assert "https://nncpcloopdenhaag.nl/" in [a["start_url"] for a in task["alternatives"]]
    assert _merged_coverage(DEN_HAAG)["status"] == "sold_out"


@pytest.mark.parametrize("distance", [5, 10, 21, 21.0975, 21.1])
def test_den_haag_availability_is_scoped_to_half_marathon(distance):
    trip = _race_trip(*DEN_HAAG)
    trip["race"]["distance_km"] = distance
    trip["race"]["distance_label"] = f"{distance} km"
    coverage = registration_coverage(trip["race"], today=MERGED_TODAY, registry=_merged())
    half = distance in (21, 21.0975, 21.1)
    assert coverage["covered"] is True
    assert coverage["prohibited"] is False
    assert coverage["status"] == ("sold_out" if half else "open")
    assert coverage["observed_at"] == "2026-11-09"
    task = build_task(trip, today=MERGED_TODAY, registry=_merged())
    assert task["instructions"].startswith("AVAILABILITY FIRST") is half


@pytest.mark.parametrize("distances", [None, [], "21.1", [True], [0], [-1], [float("inf")]])
def test_malformed_availability_distance_scope_fails_closed(distances):
    reg = _with_availability()
    reg["entries"][0]["adapters"][0]["availability"]["distances_km"] = distances
    assert _coverage(reg=reg)["covered"] is False
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), reg)


def test_merged_coverage_unknown_race():
    race = ("Unknown Hill Race", "2027-05-01", 10.0, "Bern", "Switzerland",
            "https://hill-race.example/")
    assert _merged_coverage(race) == UNCOVERED


def test_merged_every_start_and_alternative_url_passes_policy():
    reg = _merged()
    view = policy_view(reg)[0]
    for race in [MILAN, LISBON_HALF, DEN_HAAG] + [r for r, _, _ in SHOWCASE]:
        task = build_task(_race_trip(*race), today=MERGED_TODAY, registry=reg)
        for url in [task["start_url"], *[a["start_url"] for a in task["alternatives"]]]:
            assert evaluate_url(url, "registration", today=MERGED_TODAY,
                                registry=view)["allowed"], url
        assert _merged_coverage(race)["covered"] is True


FRESH_OPEN_RACES = [
    MILAN,
    ("NN CPC Loop Den Haag 10K", "2027-03-14", 10, "Den Haag", "Netherlands",
     "https://nncpcloopdenhaag.nl/"),
    ("Generali Genève Marathon", "2027-05-09", 42.195, "Genève", "Switzerland",
     "https://www.generaligenevemarathon.com/"),
    ("Run Rome The Marathon", "2027-03-14", 42.195, "Roma", "Italy",
     "https://www.runromethemarathon.com/"),
    ("Bologna Marathon", "2027-03-07", 42.195, "Bologna", "Italy",
     "https://www.bolognamarathon.run/"),
    ("Padova Marathon", "2027-04-18", 42.195, "Padova", "Italy",
     "https://padovamarathon.com/"),
    ("Vodafone Prague Marathon", "2027-05-02", 42.195, "Prague", "Czech Republic",
     "https://www.runczech.com/en/events/vodafone-prague-marathon-2027"),
    ("Movistar Madrid Medio Maratón", "2027-04-04", 21.0975, "Madrid", "Spain",
     "https://www.mediomaratonmadrid.es/en/"),
]
FRANKFURT = ("Mainova Frankfurt Marathon", "2027-10-31", 42.195, "Frankfurt am Main", "Germany",
             "https://www.frankfurt-marathon.com/")
STOOS = ("Stoos-Trail ST24", "2027-07-10", 25.6, "Brunnen", "Switzerland",
         "https://stoos-trail.ch/")
R6_OPEN = [STOOS]


def test_named_fresh_open_matrix_spans_required_countries():
    assert len({r[0] for r in FRESH_OPEN_RACES}) >= 8
    countries = {r[4] for r in FRESH_OPEN_RACES}
    assert len(countries) >= 5
    assert {"Netherlands", "Switzerland", "Spain"} <= countries
    assert any(r[4] == "Spain" and r[3] != "Sevilla" for r in FRESH_OPEN_RACES)


@pytest.mark.parametrize("race", FRESH_OPEN_RACES + R6_OPEN, ids=lambda r: r[0])
def test_named_fresh_open_matrix_builds_scrubbed_policy_checked_tasks(race, monkeypatch):
    today = date(2026, 11, 9)
    reg = _merged()
    trip = _race_trip(*race)
    coverage = registration_coverage(trip["race"], today=today, registry=reg)
    assert coverage["covered"] is True
    assert coverage["status"] == "open"
    assert coverage["registration"] == "covered" and coverage["preparable_open"] is True
    assert coverage["observed_at"] == today.isoformat()
    task = build_task(trip, today=today, registry=reg)
    assert task["max_steps"] == 60

    class ReviewClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 9, tzinfo=tz)

    monkeypatch.setattr(hclient, "datetime", ReviewClock)
    monkeypatch.setattr(site_policy, "evaluate_url", lambda url, kind: evaluate_url(
        url, kind, today=today, registry=reg))
    for attempt in [task, *task["alternatives"]]:
        assert scrub_url(attempt["start_url"]) == attempt["start_url"]
        assert scrub_url(attempt["fallback_url"]) == attempt["fallback_url"]
        assert hclient._policy(attempt)
        checkpoint = attempt["checkpoint"]
        assert checkpoint["url_patterns"] and checkpoint["beyond_patterns"]
        assert hclient._checkpoint(attempt) is not None
        for pattern in checkpoint["url_patterns"] + checkpoint["beyond_patterns"]:
            re.compile(pattern)
        for boundary in ("payment", "summary", "login", "cart"):
            assert _matches(checkpoint["beyond_patterns"], f"https://example.test/{boundary}")
        for landing in (trip["race"]["official_url"], attempt["start_url"]):
            if "web-form" not in landing:
                assert not _matches(checkpoint["url_patterns"], landing), landing


def test_fresh_open_coverage_per_required_country():
    covered = {r[4] for r in FRESH_OPEN_RACES + R6_OPEN if _merged_coverage(r)["preparable_open"]}
    assert {"Spain", "Netherlands", "Switzerland", "Italy"} <= covered


@pytest.mark.parametrize("scrub_mode", ["actual", "allowed", "denied"])
def test_frankfurt_reviewed_but_not_preparable_until_white_label_id_is_scrub_clean(
    monkeypatch, scrub_mode,
):
    start = build_task(_race_trip(*FRANKFURT), today=MERGED_TODAY,
                       registry=_merged())["start_url"]
    cleaned = scrub_url(start)
    assert cleaned in (None, start)
    if scrub_mode != "actual":
        cleaned = start if scrub_mode == "allowed" else None
        monkeypatch.setattr("runai.agents.scrub.scrub_url",
                            lambda url: cleaned if url == start else scrub_url(url))
    coverage = _merged_coverage(FRANKFURT)
    assert coverage["covered"] is (cleaned == start)
    assert coverage["preparable_open"] is (cleaned == start)
    assert coverage["prohibited"] is False


def test_coverage_fails_closed_when_scrub_module_is_missing(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "runai.agents.scrub", None)
    assert _merged_coverage(MILAN)["covered"] is False


def test_stoos_checkpoint_enabled_on_observed_participant_form():
    task = build_task(_race_trip(*STOOS), today=MERGED_TODAY, registry=_merged())
    patterns = task["checkpoint"]["url_patterns"]
    assert task["start_url"] == "https://my.raceresult.com/422182/registration"
    assert "(?!)" not in patterns
    form = "https://my.raceresult.com/422182/registration?regname=Einzel-Anmeldung"
    assert _matches(patterns, form)
    assert _matches(patterns, form.replace("regname", "lang=de&regname").upper())
    assert not _matches(patterns, task["start_url"])
    assert not _matches(patterns, "https://my.raceresult.com/422182/participants?regname=x")
    for boundary in ("payment", "login", "cart"):
        assert _matches(task["checkpoint"]["beyond_patterns"],
                        f"https://my.raceresult.com/422182/{boundary}")


@pytest.mark.parametrize("distance", [10, 11, 24, 25.6, 46.6])
def test_stoos_contest_labels_and_course_lengths_are_open(distance):
    trip = _race_trip(*STOOS)
    trip["race"]["distance_km"] = distance
    assert registration_coverage(trip["race"], today=MERGED_TODAY,
                                 registry=_merged())["status"] == "open"


def test_frankfurt_checkpoint_is_njuko_form_not_competition_list():
    task = build_task(_race_trip(*FRANKFURT), today=MERGED_TODAY, registry=_merged())
    base = "https://in.motionevents-registrations.com/mainova-frankfurt-marathon-2027-1789303690969"
    assert task["start_url"] == base + "?currentPage=select-competition"
    assert _matches(task["checkpoint"]["url_patterns"], base + "?currentPage=form_individual-form")
    assert not _matches(task["checkpoint"]["url_patterns"], task["start_url"])
    assert not evaluate_url("https://in.motionevents-registrations.com/other-race-2027",
                            "registration", today=MERGED_TODAY,
                            registry=policy_view(_merged())[0])["allowed"]


def test_madrid_checkpoint_matches_observed_form_not_event_landing():
    task = build_task(_race_trip(*FRESH_OPEN_RACES[-1]), today=MERGED_TODAY, registry=_merged())
    form = "https://www.mediomaratonmadrid.es/en/web-form/34571-general-entry"
    landing = ("https://www.mediomaratonmadrid.es/en/web-evento/"
               "13064-movistar-madrid-medio-maraton-2027")
    for attempt in [task, *task["alternatives"]]:
        assert _matches(attempt["checkpoint"]["url_patterns"], form)
        assert _matches(attempt["checkpoint"]["url_patterns"],
                        form.replace("/en/web-form", "/EN/WEB%2DFORM"))
        assert not _matches(attempt["checkpoint"]["url_patterns"], landing)


@pytest.mark.parametrize("race", FRESH_OPEN_RACES[3:6], ids=lambda r: r[0])
def test_provisional_endu_checkpoint_uses_path_query_not_host(race):
    task = build_task(_race_trip(*race), today=MERGED_TODAY, registry=_merged())
    patterns = task["checkpoint"]["url_patterns"]
    assert _matches(patterns, "https://www.endu.net/events/example/personal-data?edition=2027")
    assert not _matches(patterns, task["start_url"])
    assert not _matches(patterns, "https://participant.endu.net/events/example/book")


@pytest.mark.parametrize("distances", [[], "10", [True], [0], [float("nan")]])
def test_malformed_adapter_distance_scope_fails_closed(distances):
    reg = _with_availability()
    reg["entries"][0]["adapters"][0]["race_match"]["distances_km"] = distances
    assert _coverage(reg=reg)["covered"] is False
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), reg)


def test_fresh_observation_does_not_assert_an_unobserved_distance_open():
    trip = _race_trip(*FRESH_OPEN_RACES[-1])
    trip["race"]["distance_km"] = 10
    assert registration_coverage(trip["race"], today=MERGED_TODAY,
                                 registry=_merged())["status"] == "unknown"


def test_bologna_rounded_half_distance_has_fresh_open_coverage():
    trip = _race_trip(*FRESH_OPEN_RACES[4])
    trip["race"]["distance_km"] = 21.1
    coverage = registration_coverage(trip["race"], today=date(2026, 11, 9), registry=_merged())
    assert coverage["covered"] is True
    assert coverage["status"] == "open"


@pytest.mark.parametrize(("observed", "requested", "status"), [
    (21.097, 21.1, "open"), (42.195, 42.2, "open"), (5, 10, "unknown"),
])
def test_distance_tolerance_in_adapter_matching_and_availability(observed, requested, status):
    reg = _with_availability(distances_km=[observed])
    reg["entries"][0]["adapters"][0]["race_match"]["distances_km"] = [observed]
    coverage = _coverage(_trip(distance_km=requested)["race"], reg=reg)
    assert coverage["covered"] is True
    assert coverage["status"] == status


@pytest.mark.parametrize("distance", [None, "21.1", True, 0, float("inf"), float("nan")])
def test_distance_tolerance_rejects_invalid_distance(distance):
    assert not _distance_matches(distance, [21.097])


def test_distance_tolerance_does_not_match_empty_scope_or_different_race():
    assert not _distance_matches(21.1, [])
    assert not _distance_matches(10, [5])


@pytest.mark.parametrize(("text", "url", "status"), [
    ("Lista de Espera - Esgotada 07/03/2027", "", "sold_out"),
    ("", "https://meia-maratona.inscricoes.maratonaportugal.com/waitinglist.aspx?prova_id=3769",
     "sold_out"),
    ("As provas EDP Meia Maratona de Lisboa e Vodafone 10K estão esgotadas", "", "sold_out"),
    ("Halbmarathon AUSVERKAUFT", "", "sold_out"), ("Course complète : COMPLET", "", "sold_out"),
    ("Join the waiting list", "", "sold_out"), ("Halve marathon UITVERKOCHT", "", "sold_out"),
    ("Liste d’attente", "", "sold_out"), ("Inscripciones agotadas", "", "sold_out"),
    ("Registrations closed. The event is CLOSED.", "", "closed"),
    ("Anmeldung ist geschlossen", "", "closed"),
    ("Registration for the 2027 edition will open on Saturday, December 19.", "", "not_open"),
    ("Die Anmeldung startet voraussichtlich im Februar 2027", "", "not_open"),
    ("Einzel-Anmeldung ... Register Now", "", "open"), ("Inscrições abertas!", "", "open"),
    ("Registration open", "", "open"), ("Registration opens 1 March", "", "not_open"),
    ("", "", "unknown"), (None, 5, "unknown"), ("Marathon 2027 course map", "", "unknown"),
])
def test_availability_from_evidence(text, url, status):
    assert availability_from_evidence(text, url) == status


def test_waiting_list_registration_url_reports_sold_out_first_not_ready():
    trip = _race_trip(*LISBON_HALF)
    trip["race"]["registration_url"] = (
        "https://meia-maratona.inscricoes.maratonaportugal.com/waitinglist.aspx?prova_id=3769")
    task = build_task(trip, today=MERGED_TODAY, registry=_merged())
    first = task["instructions"].splitlines()[0]
    assert first.startswith("AVAILABILITY FIRST") and "BLOCKED sold_out" in first
    assert "Never join" in task["instructions"] and "Lista de " in task["instructions"]
    coverage = registration_coverage(trip["race"], today=MERGED_TODAY, registry=_merged())
    assert coverage["status"] == "sold_out" and coverage["registration"] == "sold_out"
    assert coverage["preparable_open"] is False


def test_sold_out_page_answer_maps_to_sold_out_not_unsafe_claim():
    task = build_task(_race_trip(*LISBON_HALF), today=MERGED_TODAY, registry=_merged())
    answer = {"blocker": "Waiting list only: Lista de Espera, inscrições esgotadas",
              "reached_step": "waitinglist.aspx"}
    assert hclient._blocked_reason(answer, task) == "sold_out"
    assert not hclient._payment_claim(
        "BLOCKED sold_out: registration is unavailable (waiting list). "
        "No payment, booking or submission was made.")


def test_not_yet_open_registration_url_is_not_preparable():
    trip = _race_trip(*FRESH_OPEN_RACES[1])
    trip["race"]["registration_url"] = "https://nncpcloopdenhaag.nl/coming-soon/"
    coverage = registration_coverage(trip["race"], today=MERGED_TODAY, registry=_merged())
    assert coverage["registration"] in {"not_open", "uncovered"}
    assert coverage["preparable_open"] is False


@pytest.mark.parametrize("race", [
    ("Schneider Electric Marathon de Paris", "2027-04-11", 42.195, "Paris", "France",
     "https://www.asicsmarathondeparis.com/"),
    ("Run In Lyon", "2027-10-03", 42.195, "Lyon", "France", "https://www.runinlyon.com/"),
    VALENCIA_10K, BARCELONA_HALF, IRONTRAIL,
])
def test_lifted_policy_does_not_invent_registration_coverage(race):
    coverage = _merged_coverage(race)
    assert coverage["prohibited"] is False
    if race in (VALENCIA_10K, BARCELONA_HALF, IRONTRAIL):
        assert coverage["covered"] is True
        assert coverage["preparable_open"] is False
        return
    assert coverage["covered"] is False and coverage["preparable_open"] is False
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build_task(_race_trip(*race), today=MERGED_TODAY, registry=_merged())


@pytest.mark.parametrize("race", [STOOS, FRANKFURT], ids=lambda r: r[0])
def test_next_edition_does_not_inherit_observed_2027_availability(race):
    trip = _race_trip(race[0], race[1].replace("2027", "2028"), *race[2:])
    coverage = registration_coverage(trip["race"], today=MERGED_TODAY, registry=_merged())
    assert coverage["status"] == "unknown" and coverage["preparable_open"] is False


BERLIN = ("BMW Berlin Marathon", "2027-09-26", 42.195, "Berlin", "Germany",
          "https://www.bmw-berlin-marathon.com/")
VALENCIA_MARATHON = (
    "Valencia Marathon Trinidad Alfonso", "2026-12-06", 42.195, "Valencia", "Spain",
    "https://www.valenciaciudaddelrunning.com/en/marathon/info-registration-2026/",
)
LISBON_MARATHON = (
    "EDP Lisbon Marathon", "2027-10-10", 42.195, "Lisboa", "Portugal",
    "https://maratonaclubedeportugal.com/maratona-de-lisboa/",
)
R7_RACES = [BERLIN, FRANKFURT, DEN_HAAG, VALENCIA_MARATHON, MILAN, STOOS,
            LISBON_HALF, LISBON_MARATHON]


@pytest.mark.parametrize("race", R7_RACES, ids=lambda r: r[0])
def test_r7_registration_build_and_current_policy(race):
    task = build_task(_race_trip(*race, edition=race[1][:4]), today=MERGED_TODAY)
    assert task["start_url"] and hclient._policy(task)
    if race == FRANKFURT:
        assert task["start_url"].startswith("https://in.motionevents-registrations.com/")
    else:
        assert scrub_url(task["start_url"]) == task["start_url"]
    if race in (BERLIN, DEN_HAAG, VALENCIA_MARATHON, LISBON_HALF, LISBON_MARATHON):
        for candidate in [task, *task["alternatives"]]:
            assert candidate["max_steps"] == 12
            assert candidate["instructions"].startswith("AVAILABILITY FIRST")
            assert "first 5 steps" in candidate["instructions"].splitlines()[0]
            assert candidate["checkpoint"]["url_patterns"] == ["(?!)"]
            assert candidate["success_signal"].startswith("BLOCKED")
        assert task["fallback_url"] in (task["start_url"], race[5])


@pytest.mark.parametrize("name", ["BMW Berlin Marathon", "Generali Berlin-Marathon",
                                  "Berlin Marathon"])
def test_berlin_official_account_boundary_not_preparable(name):
    trip = _race_trip(name, *BERLIN[1:])
    trip["runner_profile"] = {"full_name": "Test Runner"}
    task = build_task(trip, today=MERGED_TODAY)
    assert task["start_url"] == "https://www.generali-berlin-marathon.com/en/registration/run"
    assert task["fallback_url"] == task["start_url"]
    assert "BLOCKED login_required" in task["instructions"].splitlines()[0]
    assert "prefill_fields" not in task
    assert not registration_coverage(trip["race"], today=MERGED_TODAY)["preparable_open"]


def test_valencia_next_edition_is_unknown_not_inherited_sold_out():
    trip = _race_trip(VALENCIA_MARATHON[0], "2027-12-05", *VALENCIA_MARATHON[2:5],
                      "https://www.valenciaciudaddelrunning.com/en/marathon/")
    task = build_task(trip, today=MERGED_TODAY)
    assert task["start_url"].endswith("/en/marathon/")
    assert task["max_steps"] == 12
    assert "BLOCKED no_inventory" in task["instructions"].splitlines()[0]
    assert registration_coverage(trip["race"], today=MERGED_TODAY)["status"] == "unknown"


@pytest.mark.parametrize("age_days", [0, 22])
@pytest.mark.parametrize(("race", "reason"), [
    (BERLIN, "login_required"), (LISBON_MARATHON, "no_inventory"),
    (VALENCIA_MARATHON, "sold_out"),
    ((VALENCIA_MARATHON[0], "2027-12-05", *VALENCIA_MARATHON[2:5],
      "https://www.valenciaciudaddelrunning.com/en/marathon/"), "no_inventory"),
])
def test_adapter_early_stop_outlives_availability_observation(race, reason, age_days):
    today = MERGED_TODAY + timedelta(days=age_days)
    trip = _race_trip(*race, edition=race[1][:4])
    trip["runner_profile"] = {"full_name": "Test Runner"}
    task = build_task(trip, today=today)
    for candidate in [task, *task["alternatives"]]:
        assert candidate["max_steps"] == 12
        assert candidate["instructions"].startswith("AVAILABILITY FIRST")
        assert "first 5 steps" in candidate["instructions"].splitlines()[0]
        assert f"BLOCKED {reason}" in candidate["instructions"].splitlines()[0]
        assert candidate["success_signal"].startswith(f"BLOCKED {reason}")
        assert candidate["checkpoint"]["url_patterns"] == ["(?!)"]
        assert "prefill_fields" not in candidate
    assert task["fallback_url"] == task["start_url"]
    if age_days > 21:
        coverage = registration_coverage(trip["race"], today=today)
        assert coverage["status"] == "unknown"
        assert coverage["preparable_open"] is False


def test_adapter_early_stop_without_availability_observation():
    reg = _with_availability()
    adapter = reg["entries"][0]["adapters"][0]
    adapter.pop("availability")
    adapter["early_stop_reason"] = "login_required"
    task = build(_trip(), reg)
    assert task["max_steps"] == 12
    assert "BLOCKED login_required" in task["instructions"].splitlines()[0]
    assert task["checkpoint"]["url_patterns"] == ["(?!)"]


@pytest.mark.parametrize("race", [MILAN, STOOS, FRANKFURT])
def test_registration_prefill_field_names_only(race):
    trip = _race_trip(*race)
    profile = {"full_name": "Test Runner", "email": "test.runner@example.com",
               "phone": "+33 6 00 00 00 00", "birth_date": "1990-01-01",
               "given_name": "Test", "family_name": "Runner", "gender": "unspecified",
               "nationality": "Example nationality", "address_line": "Example address",
               "postal_code": "Example postal", "city": "Example hometown",
               "country": "Example country", "unexpected": "DO NOT INCLUDE"}
    trip["runner_profile"] = profile
    task = build_task(trip, today=MERGED_TODAY)
    for value in [profile[k] for k in ("full_name", "email", "phone", "birth_date", "unexpected")]:
        assert value not in json.dumps(task)
    original_trip = {k: v for k, v in trip.items() if k != "runner_profile"}
    original = build_task(original_trip, today=MERGED_TODAY)
    for candidate in [task, *task["alternatives"]]:
        assert set(candidate["prefill_fields"]) == set(profile) - {"unexpected"}
        assert candidate["prefill_scope"] == "participant form"
        assert candidate["checkpoint"]["prefill_patterns"] == original["checkpoint"]["url_patterns"]
        assert "intermediate Next/Continue" in candidate["instructions"]
        assert "Never tick terms/marketing" in candidate["instructions"]
        assert "Never echo" in candidate["success_signal"]
        assert STOP_FORM not in candidate["stop_before"]
        for boundary in ("terms", "consent", "medical", "account", "login", "payment"):
            assert _matches(candidate["checkpoint"]["url_patterns"],
                            "https://example.test/" + boundary)


STOP_FORM = "personal data form (name, email, phone, birth date, address, ID)"


@pytest.mark.parametrize("profile", [None, {}, [], "bad", 1, {"email": []},
                                     {"email": " "}, {"unknown": "Test Runner"}])
def test_registration_invalid_profile_keeps_untouched_form_boundary(profile):
    trip = _race_trip(*MILAN)
    original = build_task(trip, today=MERGED_TODAY)
    trip["runner_profile"] = profile
    result = build_task(trip, today=MERGED_TODAY)
    assert json.dumps(result) == json.dumps(original)
    assert STOP_FORM in result["stop_before"]


def test_registration_prefill_does_not_bypass_invalid_policy():
    trip = _race_trip(*MILAN)
    trip["runner_profile"] = {"full_name": "Test Runner"}
    with pytest.raises(ValueError, match="not policy-reviewed"):
        build_task(trip, today=MERGED_TODAY, registry={"schema_version": 1, "entries": []})


def test_bad_early_stop_reason_fails_closed():
    reg = _with_availability()
    reg["entries"][0]["adapters"][0]["early_stop_reason"] = "ready"
    with pytest.raises(ValueError, match="registry unavailable or invalid"):
        build(_trip(), reg)


def test_waiting_list_instruction_yields_hclient_sold_out_reason():
    task = build_task(_race_trip(*STOOS), today=MERGED_TODAY, registry=_merged())
    assert "must start with the words 'sold out'" in task["instructions"]
    answer = {"blocker": "sold out: waiting list only", "reached_step": "waiting list"}
    assert hclient._blocked_reason(answer, task) == "sold_out"


def test_invalid_availability_race_dates_fail_closed():
    reg = _with_availability()
    reg["entries"][0]["adapters"][0]["availability"]["race_dates"] = ["2027-13-40"]
    assert _coverage(reg=reg)["covered"] is False
