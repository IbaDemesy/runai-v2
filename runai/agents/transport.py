"""Transport task: a policy-reviewed public deep link for the confirmed round trip.

Adapters come only from docs/site-policy.json; a route no reviewed adapter covers raises
ValueError (blocked) instead of falling back to a generic search or homepage.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isfinite
from typing import Any

from runai.agents.site_policy import city_country, country_code, select_adapter, trip_expected

KIND = "transport"
MAX_STEPS = 80
STOP_BEFORE = [
    "passenger details / personal data form", "login or account creation", "payment page",
    "booking confirmation", "terms or consent checkbox", "cookie consent acceptance",
    "captcha or bot challenge", "any form submission", "redirect to a host not in allowed_hosts",
]


def _budget(trip: Mapping[str, Any]) -> int | float | None:
    value = trip.get("budget_eur")
    if value is None:
        return None
    if type(value) not in (int, float) or value <= 0 or not isfinite(value):
        raise ValueError("budget_eur must be a finite positive number")
    return value


def origin_country(trip: Mapping[str, Any]) -> str | None:
    if trip.get("origin_country") is not None:
        code = country_code(trip.get("origin_country"))
        if code is None:
            raise ValueError("unknown origin_country")
        return code
    return city_country(trip.get("origin_city"))


def build_task(
    trip: Mapping[str, Any], *, today: date | None = None, registry: Any = None,
) -> dict[str, Any]:
    expected = trip_expected(trip, KIND, today=today)
    budget = _budget(trip)
    adapter, url, decision = select_adapter(
        KIND, expected, origin_country=origin_country(trip), today=today, registry=registry,
    )
    origin, city = expected["origin_city"], expected["city"]
    arrival, departure, adults = (
        expected["arrival_date"], expected["departure_date"], expected["travelers"]
    )
    hosts = decision["allowed_hosts"]
    budget_hint = f"Total budget hint: EUR {budget}." if budget is not None else "No budget given."
    instructions = (
        f"Goal: select a viable round trip {origin} -> {city}, {expected['country']} for "
        f"{adults} adults: outbound arriving on or before {arrival}, return departing on "
        f"{departure}; stop before passenger data.\n"
        f"1. The start URL already encodes the route, dates and party. Allowed navigation hosts: "
        f"{', '.join(hosts)}. If any page redirects to another host (including a carrier or "
        "reseller), STOP at once and report BLOCKED unreviewed_redirect with that host.\n"
        f"2. DATE CHECK before anything else: the page must show outbound {arrival}, return "
        f"{departure}, {origin} -> {city} and {adults} adults. If it shows other dates (e.g. "
        "today's), a one-way trip, swapped dates, another route or party, or they can only be "
        "changed by submitting a search form, STOP and report BLOCKED date_mismatch.\n"
        "3. Cookie banners: reject or close only, never accept optional consent.\n"
        f"4. {budget_hint} Select one outbound that arrives in {city} no later than {arrival} AND "
        f"one return departing {departure}, then the fare, using only public select buttons. "
        "Never fill or submit any form.\n"
        f"5. Site-specific success evidence: {adapter['success_evidence']}\n"
        f"6. Site-specific blocked evidence: {adapter['blocked_evidence']}\n"
        "7. STOP at the first passenger-details, login, account, consent, captcha or payment "
        "page. Never type personal data, log in, create accounts, tick terms, solve captchas "
        "or pay. Unselected result lists or a homepage are NOT ready."
    )
    return {
        "kind": KIND,
        "site_name": decision["policy_id"],
        "start_url": url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": (
            f"READY only when a selected outbound (arriving by {arrival}) and return "
            f"({departure}) with fare and total price for {adults} adults are shown, stopped "
            "before passenger details; report that URL. Otherwise BLOCKED (date_mismatch, "
            "no_inventory, login, captcha, consent, unreviewed_redirect) with reason and last URL."
        ),
        "fallback_url": url,
        "max_steps": MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
    }
