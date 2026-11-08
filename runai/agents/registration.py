"""Registration task: the sourced race edition/distance on a policy-reviewed registration page.

The organizer and registration platform pages must each be covered by a dated site-policy
review for this race (host + path); unknown pages raise ValueError (blocked). Registration
access observations are hints only, never permission.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from runai.agents.site_policy import evaluate_url, registration_info, trip_expected

KIND = "registration"
DEFAULT_MAX_STEPS = 80

STOP_BEFORE = [
    "personal data form (name, email, phone, birth date, address, ID)",
    "account login or account creation",
    "medical certificate or health declaration upload",
    "terms, waiver, privacy or marketing consent checkbox",
    "payment page or payment details",
    "captcha or bot challenge",
    "any form submission",
    "redirect to a host or path outside the reviewed registration scope",
]


def _https_url(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError("race URLs must be strings")  # noqa: TRY004
    url = value.strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"race URL must be an absolute https URL: {url!r}")
    return url


def _text(race: Mapping[str, Any], key: str) -> str:
    value = race.get(key)
    return str(value).strip() if value not in (None, "") else ""


def build_task(
    trip: Mapping[str, Any], *, today: date | None = None, registry: Any = None,
) -> dict[str, Any]:
    """Build the H browser-agent task for the race registration step of ``trip``."""
    expected = trip_expected(trip, KIND, today=today, require_origin=False)
    race = trip["race"]
    registration_url = _https_url(race.get("registration_url"))
    official_url = _https_url(race.get("official_url"))
    if not registration_url and not official_url:
        raise ValueError("race needs an https registration_url or official_url")
    distance = _text(race, "distance_label") or (
        f"{race['distance_km']} km" if race.get("distance_km") else ""
    )
    if not distance:
        raise ValueError("race distance is required")

    decision = start_url = None
    reasons = []
    for url in (registration_url, official_url):
        if not url:
            continue
        decision = evaluate_url(url, KIND, today=today, registry=registry)
        if decision["allowed"]:
            start_url = url
            break
        reasons.append(decision["reason"])
    if start_url is None or decision is None:
        raise ValueError(f"registration site not policy-reviewed ({'; '.join(reasons)})")
    hosts = decision["allowed_hosts"]

    name = expected["race_name"] or "the selected race"
    edition = _text(race, "edition")
    label = " ".join(p for p in (name, edition) if p)
    observation = registration_info(start_url, registry=registry)
    access_hint = (
        f"Recorded access observation ({observation['observed_at']}): account_required="
        f"{observation['account_required']}, captcha={observation['captcha']}. It is a hint, "
        "not permission; verify on the page.\n" if observation else ""
    )
    stop_lines = "\n".join(f"- {item}" for item in STOP_BEFORE)
    success = (
        f"READY: the registration flow for {label}, {distance} on {expected['race_date']} is "
        "selected and the current page is the first one asking for personal data, a medical "
        "certificate, consent or payment, left untouched; report its https URL. "
        "BLOCKED: registration closed, sold out, not yet open, lottery/ballot only, another "
        "edition/date/distance only, account login/creation, captcha or consent required "
        "earlier, or an unreviewed redirect; report the reason and the last URL."
    )
    instructions = (
        f"Goal: open the official registration for {label} ({distance}; race date "
        f"{expected['race_date']}; {expected['city']}, {expected['country']}) and stop at its "
        "first personal-data page without touching it.\n"
        f"1. Start at {start_url}. Allowed navigation hosts (reviewed policy "
        f"{decision['policy_id']}): {', '.join(hosts)}. Stay on pages for this race only. If a "
        "link or redirect leaves these hosts, STOP and report BLOCKED unreviewed_redirect.\n"
        f"2. DATE/EDITION CHECK: the page must show the {edition or expected['race_date'][:4]} "
        f"edition on {expected['race_date']}. If it shows another date or edition, report "
        "BLOCKED date_mismatch; never pick another edition.\n"
        f"3. Select the distance {distance} and a ticket category with public buttons only, "
        "if this needs no personal data.\n"
        "4. Cookie banners: reject or close only, never accept optional consent.\n"
        f"{access_hint}"
        f"5. STOP at the first page that asks for any of:\n{stop_lines}\n"
        "6. Never type personal data, log in, create an account, tick consent or terms, upload "
        "documents, submit a form, pay or bypass a captcha.\n"
        f"Report: {success}"
    )
    return {
        "kind": KIND,
        "site_name": urlsplit(start_url).netloc.removeprefix("www."),
        "start_url": start_url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": success,
        "fallback_url": official_url or start_url,
        "max_steps": DEFAULT_MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
    }
