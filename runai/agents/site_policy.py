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
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from string import Formatter
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


_DATE_VARIANTS = ("dmy_slash", "dmy_dot", "day", "monthyear0", "ymd", "dmy_dash", "mdy_slash")
_PLACE_FIELDS = frozenset({
    "place_id", "place_code", "place_name", "place_country", "place_extra",
    "city_query", "iata", "station_code", "station_name", "via",
})
_ORIGIN_FIELDS = frozenset({
    "origin_place_id", "origin_place_code", "origin_city_query", "origin_iata",
    "origin_station_code", "origin_station_name",
})
_TEMPLATE_FIELDS = frozenset({
    "city", "country", "origin_city", "arrival_date", "departure_date", "travelers", "race_date",
    "race_name",
    *(f"{d}_{v}" for d in ("arrival", "departure") for v in _DATE_VARIANTS),
}) | _PLACE_FIELDS | _ORIGIN_FIELDS


def _date_values(prefix: str, value: date) -> dict[str, str]:
    """Site date encodings; monthyear0 is a zero-based month (00=January) followed by YYYY."""
    return {
        f"{prefix}_ymd": value.strftime("%Y%m%d"),
        f"{prefix}_dmy_dash": value.strftime("%d-%m-%Y"),
        f"{prefix}_dmy_slash": value.strftime("%d/%m/%Y"),
        f"{prefix}_mdy_slash": value.strftime("%m/%d/%Y"),
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
        places[city_key(city)] = {k: v.strip() for k, v in ids.items()}
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
    """Validate deep links and checkpoints.

    Checkpoint patterns use re.search against the full URL, case-insensitively.
    Beyond patterns are forbidden navigation boundaries, not success evidence.
    """
    if not isinstance(raw, Mapping) or raw.get("kind") not in KINDS:
        raise PolicyError(f"{entry_id}: invalid adapter kind")
    mode = raw.get("mode")
    checkpoint = raw.get("checkpoint")
    if "checkpoint" in raw:
        if not isinstance(checkpoint, Mapping):
            raise PolicyError(f"{entry_id}: checkpoint must be an object")
        for field in ("url_patterns", "beyond_patterns"):
            patterns = checkpoint.get(field)
            if not isinstance(patterns, list) or not patterns or not all(
                isinstance(p, str) and p.strip() for p in patterns
            ):
                raise PolicyError(f"{entry_id}: invalid checkpoint {field}")
            try:
                for pattern in patterns:
                    re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise PolicyError(f"{entry_id}: invalid checkpoint regex") from exc
        checkpoint = {key: list(checkpoint[key]) for key in ("url_patterns", "beyond_patterns")}
    traveler_counts = raw.get("traveler_counts")
    if traveler_counts is not None and (
        not isinstance(traveler_counts, list) or not traveler_counts
        or any(type(n) is not int or n < 1 for n in traveler_counts)
    ):
        raise PolicyError(f"{entry_id}: traveler_counts must be non-empty positive integers")
    if mode is not None and mode not in ("rail", "flight", "bus", "hotel", "registration"):
        raise PolicyError(f"{entry_id}: invalid adapter mode")
    template = raw.get("url_template")
    if not isinstance(template, str):
        raise PolicyError(f"{entry_id}: adapter url_template is required")
    try:
        used = set()
        for _, field, spec, conversion in Formatter().parse(template):
            if field is not None:
                if field not in _TEMPLATE_FIELDS or spec or conversion is not None:
                    raise ValueError("invalid field")
                used.add(field)
        sample = template.format(**{f: "X" for f in _TEMPLATE_FIELDS})
    except (KeyError, IndexError, ValueError) as exc:
        raise PolicyError(f"{entry_id}: malformed placeholder") from exc
    platform_hosts = []
    if raw["kind"] == "registration":
        hosts = raw.get("platform_hosts", [])
        if not isinstance(hosts, list):
            raise PolicyError(f"{entry_id}: platform_hosts must be a list")
        platform_hosts = [_host(h) for h in hosts]
    before, after = urlsplit(template), urlsplit(sample)
    if (
        before.scheme != "https" or before.hostname not in scope_hosts | set(platform_hosts)
        or (before.netloc, before.path) != (after.netloc, after.path)
    ):
        raise PolicyError(f"{entry_id}: url_template must be https on a reviewed host, "
                          "with placeholders only in the query or fragment")
    for key in ("success_evidence", "blocked_evidence"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise PolicyError(f"{entry_id}: adapter {key} is required")
    places = _places(raw.get("places"), entry_id, _PLACE_FIELDS)
    origin_places = _places(raw.get("origin_places"), entry_id, _ORIGIN_FIELDS)
    if (used & (_PLACE_FIELDS - {"city_query"}) and not places
            or used & (_ORIGIN_FIELDS - {"origin_city_query"}) and not origin_places):
        raise PolicyError(f"{entry_id}: url_template uses place IDs but adapter has none")
    race_match = None
    if raw["kind"] == "registration":
        race_match = raw.get("race_match")
        if not isinstance(race_match, Mapping):
            raise PolicyError(f"{entry_id}: race_match is required")
        patterns = race_match.get("name_patterns")
        if not isinstance(patterns, list) or not patterns:
            raise PolicyError(f"{entry_id}: name_patterns must be non-empty")
        try:
            if not all(isinstance(p, str) and p.strip() for p in patterns):
                raise ValueError("empty pattern")
            for pattern in patterns:
                re.compile(pattern, re.IGNORECASE)
        except (ValueError, re.error) as exc:
            raise PolicyError(f"{entry_id}: invalid race name pattern") from exc
        race_match = {"name_patterns": patterns,
                      "countries": _codes(race_match.get("countries"), "race_match.countries")}
    return {
        "kind": raw["kind"],
        "checkpoint": checkpoint,
        "mode": mode,
        "traveler_counts": traveler_counts,
        "race_match": race_match,
        "platform_hosts": platform_hosts,
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
    decisions = {}
    for entry in parsed:
        for scope in entry["scopes"]:
            key = (scope["host"], scope["path_prefix"])
            if key in decisions and decisions[key] != entry["automation"]:
                raise PolicyError("conflicting automation decisions for identical scope")
            decisions[key] = entry["automation"]
    registration_hosts = {
        s["host"] for e in parsed if "registration" in e["purposes"]
        and e["automation"] in ("allowed_read_only", "allowed_owner_rule") for s in e["scopes"]
    }
    for entry in parsed:
        for adapter in entry["adapters"]:
            if not set(adapter["platform_hosts"]) <= registration_hosts:
                raise PolicyError("registration platform host lacks an allowed registration policy")
    return parsed


@lru_cache(maxsize=4)
def _load(files: tuple[tuple[str, int], ...]) -> tuple[dict[str, Any], ...]:
    try:
        documents = [json.loads(Path(path).read_text(encoding="utf-8")) for path, _ in files]
        return tuple(_merge_registries(documents))
    except (ValueError, TypeError) as exc:
        raise PolicyError("malformed registry document") from exc


def load_registry(
    path: Path | str = REGISTRY_PATH, fragments_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    path = Path(path)
    directory = Path(fragments_dir) if fragments_dir is not None else path.parent / "site-policy.d"
    paths = [path, *sorted(directory.glob("*.json"))]
    return list(_load(tuple((str(p.resolve()), p.stat().st_mtime_ns) for p in paths)))


def _merge_registries(documents: Sequence[Any]) -> list[dict[str, Any]]:
    entries = []
    for document in documents:
        if (not isinstance(document, Mapping) or document.get("schema_version") != 1
                or not isinstance(document.get("entries"), list)):
            raise PolicyError("malformed registry document")
        entries.extend(document["entries"])
    return parse_registry({"schema_version": 1, "entries": entries})


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
    if isinstance(registry, (list, tuple)):
        return _merge_registries(registry)
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
    "freiburg": "DE", "freiburg im breisgau": "DE", "köln": "DE", "cologne": "DE",
    "basel": "CH", "bâle": "CH", "lausanne": "CH", "genf": "CH", "ginevra": "CH",
    "lucerne": "CH", "luzern": "CH", "interlaken": "CH", "lugano": "CH", "berne": "CH",
    "brussel": "BE", "antwerp": "BE", "anvers": "BE", "ghent": "BE", "gand": "BE",
    "valència": "ES", "sevilla": "ES", "bilbao": "ES", "malaga": "ES",
    "bologna": "IT", "florence": "IT", "firenze": "IT", "venice": "IT", "venezia": "IT",
    "naples": "IT", "napoli": "IT", "strasbourg": "FR", "bordeaux": "FR", "toulouse": "FR",
    "nantes": "FR", "montpellier": "FR", "rotterdam": "NL", "salzburg": "AT",
    "innsbruck": "AT", "prague": "CZ", "budapest": "HU", "copenhagen": "DK",
    "dublin": "IE", "athens": "GR",
    "den haag": "NL", "savognin": "CH", "grindelwald": "CH", "sierre": "CH",
    "birmingham": "GB",
    "stoos": "CH", "morschach": "CH", "chur": "CH",
}


def country_code(value: Any) -> str | None:
    """ISO code for an English/French/local country name or a 2-letter code, else None."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if len(text) == 2 and text.isalpha():
        return text.upper()
    return _COUNTRY_CODES.get(text.casefold())


def _fold(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.strip().casefold())
                   if not unicodedata.combining(c))


_CITY_ALIASES = {
    _fold(alias): canonical
    for canonical, aliases in {
        "Amsterdam": ("Amsterdam", "Amsterdam-Zuidoost", "Bijlmer"),
        "Den Haag": ("Den Haag", "The Hague", "'s-Gravenhage"),
        "Geneva": ("Geneva", "Genève", "Genf", "Ginevra"),
        "Lisbon": ("Lisbon", "Lisboa", "Lisbonne"),
        "Milan": ("Milan", "Milano"), "Seville": ("Seville", "Sevilla"),
        "Valencia": ("Valencia", "València"), "Zurich": ("Zurich", "Zürich"),
        "Brussels": ("Brussels", "Bruxelles", "Brussel"),
        "Turin": ("Turin", "Torino"), "Barcelona": ("Barcelona", "Barcelone"),
    }.items() for alias in aliases
}


def city_name(value: str) -> str:
    """Canonical lookup/search city; never rewrites expected.city."""
    return _CITY_ALIASES.get(_fold(value), value.strip())


def city_key(value: str) -> str:
    return _fold(city_name(value))


def gateway_city(via: str) -> str:
    """Extract a city from a reviewed via label, including station/transfer notes."""
    for city in sorted(_CITY_COUNTRIES, key=len, reverse=True):
        if _fold(via) == _fold(city) or _fold(via).startswith(_fold(city) + " "):
            return city_name(city).title() if city_name(city).islower() else city_name(city)
    return via


def city_country(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return {city_key(k): v for k, v in _CITY_COUNTRIES.items()}.get(city_key(value))


_HOTEL_GATEWAYS = {
    "stoos": "Lucerne", "morschach": "Lucerne", "savognin": "Chur",
    "grindelwald": "Interlaken",
}


def hotel_search_city(expected: Mapping[str, Any]) -> str:
    """Reviewed regional bases, not promises of inventory or an included local transfer."""
    city = city_name(str(expected.get("city") or ""))
    if country_code(expected.get("country")) == "CH":
        return _HOTEL_GATEWAYS.get(city_key(city), city)
    return city


def task_checkpoint(adapter: Mapping[str, Any]) -> dict[str, list[str]]:
    """Legacy adapters without checkpoints cannot claim a URL-based ready boundary."""
    checkpoint = adapter.get("checkpoint") or {
        "url_patterns": [r"(?!)"],
        "beyond_patterns": [r"guest[-_/ ]?(?:details|info)|passenger|/pax|payment|/pay"],
    }
    return {key: list(value) for key, value in checkpoint.items()}


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
    today: date | None = None, registry: Any = None, modes: Sequence[str] | None = None,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """First reviewed deep-link adapter whose filled URL passes evaluate_url, else ValueError."""
    return select_adapters(
        kind, expected, origin_country=origin_country, today=today, registry=registry,
        modes=modes,
    )[0]


def select_adapters(
    kind: str, expected: Mapping[str, Any], *, origin_country: str | None = None,
    today: date | None = None, registry: Any = None, modes: Sequence[str] | None = None,
) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
    """Up to three ordered, distinct reviewed policies, including the primary choice."""
    destination = country_code(expected.get("country"))
    if destination is None:
        raise ValueError("unknown destination country")
    try:
        entries = _registry(registry)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("site-policy registry unavailable or invalid") from exc
    reasons = []
    selected = []
    policies = set()
    for _, adapter, url, decision in _candidates(
        kind, expected, entries, origin_country=origin_country, today=today,
        registry=registry, modes=modes, reasons=reasons,
    ):
        if decision["policy_id"] not in policies:
            selected.append((adapter, url, decision))
            policies.add(decision["policy_id"])
        if len(selected) == 3:
            break
    if selected:
        return selected
    detail = "; ".join(reasons) or "no reviewed adapter covers this route/destination"
    raise ValueError(f"no policy-reviewed {kind} site for this trip ({detail})")


def _candidates(
    kind, expected, entries, *, origin_country=None, today=None, registry=None,
    modes=None, reasons=None, partial=False,
):
    reasons = reasons if reasons is not None else []
    destination = country_code(expected.get("country"))
    values = {
        k: str(expected.get(k) or "") for k in _TEMPLATE_FIELDS
    }
    values["city"] = hotel_search_city(expected) if kind == "hotel" else city_name(values["city"])
    values["origin_city"] = city_name(values["origin_city"])
    values["city_query"] = values["city"]
    values["origin_city_query"] = values["origin_city"]
    try:
        values |= _date_values("arrival", _iso(expected.get("arrival_date"), "arrival_date"))
        values |= _date_values("departure", _iso(expected.get("departure_date"), "departure_date"))
    except ValueError:
        pass
    city = city_key(values["city"])
    origin = city_key(values["origin_city"])
    candidates = [(e, a) for e in entries for a in e["adapters"]]
    if modes is not None:
        candidates = [(e, a) for mode in [*dict.fromkeys(modes), None]
                      for e, a in candidates if a["mode"] == mode]
    for entry, adapter in candidates:
        if adapter["kind"] != kind:
            continue
        if (adapter["traveler_counts"] is not None
                and expected.get("travelers") not in adapter["traveler_counts"]):
            reasons.append(f"{entry['id']}: party size not reviewed")
            continue
        if adapter["destination_countries"] is not None and (
            destination not in adapter["destination_countries"]
        ) and not (partial and expected.get("country") is None):
            continue
        if adapter["origin_countries"] is not None and (
            origin_country not in adapter["origin_countries"]
        ) and not (partial and expected.get("origin_city") is None):
            continue
        if adapter["race_match"] is not None:
            match = adapter["race_match"]
            if not partial and not any(
                re.search(p, str(expected.get("race_name") or ""), re.IGNORECASE)
                for p in match["name_patterns"]
            ):
                reasons.append(f"{entry['id']}: race name does not match")
                continue
            if (match["countries"] is not None and destination not in match["countries"]
                    and not (partial and expected.get("country") is None)):
                reasons.append(f"{entry['id']}: race country does not match")
                continue
            if any(not any(
                evaluate_url(f"https://{host}{scope['path_prefix']}", "registration",
                             today=today, registry=registry)["allowed"]
                for platform in entries
                if "registration" in platform["purposes"]
                and platform["automation"] in ("allowed_read_only", "allowed_owner_rule")
                for scope in platform["scopes"] if scope["host"] == host
            ) for host in adapter["platform_hosts"]):
                reasons.append(f"{entry['id']}: registration platform unavailable or expired")
                continue
        filled = dict(values)
        missing = False
        for key, table, fields, fallback, label in (
            (city, adapter["places"], _PLACE_FIELDS, "city_query", "city"),
            (origin, adapter["origin_places"], _ORIGIN_FIELDS, "origin_city_query", "origin"),
        ):
            required = adapter["uses"] & (fields - {fallback})
            lookup = table.get(key, {})
            if partial and not key and required and table:
                lookup = next((row for row in table.values() if required <= row.keys()), {})
            if not required <= lookup.keys():
                reasons.append(f"{entry['id']}: no reviewed place IDs for this {label}")
                missing = True
                break
            filled |= lookup
        if missing:
            continue
        url = adapter["url_template"].format(
            **{k: quote(v, safe="") for k, v in filled.items()},
        )
        decision = evaluate_url(url, kind, today=today, registry=registry)
        if decision["allowed"]:
            yield entry, adapter, url, decision
        else:
            reasons.append(f"{entry['id']}: {decision['reason']}")


def coverage(
    kind, *, country=None, city=None, origin_city=None, today=None, registry=None,
) -> dict[str, Any]:
    """Return reviewed adapter coverage without starting a provider; malformed input fails closed."""
    empty = {"covered": False, "policy_ids": []}
    try:
        if kind not in KINDS or any(
            value is not None and (not isinstance(value, str) or not value.strip())
            for value in (country, city, origin_city)
        ):
            return empty
        if country is not None and country_code(country) is None:
            return empty
        today = today or datetime.now(UTC).date()
        entries = _registry(registry)
        expected = {
            "country": country, "city": city, "origin_city": origin_city,
            "arrival_date": (today + timedelta(days=30)).isoformat(),
            "departure_date": (today + timedelta(days=32)).isoformat(), "travelers": 1,
        }
        ids = {e["id"] for e, _, _, _ in _candidates(
            kind, expected, entries, origin_country=city_country(origin_city), today=today,
            registry=registry, partial=True,
        )}
        policy_ids = [e["id"] for e in entries if e["id"] in ids]
        return {"covered": bool(policy_ids), "policy_ids": policy_ids}
    except Exception:  # noqa: BLE001
        return empty
