"""Remove contact details and credentials from provider-facing evidence."""

import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

_SENSITIVE_PARAM = re.compile(r"token|session|sid|auth|key|signature|email", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_KEY = re.compile(
    r"\b(?:sk[-_]|hai[-_]|linkup[-_]|gladia[-_])[A-Za-z0-9_-]{8,}"
    r"|\bBearer\s+[^\s,;\"']+"
    r"|\b[A-Za-z0-9_-]{32,}\b",
    re.IGNORECASE,
)
_ASSIGNED_KEY = re.compile(
    r"\b(?:api[_-]?key|access[_-]?token|secret|authorization)\s*[:=]\s*[\"']?[^\s,;\"']+",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_PRIVATE_PATH = re.compile(
    r"(?:tokens?|sessions?|sid|auth|api[-_]?key|signature|email|jsessionid)(?:[=:;].*)?",
    re.IGNORECASE,
)
_OPAQUE_PATH = re.compile(r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]{24,}|[a-fA-F0-9]{24,}")


def scrub_url(url: str | None) -> str | None:
    """Return a public HTTP(S) URL without credentials or session parameters."""
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return None
        host = parts.hostname
        if (host == "hcompany.ai" or host.endswith(".hcompany.ai")) and (
            host not in {"agp.eu.hcompany.ai", "agp.hcompany.ai"} or not re.fullmatch(
                r"/share/api/v1/trajectories/[^/]+/?", parts.path,
            )
        ):
            return None
        if ":" in host:
            host = f"[{host}]"
        netloc = host + (f":{parts.port}" if parts.port else "")
        path = re.sub(r";jsessionid=[^/;?]*", "", parts.path, flags=re.IGNORECASE)
        if host not in {"agp.eu.hcompany.ai", "agp.hcompany.ai"}:
            for segment in unquote(path).split("/"):
                if _PRIVATE_PATH.fullmatch(segment) or _OPAQUE_PATH.fullmatch(segment) or (
                    _EMAIL.search(segment) or re.match(r"(?:sk|hai|linkup|gladia)[-_]", segment)
                ):
                    return None
        query = urlencode([
            (name, value) for name, value in parse_qsl(parts.query, keep_blank_values=True)
            if not _SENSITIVE_PARAM.search(name)
            and not _EMAIL.search(value) and not _KEY.search(value)
            and (not _PHONE.search(value) or _DATE.fullmatch(value))
        ])
        return urlunsplit((parts.scheme, netloc, path, query, ""))
    except (ValueError, UnicodeError):
        return None


def scrub_text(text: str | None) -> str:
    """Scrub embedded URLs before redacting contact details and key-like strings."""
    value = str(text or "")
    value = _URL.sub(lambda match: scrub_url(match.group()) or "[private URL]", value)
    value = _EMAIL.sub("[redacted email]", value)
    value = _PHONE.sub(
        lambda match: match.group() if _DATE.fullmatch(match.group()) else "[redacted phone]",
        value,
    )
    value = _ASSIGNED_KEY.sub("[redacted key]", value)
    return _KEY.sub("[redacted key]", value)
