import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_api_guided import TRIP

from runai.app import execution_trip, sanitize_state
from runai.models import Kind, StepResult
from runai.providers import FIXTURE, FakeVoice, LiveRunner, LiveVoice, ReplayRunner


def test_p13_survives_provider_and_api_serialization(monkeypatch):
    class Client:
        async def run(self, task, on_event):
            return {"status": "blocked", "summary": "Booking step reached — verify on the site",
                    "reason_code": "checkpoint_unverified", "checkpoint_reached": True,
                    "handoff_url": "https://www.ihg.com/reservation/select-enhance-stay"}

    monkeypatch.setattr("runai.providers.importlib.import_module", lambda name: SimpleNamespace(
        HAgentRunner=Client, build_task=lambda trip: {},
    ))

    async def emit(event):
        pass

    result = asyncio.run(LiveRunner().run(Kind.hotel, TRIP, emit))
    payload = sanitize_state(result).model_dump(mode="json")
    assert payload["checkpoint_reached"] is True
    assert payload["reason_code"] == "checkpoint_unverified"
    assert payload["status"] == "blocked"
    assert payload["handoff_url"] == "https://www.ihg.com/reservation/select-enhance-stay"


@pytest.mark.parametrize("value,expected", [
    (None, None), ({}, {}), ([], []),
    ({"race": {"preparation": None}}, {"race": {}}),
    ({"nested": [{"preparation": {"invalid": "display only"}, "city": "Paris"}]},
     {"nested": [{"city": "Paris"}]}),
])
def test_execution_trip_strips_preparation_recursively(value, expected):
    assert execution_trip(value) == expected


@pytest.mark.parametrize("kind", [Kind.hotel, Kind.transport])
def test_builder_failure_has_no_unobserved_handoff(monkeypatch, kind):
    def build(trip):
        raise ValueError("private details")

    monkeypatch.setattr("runai.providers.importlib.import_module",
                        lambda name: SimpleNamespace(build_task=build))

    async def emit(event):
        pytest.fail("Builder failure must not emit H events")

    result = asyncio.run(LiveRunner().run(kind, TRIP, emit))
    assert result.status == "blocked"
    assert result.handoff_url is None


def test_blocked_preserves_observed_handoff(monkeypatch):
    class Client:
        async def run(self, task, on_event):
            return {"status": "blocked", "summary": "Stopped at consent",
                    "handoff_url": "https://example.org/observed"}

    monkeypatch.setattr("runai.providers.importlib.import_module", lambda name: SimpleNamespace(
        HAgentRunner=Client, build_task=lambda trip: {"fallback_url": "https://example.org/fallback"},
    ))

    async def emit(event):
        pass

    result = asyncio.run(LiveRunner().run(Kind.hotel, TRIP, emit))
    assert str(result.handoff_url) == "https://example.org/observed"
    assert result.status == "blocked"


def test_payment_and_invalid_handoff_cannot_be_represented():
    for extra in ({"status": "paid"}, {"payment_executed": True}, {"handoff_url": None}):
        fields = {"kind": "hotel", "status": "ready_for_payment", "summary": "x",
                  "synthetic": True, "handoff_url": "https://example.org/hotel"}
        fields.update(extra)
        with pytest.raises(ValidationError):
            StepResult(**fields)


def test_voice_stubs():
    assert "SYNTHETIC" in asyncio.run(FakeVoice().transcribe(b"audio"))
    with pytest.raises(ValueError, match="Empty"):
        asyncio.run(FakeVoice().transcribe(b""))
    with pytest.raises(NotImplementedError, match="GLADIA_API_KEY"):
        asyncio.run(LiveVoice().transcribe(b"x"))


@pytest.mark.parametrize("change", ["version", "provenance", "missing", "unsafe", "unordered"])
def test_replay_rejects_invalid_schema(tmp_path, change):
    trace = json.loads(FIXTURE.read_text())
    if change == "version":
        trace["schema_version"] = 1
    elif change == "provenance":
        trace["provenance"] = "live"
    elif change == "missing":
        del trace["agents"]["hotel"]
    elif change == "unsafe":
        trace["agents"]["hotel"]["result"]["payment_executed"] = True
    else:
        trace["agents"]["hotel"]["steps"].reverse()
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(trace))
    with pytest.raises(ValueError):
        ReplayRunner(path)


def test_missing_replay(tmp_path):
    with pytest.raises(FileNotFoundError):
        ReplayRunner(tmp_path / "missing.json")


@pytest.mark.parametrize("outcome", ["ready_for_payment", "blocked", "exception", "no_handoff"])
def test_live_runner_maps_results_and_events(monkeypatch, outcome):
    events = []
    fallback = "https://example.org/hotel"

    class Client:
        async def run(self, task, on_event):
            assert task == {"fallback_url": fallback}
            await on_event({"type": "step_progress", "message": "Public page opened"})
            await on_event({"type": "live_view_available", "live_view_url": "https://example.org/"})
            await on_event({"type": "live_frame", "image": b"image", "mime": "image/png"})
            await on_event({"type": "unknown"})
            if outcome == "exception":
                raise RuntimeError("private diagnostic must not appear")
            return {"status": "ready_for_payment" if outcome == "no_handoff" else outcome,
                    "summary": "Stopped before payment", "handoff_url": (
                        None if outcome == "no_handoff" else fallback
                    ), "payment_executed": False}

    def import_module(name):
        if name == "runai.agents.hclient":
            return SimpleNamespace(HAgentRunner=Client)
        return SimpleNamespace(build_task=lambda trip: {"fallback_url": fallback})

    async def emit(event):
        events.append(event)

    monkeypatch.setattr("runai.providers.importlib.import_module", import_module)
    result = asyncio.run(LiveRunner().run(Kind.hotel, TRIP, emit))
    assert result.status == ("failed" if outcome in {"exception", "no_handoff"} else outcome)
    assert result.synthetic is False
    assert result.payment_executed is False
    assert str(result.handoff_url) == fallback
    assert "private" not in (result.error or "")
    assert [event["type"] for event in events] == [
        "step_progress", "live_view_available", "live_frame",
    ]


def test_builder_value_error_is_blocked_and_does_not_start_h(monkeypatch):
    def build(trip):
        raise ValueError("invalid trip")

    def import_module(name):
        assert name == "runai.agents.registration"
        return SimpleNamespace(build_task=build)

    async def emit(event):
        pytest.fail("No H events expected")

    monkeypatch.setattr("runai.providers.importlib.import_module", import_module)
    result = asyncio.run(LiveRunner().run(Kind.registration, TRIP, emit))
    assert result.status == "blocked"
    assert str(result.handoff_url) == TRIP["race"]["official_url"]
    assert result.payment_executed is False


def test_invalid_registration_url_cannot_escape_failure_boundary(monkeypatch):
    def build(trip):
        raise ValueError("Invalid registration URL")

    monkeypatch.setattr("runai.providers.importlib.import_module", lambda name: SimpleNamespace(
        build_task=build,
    ))

    async def emit(event):
        pytest.fail("No H events expected")

    result = asyncio.run(LiveRunner().run(Kind.registration, {
        "race": {"official_url": "not-a-url", "registration_url": "also-invalid"},
    }, emit))
    assert result.status == "blocked"
    assert result.handoff_url is None


@pytest.mark.parametrize("unsafe", [
    "https://platform.hcompany.ai/agent-view/private-session",
    "https://agp.eu.hcompany.ai/api/v2/sessions/private-session",
    "https://example.org/checkout?token=private",
    "https://name:password@example.org/checkout",
    "https://example.org/checkout#private",
    "http://127.0.0.1/private",
])
def test_result_private_urls_are_suppressed(unsafe):
    result = StepResult(kind="hotel", status="blocked", summary="Stopped", synthetic=False,
                        handoff_url=unsafe, start_url=unsafe, final_url=unsafe, live_view_url=unsafe)
    assert all(getattr(result, key) is None for key in (
        "handoff_url", "start_url", "final_url", "live_view_url",
    ))
    with pytest.raises(ValidationError, match="requires a handoff_url"):
        StepResult(kind="hotel", status="ready_for_payment", summary="Stopped", synthetic=False,
                   handoff_url=unsafe)


def test_documented_h_share_url_is_public():
    result = StepResult(kind="hotel", status="blocked", summary="Stopped", synthetic=False,
                        live_view_url="https://agp.eu.hcompany.ai/share/api/v1/trajectories/test")
    assert str(result.live_view_url).startswith("https://agp.eu.hcompany.ai/share/")


def test_replay_registration_handoff_follows_selected_race():
    runner = ReplayRunner()
    recorded_url = str(runner.results[Kind.registration].handoff_url)
    trip = {**TRIP, "race": {**TRIP["race"], "official_url": "https://example.org/another-race"}}

    async def emit(event):
        assert event["recorded_at"]

    result = asyncio.run(runner.run(Kind.registration, trip, emit))
    assert str(result.handoff_url) == "https://example.org/another-race"
    assert "current selected race" in result.summary
    assert result.synthetic and result.payment_executed is False
    assert str(runner.results[Kind.registration].handoff_url) == recorded_url


@pytest.mark.parametrize("message,reason", [
    ("invalid trip private sentinel", "no_site_coverage"),
    ("Policy denied private sentinel", "policy_denied"),
    ("Prohibited private sentinel", "policy_denied"),
])
def test_r3_builder_friendly_reason(monkeypatch, message, reason):
    def build(trip):
        raise ValueError(message)

    monkeypatch.setattr("runai.providers.importlib.import_module", lambda name: SimpleNamespace(
        build_task=build,
    ))

    async def emit(event):
        pytest.fail("No session may start")

    result = asyncio.run(LiveRunner().run(Kind.registration, TRIP, emit))
    assert result.reason_code == reason
    assert result.status == "blocked"
    assert "private sentinel" not in result.model_dump_json()
    assert "official site" in result.summary


@pytest.mark.parametrize("code", ["captcha", None, "unknown", {}, []])
def test_r3_unknown_reason_is_dropped(code):
    result = StepResult(kind="hotel", status="blocked", summary="Stopped",
                        synthetic=False, reason_code=code)
    assert result.reason_code == ("captcha" if code == "captcha" else None)


@pytest.mark.parametrize("code,expected", [("captcha", "captcha"), ("unknown", None)])
def test_r3_live_runner_preserves_only_known_reason(monkeypatch, code, expected):
    class Client:
        async def run(self, task, on_event):
            return {"status": "blocked", "summary": "Stopped", "reason_code": code}

    monkeypatch.setattr("runai.providers.importlib.import_module", lambda name: SimpleNamespace(
        HAgentRunner=Client, build_task=lambda trip: {},
    ))

    async def emit(event):
        pass

    result = asyncio.run(LiveRunner().run(Kind.hotel, TRIP, emit))
    assert result.reason_code == expected
