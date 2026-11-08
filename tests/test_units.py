import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_api_guided import TRIP

from runai.models import Kind, StepResult
from runai.providers import FIXTURE, FakeVoice, LiveRunner, LiveVoice, ReplayRunner


def test_payment_and_invalid_handoff_cannot_be_represented():
    for extra in ({"status": "paid"}, {"payment_executed": True}, {"handoff_url": None}):
        fields = {"kind": "hotel", "status": "ready_for_payment", "summary": "x",
                  "synthetic": True, "handoff_url": "https://all.accor.com/"}
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
    fallback = "https://all.accor.com/"

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
