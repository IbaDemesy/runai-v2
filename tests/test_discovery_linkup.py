import asyncio
import copy
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from runai.discovery import DiscoveryError, DiscoveryUnavailable, discover

KEY = "offline-test-secret-never-echo"
DAY = (datetime.now(UTC).date() + timedelta(days=180)).isoformat()
YEAR = DAY[:4]
EXPECTED_KEYS = {
    "id", "name", "edition", "distance_km", "distance_label", "race_date", "date_status",
    "city", "country", "official_url", "registration_url", "source_urls", "retrieved_at",
    "synthetic",
}


def race(**changes):
    row = {
        "name": "Example Marathon",
        "edition": YEAR,
        "distance_km": 42.195,
        "distance_label": "Marathon",
        "city": "Example City",
        "country": "Italy",
        "official_url": "https://race.example/",
        "registration_url": "https://entries.example/race",
        "registration_source_url": "https://race.example/edition",
        "sources": [{"url": "https://race.example/edition", "race_date": DAY}],
    }
    return row | changes


def search(rows, **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"candidates": rows})
        )) as client:
            result = await discover("a running race", api_key=KEY, client=client, **kwargs)
            assert not client.is_closed
            return result

    return asyncio.run(run())


def test_normal_multi_candidate_and_structured_request():
    async def run():
        def handler(request):
            assert str(request.url) == "https://api.linkup.so/v1/search"
            assert request.headers["authorization"] == f"Bearer {KEY}"
            payload = json.loads(request.content)
            assert payload["depth"] == "deep"
            assert payload["outputType"] == "structured"
            schema = json.loads(payload["structuredOutputSchema"])
            assert schema["type"] == "object"
            assert "candidates" in schema["properties"]
            assert '"country": "Italy"' in payload["q"]
            assert '"distance": "marathon"' in payload["q"]
            assert "ignore_this" not in payload["q"]
            assert datetime.now(UTC).date().isoformat() in payload["q"]
            assert request.extensions["timeout"]["read"] == 7
            return httpx.Response(200, json={"candidates": [
                race(), race(name="Second Race", distance_km=21.0975),
            ]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await discover(
                "un marathon au printemps en Italie",
                {"country": "Italy", "distance": "marathon", "ignore_this": "secret"},
                api_key=KEY, client=client, timeout_s=7,
            )

    results = asyncio.run(run())
    assert len(results) == 2
    assert results[0]["id"] == f"example-marathon-{YEAR}"
    for candidate in results:
        assert set(candidate) == EXPECTED_KEYS
        assert candidate["date_status"] == "official"
        assert candidate["race_date"] == DAY
        assert candidate["synthetic"] is False
        assert candidate["registration_url"] == "https://entries.example/race"
        assert datetime.fromisoformat(candidate["retrieved_at"]).utcoffset() == timedelta(0)
    assert search([race()])[0]["id"] == results[0]["id"]


def test_empty_results():
    assert search([]) == []


def test_unicode_race_names_have_stable_distinct_ids():
    results = search([race(name="東京マラソン"), race(name="北京马拉松")])
    assert len(results) == 2
    assert results[0]["id"] != results[1]["id"]
    assert search([race(name="東京マラソン")])[0]["id"] == results[0]["id"]


def test_conflicting_dates_even_across_duplicate_candidates():
    other = (datetime.fromisoformat(DAY).date() + timedelta(days=1)).isoformat()
    results = search([
        race(),
        race(name="EXAMPLE Marathon", edition=f"25th edition ({YEAR})", sources=[
            {"url": "https://calendar.example/edition", "race_date": other},
        ]),
    ])
    assert len(results) == 1
    assert results[0]["date_status"] == "conflicting"
    assert results[0]["race_date"] is None
    assert len(results[0]["source_urls"]) == 2


def test_past_editions_filtered_before_cap_but_returned_if_only_results():
    past = race(edition="2000", sources=[
        {"url": "https://race.example/old", "race_date": "2000-04-01"},
    ])
    assert [row["edition"] for row in search([past, race()])] == [YEAR]
    assert search([past])[0]["race_date"] == "2000-04-01"
    assert len(search([race(name=f"Race {index}") for index in range(10)])) == 6
    old_unknown = race(edition="2000", sources=[
        {"url": "https://race.example/old", "race_date": None},
    ])
    assert [row["edition"] for row in search([old_unknown, race()])] == [YEAR]


def test_race_today_is_upcoming():
    today = datetime.now(UTC).date().isoformat()
    result = search([race(sources=[{"url": "https://race.example/", "race_date": today}])])
    assert result[0]["race_date"] == today


def test_unverified_unknown_and_invalid_dates():
    result = search([race(sources=[{"url": "https://directory.example/race", "race_date": DAY}])])
    assert result[0]["date_status"] == "unverified"
    for value in [None, "not a date", "2027-02-30", "2027-04-01T09:00:00"]:
        result = search([race(sources=[{"url": "https://race.example/", "race_date": value}])])
        assert result[0]["date_status"] == "unknown"
        assert result[0]["race_date"] is None


def test_sources_required_and_public_urls_only():
    assert search([race(sources=[])]) == []
    for url in ["", "javascript:alert(1)", "https://user:password@race.example/",
                "https://race.example/?token=private", "https://race.example/#private",
                "https://race.example:invalid/", "https://race.example/\nprivate"]:
        assert search([race(sources=[{"url": url, "race_date": DAY}])]) == []


def test_registration_requires_official_link_evidence_and_cannot_spoof_host():
    row = race(registration_source_url=None)
    assert search([row])[0]["registration_url"] is None
    row = race(registration_source_url="https://directory.example/race", sources=[
        {"url": "https://directory.example/race", "race_date": DAY},
    ])
    assert search([row])[0]["registration_url"] is None
    row = race(sources=[{"url": "https://race.example.evil.test/", "race_date": DAY}])
    assert search([row])[0]["date_status"] == "unverified"
    row = race(sources=[
        {"url": "https://race.example/edition", "race_date": None},
        {"url": "https://entries.example/race", "race_date": DAY},
    ])
    assert search([row])[0]["date_status"] == "official"
    row["official_url"] = None
    assert search([row])[0]["date_status"] == "unverified"
    assert search([row])[0]["registration_url"] is None


@pytest.mark.parametrize("distance", [None, 0, -1])
def test_unknown_or_invalid_distances_are_not_invented(distance):
    assert search([race(distance_km=distance)])[0]["distance_km"] is None


def test_missing_key(monkeypatch):
    monkeypatch.delenv("LINKUP_API_KEY", raising=False)
    with pytest.raises(DiscoveryUnavailable, match="LINKUP_API_KEY"):
        asyncio.run(discover("race"))
    with pytest.raises(DiscoveryUnavailable):
        asyncio.run(discover("race", api_key=" "))


def test_env_key_and_owned_client_closed(monkeypatch):
    monkeypatch.setenv("LINKUP_API_KEY", KEY)
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"candidates": []})
    ))
    monkeypatch.setattr("runai.discovery.linkup.httpx.AsyncClient", lambda: client)
    assert asyncio.run(discover("race")) == []
    assert client.is_closed


@pytest.mark.parametrize("failure", ["timeout", "401", "503", "network", "json", "shape", "key"])
def test_errors_are_safe_and_injected_client_stays_open(failure):
    async def run():
        def handler(request):
            if failure == "timeout":
                raise httpx.ReadTimeout(f"provider echoed {KEY}", request=request)
            if failure == "network":
                raise httpx.ConnectError(f"provider echoed {KEY}", request=request)
            if failure in {"401", "503"}:
                return httpx.Response(int(failure), text=f"provider echoed {KEY}")
            if failure == "json":
                return httpx.Response(200, text=f"not json {KEY[:10]}")
            if failure == "key":
                return httpx.Response(200, json={"candidates": [race(name=KEY)]})
            malformed = copy.deepcopy(race())
            malformed["sources"] = "invalid"
            return httpx.Response(200, json={"candidates": [malformed]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(DiscoveryError) as captured:
                await discover("race", api_key=KEY, client=client)
            assert KEY not in str(captured.value)
            assert KEY not in repr(captured.value)
            assert captured.value.__cause__ is None
            assert not client.is_closed
            if failure == "timeout":
                assert "timed out" in str(captured.value)
            if failure in {"401", "503"}:
                assert failure in str(captured.value)

    asyncio.run(run())
