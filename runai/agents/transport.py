"""Offline transport task specification; not execution or site authorization.

Trip uses race: {city, country, ...RaceOption fields}, origin_city,
arrival_date, departure_date (ISO strings or datetime.date). Optional travelers
is an integer >=1, default 1; budget_eur is a positive finite number, optional,
and a total EUR hint. Optional origin_country overrides city inference.
Other Trip fields (nights, race metadata) are unused. Countries accept English
names or two-letter codes. Unknown origins conservatively use flight search.
Outbound must arrive on arrival_date before evening (depart on or before that
date); the return departs on departure_date.

Rule table: domestic IT/CH/FR/ES/PT/DE uses Trenitalia/SBB/SNCF Connect/Renfe/CP/DB.
Cross-border rail: FR-IT, CH-IT use Trenitalia; FR-CH, DE-CH use SBB;
DE-FR uses DB. All other pairs use read-only Google Flights then human handoff
to an official carrier. Country rules are planning heuristics, not proof of a
viable timetable: verify routes and report blocked if unavailable. Known origin
cities may supply a missing origin_country; explicit origin_country takes priority.
"""

from collections.abc import Mapping
from datetime import date
from math import isfinite


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
    value = trip.get("travelers", 1)
    if type(value) is not int or value < 1:
        raise ValueError("travelers must be a positive integer")
    return value


def _race(trip: Mapping) -> Mapping:
    race = trip.get("race")
    if not isinstance(race, Mapping):
        raise ValueError("Missing or invalid race")  # noqa: TRY004
    return race


def _budget(trip: Mapping) -> int | float | None:
    if "budget_eur" not in trip:
        return None
    value = trip["budget_eur"]
    if type(value) not in (int, float) or value <= 0 or not isfinite(value):
        raise ValueError("budget_eur must be a finite positive number")
    return value


_COUNTRIES = {
    "italy": "IT", "switzerland": "CH", "france": "FR", "spain": "ES",
    "portugal": "PT", "germany": "DE",
}
_ORIGINS = {
    "paris": "FR", "lyon": "FR", "milan": "IT", "rome": "IT",
    "zurich": "CH", "geneva": "CH", "bern": "CH", "zermatt": "CH",
    "lisbon": "PT", "porto": "PT", "madrid": "ES", "barcelona": "ES",
    "berlin": "DE", "munich": "DE",
}
_RAIL = {
    "IT": ("Trenitalia", "https://www.trenitalia.com"),
    "CH": ("SBB", "https://www.sbb.ch"),
    "FR": ("SNCF Connect", "https://www.sncf-connect.com"),
    "ES": ("Renfe", "https://www.renfe.com"),
    "PT": ("CP", "https://www.cp.pt"),
    "DE": ("DB", "https://int.bahn.de"),
}
_CROSS_BORDER = {
    frozenset(("FR", "IT")): "IT", frozenset(("CH", "IT")): "IT",
    frozenset(("FR", "CH")): "CH", frozenset(("DE", "CH")): "CH",
    frozenset(("DE", "FR")): "DE",
}


def _country(value: str) -> str:
    return _COUNTRIES.get(value.strip().lower(), value.strip().upper())


def select_site(trip: Mapping) -> tuple[str, str, str]:
    """Return mode, official site name and public homepage using the rule table."""
    destination = _country(_text(_race(trip), "country"))
    origin = _text(trip, "origin_city")
    source = (
        _country(_text(trip, "origin_country"))
        if "origin_country" in trip else _ORIGINS.get(origin.lower())
    )
    operator = (
        destination if source == destination and destination in _RAIL
        else _CROSS_BORDER.get(frozenset((source, destination)))
    )
    if operator:
        return ("rail", *_RAIL[operator])
    return ("flight", "Google Flights", "https://www.google.com/travel/flights")


def build_task(trip: Mapping) -> dict:
    race = _race(trip)
    city, country = (_text(race, key) for key in ("city", "country"))
    origin = _text(trip, "origin_city")
    arrival, departure = _dates(trip)
    adults = _adults(trip)
    mode, site, url = select_site(trip)
    budget = _budget(trip)
    budget_hint = (
        f"Total budget hint: EUR {budget}." if budget is not None else "No budget supplied."
    )
    return {
        "kind": "transport",
        "site_name": site,
        "start_url": url,
        "instructions": (
            f"Use {mode} search from {origin} to {city}, {country}, for {adults} adults. "
            f"Outbound must arrive on {arrival.isoformat()} before evening; depart on or "
            f"before {arrival.isoformat()}. Return departs on {departure.isoformat()}. "
            f"{budget_hint} Verify a viable route, dates and available fares; select fares "
            "only without commitment. Stop before passenger details, login "
            "or payment, or any earlier guardrail. For flights, use read-only search only "
            "and hand off to the human for an official carrier; do not enter carrier checkout. "
            "Report blocked on no availability, unsuitable routes, or bot protection. "
            "Use the site's public search controls/result navigation to view availability "
            "and fares (read-only); prefer deep-linked/public result pages where available. "
            "Never pay, book, create accounts, accept terms or cookie consent beyond dismissing, "
            "enter personal data, or bypass captchas. Never submit any form, including "
            "guest/passenger details, login, account, booking, payment, consent or newsletter. "
            "If viewing results is impossible without a forbidden step, report blocked "
            "with the public homepage for human handoff."
        ),
        "stop_before": ["guest details", "passenger details", "login", "payment", "booking",
                        "account creation", "terms", "cookie consent",
                        "form submission",
                        "personal data", "captcha"],
        "success_signal": (
            "Outbound arrival on the arrival_date before evening, return departure on "
            "departure_date, fares, route and total price are visible with a public "
            "handoff link, before passenger details or any earlier guardrail. Flights are "
            "search-only carrier handoffs, not reservations. Otherwise report blocked."
        ),
        "fallback_url": url,
        "max_steps": 30,
    }
