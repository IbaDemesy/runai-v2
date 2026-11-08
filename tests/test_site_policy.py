import copy
import json
from datetime import date

import pytest

from runai.agents import site_policy
from runai.agents.site_policy import (
    PolicyError,
    evaluate_url,
    load_registry,
    parse_registry,
    registration_info,
)

TODAY = date(2026, 11, 8)


def entry(**changes):
    base = {
        "id": "example-hotels", "name": "Example Hotels", "purposes": ["hotel"],
        "scopes": [{"host": "www.hotels.example", "path_prefix": "/search"}],
        "terms_urls": ["https://www.hotels.example/terms"],
        "reviewed_at": "2026-11-01", "expires_at": "2027-02-01",
        "reviewed_sections": "Section 4 Use of the site",
        "justification": "No automation or copying restriction for personal viewing.",
        "automation": "allowed_read_only", "screenshot_scope": "in_session_only",
        "navigation_hosts": ["secure.hotels.example"],
        "registration_observations": [],
        "adapters": [{
            "kind": "hotel", "destination_countries": ["IT", "PT", "DE"],
            "url_template": "https://www.hotels.example/search?city={city}&in={arrival_date}"
                            "&out={departure_date}&adults={travelers}",
            "success_evidence": "Rate page shows dates, adults and total.",
            "blocked_evidence": "No rooms message.",
        }],
    }
    base.update(changes)
    return base


def transport_entry(**changes):
    return entry(**{
        "id": "example-rail", "purposes": ["transport"],
        "scopes": [{"host": "tickets.rail.example", "path_prefix": "/"}],
        "navigation_hosts": [],
        "adapters": [{
            "kind": "transport", "destination_countries": ["IT", "PT", "DE", "CH"],
            "origin_countries": ["FR", "IT", "PT", "DE", "CH"],
            "url_template": "https://tickets.rail.example/results?from={origin_city}"
                            "&to={city}&out={arrival_date}&ret={departure_date}&pax={travelers}",
            "success_evidence": "Selected outbound and return with total fare.",
            "blocked_evidence": "No connections message.",
        }],
        **changes,
    })


def registration_entry(**changes):
    return entry(**{
        "id": "example-marathon-2027", "purposes": ["registration"],
        "scopes": [
            {"host": "www.example-marathon.test", "path_prefix": "/"},
            {"host": "in.njuko.com", "path_prefix": "/example-marathon-2027"},
        ],
        "navigation_hosts": [], "adapters": [],
        "registration_observations": [{
            "host": "in.njuko.com", "path_prefix": "/example-marathon-2027",
            "account_required": False, "captcha": None,
            "source": "https://in.njuko.com/example-marathon-2027",
            "observed_at": "2026-11-08", "note": "Distance list visible without login.",
        }],
        **changes,
    })


def registry(*entries):
    return {"schema_version": 1, "entries": list(entries) or [
        entry(), transport_entry(), registration_entry(),
        entry(id="denied-chain", automation="prohibited", screenshot_scope="none",
              scopes=[{"host": "chain.example", "path_prefix": "/"}], adapters=[]),
    ]}


KEYS = {"allowed", "reason", "policy_id", "screenshot_scope", "allowed_hosts", "allowed_paths",
        "expires_at"}


def check(url, kind="hotel", reg=None, today=TODAY):
    result = evaluate_url(url, kind, today=today, registry=registry() if reg is None else reg)
    assert set(result) == KEYS
    return result


def test_allowed_in_scope():
    result = check("https://www.hotels.example/search/results?city=Milan")
    assert result["allowed"] is True
    assert result["policy_id"] == "example-hotels"
    assert result["screenshot_scope"] is True
    assert result["allowed_hosts"] == ["secure.hotels.example", "www.hotels.example"]
    assert result["expires_at"] == "2027-02-01"


@pytest.mark.parametrize("url", [
    "https://www.hotels.example/account", "https://www.hotels.example/searchx",
    "https://evil.www.hotels.example/search", "https://hotels.example/search",
    "https://secure.hotels.example/search", "https://unknown.example/",
])
def test_path_subdomain_and_unknown_fail_closed(url):
    result = check(url)
    assert result["allowed"] is False
    assert result["allowed_hosts"] == []


def test_purpose_restricted():
    assert check("https://www.hotels.example/search", "transport")["allowed"] is False
    assert "does not cover" in check("https://www.hotels.example/search", "transport")["reason"]


@pytest.mark.parametrize("today,reason", [
    (date(2027, 2, 1), "expired"), (date(2028, 1, 1), "expired"), (date(2026, 10, 1), "future"),
])
def test_expired_or_future_review(today, reason):
    result = check("https://www.hotels.example/search", today=today)
    assert result["allowed"] is False and reason in result["reason"]


@pytest.mark.parametrize("scope", ["none", "unclear"])
def test_missing_or_unclear_screenshot_scope(scope):
    reg = registry(entry(screenshot_scope=scope))
    result = check("https://www.hotels.example/search", reg=reg)
    assert result["allowed"] is False and "screenshot" in result["reason"]


def test_ambiguous_terms_fail_closed():
    reg = registry(entry(automation="ambiguous"))
    assert check("https://www.hotels.example/search", reg=reg)["allowed"] is False


def test_prohibited_denies_all_subdomains():
    for url in ("https://chain.example/", "https://www.chain.example/search",
                "https://deep.sub.chain.example/x"):
        result = check(url)
        assert result["allowed"] is False and "prohibit" in result["reason"]


@pytest.mark.parametrize("url", [
    None, "", "  ", 42, "http://www.hotels.example/search", "ftp://www.hotels.example/search",
    "https://user:pw@www.hotels.example/search", "https://www.hotels.example:8443/search",
    "https://www.hotels.example/se arch", "https:///nohost", "javascript:alert(1)",
])
def test_bad_urls_never_raise(url):
    assert check(url)["allowed"] is False


def test_unknown_kind_and_bad_registry():
    assert check("https://www.hotels.example/search", kind="payment")["allowed"] is False
    for bad in ({}, {"schema_version": 2, "entries": []}, {"schema_version": 1, "entries": [1]},
                {"schema_version": 1, "entries": [entry(scopes=[{"host": "*.x.example"}])]}):
        result = check("https://www.hotels.example/search", reg=bad)
        assert result["allowed"] is False and "registry" in result["reason"]


def test_empty_registry_denies():
    assert check("https://www.hotels.example/search", reg={"schema_version": 1, "entries": []})[
        "allowed"] is False


@pytest.mark.parametrize("changes", [
    {"terms_urls": []}, {"terms_urls": ["http://x.example/terms"]},
    {"reviewed_at": "2027-03-01"}, {"expires_at": "soon"}, {"justification": ""},
    {"automation": "yes"}, {"screenshot_scope": True}, {"purposes": ["payment"]},
    {"scopes": []}, {"scopes": [{"host": "WWW.X.EXAMPLE"}]},
    {"navigation_hosts": ["*.hotels.example"]},
    {"adapters": [{"kind": "hotel", "url_template": "https://other.example/?c={city}",
                   "success_evidence": "x", "blocked_evidence": "y"}]},
    {"adapters": [{"kind": "hotel", "url_template": "https://www.hotels.example/{city}",
                   "success_evidence": "x", "blocked_evidence": "y"}]},
    {"adapters": [{"kind": "hotel", "url_template": "https://www.hotels.example/?t={token}",
                   "success_evidence": "x", "blocked_evidence": "y"}]},
])
def test_parse_rejects_incomplete_reviews(changes):
    with pytest.raises(PolicyError):
        parse_registry(registry(entry(**changes)))


def test_registration_info_is_source_only_observation():
    info = registration_info("https://in.njuko.com/example-marathon-2027/race", registry=registry())
    assert info == {"account_required": False, "captcha": None,
                    "source": "https://in.njuko.com/example-marathon-2027",
                    "observed_at": "2026-11-08"}
    assert "allowed" not in info


@pytest.mark.parametrize("url", [
    "https://in.njuko.com/other-race", "https://www.example-marathon.test/", "", None,
    "http://in.njuko.com/example-marathon-2027", "https://unknown.example/",
])
def test_registration_info_unknown_or_invalid(url):
    assert registration_info(url, registry=registry()) is None


def test_registration_info_bad_registry():
    assert registration_info("https://in.njuko.com/example-marathon-2027",
                             registry={"schema_version": 9}) is None


def test_observation_does_not_grant_permission():
    reg = registry(registration_entry(automation="ambiguous"))
    assert registration_info("https://in.njuko.com/example-marathon-2027", registry=reg)
    assert check("https://in.njuko.com/example-marathon-2027", "registration", reg)[
        "allowed"] is False


def test_one_reviewed_race_does_not_allow_platform_customers():
    assert check("https://in.njuko.com/another-race-2027", "registration")["allowed"] is False
    assert check("https://www.njuko.com/", "registration")["allowed"] is False


# --- committed registry -------------------------------------------------------------------

def test_committed_registry_is_valid_and_dated():
    entries = load_registry()
    assert entries
    raw = json.loads(site_policy.REGISTRY_PATH.read_text())
    for item in raw["entries"]:
        assert item["terms_urls"] and item["reviewed_at"] and item["expires_at"]
        assert item["reviewed_sections"].strip() and item["justification"].strip()


@pytest.mark.parametrize("url", [
    "https://all.accor.com/", "https://all.accor.com/hotel/1234/index.en.shtml",
    "https://ibis.accor.com/", "https://www.accor.com/", "https://group.accor.com/",
])
def test_accor_denied(url):
    result = evaluate_url(url, "hotel", today=TODAY)
    assert result["allowed"] is False and "prohibit" in result["reason"]


@pytest.mark.parametrize("url,kind", [
    ("https://www.booking.com/searchresults.html", "hotel"),
    ("https://www.hilton.com/en/search/", "hotel"),
    ("https://www.google.com/travel/flights", "transport"),
    ("https://www.omio.com/", "transport"),
    ("https://www.sbb.ch/en", "hotel"),
    ("https://www.ihg.com/", "transport"),
    ("https://www.sncf-connect.com/", "transport"),
])
def test_official_chains_and_operators_not_allowed_without_review(url, kind):
    assert evaluate_url(url, kind, today=TODAY)["allowed"] is False


def test_committed_allow_entries_are_narrow():
    for item in load_registry():
        if item["automation"] not in ("allowed_read_only", "allowed_owner_rule"):
            continue
        assert item["screenshot_scope"] == "in_session_only"
        for scope in item["scopes"]:
            assert "*" not in scope["host"]
        if "registration" in item["purposes"]:
            assert all(s["path_prefix"] != "/" or s["host"].count(".") >= 1 for s in item["scopes"])


def test_registry_not_mutated_by_evaluation():
    reg = registry()
    snapshot = copy.deepcopy(reg)
    check("https://www.hotels.example/search", reg=reg)
    assert reg == snapshot


def test_owner_rule_allows_ambiguous_terms_with_explicit_reason():
    reg = registry(entry(automation="allowed_owner_rule"))
    result = check("https://www.hotels.example/search", reg=reg)
    assert result["allowed"] is True
    assert "ambiguous" in result["reason"] and "owner" in result["reason"]


def test_owner_rule_still_needs_in_session_screenshot_scope():
    reg = registry(entry(automation="allowed_owner_rule", screenshot_scope="unclear"))
    assert check("https://www.hotels.example/search", reg=reg)["allowed"] is False


@pytest.mark.parametrize("url,kind", [
    ("https://www.trenitalia.com/", "transport"),
    ("https://www.sbb.ch/en", "transport"),
    ("https://www.ihg.com/", "hotel"),
])
def test_committed_owner_rule_sites_are_allowed_and_labelled(url, kind):
    result = evaluate_url(url, kind, today=TODAY)
    assert result["allowed"] is True and "owner" in result["reason"]


def test_explicit_prohibition_beats_owner_rule():
    assert evaluate_url("https://www.booking.com/", "hotel", today=TODAY)["allowed"] is False
    assert evaluate_url("https://all.accor.com/", "hotel", today=TODAY)["allowed"] is False


def _place_registry(**adapter_changes):
    adapter = {
        "kind": "hotel",
        "url_template": "https://www.hotels.example/search?h={place_id}&in={arrival_day}"
                        "&m={arrival_monthyear0}&out={departure_dmy_slash}",
        "places": {"Zürich": {"place_id": "ZRH 1"}},
        "success_evidence": "selected room and rate", "blocked_evidence": "no rooms",
    }
    adapter.update(adapter_changes)
    return registry(entry(adapters=[adapter]))


EXPECTED = {"city": "zürich", "country": "CH", "arrival_date": "2027-03-13",
            "departure_date": "2027-03-15", "travelers": 1}


def test_place_ids_and_site_date_encodings():
    _, url, _ = site_policy.select_adapter("hotel", EXPECTED, today=TODAY,
                                           registry=_place_registry())
    assert url == ("https://www.hotels.example/search?h=ZRH%201&in=13&m=022027"
                   "&out=15%2F03%2F2027")


def test_city_without_reviewed_place_ids_blocks():
    with pytest.raises(ValueError, match="no reviewed place IDs"):
        site_policy.select_adapter("hotel", {**EXPECTED, "city": "Basel"}, today=TODAY,
                                   registry=_place_registry())


def test_place_template_without_places_is_invalid():
    with pytest.raises(PolicyError):
        parse_registry(_place_registry(places=None))


def test_allowed_paths_keep_event_scope():
    url = "https://in.njuko.com/wizz-air-milano-marathon-20271776152378557/registration"
    result = evaluate_url(url, "registration", today=TODAY)
    assert result["allowed"] is True
    assert result["allowed_paths"] == ["/wizz-air-milano-marathon-20271776152378557"]
    path_scoped = check("https://www.hotels.example/search", reg=registry(entry()))
    assert path_scoped["allowed_paths"] == ["/search"]
    assert check("https://unknown.example/")["allowed_paths"] == []


def test_registry_reload_picks_up_revocation(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(registry(entry())), encoding="utf-8")
    assert load_registry(path)[0]["automation"] == "allowed_read_only"
    revoked = registry(entry(automation="prohibited"))
    path.write_text(json.dumps(revoked), encoding="utf-8")
    import os
    os.utime(path, ns=(1, 1))
    assert load_registry(path)[0]["automation"] == "prohibited"
