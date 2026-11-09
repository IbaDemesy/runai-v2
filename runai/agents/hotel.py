"""Hotel task: a policy-reviewed public deep link for the exact confirmed stay.

The site comes only from docs/site-policy.json adapters whose reviewed terms allow read-only
automation with in-session screenshots. Unsupported destinations raise ValueError (blocked);
there is no default chain or homepage fallback.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import quote

from runai.agents.site_policy import (
    REGISTRY_PATH,
    city_key,
    city_name,
    hotel_search_city,
    select_adapters,
    task_checkpoint,
    trip_expected,
)

KIND = "hotel"
MAX_STEPS = 60
STOP_BEFORE = [
    "guest details / personal data form", "login or account creation", "payment page",
    "booking confirmation", "terms or consent checkbox", "cookie consent acceptance",
    "captcha or bot challenge", "any form submission", "redirect to a host not in allowed_hosts",
]

DIRECT_SITES = ("r7-booking-hotel", "r7-hilton-hotel", "r7-accor-hotel")
GUEST_FIELDS = ("full_name", "given_name", "family_name", "email", "phone")


def _prefill(task, fields, budget):
    checkpoint = task["checkpoint"]
    checkpoint["prefill_patterns"] = (
        [r"^/book\.html(?:[/?]|$)"] if task["site_name"] == "r7-booking-hotel"
        else [r"/(?:enter[-_])?guest(?:[-_/]?(?:details|info|form))?(?:[/?]|$)"]
    )
    checkpoint["url_patterns"] = [r"/(?:[^?]*/)?(?:payment|card[-_]?details)(?:[/?]|$)"]
    checkpoint["beyond_patterns"] = [r"/(?:[^?]*/)?(?:confirm|confirmation|complete)(?:[/?]|$)"]
    task["prefill_fields"] = fields.copy()
    task["prefill_scope"] = "guest details"
    task["stop_before"] = [s for s in STOP_BEFORE if s != "guest details / personal data form"]
    task["instructions"] = (
        f"Select room and rate for {task['expected']}. Verify dates, party and full-stay total. "
        f"Allowed hosts: {', '.join(task['allowed_hosts'])}. "
        f"Whole-stay budget EUR: {budget}; if exceeded report BLOCKED over_budget. "
        "Cookie banners: reject or necessary-only; never accept optional consent. "
        "Open guest details and type only the provided guest name/email/phone into guest fields. "
        "Never tick terms/marketing, submit forms, log in, create accounts, solve captchas or pay. "
        "Stop before payment or card entry; never type payment details. "
        f"Guest-details prefill patterns (do not force an answer): {checkpoint['prefill_patterns']}. "
        f"Stop URL patterns: {checkpoint['url_patterns']}; forbidden: {checkpoint['beyond_patterns']}. "
        "Match case-insensitively against unquoted path + '?' + query. "
        "READY only with selected room/rate, correct dates/party/city and full-stay total evidence; "
        "otherwise BLOCKED unsafe_claim. Missing fields stay blank; required consent, submission, "
        "login or captcha is BLOCKED, never bypassed. Return verification: room, rate, arrival_date, "
        "departure_date, travelers, total, city, selected, next_safe_boundary and last safe public URL."
    )
    task["success_signal"] = (
        "READY only after selected room/rate and provided guest details, with verified stay dates, "
        "party, city and full-stay total, stopped before payment or card entry. "
        "Never submit or accept terms/marketing. Incomplete evidence: BLOCKED unsafe_claim."
    )


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
    if registry is None:
        path = Path(REGISTRY_PATH)
        try:
            entries = [entry for file in [path, *sorted((path.parent / "site-policy.d").glob("*.json"))]
                       for entry in json.loads(file.read_text())["entries"]]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("site-policy registry unavailable or invalid") from exc
        registry = {"schema_version": 1, "entries": sorted(entries, key=lambda e: (
            DIRECT_SITES.index(e["id"]) if e["id"] in DIRECT_SITES else len(DIRECT_SITES)
        ))}
    candidates = select_adapters(KIND, expected, today=today, registry=registry)
    candidates = [
        (adapter, url.replace(quote(hotel_search_city(expected), safe=""),
                              quote(city_name(expected["city"]), safe=""), 1), decision)
        if decision["policy_id"] == "r7-booking-hotel" else (adapter, url, decision)
        for adapter, url, decision in candidates
    ]
    tasks = [_candidate_task(expected.copy(), budget, *candidate) for candidate in candidates]
    profile = trip.get("runner_profile")
    fields = [k for k in GUEST_FIELDS if isinstance(profile, dict)
              and isinstance(profile.get(k), str) and profile[k].strip()]
    if fields:
        for task in tasks:
            _prefill(task, fields, budget)
    primary = tasks[0]
    if len(tasks) > 1:
        primary["alternatives"] = tasks[1:]
    return primary


def _candidate_task(expected, budget, adapter, url, decision):
    search_city = (expected["city"] if decision["policy_id"] == "r7-booking-hotel"
                   else hotel_search_city(expected))
    if city_key(search_city) != city_key(expected["city"]):
        expected["gateway_city"] = search_city
    checkpoint = task_checkpoint(adapter)
    checkpoint_stop = (
        "When matched, STOP and answer immediately: READY if selected room, rate, dates, "
        "party and full-stay total evidence is complete, else BLOCKED unsafe_claim. "
    )
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
        "IHG qCiMy/qCoMy use a zero-based month: 062027 means July 2027, not June. "
        "Return verification dates as ISO YYYY-MM-DD, interpreted from the actual stay.\n"
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
        f"7. Checkpoint URL patterns: {checkpoint['url_patterns']}. Match with case-insensitive "
        "re.search against the unquoted current URL path + '?' + query, not host or fragment. "
        f"{checkpoint_stop}Never add extras, navigate back or keep browsing after selection. "
        f"Never navigate to a URL matching beyond patterns: {checkpoint['beyond_patterns']}. "
        f"Hotel search city: {search_city}. Only the race city {expected['city']} or reviewed "
        f"gateway city {expected.get('gateway_city', expected['city'])} is acceptable; "
        "outside both, report BLOCKED date_mismatch. Any onward local transfer is not included. "
        "Do not continue to guest details. Stop before opening guest details or payment. "
        "Never type personal data, log in, "
        "create accounts, tick terms, solve captchas or pay. For login/account walls report "
        "BLOCKED login_required; for captcha report BLOCKED captcha; for required consent "
        "report BLOCKED consent_required. Safety rules override site evidence.\n"
        f"8. Finish within {MAX_STEPS} steps; otherwise report BLOCKED step_limit. For missing site "
        "coverage report BLOCKED no_site_coverage; denied policy report BLOCKED policy_denied; "
        "session failure report BLOCKED session_failed; timeout report BLOCKED timeout; "
        "site error report BLOCKED provider_error. Never invent success: report BLOCKED "
        "unsafe_claim if selection evidence is incomplete. Include the last safe public URL."
        " Return verification with exactly these keys: room, rate, arrival_date, departure_date, "
        "travelers, total, city, selected, next_safe_boundary. Use selected=true only for an "
        "actually selected room AND rate; next_safe_boundary describes the untouched guest "
        "details/payment boundary. Never invent missing evidence."
    )
    return {
        "kind": KIND,
        "checkpoint": checkpoint,
        "site_name": decision["policy_id"],
        "start_url": url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": (
            f"READY only on the reviewed selection page where a selected room and rate show "
            f"check-in {arrival}, check-out {departure}, {adults} adults and the full-stay "
            "total for the whole party, before guest details, personal data or payment. "
            f"Checkpoint patterns: {checkpoint['url_patterns']}. {checkpoint_stop}"
            "Report that safe public URL. For incomplete evidence report BLOCKED unsafe_claim; "
            "for other stops use the exact BLOCKED reason from the instructions."
        ),
        "fallback_url": url,
        "max_steps": MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
    }
