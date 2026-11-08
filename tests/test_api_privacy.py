import builtins
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from test_api_guided import StubGuide, ready, terminal

from runai.app import create_app, sanitize

SENTINELS = ["4111 1111 1111 1111", "4111-1111-1111-1111",
             "runner.sentinel@example.com", "+33 6 12 34 56 78",
             "sk-SENTINELSECRET1234567890abcdefXYZ", "FR76 3000 6000 0112 3456 7890 189"]
TEXT = "budget 800 € le 2027-04-04 " + " ; ".join(SENTINELS)


@pytest.mark.parametrize("secret", SENTINELS)
@pytest.mark.parametrize("location", ["query", "path"])
def test_url_fields_reject_sensitive_components(secret, location):
    encoded = quote(secret, safe="")
    url = (f"https://example.org/p?contact={encoded}" if location == "query" else
           f"https://example.org/p/{encoded}")
    assert sanitize({"official_url": url, "source_urls": [url]}) == {
        "official_url": None, "source_urls": [],
    }
    safe = "https://example.org/race/2027-04-04?budget=800&distance=42.195"
    assert sanitize(safe, "official_url") == safe


@pytest.mark.parametrize("text", [
    "Bearer SENTINEL", "api_key=SENTINEL", "access_token: SENTINEL",
    "secret=SENTINEL", "authorization: SENTINEL",
])
def test_missing_scrubber_fallback_removes_credentials(monkeypatch, text):
    original_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == "runai.agents.scrub":
            raise ImportError("Scrubber unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    assert "SENTINEL" not in sanitize(text)
    assert sanitize("budget 800 € le 2027-04-04") == "budget 800 € le 2027-04-04"


@pytest.mark.parametrize("ids", [
    ["a" * 40, "b" * 40],
    ["lisbon-half-2027-1234567890", "lisbon-half-2027-0987654321"],
])
def test_distinct_slug_ids_survive_chip_round_trip(ids):
    captured = []

    class SlugGuide:
        async def start(self, text):
            return {}, {"message": "Choose a race", "ready_to_confirm": False,
                        "candidates": [{"id": item} for item in ids],
                        "suggestions": [{"id": item, "label": item[:1]} for item in ids]}

        async def step(self, state, answer):
            captured.append(answer["suggestion_id"])
            return await self.start("")

    with TestClient(create_app(guide=SlugGuide())) as client:
        mission = client.post("/api/missions", json={"text": "race"}).json()
        turn = mission["turns"][-1]
        assert [item["id"] for item in turn["candidates"]] == ids
        assert [item["id"] for item in turn["suggestions"]] == ids
        url = f"/api/missions/{mission['id']}/messages"
        for item in ids:
            assert client.post(url, json={"suggestion_id": item}).status_code == 200
    assert captured == ids
    assert sanitize("runner.sentinel@example.com", "id") != "runner.sentinel@example.com"


@pytest.mark.parametrize("key", ["id", "suggestion_id"])
@pytest.mark.parametrize("secret", [
    "4111111111111111", "4111-1111-1111-1111", "FR7630006000011234567890189",
    "sk-SENTINELSECRET1234567890abcdefXYZ", "hai_SENTINELSECRET1234567890abcdefXYZ",
    "runner.sentinel@example.com", "0612345678", "+33 6 12 34 56 78",
    "Bearer SENTINEL", "api_key=SENTINEL", "authorization:SENTINEL",
])
def test_id_exemption_does_not_preserve_sensitive_values(key, secret):
    assert secret not in sanitize(secret, key)


def test_inputs_state_output_validation_and_logs_are_private(caplog):
    captured = []

    class EchoGuide:
        async def start(self, text):
            captured.append(text)
            return {"trip": {"origin_city": text}}, {"message": text, "ready_to_confirm": False}

        async def step(self, state, answer):
            captured.append(str(state))
            return await self.start(answer["text"])

    with TestClient(create_app(guide=EchoGuide())) as client:
        response = client.post("/api/missions", json={"text": TEXT})
        assert response.status_code == 201
        url = f"/api/missions/{response.json()['id']}"
        response = client.post(url + "/messages", json={"text": TEXT})
        assert response.status_code == 200
        assert "budget 800 € le 2027-04-04" in response.json()["turns"][-1]["message"]
        invalid = client.post("/api/missions", json={"text": TEXT, "mode": TEXT})
        assert invalid.status_code == 422
        for error in invalid.json()["detail"]:
            assert set(error) == {"loc", "msg", "type"}
        everything = str(captured) + response.text + invalid.text + caplog.text
        assert all(secret not in everything for secret in SENTINELS)


def test_provider_turns_events_and_results_are_sanitized(caplog):
    class UnsafeGuide(StubGuide):
        async def step(self, state, answer):
            state, turn = await super().step(state, answer)
            turn["message"] = TEXT
            turn["nested"] = {"error": TEXT}
            state.trip["origin_city"] = TEXT
            return state, turn

    class UnsafeRunner:
        async def run(self, kind, trip, emit):
            await emit({"type": "step_progress", "message": TEXT})
            return {"kind": kind, "status": "failed", "summary": TEXT, "error": TEXT,
                    "synthetic": True}

    with TestClient(create_app(guide=UnsafeGuide(), runner_factory=lambda mode: UnsafeRunner())) as c:
        url = ready(c)
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        mission = terminal(c, url)
        assert len(mission["results"]) == 3
        assert all(secret not in str(mission) + caplog.text for secret in SENTINELS)


def test_sanitize_state_drops_unsafe_source_urls_and_keeps_state_valid():
    from pydantic import BaseModel

    from runai.app import sanitize_state

    class Candidate(BaseModel):
        id: str
        source_urls: list[str]

    class State(BaseModel):
        candidates: list[Candidate]

    state = State(candidates=[Candidate(id="lisbon-half-2027", source_urls=[
        "https://www.example.org/race", "http://localhost/private",
    ])])
    clean = sanitize_state(state)
    assert isinstance(clean, State)
    assert clean.candidates[0].source_urls == ["https://www.example.org/race"]


def test_sync_create_reports_failure_when_redaction_breaks_guide_state():
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    from runai.app import create_app

    class State(BaseModel):
        official_url: str

    class Guide:
        async def start(self, text):
            return State(official_url="http://localhost/private"), {"message": "x"}

    client = TestClient(create_app(guide=Guide()))
    response = client.post("/api/missions", json={"text": "semi de Lisbonne"})
    assert response.status_code == 201
    body = response.json()
    assert body["error"] and body["turns"] == []


def test_long_slug_chip_values_and_url_paths_survive_but_secrets_do_not():
    from runai.app import sanitize

    slug = "edp-meia-maratona-de-lisboa-2027-half-marathon"
    assert sanitize(slug, "value") == slug
    blog = ("https://berlin-laeuft.de/blog/die-anmeldung-ist-geoffnet-sichere-dir-"
            "deinen-startplatz-fur-den-s-25-berlin-2027/")
    assert sanitize(blog, "source_urls") == blog
    assert sanitize("4111 1111 1111 1111", "value") != "4111 1111 1111 1111"
    assert sanitize("runner@example.com", "value") != "runner@example.com"
    assert sanitize("https://example.org/r?ref=sk-abcdefghijklmnopqrstuvwxyz123456", "official_url") is None
    assert sanitize("https://example.org/sk-abcdefghijklmnopqrstuvwxyz123456/x", "official_url") is None


def test_url_paths_with_opaque_tokens_or_phones_are_dropped():
    from runai.app import sanitize

    assert sanitize("https://example.org/r/a8f3k2q9z7x1m4n6b5v0c2l8p3w9e1t7/x", "official_url") is None
    assert sanitize("https://example.org/contact-0612345678/", "official_url") is None
    assert sanitize("https://example.org/events/2027-04-18/s-25-berlin-2027", "official_url") == (
        "https://example.org/events/2027-04-18/s-25-berlin-2027")


def test_long_alphabetic_url_path_words_are_kept():
    from runai.app import sanitize

    url = "https://example.org/meiamaratonainternacionaldelisboaedicao/inscricoes"
    assert sanitize(url, "official_url") == url
