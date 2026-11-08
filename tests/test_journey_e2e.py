import pytest
from fastapi.testclient import TestClient

from runai.app import create_app


@pytest.mark.parametrize("mode", ["demo", "replay"])
def test_full_journey(mode):
    with TestClient(create_app()) as client:
        response = client.post("/api/missions", json={"description": "Ma course", "mode": mode})
        assert response.status_code == 201
        mission = response.json()
        url = f"/api/missions/{mission['id']}"
        assert mission["results"] == []
        assert not mission["confirmed"]
        assert client.post(url + "/reply", json={"framing": mission["plan"]["framing"]}).status_code == 200
        assert client.post(url + "/confirm", json={"confirmed": False}).status_code == 400
        response = client.post(url + "/confirm", json={"confirmed": True})
        assert response.status_code == 200
        result = client.get(url).json()
        assert result["status"] == "completed"
        assert result["synthetic"] is True
        assert {s["kind"] for s in result["results"]} == {"registration", "hotel", "transport"}
        for step in result["results"]:
            assert step["status"] == "ready_for_payment"
            assert step["handoff_url"].startswith("https://")
            assert step["payment_executed"] is False
            assert step["synthetic"] is True
        assert [e["sequence"] for e in result["events"]] == list(range(1, 8))
        assert all(e["synthetic"] for e in result["events"])
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409
        assert client.post(url + "/reply", json={"framing": mission["plan"]["framing"]}).status_code == 409
