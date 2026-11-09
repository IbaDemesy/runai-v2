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

TODAY = date(2026, 11, 9)


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


def test_registry_fragments_order_reload_and_fail_closed(tmp_path, monkeypatch):
    path = tmp_path / "policy.json"
    fragments = tmp_path / "site-policy.d"
    fragments.mkdir()
    path.write_text(json.dumps(registry(entry())))
    def fragment(name, ident):
        target = fragments / name
        target.write_text(json.dumps(registry(entry(id=ident))))
        return target
    fragment("b.json", "second")
    first = fragment("a.json", "first")
    assert [e["id"] for e in load_registry(path)] == ["example-hotels", "first", "second"]
    first.write_text(json.dumps(registry(entry(id="updated"))))
    fragment("c.json", "third")
    assert [e["id"] for e in load_registry(path)] == [
        "example-hotels", "updated", "second", "third",
    ]
    fragment("d.json", "example-hotels")
    loader = site_policy.load_registry
    monkeypatch.setattr(site_policy, "load_registry", lambda: loader(path))
    assert not evaluate_url("https://www.hotels.example/search", "hotel")["allowed"]
    with pytest.raises(ValueError, match="registry"):
        site_policy.select_adapter("hotel", EXPECTED)
    (fragments / "d.json").write_text("not json")
    with pytest.raises(PolicyError):
        loader(path)


def test_registry_documents_and_scope_conflicts():
    documents = [registry(entry()), registry(entry(id="other"))]
    assert len(site_policy._registry(tuple(documents))) == 2
    assert check("https://www.hotels.example/search", reg=documents)["allowed"]
    with pytest.raises(PolicyError, match="conflicting"):
        parse_registry(registry(entry(), entry(id="other", automation="prohibited")))


@pytest.mark.parametrize("template", [
    "https://www.hotels.example/search?q={city!r}",
    "https://www.hotels.example/search?q={city:>5}",
    "https://www.hotels.example/search?q={unknown}",
    "https://www.hotels.example/{city}", "https://{city}/search",
    "https://www.hotels.example/search?q={city.upper}",
])
def test_strict_template_fields(template):
    with pytest.raises(PolicyError):
        parse_registry(_place_registry(url_template=template, places=None))


def test_free_text_lookup_defaults_overrides_and_dates():
    reg = _place_registry(
        url_template="https://www.hotels.example/search?c={city_query}&o={origin_city_query}"
                     "&a={arrival_ymd}&d={departure_dmy_dash}", places=None,
    )
    expected = {**EXPECTED, "origin_city": "Bâle"}
    url = site_policy.select_adapter("hotel", expected, today=TODAY, registry=reg)[1]
    assert "c=z%C3%BCrich&o=B%C3%A2le&a=20270313&d=15-03-2027" in url
    reg["entries"][0]["adapters"][0]["places"] = {"ZÜRICH": {"city_query": "Zurich, CH"}}
    assert "c=Zurich%2C%20CH" in site_policy.select_adapter(
        "hotel", expected, today=TODAY, registry=reg,
    )[1]


def test_iata_requires_reviewed_city_and_field():
    reg = _place_registry(url_template="https://www.hotels.example/search?to={iata}",
                          places={"Zurich": {"iata": "ZRH"}})
    assert "to=ZRH" in site_policy.select_adapter(
        "hotel", {**EXPECTED, "city": "Zurich"}, today=TODAY, registry=reg,
    )[1]
    with pytest.raises(ValueError, match="no reviewed place IDs"):
        site_policy.select_adapter("hotel", EXPECTED, today=TODAY, registry=reg)


@pytest.mark.parametrize("counts", [[], [0], [True], ["1"], "1"])
def test_invalid_reviewed_traveler_counts(counts):
    with pytest.raises(PolicyError, match="traveler_counts"):
        parse_registry(_place_registry(traveler_counts=counts))


def test_reviewed_traveler_counts_and_mdy_dates():
    reg = _place_registry(traveler_counts=[1], url_template=(
        "https://www.hotels.example/search?in={arrival_mdy_slash}&out={departure_mdy_slash}"))
    url = site_policy.select_adapter("hotel", EXPECTED, today=TODAY, registry=reg)[1]
    assert "in=03%2F13%2F2027&out=03%2F15%2F2027" in url
    with pytest.raises(ValueError, match="party size not reviewed"):
        site_policy.select_adapter("hotel", {**EXPECTED, "travelers": 2},
                                   today=TODAY, registry=reg)


def test_mode_ordering_and_unmoded_fallback():
    base = transport_entry()
    adapter = base["adapters"][0]
    base["adapters"] = [{**adapter, "mode": mode} for mode in ("flight", "rail", None)]
    reg = registry(base)
    assert site_policy.select_adapter("transport", EXPECTED, origin_country="FR",
                                     today=TODAY, registry=reg)[0]["mode"] == "flight"
    assert site_policy.select_adapter("transport", EXPECTED, origin_country="FR",
                                     today=TODAY, registry=reg,
                                     modes=["rail", "flight"])[0]["mode"] == "rail"
    assert site_policy.select_adapter("transport", EXPECTED, origin_country="FR",
                                     today=TODAY, registry=reg, modes=["bus"])[0]["mode"] is None
    base["adapters"][0]["mode"] = "boat"
    with pytest.raises(PolicyError):
        parse_registry(reg)


def registration_adapter_registry(**changes):
    adapter = {
        "kind": "registration", "race_match": {"name_patterns": ["example marathon"],
                                                "countries": ["IT"]},
        "platform_hosts": ["platform.example"],
        "url_template": "https://www.example-marathon.test/?race={race_name}",
        "success_evidence": "race visible", "blocked_evidence": "account wall",
        **changes,
    }
    return registry(registration_entry(adapters=[adapter]), registration_entry(
        id="platform", scopes=[{"host": "platform.example", "path_prefix": "/"}],
    ))


@pytest.mark.parametrize("changes", [
    {"race_match": {"name_patterns": ["["]}}, {"race_match": {"name_patterns": []}},
    {"platform_hosts": []}, {"platform_hosts": ["unknown.example"]},
])
def test_registration_adapter_validation(changes):
    with pytest.raises(PolicyError):
        parse_registry(registration_adapter_registry(**changes))


def test_registration_matching_country_and_platform_expiry():
    reg = registration_adapter_registry()
    expected = {**EXPECTED, "country": "IT", "race_name": "EXAMPLE MARATHON 2027"}
    assert "race=EXAMPLE%20MARATHON%202027" in site_policy.select_adapter(
        "registration", expected, today=TODAY, registry=reg,
    )[1]
    assert site_policy.coverage("registration", country="IT", today=TODAY,
                                registry=reg)["covered"]
    assert not site_policy.coverage("registration", country="FR", today=TODAY,
                                    registry=reg)["covered"]
    for update in ({"race_name": "Other race"}, {"country": "FR"}):
        with pytest.raises(ValueError, match="does not match"):
            site_policy.select_adapter("registration", {**expected, **update},
                                       today=TODAY, registry=reg)
    reg["entries"][1]["expires_at"] = "2026-11-07"
    with pytest.raises(ValueError, match="platform unavailable or expired"):
        site_policy.select_adapter("registration", expected, today=TODAY, registry=reg)
    assert not site_policy.coverage("registration", today=TODAY, registry=reg)["covered"]


def test_coverage_normal_empty_and_error():
    reg = _place_registry()
    assert site_policy.coverage("hotel", city="Zürich", country="Switzerland",
                                today=TODAY, registry=reg) == {
        "covered": True, "policy_ids": ["example-hotels"],
    }
    assert site_policy.coverage("hotel", today=TODAY, registry=reg)["covered"]
    for kwargs in ({"city": "Basel"}, {"today": date(2028, 1, 1)}, {"country": "unknown"}):
        assert not site_policy.coverage("hotel", registry=reg, **kwargs)["covered"]
    for bad in (None, {}, [], 42, object(), {"schema_version": 1, "entries": [object()]}):
        if bad is None:
            continue
        assert site_policy.coverage("hotel", registry=bad) == {"covered": False, "policy_ids": []}
    assert not site_policy.coverage([], registry=reg)["covered"]
    assert not site_policy.coverage("hotel", city=[], registry=reg)["covered"]
    assert not site_policy.coverage("hotel", today="bad", registry=reg)["covered"]


def test_coverage_origin_filters_and_policy_order():
    reg = registry(transport_entry(), transport_entry(id="other"))
    result = site_policy.coverage("transport", country="CH", origin_city="Freiburg",
                                  today=TODAY, registry=reg)
    assert result == {"covered": True, "policy_ids": ["example-rail", "other"]}
    assert not site_policy.coverage("transport", origin_city="Dublin", today=TODAY,
                                    registry=reg)["covered"]


def test_origin_lookup_and_coverage():
    base = transport_entry()
    base["adapters"][0].update({
        "url_template": "https://tickets.rail.example/?o={origin_station_code}&s={station_name}",
        "places": {"Zürich": {"station_name": "Zürich HB"}},
        "origin_places": {"Bâle": {"origin_station_code": "8500010"}},
    })
    reg = registry(base)
    expected = {**EXPECTED, "origin_city": "bÂLE"}
    assert "o=8500010&s=Z%C3%BCrich%20HB" in site_policy.select_adapter(
        "transport", expected, origin_country="CH", today=TODAY, registry=reg,
    )[1]
    assert site_policy.coverage("transport", city="Zürich", origin_city="Bâle",
                                today=TODAY, registry=reg)["covered"]
    assert not site_policy.coverage("transport", city="Zürich", origin_city="Paris",
                                    today=TODAY, registry=reg)["covered"]
    with pytest.raises(ValueError, match="no reviewed place IDs for this origin"):
        site_policy.select_adapter("transport", {**expected, "origin_city": "Paris"},
                                   origin_country="FR", today=TODAY, registry=reg)


@pytest.mark.parametrize("host", ["www.flixbus.com", "www.sncf-connect.com", "www.omio.com"])
def test_unreviewed_transport_stays_denied(host):
    assert not evaluate_url(f"https://{host}/", "transport", today=TODAY)["allowed"]
