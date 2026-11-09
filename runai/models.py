import re
from datetime import UTC, datetime
from enum import StrEnum
from ipaddress import ip_address
from typing import Literal, get_args
from urllib.parse import parse_qsl, unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


def public_url(value):
    if value is None:
        return None
    url = str(value)
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"} or not host:
            return None
        if parsed.username or parsed.password or parsed.fragment or parsed.port not in {None, 80, 443}:
            return None
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            if not ip_address(host).is_global:
                return None
        except ValueError:
            pass
        if any(re.search(r"token|session|sid|auth|key|signature|email", name, re.IGNORECASE)
               for name, _ in parse_qsl(parsed.query)):
            return None
        if re.search(r"jsessionid|(?:token|session|auth|key)=", unquote(parsed.path), re.IGNORECASE):
            return None
        if (host == "hcompany.ai" or host.endswith(".hcompany.ai")) and not (
            parsed.scheme == "https" and host in {"agp.eu.hcompany.ai", "agp.hcompany.ai"}
            and re.fullmatch(r"/share/api/v1/trajectories/[\w-]+", parsed.path)
            and not parsed.query
        ):
            return None
        return url
    except ValueError:
        return None


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


ReasonCode = Literal[
    "no_site_coverage", "policy_denied", "date_mismatch", "no_inventory", "sold_out",
    "registration_closed", "login_required", "captcha", "consent_required",
    "unreviewed_redirect", "over_budget", "step_limit", "session_failed", "timeout",
    "unsafe_claim", "provider_error",
]


class StepResult(Model):
    kind: Kind
    status: Literal["ready_for_payment", "blocked", "failed"]
    summary: str
    handoff_url: HttpUrl | None = None
    start_url: HttpUrl | None = None
    final_url: HttpUrl | None = None
    live_view_url: HttpUrl | None = None
    error: str | None = None
    reason_code: ReasonCode | None = None
    blocked_url_host: str | None = None
    synthetic: bool
    payment_executed: Literal[False] = False

    @field_validator("blocked_url_host", mode="before")
    @classmethod
    def public_redirect_diagnostic(cls, value):
        if not isinstance(value, str) or any(char in value for char in "?#@\\"):
            return None
        try:
            from runai.agents.scrub import scrub_url

            url = "https://" + value
            parts = urlsplit(url)
            if (not parts.path.startswith("/") or not public_url(url)
                    or scrub_url(url) != url):
                return None
            return value
        except (ImportError, ValueError):
            return None

    @field_validator("reason_code", mode="before")
    @classmethod
    def known_reason(cls, value):
        return value if value in get_args(ReasonCode) else None

    @field_validator("handoff_url", "start_url", "final_url", "live_view_url", mode="before")
    @classmethod
    def only_public_urls(cls, value):
        return public_url(value)

    @model_validator(mode="after")
    def require_handoff(self):
        if self.status == "ready_for_payment" and self.handoff_url is None:
            raise ValueError("ready_for_payment requires a handoff_url")
        return self


class Event(Model):
    sequence: int = Field(ge=1)
    type: Literal[
        "turn", "confirmed", "step_started", "step_progress", "live_view_available",
        "live_frame", "step_finished", "discovery_progress", "discovery_failed",
    ]
    kind: Kind | None = None
    message: str
    synthetic: bool
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    recorded_at: datetime | None = None
    frame_id: str | None = None
    live_view_url: HttpUrl | None = None

    @field_validator("live_view_url", mode="before")
    @classmethod
    def only_public_view(cls, value):
        return public_url(value)


class Mission(Model):
    id: str
    mode: Mode
    synthetic: bool
    status: Literal["guiding", "ready", "discovering", "running", "completed", "partial", "failed"] = "guiding"
    error: str | None = None
    language: Literal["fr", "en"] | None = None
    turns: list[dict] = Field(default_factory=list)
    trip: dict | None = None
    results: list[StepResult] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
