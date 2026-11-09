"""Transport task: a policy-reviewed public deep link for the confirmed round trip.

Adapters come only from the policy registry; a route no H-render-verified adapter covers raises
ValueError (blocked) instead of falling back to a generic search or homepage.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from importlib import import_module
from math import isfinite
from typing import Any
from urllib.parse import urlsplit

from runai.agents.scrub import scrub_text, scrub_url
from runai.agents.site_policy import (
    city_country,
    city_key,
    country_code,
    gateway_city,
    select_adapters,
    task_checkpoint,
    trip_expected,
)

KIND = "transport"
MAX_STEPS = 60
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
    candidates = select_adapters(
        KIND, expected, origin_country=origin_country(trip), today=today, registry=registry,
        modes=("rail", "flight"),
        url_filter=_runnable_start_url,
    )
    profile = trip.get("runner_profile")
    tasks = [_candidate_task(expected.copy(), budget, *candidate, profile=profile)
             for candidate in candidates]
    primary = tasks[0]
    if len(tasks) > 1:
        primary["alternatives"] = tasks[1:]
    return primary


def _keep_fragment(url):
    parts = urlsplit(url)
    fragment_url = "https://fragment.example/" + parts.fragment.lstrip("/")
    return bool(parts.fragment and scrub_url(fragment_url) == fragment_url
                and scrub_text(parts.fragment) == parts.fragment
                and scrub_url(url) == parts._replace(fragment="").geturl())


def _runnable_start_url(url):
    public_https = import_module("runai.agents.hclient")._public_https
    return public_https(url) and public_https(scrub_url(url))


def _candidate_task(expected, budget, adapter, url, decision, *, profile=None):
    origin, city = expected["origin_city"], expected["city"]
    mode = {"rail": "train", "flight": "flight"}.get(adapter.get("mode"), "transport")
    checkpoint = task_checkpoint(adapter)
    prefill = adapter.get("prefill")
    fields = [f for f in prefill["fields"] if isinstance(profile.get(f), str)
              and profile[f].strip()] if prefill and isinstance(profile, Mapping) else []
    if fields:
        checkpoint = {key: list(prefill[key]) for key in (
            "prefill_patterns", "url_patterns", "beyond_patterns",
        )}
    checkpoint_stop = (
        "When matched, STOP and answer immediately: READY if evidence is complete else "
        "BLOCKED unsafe_claim. "
    )
    place = adapter["places"].get(city_key(city), {})
    if place.get("via"):
        expected["gateway_city"] = gateway_city(place["via"])
    destination = place.get("via") or ", ".join(dict.fromkeys(
        place[key] for key in ("station_name", "station_code", "iata") if place.get(key)
    ))
    route_city = f"{city} via {destination}" if destination else city
    arrival, departure, adults = (
        expected["arrival_date"], expected["departure_date"], expected["travelers"]
    )
    hosts = decision["allowed_hosts"]
    budget_hint = (
        f"Round-trip budget: EUR {budget} for the whole party, not per person or leg. "
        "If no fare fits, report BLOCKED over_budget with the cheapest full total seen."
        if budget is not None else "No budget given: choose the cheapest suitable full total."
    )
    sbb_hint = (
        "SBB start link has no return-date or party URL parameters. "
        "Reject cookies or choose necessary-only; never accept consent. "
        "FIRST set the traveller to 1 adult without reduction/Half-Fare BEFORE reading any fare, "
        "without personal data or form submission. Never open Top offers or travelcard/Half-Fare/GA "
        "purchase pages. "
        f"Choose outbound then add the return departing on {departure} using safe selection "
        "controls only; never submit a search form. Stop at the fare/ticket selection summary "
        "before passenger details, login or payment. If these safe controls are unavailable, "
        "report BLOCKED date_mismatch rather than use a reduced or one-way quote. "
        if decision["policy_id"] == "sbb-ch" else ""
    )
    instructions = (
        f"1. DATE CHECK first: round-trip {mode}, {origin} -> {route_city}, "
        f"{expected['country']}; outbound {arrival}, return {departure}, {adults} adults. "
        f"{sbb_hint}For missing/wrong dates, route or party, or a one-way trip, report BLOCKED "
        "date_mismatch. Never change the dates or submit search forms.\n"
        f"2. Allowed hosts: {', '.join(hosts)}. STOP on any other host (including a carrier or "
        "reseller) and report BLOCKED unreviewed_redirect; do not interact with it. "
        "Cookie banners: reject or close only; never accept optional consent.\n"
        "3. Within your first ~10 steps, if the site shows its no-availability / not-on-sale / "
        "sales-horizon message (see blocked evidence), report BLOCKED no_inventory immediately "
        "— do not wander until the step limit. If the selected fare is sold out, "
        "report BLOCKED sold_out.\n"
        f"4. {budget_hint} Use public links only: select outbound arriving on or before "
        f"{arrival} AND return departing on {departure}, then fare with the full round-trip "
        "total for the whole party. Never fill or submit any form. "
        "Unselected result lists or a homepage are NOT ready. An explicitly reviewed via "
        "gateway is the arrival point for the race city: READY covers the round trip to/from "
        "that gateway, without changing the race city in expected. The onward local transfer "
        "is out of scope: mention it in the final report, never claim it as booked or included. "
        "Never substitute a non-reviewed gateway or invent race-city evidence.\n"
        f"5. Site-specific success evidence: {adapter['success_evidence']}\n"
        f"6. Site-specific blocked evidence: {adapter['blocked_evidence']}\n"
        "7. STOP on the reviewed fare-selection page and report READY immediately when both "
        "outbound and return fares, dates, party and full round-trip total are selected and visible. "
        f"Checkpoint URL patterns: {checkpoint['url_patterns']}. Match with case-insensitive "
        "re.search against the unquoted current URL path + '?' + query, not host or fragment. "
        f"{checkpoint_stop}"
        f"Never navigate to a URL matching beyond patterns: {checkpoint['beyond_patterns']}. "
        "Stop before opening passenger details or payment. Never type personal data, log in, "
        "create accounts, tick terms, solve captchas or pay. For login/account walls report "
        "BLOCKED login_required; for captcha report BLOCKED captcha; for required consent "
        "report BLOCKED consent_required. Safety rules override site evidence.\n"
        f"8. Finish within {MAX_STEPS} steps; otherwise report BLOCKED step_limit. For missing site "
        "coverage report BLOCKED no_site_coverage; denied policy report BLOCKED policy_denied; "
        "session failure report BLOCKED session_failed; timeout report BLOCKED timeout; "
        "site error report BLOCKED provider_error. Never invent success: report BLOCKED "
        "unsafe_claim if selection evidence is incomplete. Include the last safe public URL."
    )
    task = {
        "kind": KIND,
        "checkpoint": checkpoint,
        "site_name": decision["policy_id"],
        "start_url": url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": (
            f"READY only on the reviewed selection page where a selected outbound "
            f"(arriving by {arrival}) and return ({departure}) show the fare and full round-trip "
            f"total for {adults} adults, before passenger details, personal data or payment. "
            "Report that safe public URL. For incomplete evidence report BLOCKED unsafe_claim; "
            "for other stops use the exact BLOCKED reason from the instructions."
        ),
        "fallback_url": url,
        "max_steps": MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
    }
    if fields:
        passenger_rules = (
            "Passenger fields may be typed only from the Runner profile block appended by the "
            "system, only into passenger fields, and only the authorized prefill_fields. "
            "Intermediate Continue to the next form page is allowed, never a final submit/book/pay. "
            "Never log in or create an account, accept terms or consent, buy extras/insurance, "
            "select paid seats, pay or submit a final booking. "
            f"Prefill page patterns: {checkpoint['prefill_patterns']}; do not force an answer there. "
            f"Stop at final checkpoint patterns {checkpoint['url_patterns']}, before payment, "
            "seats, extras, insurance or terms; an unobserved checkpoint remains BLOCKED. "
            f"Never navigate beyond {checkpoint['beyond_patterns']}."
        )
        task["instructions"] = instructions.replace(
            "Never fill or submit any form.", passenger_rules,
        )
        task["instructions"] = task["instructions"].replace(
            adapter["success_evidence"],
            "Prefer trains if supported, otherwise a reviewed bus/flight mode tab with fares. "
            "Disclose actual airports, including Beauvais, and reviewed gateways. "
            "Select both legs and verify round-trip dates, adults and full party total, then "
            "proceed only to authorized passenger fields and the reviewed final checkpoint.",
        ).replace("passenger forms or ", "")
        start = task["instructions"].index("7. STOP")
        end = task["instructions"].index("8. Finish", start)
        task["instructions"] = (task["instructions"][:start] + "7. " + passenger_rules + "\n"
                                + task["instructions"][end:])
        task["stop_before"] = [s for s in STOP_BEFORE if s not in {
            "passenger details / personal data form", "any form submission",
        }] + ["seats / extras / insurance", "final submit / book / pay"]
        task["prefill_fields"] = fields
        task["prefill_scope"] = "passenger details"
        task["success_signal"] = (
            "READY only at the reviewed final checkpoint with selected round-trip total, "
            "dates, party and authorized passenger fields completed; before seats, extras, "
            "insurance, terms or payment. Unobserved checkpoint means BLOCKED."
        )
    if _keep_fragment(url):
        task["keep_fragment"] = True
    return task
