"""Machine-readable site-policy registry: dated terms reviews gate every H navigation.

The registry (docs/site-policy.json) records, per reviewed host/path scope, the official
terms URLs, review dates, reviewed sections, the automation decision, the in-session
screenshot/live-view scope and the exact hosts the agent may navigate to. Anything unknown,
expired, prohibited, ambiguous or malformed fails closed. Registration access observations
(account wall, captcha) are recorded separately and are never a permission.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "docs" / "site-policy.json"
KINDS = frozenset({"registration", "hotel", "transport"})
# allowed_owner_rule: terms reviewed, no explicit agent prohibition but materially
# ambiguous (personal-use/copying clauses); allowed read-only by owner decision.
AUTOMATION = frozenset({"allowed_read_only", "allowed_owner_rule", "prohibited", "ambiguous"})
SCREENSHOTS = frozenset({"in_session_only", "none", "unclear"})


class PolicyError(ValueError):
    """The registry is malformed; every decision then fails closed."""


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise PolicyError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PolicyError(f"{field} must be an ISO date") from exc


def _host(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip().lower():
        raise PolicyError(f"invalid host {value!r}")
    if "*" in value or "/" in value or ":" in value or value.startswith("."):
        raise PolicyError(f"hosts are exact names without wildcards: {value!r}")
    return value


def _https(value: Any, field: str) -> str:
    if not isinstance(value, str) or urlsplit(value).scheme != "https" or not urlsplit(value).hostname:
        raise PolicyError(f"{field} must be an https URL")
    return value


def _bool_or_none(value: Any, field: str) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise PolicyError(f"{field} must be true, false or null")
    return value


def _observation(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PolicyError("registration observation must be an object")
    path = raw.get("path_prefix", "/")
    if not isinstance(path, str) or not path.startswith("/"):
        raise PolicyError("observation path_prefix must start with /")
    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        raise PolicyError("observation note must be text")
    return {
        "host": _host(raw.get("host")),
        "path_prefix": path,
        "account_required": _bool_or_none(raw.get("account_required"), "account_required"),
        "captcha": _bool_or_none(raw.get("captcha"), "captcha"),
        "source": _https(raw.get("source"), "observation source"),
        "observed_at": _date(raw.get("observed_at"), "observed_at").isoformat(),
        "note": note,
    }


_DATE_VARIANTS = ("dmy_slash", "dmy_dot", "day", "monthyear0")
_PLACE_FIELDS = frozenset({"place_id", "place_code", "place_name", "place_country", "place_extra"})
_ORIGIN_FIELDS = frozenset({"origin_place_id", "origin_place_code"})
_TEMPLATE_FIELDS = frozenset({
    "city", "country", "origin_city", "arrival_date", "departure_date", "travelers", "race_date",
    *(f"{d}_{v}" for d in ("arrival", "departure") for v in _DATE_VARIANTS),
}) | _PLACE_FIELDS | _ORIGIN_FIELDS


def _date_values(prefix: str, value: date) -> dict[str, str]:
    """Site date encodings; monthyear0 is a zero-based month (00=January) followed by YYYY."""
    return {
        f"{prefix}_dmy_slash": value.strftime("%d/%m/%Y"),
        f"{prefix}_dmy_dot": value.strftime("%d.%m.%Y"),
        f"{prefix}_day": value.strftime("%d"),
        f"{prefix}_monthyear0": f"{value.month - 1:02d}{value.year}",
    }


def _places(raw: Any, entry_id: str, fields: frozenset[str]) -> dict[str, dict[str, str]]:
    """Reviewed public IDs per city (keys casefolded, aliases allowed)."""
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise PolicyError(f"{entry_id}: adapter places must be a mapping")
    places = {}
    for city, ids in raw.items():
        if (
            not isinstance(city, str) or not city.strip() or not isinstance(ids, Mapping)
            or not ids or not set(ids) <= fields
            or not all(isinstance(v, str) and v.strip() for v in ids.values())
        ):
            raise PolicyError(f"{entry_id}: invalid adapter place {city!r}")
        places[city.strip().casefold()] = {k: v.strip() for k, v in ids.items()}
    return places


def _codes(value: Any, field: str) -> frozenset[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(
        isinstance(c, str) and len(c) == 2 and c.isupper() for c in value
    ):
        raise PolicyError(f"{field} must be a list of ISO country codes")
    return frozenset(value)


def _adapter(raw: Any, entry_id: str, scope_hosts: set[str]) -> dict[str, Any]:
    """A reviewed public deep link: values are filled only into the query or fragment."""
    if not isinstance(raw, Mapping) or raw.get("kind") not in KINDS - {"registration"}:
        raise PolicyError(f"{entry_id}: adapter needs kind hotel or transport")
    template = raw.get("url_template")
    if not isinstance(template, str):
        raise PolicyError(f"{entry_id}: adapter url_template is required")
    try:
        sample = template.format(**{f: "X" for f in _TEMPLATE_FIELDS})
    except (KeyError, IndexError, ValueError) as exc:
        raise PolicyError(f"{entry_id}: unknown url_template placeholder") from exc
    before, after = urlsplit(template), urlsplit(sample)
    if (
        before.scheme != "https" or before.hostname not in scope_hosts
        or (before.netloc, before.path) != (after.netloc, after.path)
    ):
        raise PolicyError(f"{entry_id}: url_template must be https on a reviewed host, "
                          "with placeholders only in the query or fragment")
    for key in ("success_evidence", "blocked_evidence"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise PolicyError(f"{entry_id}: adapter {key} is required")
    places = _places(raw.get("places"), entry_id, _PLACE_FIELDS)
    origin_places = _places(raw.get("origin_places"), entry_id, _ORIGIN_FIELDS)
    used = {f for f in _TEMPLATE_FIELDS if "{" + f + "}" in template}
    if used & _PLACE_FIELDS and not places or used & _ORIGIN_FIELDS and not origin_places:
        raise PolicyError(f"{entry_id}: url_template uses place IDs but adapter has none")
    return {
        "kind": raw["kind"],
        "places": places,
        "origin_places": origin_places,
        "uses": frozenset(used),
        "destination_countries": _codes(raw.get("destination_countries"), "destination_countries"),
        "origin_countries": _codes(raw.get("origin_countries"), "origin_countries"),
        "url_template": template,
        "success_evidence": raw["success_evidence"].strip(),
        "blocked_evidence": raw["blocked_evidence"].strip(),
    }


def _entry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise PolicyError("policy entry must be an object")
    entry_id = raw.get("id")
    if not isinstance(entry_id, str) or not entry_id:
        raise PolicyError("policy entry needs an id")
    purposes = raw.get("purposes")
    if not isinstance(purposes, list) or not set(purposes) <= KINDS:
        raise PolicyError(f"{entry_id}: purposes must be registration/hotel/transport")
    scopes = raw.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        raise PolicyError(f"{entry_id}: at least one host/path scope is required")
    parsed_scopes = []
    for scope in scopes:
        if not isinstance(scope, Mapping):
            raise PolicyError(f"{entry_id}: scope must be an object")
        path = scope.get("path_prefix", "/")
        if not isinstance(path, str) or not path.startswith("/"):
            raise PolicyError(f"{entry_id}: path_prefix must start with /")
        parsed_scopes.append({"host": _host(scope.get("host")), "path_prefix": path})
    terms = raw.get("terms_urls")
    if not isinstance(terms, list) or not terms:
        raise PolicyError(f"{entry_id}: official terms_urls are required")
    reviewed, expires = (_date(raw.get(k), f"{entry_id}.{k}") for k in ("reviewed_at", "expires_at"))
    if expires <= reviewed:
        raise PolicyError(f"{entry_id}: expires_at must be after reviewed_at")
    for key in ("reviewed_sections", "justification"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise PolicyError(f"{entry_id}: {key} is required")
    if raw.get("automation") not in AUTOMATION:
        raise PolicyError(f"{entry_id}: automation must be one of {sorted(AUTOMATION)}")
    if raw.get("screenshot_scope") not in SCREENSHOTS:
        raise PolicyError(f"{entry_id}: screenshot_scope must be one of {sorted(SCREENSHOTS)}")
    adapters = raw.get("adapters", [])
    if not isinstance(adapters, list):
        raise PolicyError(f"{entry_id}: adapters must be a list")
    scope_hosts = {s["host"] for s in parsed_scopes}
    navigation = raw.get("navigation_hosts", [])
    observations = raw.get("registration_observations", [])
    if not isinstance(navigation, list) or not isinstance(observations, list):
        raise PolicyError(f"{entry_id}: navigation_hosts/registration_observations must be lists")
    return {
        "id": entry_id,
        "purposes": frozenset(purposes),
        "scopes": parsed_scopes,
        "terms_urls": [_https(u, f"{entry_id}.terms_urls") for u in terms],
        "reviewed_at": reviewed,
        "expires_at": expires,
        "automation": raw["automation"],
        "screenshot_scope": raw["screenshot_scope"],
        "navigation_hosts": [_host(h) for h in navigation],
        "registration_observations": [_observation(o) for o in observations],
        "adapters": [_adapter(a, entry_id, scope_hosts) for a in adapters],
    }


def parse_registry(data: Any) -> list[dict[str, Any]]:
    """Validate a registry document; raise PolicyError if anything is malformed."""
    if not isinstance(data, Mapping) or data.get("schema_version") != 1:
        raise PolicyError("registry must be an object with schema_version 1")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise PolicyError("registry entries must be a list")
    parsed = [_entry(raw) for raw in entries]
    if len({e["id"] for e in parsed}) != len(parsed):
        raise PolicyError("duplicate policy ids")
    return parsed


@lru_cache(maxsize=4)
def _load(path: str, mtime_ns: int) -> tuple[dict[str, Any], ...]:
    return tuple(parse_registry(json.loads(Path(path).read_text(encoding="utf-8"))))


def load_registry(path: Path | str = REGISTRY_PATH) -> list[dict[str, Any]]:
    return list(_load(str(path), Path(path).stat().st_mtime_ns))


def _split(url: Any) -> tuple[str, str] | None:
    if not isinstance(url, str) or not url.strip() or any(c.isspace() for c in url.strip()):
        return None
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError:
        return None
    host = (parts.hostname or "").rstrip(".")
    if parts.scheme != "https" or not host or parts.username or parts.password:
        return None
    if port not in (None, 443):
        return None
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    return host, parts.path or "/"


def _path_match(path: str, prefix: str) -> bool:
    if prefix == "/":
        return True
    prefix = prefix.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def _deny(reason: str, entry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "allowed": False, "reason": reason,
        "policy_id": entry["id"] if entry else None,
        "screenshot_scope": False, "allowed_hosts": [], "allowed_paths": [],
        "expires_at": entry["expires_at"].isoformat() if entry else None,
    }


def _registry(registry: Any) -> list[dict[str, Any]]:
    return load_registry() if registry is None else parse_registry(registry)


def evaluate_url(
    url: str, kind: str, *, today: date | None = None, registry: Any = None,
) -> dict[str, Any]:
    """Decide whether an H agent may open ``url`` for ``kind``. Never raises; fails closed."""
    if kind not in KINDS:
        return _deny("unknown agent kind")
    split = _split(url)
    if split is None:
        return _deny("not a valid public https URL")
    host, path = split
    try:
        entries = _registry(registry)
    except (OSError, ValueError, TypeError):
        return _deny("site-policy registry unavailable or invalid")
    today = today or datetime.now(UTC).date()

    for entry in entries:
        if entry["automation"] == "prohibited" and any(
            host == s["host"] or host.endswith("." + s["host"]) for s in entry["scopes"]
        ):
            return _deny(f"site terms prohibit automated agents ({entry['id']})", entry)

    matches = [
        e for e in entries
        if any(host == s["host"] and _path_match(path, s["path_prefix"]) for s in e["scopes"])
    ]
    if not matches:
        return _deny("no reviewed site policy for this host/path")
    in_purpose = [e for e in matches if kind in e["purposes"]]
    if not in_purpose:
        return _deny(f"policy does not cover {kind}", matches[0])
    def specificity(e: Mapping[str, Any]) -> tuple[int, date]:
        prefixes = [
            len(s["path_prefix"]) for s in e["scopes"]
            if host == s["host"] and _path_match(path, s["path_prefix"])
        ]
        return max(prefixes), e["reviewed_at"]

    entry = max(in_purpose, key=specificity)
    if today < entry["reviewed_at"]:
        return _deny("policy review is dated in the future", entry)
    if today >= entry["expires_at"]:
        return _deny("policy review expired", entry)
    if entry["automation"] not in ("allowed_read_only", "allowed_owner_rule"):
        return _deny("site terms are ambiguous for automated agents", entry)
    if entry["screenshot_scope"] != "in_session_only":
        return _deny("in-session screenshot/live-view scope not authorized", entry)
    hosts = sorted({s["host"] for s in entry["scopes"]} | set(entry["navigation_hosts"]))
    return {
        "allowed": True,
        "reason": (
            "reviewed read-only automation within policy scope"
            if entry["automation"] == "allowed_read_only" else
            "terms reviewed: no explicit agent prohibition (ambiguous); "
            "allowed read-only by owner decision"
        ),
        "policy_id": entry["id"], "screenshot_scope": True, "allowed_hosts": hosts,
        "allowed_paths": sorted({s["path_prefix"] for s in entry["scopes"]}),
        "expires_at": entry["expires_at"].isoformat(),
    }


def registration_info(url: str, *, registry: Any = None) -> dict[str, Any] | None:
    """Return the latest sourced registration access observation for ``url``, else None.

    This is an observation (account wall, captcha), never an automation permission.
    """
    split = _split(url)
    if split is None:
        return None
    host, path = split
    try:
        entries = _registry(registry)
    except (OSError, ValueError, TypeError):
        return None
    observations = [
        o for e in entries for o in e["registration_observations"]
        if o["host"] == host and _path_match(path, o["path_prefix"])
    ]
    if not observations:
        return None
    latest = max(observations, key=lambda o: o["observed_at"])
    return {k: latest[k] for k in ("account_required", "captcha", "source", "observed_at")}


_COUNTRY_CODES = {
    "italy": "IT", "italie": "IT", "italia": "IT", "italien": "IT",
    "switzerland": "CH", "suisse": "CH", "svizzera": "CH", "schweiz": "CH",
    "france": "FR", "frankreich": "FR", "francia": "FR",
    "spain": "ES", "espagne": "ES", "españa": "ES", "espana": "ES", "spanien": "ES",
    "portugal": "PT", "germany": "DE", "allemagne": "DE", "deutschland": "DE",
    "austria": "AT", "autriche": "AT", "österreich": "AT", "belgium": "BE", "belgique": "BE",
    "netherlands": "NL", "pays-bas": "NL", "united kingdom": "GB", "royaume-uni": "GB",
    "uk": "GB", "ireland": "IE", "irlande": "IE", "denmark": "DK", "danemark": "DK",
    "greece": "GR", "grèce": "GR", "czech republic": "CZ", "czechia": "CZ",
    "poland": "PL", "pologne": "PL", "hungary": "HU", "hongrie": "HU",
    "iceland": "IS", "islande": "IS", "norway": "NO", "norvège": "NO",
    "sweden": "SE", "suède": "SE", "united states": "US", "usa": "US", "états-unis": "US",
}
_CITY_COUNTRIES = {
    "paris": "FR", "lyon": "FR", "marseille": "FR", "lille": "FR", "nice": "FR",
    "milan": "IT", "milano": "IT", "rome": "IT", "roma": "IT", "turin": "IT", "torino": "IT",
    "zurich": "CH", "zürich": "CH", "geneva": "CH", "genève": "CH", "bern": "CH",
    "lisbon": "PT", "lisbonne": "PT", "lisboa": "PT", "porto": "PT",
    "madrid": "ES", "barcelona": "ES", "barcelone": "ES", "valencia": "ES", "seville": "ES",
    "berlin": "DE", "munich": "DE", "münchen": "DE", "frankfurt": "DE", "hamburg": "DE",
    "brussels": "BE", "bruxelles": "BE", "amsterdam": "NL", "london": "GB", "londres": "GB",
    "vienna": "AT", "vienne": "AT", "wien": "AT",
}


def country_code(value: Any) -> str | None:
    """ISO code for an English/French/local country name or a 2-letter code, else None."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if len(text) == 2 and text.isalpha():
        return text.upper()
    return _COUNTRY_CODES.get(text.casefold())


def city_country(value: Any) -> str | None:
    return _CITY_COUNTRIES.get(value.strip().casefold()) if isinstance(value, str) else None


def _iso(value: Any, field: str) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise ValueError(f"{field} must be an ISO date")


def _required_text(source: Mapping[str, Any], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid {key}")
    return value.strip()


def trip_expected(
    trip: Any, kind: str, *, today: date | None = None, require_origin: bool = True,
) -> dict[str, Any]:
    """Validate the confirmed trip and return the pinned ``expected`` object (ValueError)."""
    if not isinstance(trip, Mapping):
        raise ValueError("trip must be a mapping")  # noqa: TRY004
    race = trip.get("race")
    if not isinstance(race, Mapping) or not race:
        raise ValueError("trip.race is required")
    today = today or datetime.now(UTC).date()
    city, country = _required_text(race, "city"), _required_text(race, "country")
    if race.get("date_status") in {"conflicting", "unknown"}:
        raise ValueError("race date is not confirmed")
    race_date = _iso(race.get("race_date"), "race.race_date")
    if race_date <= today:
        raise ValueError("race date is not in the future")
    edition = race.get("edition")
    years = {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", str(edition or ""))}
    if years and race_date.year not in years:
        raise ValueError("race edition does not match the race date")
    arrival = _iso(trip.get("arrival_date"), "arrival_date")
    departure = _iso(trip.get("departure_date"), "departure_date")
    if departure <= arrival:
        raise ValueError("departure_date must be after arrival_date")
    if arrival <= today:
        raise ValueError("arrival_date must be in the future")
    if not arrival <= race_date <= departure:
        raise ValueError("the stay must include the race date")
    nights = trip.get("nights")
    if nights is not None and (type(nights) is not int or nights != (departure - arrival).days):
        raise ValueError("nights does not match arrival/departure dates")
    travelers = trip.get("travelers", 1)
    if type(travelers) is not int or not 1 <= travelers <= 9:
        raise ValueError("travelers must be an integer from 1 to 9")
    expected: dict[str, Any] = {
        "kind": kind, "race_name": str(race.get("name") or "").strip() or None,
        "race_date": race_date.isoformat(), "distance_km": race.get("distance_km"),
        "city": city, "country": country, "origin_city": None,
        "arrival_date": arrival.isoformat(), "departure_date": departure.isoformat(),
        "travelers": travelers,
    }
    if require_origin:
        expected["origin_city"] = _required_text(trip, "origin_city")
    elif isinstance(trip.get("origin_city"), str) and trip["origin_city"].strip():
        expected["origin_city"] = trip["origin_city"].strip()
    return expected


def select_adapter(
    kind: str, expected: Mapping[str, Any], *, origin_country: str | None = None,
    today: date | None = None, registry: Any = None,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """First reviewed deep-link adapter whose filled URL passes evaluate_url, else ValueError."""
    destination = country_code(expected.get("country"))
    if destination is None:
        raise ValueError("unknown destination country")
    try:
        entries = _registry(registry)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("site-policy registry unavailable or invalid") from exc
    values = {
        k: str(expected.get(k) or "") for k in _TEMPLATE_FIELDS
    }
    try:
        values |= _date_values("arrival", _iso(expected.get("arrival_date"), "arrival_date"))
        values |= _date_values("departure", _iso(expected.get("departure_date"), "departure_date"))
    except ValueError:
        pass
    city = str(expected.get("city") or "").strip().casefold()
    origin = str(expected.get("origin_city") or "").strip().casefold()
    reasons = []
    for entry in entries:
        for adapter in entry["adapters"]:
            if adapter["kind"] != kind:
                continue
            if adapter["destination_countries"] is not None and (
                destination not in adapter["destination_countries"]
            ):
                continue
            if adapter["origin_countries"] is not None and (
                origin_country not in adapter["origin_countries"]
            ):
                continue
            filled = dict(values)
            if adapter["uses"] & _PLACE_FIELDS:
                if city not in adapter["places"]:
                    reasons.append(f"{entry['id']}: no reviewed place IDs for this city")
                    continue
                filled |= adapter["places"][city]
            if adapter["uses"] & _ORIGIN_FIELDS:
                if origin not in adapter["origin_places"]:
                    reasons.append(f"{entry['id']}: no reviewed place IDs for this origin")
                    continue
                filled |= adapter["origin_places"][origin]
            url = adapter["url_template"].format(
                **{k: quote(v, safe="") for k, v in filled.items()},
            )
            decision = evaluate_url(url, kind, today=today, registry=registry)
            if decision["allowed"]:
                return adapter, url, decision
            reasons.append(f"{entry['id']}: {decision['reason']}")
    detail = "; ".join(reasons) or "no reviewed adapter covers this route/destination"
    raise ValueError(f"no policy-reviewed {kind} site for this trip ({detail})")
