import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, date, datetime
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


def test_race_today_cannot_be_confirmed():
    def forbidden(mode):
        pytest.fail("Today's race must not launch runners")

    with TestClient(create_app(guide=StubGuide(), runner_factory=forbidden,
                              today=lambda: date.fromisoformat(TRIP["race"]["race_date"]))) as client:
        url = ready(client)
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409


@pytest.mark.parametrize("change,mode", [
    ({"race": {**TRIP["race"], "race_date": "2020-01-01"}}, "demo"),
    ({"arrival_date": None}, "demo"),
    ({"nights": 7}, "demo"),
    ({}, "live"),
    ({"race": {**TRIP["race"], "synthetic": False, "date_status": "unverified"}}, "live"),
    ({"race": {**TRIP["race"], "synthetic": False}}, "demo"),
    ({"travelers": 0}, "demo"),
    ({"budget_eur": 0}, "demo"),
    ({"origin_city": ""}, "demo"),
])
def test_buggy_ready_plan_cannot_launch(change, mode):
    class BuggyGuide(StubGuide):
        async def step(self, state, answer):
            state, turn = await super().step(state, answer)
            state.trip.update(change)
            return state, turn

    def forbidden(mode):
        pytest.fail("Invalid plan launched a runner")

    with TestClient(create_app(guide=BuggyGuide(), runner_factory=forbidden,
                              today=lambda: date(2026, 1, 1))) as client:
        url = ready(client, mode)
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409


def test_stale_latest_turn_cannot_confirm():
    class ChangedGuide(StubGuide):
        async def step(self, state, answer):
            state, turn = await super().step(state, answer)
            if answer == {"text": "yes"}:
                turn["ready_to_confirm"] = False
            return state, turn

    with TestClient(create_app(guide=ChangedGuide())) as client:
        url = ready(client)
        assert client.post(url + "/messages", json={"text": "yes"}).status_code == 200
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 409


def test_duplicate_confirms_launch_three_overlapping_runners_once():
    barrier = asyncio.Barrier(3)
    calls = []

    class BarrierRunner:
        async def run(self, kind, trip, emit):
            calls.append(kind)
            await asyncio.wait_for(barrier.wait(), timeout=1)
            return StepResult(kind=kind, status="blocked", summary="SYNTHETIC stopped",
                              synthetic=True)

    with TestClient(create_app(guide=StubGuide(), runner_factory=lambda mode: BarrierRunner())) as c:
        url = ready(c)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: c.post(url + "/confirm", json={"confirmed": True}),
                                    range(2)))
        assert sorted(result.status_code for result in results) == [202, 409]
        mission = terminal(c, url)
        assert len(calls) == 3
        assert all(result["status"] == "blocked" for result in mission["results"])


class GuideState(BaseModel):
    trip: dict | None = None


class StubGuide:
    def __init__(self, live=False):
        self.live = live

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
        trip = deepcopy(TRIP)
        if self.live:
            trip["race"].update(synthetic=False, date_status="official")
        return GuideState(trip=trip), {
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
    with TestClient(create_app(guide=StubGuide(live=True))) as client:
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
    with TestClient(create_app(guide=StubGuide(live=True))) as client:
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

    with TestClient(create_app(guide=StubGuide(live=True), runner_factory=lambda mode: FramesRunner())) as c:
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


@pytest.mark.parametrize("timestamp,valid", [
    ("2026-01-01T12:00:00Z", True), ("2026-01-01T14:00:00+02:00", True),
    ("2099-01-01T12:00:00Z", False), ("malformed", False),
    ("2026-01-01T12:00:00", False), (None, False), (1234, False),
])
def test_live_frame_observation_timestamp_survives_api_or_is_omitted(monkeypatch, timestamp, valid):
    monkeypatch.setenv("HAI_API_KEY", "test-only-placeholder")

    class Runner:
        async def run(self, kind, trip, emit):
            await emit({"type": "live_frame", "image": b"offline-frame", "mime": "image/png",
                        "observed_at": timestamp})
            return StepResult(kind=kind, status="blocked", summary="Stopped safely",
                              synthetic=False)

    with TestClient(create_app(guide=StubGuide(live=True), runner_factory=lambda mode: Runner())) as c:
        url = ready(c, "live")
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        mission = terminal(c, url)
        for events in (mission["events"], c.get(url + "/events").json()):
            frames = [event for event in events if event["type"] == "live_frame"]
            assert len(frames) == 3
            for event in frames:
                if valid:
                    assert datetime.fromisoformat(event["observed_at"]) == datetime(
                        2026, 1, 1, 12, tzinfo=UTC,
                    )
                else:
                    assert "observed_at" not in event
        assert all(step["status"] == "blocked" for step in mission["results"])


def test_checkpoint_unverified_fields_survive_live_api(monkeypatch):
    monkeypatch.setenv("HAI_API_KEY", "test-only-placeholder")

    class Runner:
        async def run(self, kind, trip, emit):
            return {"kind": kind, "synthetic": False, "status": "blocked",
                    "reason_code": "checkpoint_unverified", "checkpoint_reached": True,
                    "summary": "Booking step reached — verify on the site",
                    "handoff_url": "https://www.ihg.com/reservation/select-enhance-stay"}

    with TestClient(create_app(guide=StubGuide(live=True), runner_factory=lambda mode: Runner())) as c:
        url = ready(c, "live")
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        mission = terminal(c, url)
        assert len(mission["results"]) == 3
        for result in mission["results"]:
            assert result["status"] == "blocked"
            assert result["reason_code"] == "checkpoint_unverified"
            assert result["checkpoint_reached"] is True
            assert result["handoff_url"] == "https://www.ihg.com/reservation/select-enhance-stay"


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
        race["date_status"] = "official"
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
        if name in builders:
            return builders[name]
        return original(name)

    def builder(kind):
        def build_task(trip):
            return {"kind": kind, "start_url": "https://example.org/start",
                    "fallback_url": "https://example.org/", "instructions": "offline",
                    "max_steps": 1}
        return SimpleNamespace(build_task=build_task)

    builders = {f"runai.agents.{kind.value}": builder(kind.value) for kind in Kind}

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


def test_live_builder_rejection_blocks_without_h_calls(monkeypatch):
    import importlib

    from runai.providers import LiveRunner

    original = importlib.import_module
    calls = []

    class HClient:
        async def run(self, task, on_event):
            calls.append(task["kind"])
            return {"status": "ready_for_payment", "summary": "must not run"}

    def reject(trip):
        raise ValueError("no reviewed site policy")

    def modules(name):
        if name == "runai.agents.hclient":
            return SimpleNamespace(HAgentRunner=HClient)
        if name.startswith("runai.agents."):
            return SimpleNamespace(build_task=reject)
        return original(name)

    monkeypatch.setattr("runai.providers.importlib.import_module", modules)

    async def emit(event):
        pass

    for kind in Kind:
        result = asyncio.run(LiveRunner().run(kind, deepcopy(TRIP), emit))
        assert result.status == "blocked"
        assert result.payment_executed is False
    assert calls == []


@pytest.mark.parametrize("language,expected", [("en", "en"), ("fr", "fr"), ("xx", "en"), (None, "en")])
def test_r3_latest_guide_language(language, expected):
    class LanguageGuide(StubGuide):
        async def start(self, text):
            state, turn = await super().start(text)
            turn["language"] = "en"
            return state, turn

        async def step(self, state, answer):
            state, turn = await super().step(state, answer)
            turn["language"] = language
            return state, turn

    with TestClient(create_app(guide=LanguageGuide())) as client:
        url = ready(client)
        assert client.get(url).json()["language"] == expected


def test_r3_reason_in_api_json():
    class BlockedRunner:
        async def run(self, kind, trip, emit):
            return StepResult(kind=kind, status="blocked", summary="No inventory",
                              reason_code="no_inventory", synthetic=True)

    with TestClient(create_app(guide=StubGuide(), runner_factory=lambda mode: BlockedRunner())) as c:
        url = ready(c)
        assert c.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        mission = terminal(c, url)
        assert all(result["reason_code"] == "no_inventory" for result in mission["results"])


@pytest.mark.parametrize("source", ["state", "trip_payload", "draft"])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_preparation_is_display_only_in_turns_not_execution(source, language):
    preparation = {"registration": "covered", "hotel": True, "transport": None,
                   "origin_city": "Paris"}
    trip = deepcopy(TRIP)
    trip["race"]["preparation"] = deepcopy(preparation)
    trip["preparation"] = deepcopy(preparation)
    trip["nested"] = [{"preparation": deepcopy(preparation), "keep": "public context"}]
    original = deepcopy(trip)
    captured = []

    class PreparationGuide:
        async def start(self, text):
            state = {"trip": trip} if source == "state" else {}
            turn = {"message": "Plan ready", "candidates": [trip["race"]], "draft": trip,
                    "ready_to_confirm": True, "language": language}
            return state, turn

        async def step(self, state, answer):
            return await self.start("")

    guide = PreparationGuide()
    if source == "trip_payload":
        guide.trip_payload = lambda state: trip

    class CaptureRunner:
        async def run(self, kind, trip, emit):
            captured.append(deepcopy(trip))
            return StepResult(kind=kind, status="blocked", summary="Synthetic stop",
                              synthetic=True)

    with TestClient(create_app(guide=guide, runner_factory=lambda mode: CaptureRunner())) as client:
        response = client.post("/api/missions", json={"text": "race"})
        assert response.status_code == 201, response.text
        created = response.json()
        url = f"/api/missions/{created['id']}"
        for mission in (created, client.get(url).json(),
                        client.post(url + "/messages", json={"text": "yes"}).json()):
            assert mission["turns"][-1]["candidates"][0]["preparation"] == preparation
            assert mission["turns"][-1]["draft"]["race"]["preparation"] == preparation
            assert mission["language"] == language
            assert "preparation" not in str(mission["trip"])
            assert mission["trip"]["nested"] == [{"keep": "public context"}]
        assert client.post(url + "/confirm", json={"confirmed": True}).status_code == 202
        assert len(terminal(client, url)["results"]) == 3
    assert len(captured) == 3
    assert all("preparation" not in str(item) for item in captured)
    assert trip == original
