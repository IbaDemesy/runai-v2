import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from runai.app import TARGET, create_app
from runai.models import Kind, StepResult
from runai.providers import FIXTURE, FakeVoice, LiveRunner, LiveVoice, ReplayRunner


def test_invalid_requests_and_live():
    with TestClient(create_app()) as client:
        assert client.get("/api/missions/unknown").status_code == 404
        assert client.post("/api/missions", json={"description": ""}).status_code == 422
        assert client.post("/api/missions", json={"description": "x", "mode": "live"}).status_code == 501
        m = client.post("/api/missions", json={"description": "x"}).json()
        framing = TARGET.model_dump(mode="json")
        framing["budget_eur"] = 0
        url = f"/api/missions/{m['id']}/reply"
        assert client.post(url, json={"framing": framing}).status_code == 422
        framing["budget_eur"] = 500
        assert client.post(url, json={"framing": framing}).status_code == 422


def test_payment_cannot_be_represented():
    with pytest.raises(ValidationError):
        StepResult(kind="hotel", status="paid", summary="x", synthetic=True)
    with pytest.raises(ValidationError):
        StepResult(kind="hotel", status="ready_for_payment", summary="x",
                   synthetic=True, payment_executed=True)


def test_voice_and_live_stubs():
    assert "SYNTHETIC" in asyncio.run(FakeVoice().transcribe(b"audio"))
    with pytest.raises(ValueError, match="Empty"):
        asyncio.run(FakeVoice().transcribe(b""))
    with pytest.raises(NotImplementedError, match="GLADIA_API_KEY"):
        asyncio.run(LiveVoice().transcribe(b"x"))
    with pytest.raises(NotImplementedError, match="HAI_API_KEY"):
        asyncio.run(LiveRunner().run(Kind.hotel, None))


def test_missing_replay(tmp_path):
    with pytest.raises(FileNotFoundError):
        ReplayRunner(tmp_path / "missing.json")


def test_provider_failure_is_visible(monkeypatch):
    async def fail(self, kind, plan):
        raise RuntimeError("test provider failure")

    monkeypatch.setattr("runai.providers.FakeRunner.run", fail)
    with TestClient(create_app()) as client:
        m = client.post("/api/missions", json={"description": "x"}).json()
        result = client.post(f"/api/missions/{m['id']}/confirm", json={"confirmed": True}).json()
        assert result["status"] == "failed"
        assert len(result["results"]) == 3
        assert all(r["error"] == "test provider failure" for r in result["results"])


def _write_trace(path, **overrides):
    import json

    trace = json.loads(FIXTURE.read_text())
    trace.update(overrides)
    path.write_text(json.dumps(trace))
    return path


def test_replay_trace_validation(tmp_path):
    assert set(ReplayRunner(_write_trace(tmp_path / "ok.json")).results) == set(Kind)
    with pytest.raises(ValueError, match="all three"):
        ReplayRunner(_write_trace(tmp_path / "empty.json", results=[]))
    with pytest.raises(ValueError, match="schema_version"):
        ReplayRunner(_write_trace(tmp_path / "v2.json", schema_version=2))
    with pytest.raises(ValueError, match="synthetic"):
        ReplayRunner(_write_trace(tmp_path / "live.json", provenance="live"))


def test_broken_replay_fails_visibly(monkeypatch):
    def broken():
        raise ValueError("bad trace")

    monkeypatch.setattr("runai.app.ReplayRunner", broken)
    with TestClient(create_app()) as client:
        m = client.post("/api/missions", json={"description": "x", "mode": "replay"}).json()
        result = client.post(f"/api/missions/{m['id']}/confirm", json={"confirmed": True})
        assert result.status_code == 200
        body = result.json()
        assert body["status"] == "failed"
        assert {r["kind"] for r in body["results"]} == set(Kind)
        assert all(r["status"] == "failed" and "bad trace" in r["error"] for r in body["results"])
        assert all(not r["payment_executed"] for r in body["results"])
