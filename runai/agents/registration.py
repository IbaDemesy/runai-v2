"""Registration task: the sourced race edition/distance on a policy-reviewed registration page.

Start URL priority: a reviewed registration adapter matching the race name/country, then the
sourced ``registration_url``, then ``official_url``; each must be allowed by a dated site-policy
review (host + path). Unknown, prohibited or expired pages raise ValueError (blocked). Allowed
hosts add the organizer's reviewed registration platforms (organizer -> njuko/raceresult/endu).
Registration access observations are hints only, never permission. A sourced registration URL
on a prohibited site blocks (no organizer fallback). Adapters may carry a dated ``availability``
observation (validated here, fail closed); a fresh sold_out/closed one is put first in the
instructions. ``registration_coverage`` (P8) answers offline whether ``build_task`` would succeed.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from runai.agents import site_policy
from runai.agents.site_policy import (
    country_code,
    evaluate_url,
    parse_registry,
    registration_info,
    trip_expected,
)

KIND = "registration"
DEFAULT_MAX_STEPS = 40
FRAGMENT_DIR = Path(site_policy.REGISTRY_PATH).parent / "site-policy.d"
_TEMPLATE_FIELDS = ("race_date", "edition")
REASON_CODES = (
    "registration_closed", "sold_out", "login_required", "captcha", "consent_required",
    "unreviewed_redirect", "date_mismatch",
)

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
AVAILABILITY_STATUSES = ("open", "sold_out", "not_open", "closed", "unknown")
AVAILABILITY_MAX_AGE_DAYS = 21
_PROHIBITED = "site terms prohibit"


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


def _read(path: Path) -> list[Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping) or data.get("schema_version") != 1 or not isinstance(
        data.get("entries"), list
    ):
        raise site_policy.PolicyError(f"{path.name}: invalid registry document")
    return list(data["entries"])


def default_registry() -> dict[str, Any]:
    """docs/site-policy.json merged with docs/site-policy.d/*.json (sorted), as raw entries."""
    entries = _read(Path(site_policy.REGISTRY_PATH))
    if FRAGMENT_DIR.is_dir():
        for path in sorted(FRAGMENT_DIR.glob("*.json")):
            entries += _read(path)
    return {"schema_version": 1, "entries": entries}


def _check_scopes(entries: list[Any]) -> None:
    decisions: dict[tuple[str, str], str] = {}
    for raw in entries:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("scopes") or [], list):
            raise site_policy.PolicyError("registry entries and scopes must be objects/lists")
        for scope in raw.get("scopes") or []:
            if not isinstance(scope, Mapping):
                raise site_policy.PolicyError("registry scopes must be objects")
            key = (scope.get("host"), scope.get("path_prefix", "/"))
            if decisions.setdefault(key, raw.get("automation")) != raw.get("automation"):
                raise site_policy.PolicyError(f"conflicting policy decisions for {key}")


def _availability(raw: Any, entry_id: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or raw.get("status") not in AVAILABILITY_STATUSES:
        raise site_policy.PolicyError(f"{entry_id}: availability.status is invalid")
    observed = raw.get("observed_at")
    try:
        if not isinstance(observed, str):
            raise TypeError(observed)
        observed = date.fromisoformat(observed).isoformat()
    except (TypeError, ValueError) as exc:
        raise site_policy.PolicyError(f"{entry_id}: availability.observed_at is invalid") from exc
    source, note = raw.get("source"), raw.get("note", "")
    if not isinstance(source, str) or urlsplit(source).scheme != "https" or not urlsplit(
        source).hostname:
        raise site_policy.PolicyError(f"{entry_id}: availability.source must be an https URL")
    if not isinstance(note, str):
        raise site_policy.PolicyError(f"{entry_id}: availability.note must be text")
    result = {"status": raw["status"], "observed_at": observed, "source": source,
              "note": note.strip()}
    if "distances_km" in raw:
        distances = raw["distances_km"]
        if not isinstance(distances, list) or not distances or not all(
            type(d) in (int, float) and 0 < d < float("inf") for d in distances
        ):
            raise site_policy.PolicyError(f"{entry_id}: availability.distances_km is invalid")
        result["distances_km"] = distances
    return result


def _fresh_status(
    adapter: Mapping[str, Any] | None, today: date, distance_km: Any,
) -> tuple[str, str | None]:
    """Observed availability status, or 'unknown' when absent, stale or dated in the future."""
    availability = adapter.get("availability") if adapter else None
    if not availability:
        return "unknown", None
    if "distances_km" in availability and distance_km not in availability["distances_km"]:
        return "unknown", None
    age = (today - date.fromisoformat(availability["observed_at"])).days
    if not 0 <= age <= AVAILABILITY_MAX_AGE_DAYS:
        return "unknown", availability["observed_at"]
    return availability["status"], availability["observed_at"]


def _registration_adapter(raw: Any, entry: Mapping[str, Any]) -> dict[str, Any]:
    entry_id = entry.get("id")
    if not isinstance(raw, Mapping):
        raise site_policy.PolicyError(f"{entry_id}: registration adapter must be an object")
    match = raw.get("race_match")
    patterns = match.get("name_patterns") if isinstance(match, Mapping) else None
    if not isinstance(patterns, list) or not patterns or not all(
        isinstance(p, str) and p.strip() for p in patterns
    ):
        raise site_policy.PolicyError(f"{entry_id}: race_match.name_patterns is required")
    try:
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    except re.error as exc:
        raise site_policy.PolicyError(f"{entry_id}: invalid name pattern") from exc
    countries = match.get("countries")
    if countries is not None and (not isinstance(countries, list) or not all(
        isinstance(c, str) and len(c) == 2 and c.isupper() for c in countries
    )):
        raise site_policy.PolicyError(f"{entry_id}: race_match.countries must be ISO codes")
    platforms = raw.get("platform_hosts", [])
    if not isinstance(platforms, list):
        raise site_policy.PolicyError(f"{entry_id}: platform_hosts must be a list")
    platforms = [site_policy._host(h) for h in platforms]
    template = raw.get("url_template")
    if not isinstance(template, str):
        raise site_policy.PolicyError(f"{entry_id}: adapter url_template is required")
    try:
        sample = template.format(**dict.fromkeys(_TEMPLATE_FIELDS, "X"))
    except (KeyError, IndexError, ValueError) as exc:
        raise site_policy.PolicyError(f"{entry_id}: unknown url_template placeholder") from exc
    before, after = urlsplit(template), urlsplit(sample)
    scopes = [s for s in entry.get("scopes") or [] if isinstance(s, Mapping)]
    scope_hosts = {s.get("host") for s in scopes}
    if (
        before.scheme != "https" or before.hostname not in scope_hosts | set(platforms)
        or (before.netloc, before.path) != (after.netloc, after.path)
    ):
        raise site_policy.PolicyError(f"{entry_id}: url_template must be https on a reviewed "
                                      "host, with placeholders only in the query or fragment")
    for key in ("success_evidence", "blocked_evidence"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise site_policy.PolicyError(f"{entry_id}: adapter {key} is required")
    return {
        "policy_id": entry_id, "patterns": compiled,
        "countries": frozenset(countries) if countries else None,
        "url_template": template, "platform_hosts": platforms,
        "organizer_url": (
            f"https://{scopes[0]['host']}{scopes[0].get('path_prefix', '/')}" if scopes else None
        ),
        "success_evidence": raw["success_evidence"].strip(),
        "blocked_evidence": raw["blocked_evidence"].strip(),
        "availability": _availability(raw.get("availability"), entry_id),
    }


def policy_view(registry: Any = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Split registration adapters from ``registry`` (raw document; default: merged files).

    Returns the registry without registration adapters (parsed by site_policy) and the
    validated registration adapters. Any malformed part raises PolicyError (fail closed).
    """
    raw = default_registry() if registry is None else registry
    if not isinstance(raw, Mapping) or not isinstance(raw.get("entries"), list):
        raise site_policy.PolicyError("registry must be an object with entries")
    view = copy.deepcopy(dict(raw))
    adapters = []
    for entry in view["entries"]:
        if isinstance(entry, dict) and isinstance(entry.get("adapters"), list):
            mine = [a for a in entry["adapters"] if isinstance(a, Mapping)
                    and a.get("kind") == KIND]
            entry["adapters"] = [a for a in entry["adapters"] if a not in mine]
            adapters += [_registration_adapter(a, entry) for a in mine]
    _check_scopes(view["entries"])
    parse_registry(view)
    return view, adapters


def _host_allowed(host: str, *, today: date | None, registry: Any) -> bool:
    return evaluate_url(f"https://{host}/", KIND, today=today, registry=registry)["allowed"]


def _matching(adapters, race: Mapping[str, Any]) -> list[dict[str, Any]]:
    year = (_text(race, "race_date") or "")[:4]
    name = " ".join(p for p in (_text(race, "name"), _text(race, "edition"), year) if p)
    code = country_code(race.get("country"))
    return [
        a for a in adapters
        if name and any(p.search(name) for p in a["patterns"])
        and (a["countries"] is None or code in a["countries"])
    ]


def build_task(
    trip: Mapping[str, Any], *, today: date | None = None, registry: Any = None,
) -> dict[str, Any]:
    """Build the H browser-agent task for the race registration step of ``trip``."""
    return _plan(trip, today=today, registry=registry)[0]


def _plan(
    trip: Mapping[str, Any], *, today: date | None, registry: Any,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    today = today or datetime.now(UTC).date()
    expected = trip_expected(trip, KIND, today=today, require_origin=False)
    race = trip["race"]
    registration_url = _https_url(race.get("registration_url"))
    official_url = _https_url(race.get("official_url"))
    if not registration_url and not official_url:
        raise ValueError("race needs an https registration_url or official_url")
    distance_km = race.get("distance_km")
    if type(distance_km) not in (int, float) or not 0 < distance_km < float("inf"):
        raise ValueError("race distance_km is required to verify the selected distance")
    distance = _text(race, "distance_label") or f"{distance_km} km"
    try:
        view, adapters = policy_view(registry)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("site-policy registry unavailable or invalid") from exc

    for sourced_url in (registration_url, official_url):
        if not sourced_url:
            continue
        denial = evaluate_url(sourced_url, KIND, today=today, registry=view)
        if denial["reason"].startswith(_PROHIBITED):
            raise ValueError(f"registration site not policy-reviewed: denied ({denial['reason']})")
    values = {"race_date": expected["race_date"], "edition": _text(race, "edition")}
    candidates: list[tuple[str, dict[str, Any] | None]] = []
    for adapter in _matching(adapters, race):
        if adapter["organizer_url"] and not evaluate_url(
            adapter["organizer_url"], KIND, today=today, registry=view)["allowed"]:
            continue
        if not all(_host_allowed(h, today=today, registry=view)
                   for h in adapter["platform_hosts"]):
            continue
        filled = adapter["url_template"].format(
            **{k: quote(v, safe="") for k, v in values.items()})
        candidates.append((filled, adapter))
    candidates += [(url, None) for url in (registration_url, official_url) if url]

    decision = start_url = adapter = None
    reasons = []
    for url, candidate in candidates:
        decision = evaluate_url(url, KIND, today=today, registry=view)
        if decision["allowed"]:
            start_url, adapter = url, candidate
            break
        reasons.append(decision["reason"])
    if start_url is None or decision is None:
        raise ValueError(f"registration site not policy-reviewed ({'; '.join(reasons)})")
    alternatives = []
    if adapter:
        for url in dict.fromkeys(
            [u for u, _ in candidates] + [adapter["organizer_url"]]
        ):
            if url and url != start_url and evaluate_url(
                url, KIND, today=today, registry=view)["allowed"]:
                alternatives.append(url)

    fallback_url = next(
        (u for u in (registration_url, official_url)
         if u and evaluate_url(u, KIND, today=today, registry=view)["allowed"]), start_url)
    start_host = urlsplit(start_url).hostname
    scope_hosts = {
        s["host"] for e in parse_registry(view) if e["id"] == decision["policy_id"]
        for s in e["scopes"]
    }
    platforms = set(adapter["platform_hosts"]) if adapter else set()
    hosts = sorted(
        {start_host} | (scope_hosts & set(decision["allowed_hosts"])) | {
            h for h in (set(decision["allowed_hosts"]) - scope_hosts) | platforms
            if _host_allowed(h, today=today, registry=view)
        }
    )

    name = expected["race_name"] or "the selected race"
    edition = _text(race, "edition")
    label = " ".join(p for p in (name, edition) if p)
    observation = registration_info(start_url, registry=view)
    access_hint = (
        f"Recorded access observation ({observation['observed_at']}): account_required="
        f"{observation['account_required']}, captcha={observation['captcha']}. It is a hint, "
        "not permission; verify on the page.\n" if observation else ""
    )
    adapter_hint = (
        f"Reviewed registration entry (policy {adapter['policy_id']}): READY looks like: "
        f"{adapter['success_evidence']} BLOCKED looks like: {adapter['blocked_evidence']}\n"
        if adapter else ""
    )
    status, observed_at = _fresh_status(adapter, today, distance_km)
    availability_first = ""
    if adapter and status in ("sold_out", "closed"):
        code = "sold_out" if status == "sold_out" else "registration_closed"
        availability_first = (
            f"AVAILABILITY FIRST: registration was observed {status.replace('_', ' ')} on "
            f"{observed_at} ({adapter['availability']['source']}). Within your first 5 steps, "
            f"check whether this is still the case; if it is, STOP and report BLOCKED {code} "
            "with the URL. Never join a waiting list or fill any form.\n"
        )
    alternatives_hint = (
        "Other reviewed entry points for this race (human handoff only; do not navigate "
        f"there unless they are on an allowed host): {', '.join(alternatives)}.\n"
        if alternatives else ""
    )
    stop_lines = "\n".join(f"- {item}" for item in STOP_BEFORE)
    success = (
        f"READY: the registration flow for {label}, {distance} on {expected['race_date']} is "
        "selected and the current page is the first one asking for personal data, a medical "
        "certificate, consent or payment, left untouched; report its https URL. "
        "BLOCKED: registration closed, sold out, not yet open, lottery/ballot only, another "
        "edition/date/distance only, account login/creation, captcha or consent required "
        "earlier, or an unreviewed redirect; report the reason code and the last URL. "
        "Always end with: no payment, booking or submission was made."
    )
    instructions = availability_first + (
        f"Goal: open the official registration for {label} ({distance}; race date "
        f"{expected['race_date']}; {expected['city']}, {expected['country']}) and stop at its "
        "first personal-data page without touching it. Be step-efficient: finish in under "
        f"{DEFAULT_MAX_STEPS} steps.\n"
        f"1. Start at {start_url}. Allowed navigation hosts (reviewed policy "
        f"{decision['policy_id']}): {', '.join(hosts)}. Stay on pages for this race only. If a "
        "link or redirect leaves these hosts, STOP and report BLOCKED unreviewed_redirect.\n"
        "2. If this is the organizer site, open its registration link (Register, Sign up, "
        "Inscriptions, Iscriviti, Iscrizioni, Inscrições, Inscripciones, Anmeldung) directly; "
        "do not browse news or other pages.\n"
        f"3. DATE/EDITION CHECK: the page must show the {edition or expected['race_date'][:4]} "
        f"edition on {expected['race_date']}. If it shows another date or edition, report "
        "BLOCKED date_mismatch; never pick another edition.\n"
        f"4. Select the distance {distance} and a ticket category with public buttons only, "
        "if this needs no personal data.\n"
        "5. Cookie banners: reject or close only, never accept optional consent.\n"
        f"{access_hint}{adapter_hint}{alternatives_hint}"
        f"6. STOP at the first page that asks for any of:\n{stop_lines}\n"
        "7. Never type personal data, log in, create an account, tick consent or terms, upload "
        "documents, submit a form, pay or bypass a captcha.\n"
        "8. Reaching a page whose URL path contains /book, /checkout or /register is NOT a "
        "booking or registration: it is only a form you leave untouched. Do not claim anything "
        "was booked, registered, submitted or paid; your answer must state 'no payment, "
        "booking or submission was made'.\n"
        f"9. Blocked reason codes: {', '.join(REASON_CODES)}.\n"
        f"Report: {success}"
    )
    return {
        "kind": KIND,
        "site_name": urlsplit(start_url).netloc.removeprefix("www."),
        "start_url": start_url,
        "instructions": instructions,
        "stop_before": list(STOP_BEFORE),
        "success_signal": success,
        "fallback_url": fallback_url,
        "max_steps": DEFAULT_MAX_STEPS,
        "expected": expected,
        "allowed_hosts": hosts,
        "alternatives": alternatives,
    }, adapter


def _coverage_trip(race: Mapping[str, Any], today: date) -> dict[str, Any]:
    race_date = date.fromisoformat(str(race.get("race_date")))
    arrival = max(race_date - timedelta(days=1), today + timedelta(days=1))
    departure = race_date + timedelta(days=1)
    return {"race": dict(race), "travelers": 1, "nights": (departure - arrival).days,
            "arrival_date": arrival.isoformat(), "departure_date": departure.isoformat()}


def _prohibition(race: Mapping[str, Any], today: date, registry: Any) -> str | None:
    view, adapters = policy_view(registry)
    urls = [race.get("registration_url"), race.get("official_url")]
    for adapter in _matching(adapters, race):
        urls += [adapter["organizer_url"], adapter["url_template"]]
    for url in urls:
        if isinstance(url, str):
            decision = evaluate_url(url, KIND, today=today, registry=view)
            if decision["reason"].startswith(_PROHIBITED):
                return decision["policy_id"]
    return None


def registration_coverage(
    race: Mapping[str, Any], *, today: date | None = None, registry: Any = None,
) -> dict[str, Any]:
    """Offline P8 coverage: would ``build_task`` succeed for ``race``? Never raises.

    ``status`` is the matched adapter's recorded availability, or ``unknown`` when absent,
    older than 21 days or the race is not covered.
    """
    result: dict[str, Any] = {"covered": False, "status": "unknown", "policy_id": None,
                              "observed_at": None, "prohibited": False}
    try:
        if not isinstance(race, Mapping):
            return result
        today = today if isinstance(today, date) else datetime.now(UTC).date()
        try:
            task, adapter = _plan(_coverage_trip(race, today), today=today, registry=registry)
        except (ValueError, TypeError, KeyError):
            policy_id = _prohibition(race, today, registry)
            if policy_id:
                result.update(prohibited=True, policy_id=policy_id)
            return result
        status, observed_at = _fresh_status(adapter, today, race.get("distance_km"))
        decision = evaluate_url(task["start_url"], KIND, today=today,
                                registry=policy_view(registry)[0])
        result.update(covered=True, status=status, observed_at=observed_at,
                      policy_id=decision["policy_id"])
    except Exception:  # noqa: BLE001
        return {"covered": False, "status": "unknown", "policy_id": None,
                "observed_at": None, "prohibited": False}
    return result
