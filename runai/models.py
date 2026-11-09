import re
from datetime import UTC, date, datetime
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


class RunnerProfile(Model):
    @model_validator(mode="before")
    @classmethod
    def canonical_address(cls, value):
        if isinstance(value, dict) and "address" in value:
            value = dict(value)
            address = value.pop("address")
            if "address_line" in value and value["address_line"] != address:
                raise ValueError("Conflicting address fields")
            value["address_line"] = address
        return value

    full_name: str | None = Field(default=None, max_length=200)
    given_name: str | None = Field(default=None, max_length=100)
    family_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=40)
    birth_date: str | None = Field(default=None, max_length=10)
    gender: str | None = Field(default=None, max_length=40)
    nationality: str | None = Field(default=None, max_length=2)
    address_line: str | None = Field(default=None, max_length=300)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)

    @property
    def complete(self):
        return bool((self.full_name or (self.given_name and self.family_name)) and all(
            getattr(self, key) for key in (
                "email", "phone", "birth_date", "gender", "nationality",
            )
        ))

    @field_validator("*", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("email", "phone", "birth_date", "nationality")
    @classmethod
    def valid_format(cls, value, info):
        if value is None:
            return value
        if info.field_name == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email")
        if info.field_name == "phone" and (
            not re.fullmatch(r"\+?[0-9 ().-]+", value)
            or not 7 <= len(re.sub(r"\D", "", value)) <= 15
        ):
            raise ValueError("Invalid phone")
        if info.field_name == "birth_date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("Invalid ISO date")
            date.fromisoformat(value)
        if info.field_name == "nationality":
            if value.upper() not in _COUNTRY_CODES:
                raise ValueError("Invalid nationality")
            return value.upper()
        return value


_COUNTRY_CODES = {
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT",
    "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI",
    "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY",
    "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN",
    "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK",
    "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL",
    "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM",
    "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR",
    "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
    "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS",
    "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK",
    "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW",
    "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP",
    "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
    "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW",
    "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM",
    "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF",
    "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW",
    "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI",
    "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
}


class ProfileStatus(Model):
    complete: bool = False
    fields: list[str] = Field(default_factory=list)


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
    "unsafe_claim", "provider_error", "checkpoint_unverified", "not_yet_bookable",
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
    checkpoint_reached: bool | None = None
    stale_frame: bool | None = None
    prefilled: bool | None = None
    stop_label: str | None = Field(default=None, max_length=100)
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
    stale_frame: bool | None = None
    sequence: int = Field(ge=1)
    type: Literal[
        "turn", "confirmed", "step_started", "step_progress", "live_view_available",
        "live_frame", "step_finished", "discovery_progress", "discovery_failed",
    ]
    kind: Kind | None = None
    message: str
    synthetic: bool
    observed_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC), exclude_if=lambda value: value is None,
    )
    recorded_at: datetime | None = None
    frame_id: str | None = None
    live_view_url: HttpUrl | None = None

    @field_validator("live_view_url", mode="before")
    @classmethod
    def only_public_view(cls, value):
        return public_url(value)


class Mission(Model):
    profile_status: ProfileStatus = Field(default_factory=ProfileStatus)
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
