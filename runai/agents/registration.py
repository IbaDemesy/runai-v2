"""Registration agent task builder: official race registration page, stop before personal data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

KIND = "registration"
DEFAULT_MAX_STEPS = 25

STOP_BEFORE = [
    "personal data form (name, email, phone, birth date, address, ID)",
    "account login or account creation",
    "medical certificate or health declaration upload",
    "terms, waiver, privacy or marketing consent checkbox",
    "payment page or payment details",
    "captcha or bot challenge",
    "any form submission",
]

KNOWN_PLATFORMS = (
    "Njuko",
    "Active",
    "Race Result",
    "Ahotu",
    "RPM Sports",
    "Endu",
    "MyRaceResult",
    "Eventbrite",
    "organizer ticketing / shop pages",
)

SUCCESS_SIGNAL = (
    "READY: the registration flow for the selected distance is open and the next step asks for "
    "personal data, a medical certificate, consent or payment; report its https URL. "
    "BLOCKED: registration is closed, sold out, not yet open, lottery-only, or requires an "
    "account login/creation or a captcha before that step; report the reason and the last URL."
)


def _https_url(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError("race URLs must be strings")  # noqa: TRY004
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"race URL must be an absolute https URL: {url!r}")
    return url


def _text(race: Mapping[str, Any], key: str) -> str:
    value = race.get(key)
    return str(value).strip() if value not in (None, "") else ""


def build_task(trip: Mapping[str, Any]) -> dict[str, Any]:
    """Build the H browser-agent task for the race registration step of ``trip``."""
    if not isinstance(trip, Mapping):
        raise ValueError("trip must be a mapping")  # noqa: TRY004
    race = trip.get("race")
    if not isinstance(race, Mapping) or not race:
        raise ValueError("trip.race is required")

    registration_url = _https_url(race.get("registration_url"))
    official_url = _https_url(race.get("official_url"))
    if not registration_url and not official_url:
        raise ValueError("race needs an https registration_url or official_url")
    start_url = registration_url or official_url

    name = _text(race, "name") or "the selected race"
    edition = _text(race, "edition")
    distance = _text(race, "distance_label") or "the selected distance"
    race_date = _text(race, "race_date")
    place = ", ".join(p for p in (_text(race, "city"), _text(race, "country")) if p)
    label = " ".join(p for p in (name, edition) if p)
    details = "; ".join(
        p for p in (f"distance: {distance}", race_date and f"date: {race_date}", place) if p
    )
    site_name = urlparse(start_url).netloc.removeprefix("www.")

    stop_lines = "\n".join(f"- {item}" for item in STOP_BEFORE)
    instructions = (
        f"Goal: open the official registration flow for {label} ({details}) and stop before "
        "any commitment.\n"
        f"1. Start at {start_url}. If it is the organizer site, find the official registration "
        "link (Register / Inscription / Iscriviti / Anmeldung / Inscripción / Entries).\n"
        "2. Follow only links published by the organizer. Officially linked platforms "
        f"({', '.join(KNOWN_PLATFORMS)}) are fine; do not use resellers or unofficial sites.\n"
        f"3. Select {distance}"
        + (f" for the {edition} edition" if edition else "")
        + " and a ticket/price category if this can be done WITHOUT entering any personal data.\n"
        "4. You may only dismiss cookie banners (reject or close; never accept optional "
        "consent) and switch the site language.\n"
        "5. STOP at the first page that asks for any of the following and report its URL:\n"
        f"{stop_lines}\n"
        "6. Never type personal data, never log in or create an account, never tick consent or "
        "terms, never upload documents, never submit a form, never pay, never bypass a captcha.\n"
        "7. If registration is closed, sold out, not yet open, lottery/ballot only, or blocked by "
        "a captcha or login wall, stop and report BLOCKED with the reason and the last URL.\n"
        f"Fallback: if the start page fails, go to {official_url or start_url}.\n"
        f"Report: {SUCCESS_SIGNAL}"
    )

    return {
        "kind": KIND,
        "site_name": site_name,
        "start_url": start_url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": SUCCESS_SIGNAL,
        "fallback_url": official_url,
        "max_steps": DEFAULT_MAX_STEPS,
    }
