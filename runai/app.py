import asyncio
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import Field

from runai.models import Event, Framing, Kind, Mission, Mode, Model, StepResult
from runai.providers import FakeRunner, FakeSearch, LiveRunner, LiveSearch, ReplayRunner

ROOT = Path(__file__).resolve().parent.parent
TARGET = Framing(
    race="Milano Marathon", race_date="2027-04-04", origin_city="Paris", nights=2, budget_eur=600
)


class CreateRequest(Model):
    description: str = Field(min_length=1, max_length=2000)
    mode: Mode | None = None


class ReplyRequest(Model):
    framing: Framing


class ConfirmRequest(Model):
    confirmed: bool


def create_app() -> FastAPI:
    app = FastAPI(title="RunAI v2 — synthetic demo")
    missions: dict[str, Mission] = {}

    def get(mission_id: str) -> Mission:
        if mission_id not in missions:
            raise HTTPException(404, "Mission not found")
        return missions[mission_id]

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static/index.html")

    @app.post("/api/missions", response_model=Mission, status_code=201)
    async def create(request: CreateRequest):
        mode = request.mode or Mode(os.getenv("RUNAI_MODE", "demo"))
        search = LiveSearch() if mode == Mode.live else FakeSearch()
        try:
            plan = await search.search(TARGET.model_copy())
        except NotImplementedError as exc:
            raise HTTPException(501, str(exc)) from exc
        mission = Mission(
            id=uuid4().hex, mode=mode, synthetic=True,
            description=request.description, plan=plan,
        )
        missions[mission.id] = mission
        return mission

    @app.post("/api/missions/{mission_id}/reply", response_model=Mission)
    async def reply(mission_id: str, request: ReplyRequest):
        mission = get(mission_id)
        if mission.confirmed:
            raise HTTPException(409, "Already confirmed")
        if request.framing != TARGET:
            raise HTTPException(422, "Frozen synthetic journey only; use the displayed framing")
        mission.plan.framing = request.framing
        return mission

    @app.post("/api/missions/{mission_id}/confirm", response_model=Mission)
    async def confirm(mission_id: str, request: ConfirmRequest):
        mission = get(mission_id)
        if not request.confirmed:
            raise HTTPException(400, "Explicit confirmation required")
        if mission.confirmed:
            raise HTTPException(409, "Already confirmed")
        mission.confirmed = True
        mission.status = "running"

        def emit(event_type, message, kind=None):
            mission.events.append(Event(
                sequence=len(mission.events) + 1, type=event_type, kind=kind,
                message=message, synthetic=mission.synthetic,
            ))

        emit("confirmed", "SYNTHETIC journey confirmed; no purchases")
        runner = (
            ReplayRunner() if mission.mode == Mode.replay
            else LiveRunner() if mission.mode == Mode.live else FakeRunner()
        )

        async def run(kind: Kind):
            emit("step_started", "SYNTHETIC preparation started", kind)
            try:
                result = await runner.run(kind, mission.plan)
                if result.status == "ready_for_payment" and not result.handoff_url:
                    raise ValueError("Missing handoff URL")
            except (RuntimeError, ValueError, OSError) as exc:
                result = StepResult(
                    kind=kind, status="failed", summary="Preparation failed",
                    error=str(exc), synthetic=mission.synthetic,
                )
            mission.results.append(result)
            emit("step_finished", result.summary, kind)

        await asyncio.gather(*(run(kind) for kind in Kind))
        mission.status = (
            "completed" if all(r.status == "ready_for_payment" for r in mission.results) else "failed"
        )
        return mission

    @app.get("/api/missions/{mission_id}", response_model=Mission)
    def status(mission_id: str):
        return get(mission_id)

    return app


app = create_app()
