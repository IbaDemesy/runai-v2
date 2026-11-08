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
        "official_url": None, "source_urls": [None],
    }
    safe = "https://example.org/race/2027-04-04?budget=800&distance=42.195"
    assert sanitize(safe, "official_url") == safe


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
