import asyncio
import importlib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Protocol

from pydantic import HttpUrl, TypeAdapter

from runai.models import Kind, StepResult, public_url

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/synthetic-journey.json"
Emit = Callable[[dict], Awaitable[None]]


class AgentRunner(Protocol):
    async def run(self, kind: Kind, trip: dict, emit: Emit) -> StepResult: ...


class VoiceProvider(Protocol):
    async def transcribe(self, audio: bytes) -> str: ...


class FakeVoice:
    async def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise ValueError("Empty audio")
        return "SYNTHETIC: un marathon au printemps en Italie"


class LiveVoice:
    async def transcribe(self, audio: bytes) -> str:
        raise NotImplementedError("Live Gladia voice not implemented; requires GLADIA_API_KEY")


def _valid_url(value):
    try:
        return public_url(str(TypeAdapter(HttpUrl).validate_python(value)))
    except ValueError:
        return None


def _fallback(kind, trip):
    if kind == Kind.registration:
        race = trip.get("race", {})
        return _valid_url(race.get("registration_url")) or _valid_url(race.get("official_url"))
    return None


class FakeRunner:
    async def run(self, kind: Kind, trip: dict, emit: Emit) -> StepResult:
        for index, message in enumerate(("Opening official site", "Reviewing options", "Human handoff")):
            await emit({"type": "step_progress", "message": f"SYNTHETIC: {message}"})
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">'
                '<rect width="960" height="540" fill="#101819"/>'
                '<rect x="48" y="48" width="864" height="8" rx="4" fill="#fc4c02"/>'
                '<g fill="#fff" font-family="sans-serif">'
                '<text x="48" y="124" font-size="28">RUNAI / SYNTHETIC</text>'
                f'<text x="48" y="220" font-size="40">{escape(kind.value.upper())}</text>'
                f'<text x="48" y="290" font-size="28">{escape(message)}</text>'
                f'<text x="48" y="390" font-size="22">Frame {index + 1}/3 — simulation only</text>'
                '<text x="48" y="460" font-size="20">No booking, submission or payment</text>'
                '</g></svg>'
            )
            await emit({
                "type": "live_frame", "message": f"SYNTHETIC: {message}",
                "image": svg.encode(), "mime": "image/svg+xml",
            })
            await asyncio.sleep(0)
        return StepResult(
            kind=kind, status="ready_for_payment",
            summary="SYNTHETIC: simulated handoff to homepage; no prepared booking or purchase.",
            handoff_url=(_fallback(kind, trip) if kind == Kind.registration else
                         f"https://example.com/runai-synthetic/{kind.value}"), synthetic=True,
        )


class ReplayRunner:
    def __init__(self, path: Path = FIXTURE):
        trace = json.loads(Path(path).read_text())
        if trace.get("schema_version") != 2 or trace.get("provenance") != "synthetic":
            raise ValueError("Replay requires schema_version 2 and synthetic provenance")
        agents = trace.get("agents", {})
        if set(agents) != set(Kind):
            raise ValueError("Replay must contain all three kinds")
        self.agents = agents
        self.results = {}
        for kind in Kind:
            result = StepResult.model_validate(agents[kind]["result"])
            if not result.synthetic or result.kind != kind:
                raise ValueError("Invalid synthetic replay result")
            previous = None
            steps = agents[kind]["steps"]
            if not steps:
                raise ValueError("Replay needs recorded steps")
            for step in steps:
                recorded = datetime.fromisoformat(step["recorded_at"])
                if recorded.tzinfo is None or (previous is not None and recorded < previous):
                    raise ValueError("Replay timestamps must be ordered and timezone-aware")
                previous = recorded
                if not isinstance(step.get("message"), str):
                    raise TypeError("Replay steps need a message")
                if "frame" in step and (
                    not isinstance(step["frame"], str) or "SYNTHETIC" not in step["frame"]
                ):
                    raise ValueError("Replay frames must be labelled SYNTHETIC")
            self.results[kind] = result

    async def run(self, kind: Kind, trip: dict, emit: Emit) -> StepResult:
        for step in self.agents[kind]["steps"]:
            await emit({
                "type": "step_progress", "message": f"SYNTHETIC replay: {step['message']}",
                "recorded_at": step["recorded_at"],
            })
            if step.get("frame"):
                await emit({
                    "type": "live_frame", "message": "SYNTHETIC recorded frame",
                    "recorded_at": step["recorded_at"], "image": step["frame"].encode(),
                    "mime": "image/svg+xml",
                })
            await asyncio.sleep(0)
        result = self.results[kind].model_dump(mode="json")
        if kind == Kind.registration:
            result["handoff_url"] = _fallback(kind, trip)
            result["summary"] += " Manual registration link follows the current selected race."
        return StepResult.model_validate(result)


class LiveRunner:
    @staticmethod
    def ensure_available():
        _ = importlib.import_module("runai.agents.hclient").HAgentRunner
        for kind in Kind:
            _ = importlib.import_module(f"runai.agents.{kind.value}").build_task

    async def run(self, kind: Kind, trip: dict, emit: Emit) -> StepResult:
        fallback = _fallback(kind, trip)
        try:
            builder = importlib.import_module(f"runai.agents.{kind.value}")
            try:
                task = builder.build_task(trip)
            except ValueError as exc:
                denied = any(word in str(exc).lower() for word in ("denied", "prohibited"))
                return StepResult(
                    kind=kind, status="blocked", summary=(
                        "Site policy does not permit this trip; continue on the official site"
                        if denied else
                        "No reviewed site covers this trip yet; continue on the official site"
                    ),
                    reason_code="policy_denied" if denied else "no_site_coverage",
                    error="Task builder rejected this plan", handoff_url=fallback, synthetic=False,
                )
            fallback = _valid_url(task.get("fallback_url") if isinstance(task, dict) else getattr(
                task, "fallback_url", None,
            ))
            client = importlib.import_module("runai.agents.hclient").HAgentRunner()
            if trip.get("runner_profile"):
                task = {**task, "runner_profile": dict(trip["runner_profile"])}

            async def on_event(event):
                if event.get("type") in {"step_progress", "live_view_available", "live_frame"}:
                    await emit(event)

            result = await client.run(task, on_event)
            if hasattr(result, "model_dump"):
                result = result.model_dump(mode="json")
            fields = {
                key: value for key, value in result.items()
                if key in StepResult.model_fields and key not in {"kind", "synthetic"}
            }
            fields["kind"], fields["synthetic"] = kind, False
            fallback = _valid_url(fields.get("handoff_url")) or fallback
            if fields.get("status") in {"blocked", "failed"}:
                fields["handoff_url"] = _valid_url(fields.get("handoff_url")) or fallback
            return StepResult.model_validate(fields)
        except Exception as exc:  # noqa: BLE001 — provider failures must remain visible results
            return StepResult(
                kind=kind, status="failed", summary="Live preparation failed; continue manually",
                error=f"Live preparation unavailable ({type(exc).__name__})",
                reason_code="provider_error",
                handoff_url=fallback, synthetic=False,
            )
