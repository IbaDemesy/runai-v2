from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mode(StrEnum):
    demo = "demo"
    replay = "replay"
    live = "live"


class Kind(StrEnum):
    registration = "registration"
    hotel = "hotel"
    transport = "transport"


class StepResult(Model):
    kind: Kind
    status: Literal["ready_for_payment", "blocked", "failed"]
    summary: str
    handoff_url: HttpUrl | None = None
    start_url: HttpUrl | None = None
    final_url: HttpUrl | None = None
    live_view_url: HttpUrl | None = None
    error: str | None = None
    synthetic: bool
    payment_executed: Literal[False] = False

    @model_validator(mode="after")
    def require_handoff(self):
        if self.status == "ready_for_payment" and self.handoff_url is None:
            raise ValueError("ready_for_payment requires a handoff_url")
        return self


class Event(Model):
    sequence: int = Field(ge=1)
    type: Literal[
        "turn", "confirmed", "step_started", "step_progress", "live_view_available",
        "live_frame", "step_finished",
    ]
    kind: Kind | None = None
    message: str
    synthetic: bool
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    recorded_at: datetime | None = None
    frame_id: str | None = None
    live_view_url: HttpUrl | None = None


class Mission(Model):
    id: str
    mode: Mode
    synthetic: bool
    status: Literal["guiding", "ready", "running", "completed", "partial", "failed"] = "guiding"
    turns: list[dict] = Field(default_factory=list)
    trip: dict | None = None
    results: list[StepResult] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
