from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RaceOption(Model):
    id: str
    name: str
    edition: str | None = None
    distance_km: float | None = None
    distance_label: str = ""
    city: str | None = None
    country: str | None = None
    race_date: date | None = None
    date_status: Literal["official", "unverified", "conflicting", "unknown"]
    official_url: str | None = None
    registration_url: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    retrieved_at: datetime | None = None
    synthetic: bool = False


class Suggestion(Model):
    id: str
    label: str
    value: str
    kind: Literal["choose_race", "answer", "confirm", "edit", "retry"]
    provenance: Literal["source", "suggested_default", "synthetic"]


class TripDraft(Model):
    race: RaceOption | None = None
    origin_city: str | None = None
    travelers: int = Field(default=1, ge=1)
    nights: int | None = Field(default=None, ge=1, le=14)
    budget_eur: int | None = Field(default=None, gt=0)
    arrival_date: date | None = None
    departure_date: date | None = None
    provenance: dict[str, Literal["source", "suggested_default", "user"]] = Field(
        default_factory=dict
    )


class GuidedTurn(Model):
    message: str
    question: str | None = None
    suggestions: list[Suggestion] = Field(default_factory=list)
    candidates: list[RaceOption] = Field(default_factory=list)
    draft: TripDraft
    ready_to_confirm: bool = False
    error: str | None = None


class GuideState(Model):
    stage: Literal[
        "discover", "choose_race", "origin", "nights", "budget", "confirm", "confirmed"
    ] = "discover"
    hints: dict = Field(default_factory=dict)
    query: str = ""
    candidates: list[RaceOption] = Field(default_factory=list)
    draft: TripDraft = Field(default_factory=TripDraft)
    history: list[dict] = Field(default_factory=list)
    lang: Literal["fr", "en"] = "fr"
    pending_suggestions: list[Suggestion] = Field(default_factory=list)
