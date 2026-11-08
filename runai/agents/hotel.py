"""Offline hotel task specification; not execution or site authorization.

Required trip keys: city (race/start area), country, origin (city),
arrival_date, departure_date (ISO strings or datetime.date). Optional adults
(or travelers) defaults to 1; budget is a total hint including its currency.
hotel_preference may be accor (default) or hilton: only these official chain
homepages are allowlisted. Unsupported preferences fail closed.
Actual site authorization and availability must be reviewed before execution.
"""

from collections.abc import Mapping
from datetime import date


def _text(trip: Mapping, key: str) -> str:
    value = trip.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid {key}")
    return value.strip()


def _dates(trip: Mapping) -> tuple[date, date]:
    try:
        values = []
        for key in ("arrival_date", "departure_date"):
            value = trip.get(key)
            if type(value) is date:
                values.append(value)
            elif isinstance(value, str):
                values.append(date.fromisoformat(value))
            else:
                raise ValueError(key)
        arrival, departure = values
    except (TypeError, ValueError) as exc:
        raise ValueError("Expected valid arrival_date and departure_date") from exc
    if departure <= arrival:
        raise ValueError("departure_date must be after arrival_date")
    return arrival, departure


def _adults(trip: Mapping) -> int:
    value = trip.get("adults", trip.get("travelers", 1))
    if type(value) is not int or value < 1:
        raise ValueError("adults/travelers must be a positive integer")
    return value


def select_site(trip: Mapping) -> tuple[str, str]:
    """Select an allowlisted worldwide official chain, never an arbitrary URL."""
    preference = trip.get("hotel_preference", "accor")
    sites = {
        "accor": ("Accor", "https://all.accor.com"),
        "hilton": ("Hilton", "https://www.hilton.com"),
    }
    if not isinstance(preference, str) or preference.lower() not in sites:
        raise ValueError("Unsupported hotel_preference")
    return sites[preference.lower()]


def build_task(trip: Mapping) -> dict:
    city, country, origin = (_text(trip, key) for key in ("city", "country", "origin"))
    arrival, departure = _dates(trip)
    adults = _adults(trip)
    site, url = select_site(trip)
    budget = trip.get("budget")
    budget_hint = (
        f"Total stay budget hint: {budget}; do not treat it as a nightly limit."
        if budget is not None else "No budget supplied; ask the human before choosing a rate."
    )
    return {
        "kind": "hotel",
        "site_name": site,
        "start_url": url,
        "instructions": (
            f"Search hotels near the race city/start area {city}, {country}, for "
            f"{arrival.isoformat()} to {departure.isoformat()}, {adults} adults "
            f"traveling from {origin}. {budget_hint} "
            "Choose an available room/rate within the total budget only if this is possible "
            "without submission or commitment. Stop at the guest-details page or any earlier "
            "guardrail, always before payment. Report blocked if no availability, no suitable "
            "rate, or a bot-protection challenge. Do not claim a reservation. "
            "Never pay, book, create accounts, accept terms or cookie consent (dismissing is allowed), submit forms, enter personal data, or bypass captchas. If searching requires form submission or consent, stop and report blocked with the public homepage for human handoff."
        ),
        "stop_before": ["guest details", "passenger details", "login", "payment", "booking",
                        "account creation", "terms", "cookie consent", "form submission",
                        "personal data", "captcha"],
        "success_signal": (
            "An available room/rate and total price are visible within budget, with a public "
            "handoff link; stopped before guest details or any earlier guardrail. "
            "If not observable, report blocked, never success."
        ),
        "fallback_url": url,
        "max_steps": 30,
    }
