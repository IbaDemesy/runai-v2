import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from test_api_guided import StubGuide

from runai.app import create_app


class DelayedGuide(StubGuide):
    def __init__(self, fail=False):
        super().__init__()
        self.release = asyncio.Event()
        self.fail = fail
        self.starts = 0
        self.cancelled = False

    async def start(self, text):
        self.starts += 1
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if self.fail:
            raise ValueError("private provider diagnostic")
        return await super().start(text)


def settled(client, url):
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        mission = client.get(url).json()
        if mission["status"] != "discovering":
            return mission
    pytest.fail("Discovery did not settle")


def test_background_progress_and_conflict():
    guide = DelayedGuide()
    with TestClient(create_app(guide=guide, discovery_heartbeat_s=0.001)) as client:
        started = time.monotonic()
        response = client.post("/api/missions", json={"text": "a race", "background": True})
        assert time.monotonic() - started < 1
        assert response.status_code == 202
        assert response.json()["status"] == "discovering"
        url = f"/api/missions/{response.json()['id']}"
        assert client.post(url + "/messages", json={"text": "yes"}).status_code == 409
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409
        deadline = time.monotonic() + 1
        while len(client.get(url + "/events").json()) < 2:
            assert time.monotonic() < deadline
        client.portal.call(guide.release.set)
        mission = settled(client, url)
        events = mission["events"]
        assert events[0]["message"] == "Race search started"
        assert "elapsed" in events[1]["message"]
        assert events[-2]["message"] == "Race search finished"
        assert events[-1]["type"] == "turn"
        assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
        assert client.post(url + "/messages", json={"text": "yes"}).status_code == 200


@pytest.mark.parametrize("background", [False, True])
def test_failed_create_retry_uses_start(background):
    guide = DelayedGuide(fail=True)
    with TestClient(create_app(guide=guide)) as client:
        response = client.post("/api/missions", json={"text": "race", "background": True})
        url = f"/api/missions/{response.json()['id']}"
        client.portal.call(guide.release.set)
        mission = settled(client, url)
        assert mission["status"] == "guiding"
        assert mission["error"]
        assert mission["events"][-1]["type"] == "discovery_failed"
        assert "diagnostic" not in str(mission)
        guide.fail = False
        response = client.post(url + "/messages", json={"text": "retry", "background": background})
        assert response.status_code == (202 if background else 200)
        assert settled(client, url)["error"] is None
        assert guide.starts == 2


def test_shutdown_cancels_pending_discovery():
    guide = DelayedGuide()
    with TestClient(create_app(guide=guide)) as client:
        assert client.post("/api/missions", json={"text": "race", "background": True}).status_code == 202
    assert guide.cancelled


def test_background_missing_live_key(monkeypatch):
    monkeypatch.delenv("LINKUP_API_KEY", raising=False)
    with TestClient(create_app()) as client:
        assert client.post("/api/missions", json={
            "text": "race", "mode": "live", "background": True,
        }).status_code == 501
