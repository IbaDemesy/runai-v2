import asyncio
import importlib
import os
import re
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field, StrictBool, model_validator

from runai.models import Event, Kind, Mission, Mode, Model, StepResult, public_url
from runai.providers import FakeRunner, LiveRunner, ReplayRunner

ROOT = Path(__file__).resolve().parent.parent
MAX_FRAMES = 256
MAX_FRAME_BYTES = 32 * 1024 * 1024


class CreateRequest(Model):
    background: StrictBool = False
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    mode: Mode | None = None


class MessageRequest(Model):
    background: StrictBool = False
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


def _fallback_scrub(value, *, scrub_phone=True):
    value = re.sub(
        r"\b(?:api[_-]?key|access[_-]?token|secret|authorization)\s*[:=]\s*[\"']?[^\s,;\"']+"
        r"|\bBearer\s+[^\s,;\"']+", "[redacted key]", value, flags=re.IGNORECASE,
    )
    value = re.sub(r"[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted email]", value)
    value = re.sub(r"\b(?:sk|hai|linkup|gladia)[-_][\w-]+", "[redacted key]", value,
                   flags=re.IGNORECASE)
    if scrub_phone:
        value = re.sub(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)", "[redacted phone]", value)
    return value


def sanitize(value, key=""):
    if isinstance(value, dict):
        return {name: sanitize(item, name) for name, item in value.items()}
    if isinstance(value, list):
        items = [sanitize(item, key) for item in value]
        return [item for item in items if item is not None] if key == "source_urls" else items
    if not isinstance(value, str):
        return value
    if key == "blocked_url_host":
        return StepResult.public_redirect_diagnostic(value)
    safe_id = (key in {"id", "value", "path_segment"} or key.endswith("_id")) and re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", value,
    )
    if safe_id and key == "path_segment" and any(len(chunk) > 20 and re.search(r"\d", chunk) for chunk in re.split(r"[_.:-]", value)):
        safe_id = None
    if key.endswith("_url") or key == "source_urls":
        url = public_url(value)
        if url is None:
            return None
        parsed = urlsplit(url)
        segments = [unquote(segment) for segment in parsed.path.split("/")]
        queries = [item for _, item in parse_qsl(parsed.query, keep_blank_values=True)]
        try:
            from runai.agents.scrub import _njuko_public_id

            safe = all(_njuko_public_id(parsed.hostname, segments, index) or
                       sanitize(item, "path_segment") == item
                       for index, item in enumerate(segments))
        except ImportError:
            safe = all(sanitize(item, "path_segment") == item for item in segments)
        return url if safe and all(sanitize(item) == item for item in queries) else None
    parts = re.split(r"(\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?\b)", value)
    if len(parts) > 1:
        return "".join(part if index % 2 else sanitize(part, key) for index, part in enumerate(parts))
    value = re.sub(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){11,30}\b", "[redacted IBAN]", value,
                   flags=re.IGNORECASE)
    card_pattern = (r"(?<!\d)(?:\d{13,19}|\d{4}(?:-\d{3,6}){2,4})(?!\d)" if safe_id else
                    r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
    value = re.sub(card_pattern, "[redacted card]", value)
    if safe_id:
        return _fallback_scrub(value, scrub_phone=key == "path_segment" or not re.search(r"[A-Za-z]", value))
    try:
        from runai.agents.scrub import scrub_text
        return scrub_text(value)
    except ImportError:
        return _fallback_scrub(value)


def sanitize_state(state):
    clean = sanitize(jsonable_encoder(state))
    if callable(getattr(type(state), "model_validate", None)):
        return type(state).model_validate(clean)
    return clean


def execution_trip(value):
    if isinstance(value, dict):
        return {name: execution_trip(item) for name, item in value.items()
                if name != "preparation"}
    if isinstance(value, list):
        return [execution_trip(item) for item in value]
    return value


def valid_plan(mission, today):
    try:
        if not mission.turns or not mission.turns[-1].get("ready_to_confirm"):
            return False
        trip = mission.trip or {}
        race = trip["race"]
        if any(not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
               for value in (race.get("race_date"), trip.get("arrival_date"),
                             trip.get("departure_date"))):
            return False
        race_day = date.fromisoformat(race["race_date"])
        arrival = date.fromisoformat(trip["arrival_date"])
        departure = date.fromisoformat(trip["departure_date"])
        if not (race["name"].strip() and race_day > today()
                and arrival <= race_day <= departure and arrival < departure
                and type(trip["travelers"]) is int and trip["travelers"] >= 1
                and trip["origin_city"].strip()):
            return False
        if trip.get("nights") is not None and trip["nights"] != (departure - arrival).days:
            return False
        if trip.get("budget_eur") is not None and trip["budget_eur"] <= 0:
            return False
        if mission.mode == Mode.live:
            return race.get("synthetic") is False and race.get("date_status") == "official" and bool(
                public_url(race.get("official_url")) or public_url(race.get("registration_url")))
        return race.get("synthetic") is True
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def create_app(*, guide=None, runner_factory=None, replay_path=None,
               discovery_heartbeat_s=5.0, today=date.today) -> FastAPI:
    if discovery_heartbeat_s <= 0:
        raise ValueError("Discovery heartbeat must be positive")
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
    generations: dict[str, int] = {}

    @asynccontextmanager
    async def lifespan(app):
        yield
        pending = list(tasks)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    app = FastAPI(title="RunAI v2 — guided race preparation", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": [sanitize(part) for part in error["loc"]],
             "msg": "Invalid request", "type": error["type"]} for error in exc.errors()
        ]})

    def track(coro):
        task = asyncio.create_task(coro)
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return task

    def get(mission_id: str) -> Mission:
        if mission_id not in missions:
            raise HTTPException(404, "Mission not found")
        return missions[mission_id]

    def emit(mission, event_type, message, kind=None, **kwargs):
        mission.events.append(Event(
            sequence=len(mission.events) + 1, type=event_type, kind=kind,
            message=sanitize(message), synthetic=mission.synthetic, **kwargs,
        ))

    def apply_turn(mission, state, turn, engine):
        turn = sanitize(jsonable_encoder(turn))
        if not isinstance(turn, dict):
            raise HTTPException(501, "Guide returned an unsupported turn")
        state_data = jsonable_encoder(state)
        trip = state_data.get("trip") if isinstance(state_data, dict) else None
        if turn.get("ready_to_confirm") and callable(getattr(engine, "trip_payload", None)):
            trip = jsonable_encoder(engine.trip_payload(state))
        if trip is None and turn.get("ready_to_confirm"):
            trip = turn.get("draft")
        mission.turns.append(turn)
        if turn.get("language") in ("fr", "en"):
            mission.language = turn["language"]
        mission.trip = execution_trip(sanitize(trip))
        mission.status = "ready" if turn.get("ready_to_confirm") else "guiding"
        if turn.get("error") == "discovery_failed":
            discovery_failed(mission)
        else:
            mission.error = None
        emit(mission, "turn", turn.get("message", ""))

    def discovery_failed(mission):
        mission.error = "Race search failed; please retry"
        emit(mission, "discovery_failed", mission.error)

    def background_discovery(mission, answer):
        previous = mission.status
        mission.status, mission.error = "discovering", None
        generation = generations.get(mission.id, 0) + 1
        generations[mission.id] = generation
        emit(mission, "discovery_progress", "Race search started")

        async def discover():
            engine = guides[mission.id]
            async def search():
                async with asyncio.timeout(120):
                    if not mission.turns or mission.id not in states:
                        return await engine.start(answer.get("text", ""))
                    return await engine.step(sanitize_state(states[mission.id]), answer)

            started = asyncio.get_running_loop().time()
            worker = track(search())
            try:
                while not worker.done():
                    done, _ = await asyncio.wait({worker}, timeout=discovery_heartbeat_s)
                    if not done and generations[mission.id] == generation:
                        elapsed = asyncio.get_running_loop().time() - started
                        emit(mission, "discovery_progress", f"Still searching official race sources ({int(elapsed)} s elapsed)")
                state, turn = await worker
                if generations[mission.id] != generation:
                    return
                clean_state = sanitize_state(state)
                if jsonable_encoder(turn).get("error") != "discovery_failed":
                    emit(mission, "discovery_progress", "Race search finished")
                apply_turn(mission, state, turn, engine)
                states[mission.id] = clean_state
            except asyncio.CancelledError:
                worker.cancel()
                if generations[mission.id] == generation:
                    generations[mission.id] += 1
                raise
            except Exception:  # noqa: BLE001
                if generations[mission.id] == generation:
                    mission.status = previous
                    discovery_failed(mission)
        track(discover())

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
                result = StepResult.model_validate(sanitize(jsonable_encoder(result)))
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
    async def create(request: CreateRequest, response: Response):
        mode = request.mode or default_mode
        engine = guide if guide is not None else _default_guide(mode)
        mission = Mission(id=uuid4().hex, mode=mode, synthetic=mode != Mode.live)
        missions[mission.id] = mission
        guides[mission.id] = engine
        locks[mission.id] = asyncio.Lock()
        if request.background:
            background_discovery(mission, {"text": sanitize(request.text)})
            response.status_code = 202
            return mission
        try:
            state, turn = await engine.start(sanitize(request.text))
        except (ImportError, NotImplementedError) as exc:
            raise HTTPException(501, "Guided discovery unavailable for this mode") from exc
        except Exception:  # noqa: BLE001
            discovery_failed(mission)
            return mission
        try:
            clean_state = sanitize_state(state)
        except ValueError:
            discovery_failed(mission)
            return mission
        apply_turn(mission, state, turn, engine)
        missions[mission.id] = mission
        states[mission.id], guides[mission.id] = clean_state, engine
        locks[mission.id] = asyncio.Lock()
        return mission

    @app.post("/api/missions/{mission_id}/messages", response_model=Mission)
    async def message(mission_id: str, request: MessageRequest, response: Response):
        mission = get(mission_id)
        async with locks[mission_id]:
            if mission.status not in {"guiding", "ready"}:
                raise HTTPException(409, "Already confirmed")
            answer = sanitize(request.model_dump(exclude_none=True, exclude={"background"}))
            if request.background:
                background_discovery(mission, answer)
                response.status_code = 202
                return mission
            mission.error = None
            generations[mission_id] = generations.get(mission_id, 0) + 1
            try:
                if not mission.turns or mission_id not in states:
                    state, turn = await guides[mission_id].start(answer.get("text", ""))
                else:
                    state, turn = await guides[mission_id].step(
                        sanitize_state(states[mission_id]), answer,
                    )
            except ValueError as exc:
                discovery_failed(mission)
                raise HTTPException(422, "Invalid guide answer") from exc
            except (ImportError, NotImplementedError) as exc:
                discovery_failed(mission)
                raise HTTPException(501, "Guided discovery unavailable for this mode") from exc
            except Exception:  # noqa: BLE001
                discovery_failed(mission)
                return mission
            try:
                clean_state = sanitize_state(state)
            except ValueError:
                discovery_failed(mission)
                return mission
            apply_turn(mission, state, turn, guides[mission_id])
            states[mission_id] = clean_state
            return mission

    @app.post("/api/missions/{mission_id}/confirm", response_model=Mission, status_code=202)
    async def confirm(mission_id: str, request: ConfirmRequest):
        mission = get(mission_id)
        async with locks[mission_id]:
            if mission.status == "discovering":
                raise HTTPException(409, "Race search in progress")
            if not request.confirmed:
                raise HTTPException(400, "Explicit confirmation required")
            if mission.status != "ready" or not valid_plan(mission, today):
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
