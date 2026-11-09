"""Remove contact details and credentials from provider-facing evidence."""

import re
from urllib.parse import parse_qsl, quote, quote_plus, unquote, urlencode, urlsplit, urlunsplit

_SENSITIVE_PARAM = re.compile(
    r"token|session|sid|auth|key|signature|email|password|passwd|card|cvv|cvc|iban|phone|contact",
    re.IGNORECASE,
)
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]){11,30}\b", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_FINANCIAL = re.compile(
    r"\b(?:cvv|cvc|expiry|expiration|card number|iban)\s*[:=]?\s*[\w /-]+", re.IGNORECASE,
)
_EMAIL = re.compile(r"[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
_DATE = re.compile(
    r"\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"(?:[-T](?:[01]\d|2[0-3])[-:][0-5]\d(?:[-:][0-5]\d)?)?"
)
_BEARER = re.compile(r"\bBearer\s+[^\s,;\"']+", re.IGNORECASE)
_KEY_PREFIX = re.compile(r"\b(?:sk|hai|linkup|gladia)[-_][A-Za-z0-9_-]+", re.IGNORECASE)
_KEY = re.compile(
    _KEY_PREFIX.pattern + "|" + _BEARER.pattern +
    r"|\b[A-Za-z0-9_-]{32,}\b",
    re.IGNORECASE,
)
_ASSIGNED_KEY = re.compile(
    r"(?<![\w?&])(?:api[_-]?key|access[_-]?token|token|password|passwd|secret|authorization)"
    r"\s*[:=]\s*[\"']?[^\s,;\"']+",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_PRIVATE_PATH = re.compile(
    r"(?:tokens?|sessions?|sid|auth|api[-_]?key|signature|email|jsessionid)(?:[=:;].*)?",
    re.IGNORECASE,
)
_OPAQUE_PATH = re.compile(r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{24,}|[a-fA-F0-9]{24,}")
_PUBLIC_SLUG = re.compile(r"[A-Za-z]{1,23}(?:[-_](?:[A-Za-z]{1,23}|\d{1,20})){2,}")
_OMIO_RESULT = re.compile(
    r"/links/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _njuko_public_id(host, segments, index):
    if host not in {"in.njuko.com", "www.njuko.net", "njuko.net", "njuko.com"} and not (
        re.fullmatch(r"(?:[a-z0-9-]+\.)*[a-z0-9]+(?:-[a-z0-9]+)*-registrations\.com", host)
    ):
        return False
    segment = segments[index]
    event = re.fullmatch(r"([a-z][a-z0-9-]*)-20\d{2}-?([12]\d{12})", segment, re.IGNORECASE)
    return bool((event and scrub_text(event[1]) == event[1]) or (
        index > 0 and segments[index - 1] == "w"
        and re.fullmatch(r"[a-f0-9]{24,64}", segment, re.IGNORECASE)
    ))


def scrub_url(url: str | None) -> str | None:
    """Return a public HTTP(S) URL without credentials or session parameters."""
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return None
        host = parts.hostname
        if host == "hcompany.ai" or host.endswith(".hcompany.ai"):
            return None
        if ":" in host:
            host = f"[{host}]"
        netloc = host + (f":{parts.port}" if parts.port else "")
        path = re.sub(r";jsessionid=[^/;?]*", "", parts.path, flags=re.IGNORECASE)
        omio_result = host in {
            "omio.com", "www.omio.com", "omio.fr", "www.omio.fr", "omio.de", "www.omio.de",
        } and _OMIO_RESULT.fullmatch(path)
        if host not in {"agp.eu.hcompany.ai", "agp.hcompany.ai"}:
            segments = unquote(path).split("/")
            for index, segment in enumerate(segments):
                if _njuko_public_id(host, segments, index) or (omio_result and index == 2):
                    continue
                if _PRIVATE_PATH.fullmatch(segment) or (
                    _OPAQUE_PATH.fullmatch(segment) and not _PUBLIC_SLUG.fullmatch(segment)
                ) or (
                    _EMAIL.search(segment) or _KEY_PREFIX.search(segment)
                ) or any(
                    not number.isdecimal() and not _DATE.fullmatch(number)
                    for number in _PHONE.findall(segment)
                ):
                    return None
        query = urlencode([
            (name, value) for name, value in parse_qsl(parts.query, keep_blank_values=True)
            if not _SENSITIVE_PARAM.search(name)
            and not re.fullmatch(r"utm_.*|gclid|fbclid|cm_mmc|icdv|tracking", name, re.IGNORECASE)
            and not _EMAIL.search(value) and not _KEY.search(value)
            and not _IBAN.search(value) and not _JWT.search(value)
            and not _FINANCIAL.search(value) and not _ASSIGNED_KEY.search(value)
            and (not _PHONE.search(value) or _DATE.fullmatch(value))
        ])
        return urlunsplit((parts.scheme, netloc, path, query, ""))
    except (ValueError, UnicodeError):
        return None


def _scrub_plain_text(value: str) -> str:
    value = _FINANCIAL.sub("[redacted financial]", value)
    value = _IBAN.sub("[redacted financial]", value)
    value = _JWT.sub("[redacted key]", value)
    value = _EMAIL.sub("[redacted email]", value)
    value = _PHONE.sub(
        lambda match: match.group() if _DATE.fullmatch(match.group()) else "[redacted phone]",
        value,
    )
    return _KEY.sub("[redacted key]", value)


def scrub_text(text: str | None) -> str:
    """Scrub URLs separately so public slugs are not mistaken for keys or phones."""
    value = _BEARER.sub("[redacted key]", _ASSIGNED_KEY.sub("[redacted key]", str(text or "")))
    parts = []
    end = 0
    for match in _URL.finditer(value):
        parts.append(_scrub_plain_text(value[end:match.start()]))
        parts.append(scrub_url(match.group()) or "[private URL]")
        end = match.end()
    parts.append(_scrub_plain_text(value[end:]))
    return "".join(parts)


def public_profile_context(value):
    if isinstance(value, dict):
        return set().union(*(public_profile_context(item) for key, item in value.items()
                             if key != "runner_profile"))
    if isinstance(value, (list, tuple)):
        return set().union(*(public_profile_context(item) for item in value))
    return {value.casefold()} if isinstance(value, str) else set()


def scrub_profile(value, profile, skip=None):
    if isinstance(value, dict):
        return {key: scrub_profile(item, profile, skip) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_profile(item, profile, skip) for item in value]
    if not isinstance(value, str):
        return value
    identifying, quasi = set(), set()
    skip = {item.casefold() for item in (skip or set())}
    for key, item in profile.items():
        if isinstance(item, str) and item:
            target = quasi if key in {"gender", "nationality", "city", "country"} else identifying
            if target is quasi and item.casefold() in skip:
                continue
            for variant in (item, item.casefold(), item.upper()):
                target.update((variant, quote(variant, safe=""), quote_plus(variant)))

    def redact(text, variants, boundaries=False):
        for item in sorted(variants, key=len, reverse=True):
            pattern = re.escape(item)
            if boundaries:
                pattern = r"(?<!\w)" + pattern + r"(?!\w)"
            text = re.sub(pattern, "[redacted profile]", text, flags=re.IGNORECASE)
        return text

    def clean_url(url):
        return None if redact(url, identifying) != url else url

    if re.fullmatch(_URL, value):
        return clean_url(value)
    parts, end = [], 0
    for match in _URL.finditer(value):
        parts.append(redact(redact(value[end:match.start()], identifying), quasi, True))
        parts.append(clean_url(match.group()) or "[private URL]")
        end = match.end()
    parts.append(redact(redact(value[end:], identifying), quasi, True))
    return "".join(parts)
