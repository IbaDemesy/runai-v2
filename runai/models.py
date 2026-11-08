from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


class Framing(Model):
    race: str = Field(min_length=1)
    race_date: date
    origin_city: str = Field(min_length=1)
    nights: int = Field(ge=1, le=14)
    budget_eur: float = Field(gt=0, le=100000)


class JourneyPlan(Model):
    framing: Framing
    departure: date = date(2027, 4, 3)
    return_date: date = date(2027, 4, 5)
    sites: dict[Kind, HttpUrl]


class StepResult(Model):
    kind: Kind
    status: Literal["ready_for_payment", "failed"]
    summary: str
    handoff_url: HttpUrl | None = None
    error: str | None = None
    synthetic: bool
    payment_executed: Literal[False] = False


class Event(Model):
    sequence: int
    type: Literal["confirmed", "step_started", "step_finished"]
    kind: Kind | None = None
    message: str
    synthetic: bool


class Mission(Model):
    id: str
    mode: Mode
    synthetic: bool
    description: str
    plan: JourneyPlan
    confirmed: bool = False
    status: Literal["awaiting_confirmation", "running", "completed", "failed"] = (
        "awaiting_confirmation"
    )
    results: list[StepResult] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
