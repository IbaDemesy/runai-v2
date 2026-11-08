import asyncio
import threading
import time
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from runai.app import create_app
from runai.models import Kind, StepResult

TRIP = {
    "race": {
        "id": "synthetic-lisbon", "name": "SYNTHETIC Lisbon half marathon",
        "edition": "2027", "distance_km": 21.0975, "distance_label": "Semi-marathon",
        "race_date": "2027-03-14", "date_status": "confirmed", "city": "Lisbon",
        "country": "Portugal", "official_url": "https://www.maratonaclubedeportugal.com/",
        "registration_url": None, "source_urls": ["https://www.maratonaclubedeportugal.com/"],
        "retrieved_at": "2026-11-01T12:00:00Z", "synthetic": True,
    },
    "origin_city": "Paris", "travelers": 1, "nights": 2, "budget_eur": 600,
    "arrival_date": "2027-03-13", "departure_date": "2027-03-15",
}


class GuideState(BaseModel):
    trip: dict | None = None


class StubGuide:
    async def start(self, text):
        return GuideState(), {
            "message": "SYNTHETIC race proposed with date", "question": "This race?",
            "suggestions": [{"id": "race-1", "label": "Choose Lisbon", "value": "lisbon",
                             "kind": "race", "provenance": "synthetic"}],
            "candidates": [deepcopy(TRIP["race"])], "draft": {},
            "ready_to_confirm": False, "error": None,
        }

    async def step(self, state, answer):
        if answer not in ({"suggestion_id": "race-1"}, {"text": "yes"}):
            raise ValueError("Unknown suggestion")
        return GuideState(trip=deepcopy(TRIP)), {
            "message": "SYNTHETIC plan ready", "question": None, "suggestions": [],
            "candidates": [deepcopy(TRIP["race"])], "draft": deepcopy(TRIP),
            "ready_to_confirm": True, "error": None,
        }


def ready(client, mode="demo"):
    response = client.post("/api/missions", json={"text": "le semi de Lisbonne", "mode": mode})
    assert response.status_code == 201, response.text
    url = f"/api/missions/{response.json()['id']}"
    response = client.post(url + "/messages", json={"suggestion_id": "race-1"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ready"
    return url


def terminal(client, url):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        mission = client.get(url).json()
        if mission["status"] in {"completed", "partial", "failed"}:
            return mission
        time.sleep(0.005)
    pytest.fail("Mission did not reach terminal status")


def test_request_errors(monkeypatch):
    monkeypatch.delenv("HAI_API_KEY", raising=False)
    monkeypatch.delenv("LINKUP_API_KEY", raising=False)
    with TestClient(create_app(guide=StubGuide())) as client:
        for path in ("/api/missions/missing", "/api/missions/missing/events", "/api/frames/missing"):
            assert client.get(path).status_code == 404
        for body in ({}, {"text": ""}, {"text": "   "}, {"text": "x", "mode": "unknown"}):
            assert client.post("/api/missions", json=body).status_code == 422
        mission = client.post("/api/missions", json={"text": "un trail"}).json()
        url = f"/api/missions/{mission['id']}"
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409
        assert client.post(url + "/confirm", json={"confirmed": False}).status_code == 400
        assert client.post(url + "/confirm", json={"confirmed": "true"}).status_code == 422
        for answer in ({}, {"text": "  "}, {"suggestion_id": ""}, {"suggestion_id": "unknown"}):
            assert client.post(url + "/messages", json=answer).status_code == 422
        assert client.post(url + "/messages", json={"text": "yes"}).status_code == 200
        assert client.get(url + "/events?after=-1").status_code == 422
        live_url = ready(client, "live")
        response = client.post(live_url + "/confirm", json={"confirmed": True})
        assert response.status_code == 501
        assert "HAI_API_KEY" in response.json()["detail"]
        assert client.get(live_url).json()["status"] == "ready"
        assert client.get("/api/health").json() == {
            "mode": "demo", "live_ready": {"linkup": False, "h": False},
        }
        assert client.get("/").status_code == 200
        assert client.get("/static/index.html").status_code == 200


def test_default_missing_module_explicit_501(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("runai.app.importlib.import_module", missing)
    with TestClient(create_app()) as client:
        response = client.post("/api/missions", json={"text": "un marathon"})
        assert response.status_code == 501
        assert "unavailable" in response.json()["detail"]


def test_default_live_missing_key_explicit_501(monkeypatch):
    monkeypatch.delenv("LINKUP_API_KEY", raising=False)
    with TestClient(create_app()) as client:
        response = client.post("/api/missions", json={"text": "un trail", "mode": "live"})
        assert response.status_code == 501
        assert "LINKUP_API_KEY" in response.json()["detail"]


def test_live_missing_modules_at_confirm_is_501(monkeypatch):
    monkeypatch.setenv("HAI_API_KEY", "test-only-placeholder")

    def missing():
        raise ModuleNotFoundError("missing live provider")

    monkeypatch.setattr("runai.app.LiveRunner.ensure_available", missing)
    with TestClient(create_app(guide=StubGuide())) as client:
        url = ready(client, "live")
        response = client.post(url + "/confirm", json={"confirmed": True})
        assert response.status_code == 501
        assert "modules unavailable" in response.json()["detail"]
        assert client.get(url).json()["status"] == "ready"


def test_injected_live_events_and_frame_bytes(monkeypatch):
    monkeypatch.setenv("HAI_API_KEY", "test-only-placeholder")

    class FramesRunner:
        async def run(self, kind, trip, emit):
            await emit({"type": "live_view_available", "live_view_url": "https://example.org/",
                        "message": "Public view available"})
            await emit({"type": "live_view_available",
                        "live_view_url": "https://platform.hcompany.ai/agent-view/private-session"})
            await emit({"type": "live_frame", "image": b"png-bytes", "mime": "image/png"})
            await emit({"type": "live_frame", "image": b"unsafe", "mime": "text/html"})
            return StepResult(kind=kind, status="blocked", summary="Stop before consent",
                              handoff_url=TRIP["race"]["official_url"], synthetic=False)

    with TestClient(create_app(guide=StubGuide(), runner_factory=lambda mode: FramesRunner())) as c:
        url = ready(c, "live")
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        mission = terminal(c, url)
        assert mission["status"] == "failed"
        assert mission["synthetic"] is False
        frames = [event for event in mission["events"] if event["type"] == "live_frame"]
        assert len(frames) == 3
        assert all(not event["synthetic"] for event in mission["events"])
        for event in frames:
            response = c.get(f"/api/frames/{event['frame_id']}")
            assert response.content == b"png-bytes"
            assert response.headers["content-type"] == "image/png"
            assert "sandbox" in response.headers["content-security-policy"]
        assert sum(event["type"] == "live_view_available" for event in mission["events"]) == 3
        assert "private-session" not in str(mission)


def test_unknown_server_mode_is_clean_startup_error(monkeypatch):
    monkeypatch.setenv("RUNAI_MODE", "typo")
    with pytest.raises(ValueError, match="RUNAI_MODE must be demo, replay, or live"):
        create_app()


def test_background_returns_before_runners_and_all_three_overlap():
    release = threading.Event()
    all_started = threading.Event()
    started = set()

    class PausedRunner:
        async def run(self, kind, trip, emit):
            started.add(kind)
            if len(started) == 3:
                all_started.set()
            await emit({"type": "step_progress", "message": "SYNTHETIC waiting"})
            while not release.is_set():
                await asyncio.sleep(0.005)
            return StepResult(kind=kind, status="ready_for_payment", summary="SYNTHETIC done",
                              handoff_url=TRIP["race"]["official_url"], synthetic=True)

    with TestClient(create_app(guide=StubGuide(), runner_factory=lambda mode: PausedRunner())) as c:
        url = ready(c)
        try:
            response = c.post(url + "/confirm", json={"confirmed": True})
            assert response.status_code == 202
            assert response.json()["status"] == "running"
            assert response.json()["results"] == []
            assert all_started.wait(1), "Runners must overlap rather than run sequentially"
            assert c.get(url).json()["status"] == "running"
            assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 409
            assert c.post(url + "/messages", json={"text": "yes"}).status_code == 409
        finally:
            release.set()
        assert terminal(c, url)["status"] == "completed"


@pytest.mark.parametrize("statuses,expected", [
    (["ready_for_payment", "blocked", "failed"], "partial"),
    (["blocked", "failed", "failed"], "failed"),
])
def test_runner_outcomes_and_exceptions(statuses, expected):
    class MixedRunner:
        async def run(self, kind, trip, emit):
            status = statuses[list(Kind).index(kind)]
            if status == "failed":
                raise RuntimeError("not echoed to clients")
            return StepResult(kind=kind, status=status, summary="SYNTHETIC outcome",
                              handoff_url=TRIP["race"]["official_url"], synthetic=True)

    with TestClient(create_app(guide=StubGuide(), runner_factory=lambda mode: MixedRunner())) as c:
        url = ready(c)
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        result = terminal(c, url)
        assert result["status"] == expected
        assert len(result["results"]) == 3
        assert all(r["payment_executed"] is False for r in result["results"])
        assert all("not echoed" not in (r["error"] or "") for r in result["results"])


def test_replay_load_failure_is_three_visible_failures(tmp_path):
    with TestClient(create_app(guide=StubGuide(), replay_path=tmp_path / "missing.json")) as c:
        url = ready(c, "replay")
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        mission = terminal(c, url)
        assert mission["status"] == "failed"
        assert len(mission["results"]) == 3
        assert all(r["status"] == "failed" for r in mission["results"])
        assert sum(e["type"] == "step_finished" for e in mission["events"]) == 3


def test_guide_trip_payload_is_preferred_and_missions_are_isolated():
    class PayloadGuide(StubGuide):
        def trip_payload(self, state):
            return {**state.trip, "origin_city": "Lyon"}

    with TestClient(create_app(guide=PayloadGuide())) as c:
        first = c.post("/api/missions", json={"text": "a race"}).json()
        second = c.post("/api/missions", json={"text": "another race"}).json()
        first_url, second_url = (f"/api/missions/{m['id']}" for m in (first, second))
        result = c.post(first_url + "/messages", json={"text": "yes"}).json()
        assert result["trip"]["origin_city"] == "Lyon"
        assert c.get(second_url).json()["status"] == "guiding"
        assert len(c.get(second_url).json()["turns"]) == 1


def test_default_live_wiring_translates_hints_and_timeout(monkeypatch):
    monkeypatch.setenv("LINKUP_API_KEY", "test-only-placeholder")
    calls = []

    async def discover(query, hints, *, timeout_s):
        calls.append((query, hints, timeout_s))
        return []

    class WiredGuide(StubGuide):
        def __init__(self, discovery):
            self.discovery = discovery

        async def start(self, text):
            await self.discovery(text, {"months": [12, 1, 2], "named": "Lisbon", "city": "Lisbon"})
            return await super().start(text)

    modules = {
        "runai.guide": SimpleNamespace(GuideEngine=WiredGuide),
        "runai.discovery.linkup": SimpleNamespace(discover=discover),
    }
    monkeypatch.setattr("runai.app.importlib.import_module", modules.__getitem__)
    with TestClient(create_app()) as c:
        response = c.post("/api/missions", json={"text": "a winter race", "mode": "live"})
        assert response.status_code == 201
        assert response.json()["synthetic"] is False
    assert calls == [("a winter race", {
        "month_from": 12, "month_to": 2, "race_name": "Lisbon", "city": "Lisbon",
    }, 120)]


def test_frame_store_is_bounded_across_finished_missions(monkeypatch):
    monkeypatch.setattr("runai.app.MAX_FRAMES", 4)
    monkeypatch.setattr("runai.app.MAX_FRAME_BYTES", 10)

    class BurstRunner:
        async def run(self, kind, trip, emit):
            for _ in range(5):
                await emit({"type": "live_frame", "image": b"1234", "mime": "image/png"})
            return StepResult(kind=kind, status="blocked", summary="SYNTHETIC stopped",
                              synthetic=True)

    with TestClient(create_app(guide=StubGuide(), runner_factory=lambda mode: BurstRunner())) as c:
        previous = []
        for _ in range(2):
            url = ready(c)
            assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
            mission = terminal(c, url)
            ids = [e["frame_id"] for e in mission["events"] if e["type"] == "live_frame"]
            assert len(ids) == 15
            assert all(c.get(f"/api/frames/{fid}").status_code == 404 for fid in previous)
            available = [fid for fid in ids if c.get(f"/api/frames/{fid}").status_code == 200]
            assert available == ids[-2:]
            previous = available


def test_default_live_guide_and_builder_contracts_without_network(monkeypatch):
    import importlib

    pytest.importorskip("runai.guide")
    original = importlib.import_module
    calls = []

    async def discover(query, hints, *, timeout_s):
        assert timeout_s == 120
        race = deepcopy(TRIP["race"])
        race["synthetic"] = False
        return [race]

    class HClient:
        async def run(self, task, on_event):
            calls.append(task["kind"])
            await on_event({"type": "step_progress", "message": "Injected offline client"})
            return {"status": "blocked", "summary": "Injected offline client stopped",
                    "handoff_url": task["fallback_url"]}

    def modules(name):
        if name == "runai.discovery.linkup":
            return SimpleNamespace(discover=discover)
        if name == "runai.agents.hclient":
            return SimpleNamespace(HAgentRunner=HClient)
        return original(name)

    monkeypatch.setattr("runai.app.importlib.import_module", modules)
    monkeypatch.setenv("LINKUP_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("HAI_API_KEY", "test-only-placeholder")
    with TestClient(create_app()) as client:
        response = client.post("/api/missions", json={"text": "le semi de Lisbonne", "mode": "live"})
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
        assert mission["status"] == "ready"
        assert mission["trip"]["race"]["distance_label"] == "Semi-marathon"
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        result = terminal(client, url)
        assert set(calls) == {kind.value for kind in Kind}
        assert all(step["status"] == "blocked" for step in result["results"])
        assert all(not step["payment_executed"] for step in result["results"])
