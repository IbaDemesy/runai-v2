import asyncio
import importlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field, StrictBool, model_validator

from runai.models import Event, Kind, Mission, Mode, Model, StepResult, public_url
from runai.providers import FakeRunner, LiveRunner, ReplayRunner

ROOT = Path(__file__).resolve().parent.parent
MAX_FRAMES = 256
MAX_FRAME_BYTES = 32 * 1024 * 1024


class CreateRequest(Model):
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    mode: Mode | None = None


class MessageRequest(Model):
    text: str | None = Field(default=None, max_length=2000)
    suggestion_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def require_answer(self):
        if not any(value and value.strip() for value in (self.text, self.suggestion_id)):
            raise ValueError("Provide text or suggestion_id")
        return self


class ConfirmRequest(Model):
    confirmed: StrictBool


def _discovery_hints(hints):
    mapped = dict(hints or {})
    months = mapped.pop("months", None)
    if months:
        mapped.setdefault("month_from", months[0])
        mapped.setdefault("month_to", months[-1])
    named = mapped.pop("named", None)
    if named:
        mapped.setdefault("race_name", named)
    return mapped


def _default_guide(mode):
    if mode == Mode.live and not os.getenv("LINKUP_API_KEY"):
        raise HTTPException(501, "Live race discovery requires LINKUP_API_KEY")
    try:
        module = importlib.import_module("runai.guide")
        if mode == Mode.live:
            provider = importlib.import_module("runai.discovery.linkup").discover

            async def discovery(query, hints):
                return await provider(query, _discovery_hints(hints), timeout_s=120)
        else:
            discovery = importlib.import_module("runai.guide.fake").FakeDiscovery()
        return module.GuideEngine(discovery)
    except (ImportError, AttributeError) as exc:
        raise HTTPException(501, "Guided discovery module unavailable for this mode") from exc


def create_app(*, guide=None, runner_factory=None, replay_path=None) -> FastAPI:
    try:
        default_mode = Mode(os.getenv("RUNAI_MODE", "demo"))
    except ValueError as exc:
        raise ValueError("RUNAI_MODE must be demo, replay, or live") from exc

    missions: dict[str, Mission] = {}
    states: dict[str, object] = {}
    guides: dict[str, object] = {}
    locks: dict[str, asyncio.Lock] = {}
    frames: dict[str, tuple[bytes, str]] = {}
    tasks: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app):
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="RunAI v2 — guided race preparation", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    def get(mission_id: str) -> Mission:
        if mission_id not in missions:
            raise HTTPException(404, "Mission not found")
        return missions[mission_id]

    def emit(mission, event_type, message, kind=None, **kwargs):
        mission.events.append(Event(
            sequence=len(mission.events) + 1, type=event_type, kind=kind,
            message=message, synthetic=mission.synthetic, **kwargs,
        ))

    def apply_turn(mission, state, turn, engine):
        turn = jsonable_encoder(turn)
        if not isinstance(turn, dict):
            raise HTTPException(501, "Guide returned an unsupported turn")
        mission.turns.append(turn)
        state_data = jsonable_encoder(state)
        trip = state_data.get("trip") if isinstance(state_data, dict) else None
        if turn.get("ready_to_confirm") and callable(getattr(engine, "trip_payload", None)):
            trip = jsonable_encoder(engine.trip_payload(state))
        if trip is None and turn.get("ready_to_confirm"):
            trip = turn.get("draft")
        mission.trip = trip
        mission.status = "ready" if turn.get("ready_to_confirm") else "guiding"
        emit(mission, "turn", turn.get("message", ""))

    async def prepare(mission):
        async def run(kind):
            emit(mission, "step_started", "Preparation started; no purchases or submissions", kind)

            async def progress(data):
                event_type = data.get("type", "step_progress")
                if event_type not in {"step_progress", "live_view_available", "live_frame"}:
                    return
                fields = {}
                if data.get("recorded_at"):
                    fields["recorded_at"] = data["recorded_at"]
                if event_type == "live_frame":
                    content = data.get("image")
                    mime = data.get("mime", "image/png")
                    allowed = {"image/png", "image/jpeg", "image/webp", "image/gif"}
                    if mission.synthetic:
                        allowed.add("image/svg+xml")
                    if not isinstance(content, bytes) or not content or mime not in allowed:
                        emit(mission, "step_progress", "Frame unavailable", kind)
                        return
                    if len(content) > 5 * 1024 * 1024:
                        emit(mission, "step_progress", "Frame exceeds size limit", kind)
                        return
                    frame_id = uuid4().hex
                    frames[frame_id] = content, mime
                    while len(frames) > MAX_FRAMES or sum(
                        len(frame[0]) for frame in frames.values()
                    ) > MAX_FRAME_BYTES:
                        del frames[next(iter(frames))]
                    fields["frame_id"] = frame_id
                if data.get("live_view_url"):
                    fields["live_view_url"] = public_url(data["live_view_url"])
                if event_type == "live_view_available" and not fields.get("live_view_url"):
                    emit(mission, "step_progress", "Public live view unavailable", kind)
                    return
                emit(mission, event_type, data.get("message", "Preparation update"), kind, **fields)

            try:
                if runner_factory is not None:
                    runner = runner_factory(mission.mode)
                elif mission.mode == Mode.replay:
                    runner = ReplayRunner(replay_path) if replay_path is not None else ReplayRunner()
                else:
                    runner = LiveRunner() if mission.mode == Mode.live else FakeRunner()
                result = await runner.run(kind, mission.trip, progress)
                result = StepResult.model_validate(result)
                if result.kind != kind or result.synthetic != mission.synthetic:
                    raise ValueError("Runner result provenance mismatch")
            except Exception as exc:  # noqa: BLE001 — isolate each background provider failure
                result = StepResult(
                    kind=kind, status="failed", summary="Preparation failed; continue manually",
                    error=f"Preparation unavailable ({type(exc).__name__})",
                    synthetic=mission.synthetic,
                )
            mission.results.append(result)
            emit(mission, "step_finished", result.summary, kind)

        await asyncio.gather(*(run(kind) for kind in Kind))
        successes = sum(result.status == "ready_for_payment" for result in mission.results)
        mission.status = "completed" if successes == 3 else "partial" if successes else "failed"

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static/index.html")

    @app.get("/api/health")
    def health():
        return {"mode": default_mode, "live_ready": {
            "linkup": bool(os.getenv("LINKUP_API_KEY")), "h": bool(os.getenv("HAI_API_KEY")),
        }}

    @app.post("/api/missions", response_model=Mission, status_code=201)
    async def create(request: CreateRequest):
        mode = request.mode or default_mode
        engine = guide if guide is not None else _default_guide(mode)
        try:
            state, turn = await engine.start(request.text)
        except (ImportError, NotImplementedError) as exc:
            raise HTTPException(501, "Guided discovery unavailable for this mode") from exc
        mission = Mission(id=uuid4().hex, mode=mode, synthetic=mode != Mode.live)
        apply_turn(mission, state, turn, engine)
        missions[mission.id] = mission
        states[mission.id], guides[mission.id] = state, engine
        locks[mission.id] = asyncio.Lock()
        return mission

    @app.post("/api/missions/{mission_id}/messages", response_model=Mission)
    async def message(mission_id: str, request: MessageRequest):
        mission = get(mission_id)
        async with locks[mission_id]:
            if mission.status not in {"guiding", "ready"}:
                raise HTTPException(409, "Already confirmed")
            try:
                state, turn = await guides[mission_id].step(
                    states[mission_id], request.model_dump(exclude_none=True),
                )
            except ValueError as exc:
                raise HTTPException(422, "Invalid guide answer") from exc
            except (ImportError, NotImplementedError) as exc:
                raise HTTPException(501, "Guided discovery unavailable for this mode") from exc
            apply_turn(mission, state, turn, guides[mission_id])
            states[mission_id] = state
            return mission

    @app.post("/api/missions/{mission_id}/confirm", response_model=Mission, status_code=202)
    async def confirm(mission_id: str, request: ConfirmRequest):
        mission = get(mission_id)
        async with locks[mission_id]:
            if not request.confirmed:
                raise HTTPException(400, "Explicit confirmation required")
            if mission.status != "ready" or not mission.trip:
                raise HTTPException(409, "Already confirmed or plan not ready to confirm")
            if mission.mode == Mode.live:
                if not os.getenv("HAI_API_KEY"):
                    raise HTTPException(501, "Live preparation requires HAI_API_KEY")
                if runner_factory is None:
                    try:
                        LiveRunner.ensure_available()
                    except (ImportError, AttributeError) as exc:
                        raise HTTPException(501, "Live H preparation modules unavailable") from exc
            mission.status = "running"
            emit(mission, "confirmed", "Explicitly confirmed; stop before payment or commitment")
            task = asyncio.create_task(prepare(mission))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
            return mission

    @app.get("/api/missions/{mission_id}", response_model=Mission)
    def status(mission_id: str):
        return get(mission_id)

    @app.get("/api/missions/{mission_id}/events", response_model=list[Event])
    def events(mission_id: str, after: int = Query(default=0, ge=0)):
        return [event for event in get(mission_id).events if event.sequence > after]

    @app.get("/api/frames/{frame_id}")
    def frame(frame_id: str):
        if frame_id not in frames:
            raise HTTPException(404, "Frame not found")
        content, mime = frames[frame_id]
        return Response(content, media_type=mime, headers={
            "Content-Security-Policy": "sandbox; default-src 'none'",
            "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
        })

    return app


app = create_app()
