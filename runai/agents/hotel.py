"""Hotel task: a policy-reviewed public deep link for the exact confirmed stay.

The site comes only from docs/site-policy.json adapters whose reviewed terms allow read-only
automation with in-session screenshots. Unsupported destinations raise ValueError (blocked);
there is no default chain or homepage fallback.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isfinite
from typing import Any

from runai.agents.site_policy import select_adapter, trip_expected

KIND = "hotel"
MAX_STEPS = 80
STOP_BEFORE = [
    "guest details / personal data form", "login or account creation", "payment page",
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


def build_task(
    trip: Mapping[str, Any], *, today: date | None = None, registry: Any = None,
) -> dict[str, Any]:
    expected = trip_expected(trip, KIND, today=today)
    budget = _budget(trip)
    adapter, url, decision = select_adapter(KIND, expected, today=today, registry=registry)
    arrival, departure, adults = (
        expected["arrival_date"], expected["departure_date"], expected["travelers"]
    )
    hosts = decision["allowed_hosts"]
    budget_hint = (
        f"Total stay budget: EUR {budget} (whole stay, not per night). Select a rate whose "
        "total is at most this budget; if none fits, report BLOCKED over_budget with the "
        "cheapest total seen."
        if budget is not None else "No budget supplied: pick the cheapest suitable rate."
    )
    instructions = (
        f"Goal: show one available hotel room AND rate in {expected['city']}, "
        f"{expected['country']} for check-in {arrival}, check-out {departure}, {adults} adults "
        f"(traveling from {expected['origin_city']}), then stop before guest data.\n"
        f"1. The start URL already encodes the city, dates and party. Allowed navigation hosts: "
        f"{', '.join(hosts)}. If any page redirects to another host, STOP at once and report "
        "BLOCKED unreviewed_redirect with that host; do not interact with it.\n"
        f"2. DATE CHECK before anything else: the page must show check-in {arrival}, check-out "
        f"{departure} and {adults} adults. If it shows other dates (e.g. today's), swapped dates "
        "or another party, or they can only be changed by submitting a search form, STOP and "
        "report BLOCKED date_mismatch with what was shown. Never change the dates yourself.\n"
        "3. Cookie banners: reject or close only, never accept optional consent.\n"
        f"4. {budget_hint} Open one available hotel and select one room and rate whose page shows "
        f"the full stay {arrival} to {departure}, {adults} adults and a total price. Only use "
        "public links/select buttons; never fill or submit any form.\n"
        f"5. Site-specific success evidence: {adapter['success_evidence']}\n"
        f"6. Site-specific blocked evidence: {adapter['blocked_evidence']}\n"
        "7. STOP at the first guest-details, login, account, consent, captcha or payment page. "
        "Never type personal data, log in, create accounts, tick terms, solve captchas or pay.\n"
        "Search results without a selected room and rate are NOT ready."
    )
    return {
        "kind": KIND,
        "site_name": decision["policy_id"],
        "start_url": url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": (
            f"READY only when a selected room and rate show check-in {arrival}, check-out "
            f"{departure}, {adults} adults and a total price, stopped before guest details; "
            "report that URL. Otherwise BLOCKED (date_mismatch, no_inventory, login, captcha, "
            "consent, unreviewed_redirect) with the reason and last URL."
        ),
        "fallback_url": url,
        "max_steps": MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
    }
