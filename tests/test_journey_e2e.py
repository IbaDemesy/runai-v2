import pytest
from fastapi.testclient import TestClient
from test_api_guided import StubGuide, ready, terminal

from runai.app import create_app


@pytest.mark.parametrize("mode", ["demo", "replay"])
def test_full_journey(mode):
    with TestClient(create_app(guide=StubGuide())) as client:
        url = ready(client, mode)
        mission = client.get(url).json()
        assert mission["results"] == []
        assert len(mission["turns"]) == 2
        assert mission["trip"]["race"]["race_date"]
        response = client.post(url + "/confirm", json={"confirmed": True})
        assert response.status_code == 202
        result = terminal(client, url)
        assert result["status"] == "completed"
        assert result["synthetic"] is True
        assert {s["kind"] for s in result["results"]} == {"registration", "hotel", "transport"}
        for step in result["results"]:
            assert step["status"] == "ready_for_payment"
            assert step["handoff_url"].startswith("https://")
            assert step["payment_executed"] is False
            assert step["synthetic"] is True
        events = result["events"]
        assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
        assert all(e["synthetic"] and e["observed_at"] for e in events)
        for kind in ("registration", "hotel", "transport"):
            types = {e["type"] for e in events if e["kind"] == kind}
            assert {"step_started", "step_progress", "live_frame", "step_finished"} <= types
        for event in events:
            if event["type"] == "live_frame":
                frame = client.get(f"/api/frames/{event['frame_id']}")
                assert frame.status_code == 200
                assert frame.headers["content-type"].startswith("image/svg+xml")
                assert b"SYNTHETIC" in frame.content
                if mode == "replay":
                    assert event["recorded_at"].startswith("2026-11-01")
        after = events[5]["sequence"]
        assert client.get(url + f"/events?after={after}").json() == events[6:]
        assert client.get(url + f"/events?after={events[-1]['sequence']}").json() == []
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409


def test_default_wiring_when_guide_is_installed():
    pytest.importorskip("runai.guide")
    with TestClient(create_app()) as client:
        response = client.post("/api/missions", json={"text": "un marathon au printemps en Italie"})
        assert response.status_code == 201, response.text
        mission = response.json()
        url = f"/api/missions/{mission['id']}"
        for _ in range(12):
            turn = mission["turns"][-1]
            if turn["ready_to_confirm"]:
                break
            assert turn["suggestions"], turn
            response = client.post(url + "/messages", json={
                "suggestion_id": turn["suggestions"][0]["id"],
            })
            assert response.status_code == 200, response.text
            mission = response.json()
        assert mission["turns"][-1]["ready_to_confirm"]
        assert mission["trip"]["race"]["race_date"]
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        assert terminal(client, url)["status"] == "completed"
