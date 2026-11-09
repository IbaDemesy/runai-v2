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

from runai.agents.site_policy import select_adapters, trip_expected

KIND = "hotel"
MAX_STEPS = 40
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
    candidates = select_adapters(KIND, expected, today=today, registry=registry)
    tasks = [_candidate_task(expected.copy(), budget, *candidate) for candidate in candidates]
    primary = tasks[0]
    if len(tasks) > 1:
        primary["alternatives"] = tasks[1:]
    return primary


def _candidate_task(expected, budget, adapter, url, decision):
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
        f"1. DATE CHECK first: {expected['city']}, {expected['country']}, check-in {arrival}, "
        f"check-out {departure}, {adults} adults. For missing/wrong dates, city or party, "
        "report BLOCKED date_mismatch. Never change the dates or submit search forms.\n"
        f"2. Allowed hosts: {', '.join(hosts)}. STOP on any other host and report BLOCKED "
        "unreviewed_redirect; do not interact with it. Cookie banners: reject or close only; "
        "never accept optional consent.\n"
        "3. Within your first ~10 steps, if the site shows its no-availability / not-on-sale / "
        "sales-horizon message (see blocked evidence), report BLOCKED no_inventory immediately "
        "— do not wander until the step limit. If the selected room/rate is sold out, "
        "report BLOCKED sold_out.\n"
        f"4. {budget_hint} Use public links only to select one room AND rate with the "
        "full-stay total for the whole party. Never fill or submit any form. "
        "Search results without a selected room and rate are NOT ready.\n"
        f"5. Site-specific success evidence: {adapter['success_evidence']}\n"
        f"6. Site-specific blocked evidence: {adapter['blocked_evidence']}\n"
        "7. On the reviewed selection/review page (IHG: Add Extras / select-enhance-stay), "
        "STOP and report READY immediately only "
        "when the selected room, rate, dates, party and full-stay total are visible. Do not "
        "continue to guest details. Stop before opening guest details or payment. "
        "Never type personal data, log in, "
        "create accounts, tick terms, solve captchas or pay. For login/account walls report "
        "BLOCKED login_required; for captcha report BLOCKED captcha; for required consent "
        "report BLOCKED consent_required. Safety rules override site evidence.\n"
        "8. Finish within 40 steps; otherwise report BLOCKED step_limit. For missing site "
        "coverage report BLOCKED no_site_coverage; denied policy report BLOCKED policy_denied; "
        "session failure report BLOCKED session_failed; timeout report BLOCKED timeout; "
        "site error report BLOCKED provider_error. Never invent success: report BLOCKED "
        "unsafe_claim if selection evidence is incomplete. Include the last safe public URL."
    )
    return {
        "kind": KIND,
        "site_name": decision["policy_id"],
        "start_url": url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": (
            f"READY only on the reviewed selection page where a selected room and rate show "
            f"check-in {arrival}, check-out {departure}, {adults} adults and the full-stay "
            "total for the whole party, before guest details, personal data or payment. "
            "For IHG this is the Add Extras / select-enhance-stay page: STOP there and report "
            "READY immediately when all selection evidence is visible. "
            "Report that safe public URL. For incomplete evidence report BLOCKED unsafe_claim; "
            "for other stops use the exact BLOCKED reason from the instructions."
        ),
        "fallback_url": url,
        "max_steps": MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
    }
