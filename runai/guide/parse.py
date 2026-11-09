import re
import unicodedata
from datetime import date

from pydantic import Field

from runai.agents.scrub import scrub_text

from .types import Model


def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c)
    )


COUNTRIES = {
    "Italy": "italy italie italia",
    "France": "france",
    "Spain": "spain espagne espana",
    "Portugal": "portugal",
    "Switzerland": "switzerland suisse schweiz",
    "Germany": "germany allemagne deutschland",
    "Belgium": "belgium belgique",
    "Netherlands": "netherlands pays-bas hollande",
    "Austria": "austria autriche",
    "United Kingdom": "united kingdom royaume-uni england angleterre uk",
    "Ireland": "ireland irlande",
    "Denmark": "denmark danemark",
    "Sweden": "sweden suede",
    "Norway": "norway norvege",
    "Finland": "finland finlande",
    "Iceland": "iceland islande",
    "Poland": "poland pologne",
    "Czechia": "czechia tchequie",
    "Slovakia": "slovakia slovaquie",
    "Hungary": "hungary hongrie",
    "Romania": "romania roumanie",
    "Bulgaria": "bulgaria bulgarie",
    "Greece": "greece grece",
    "Croatia": "croatia croatie",
    "Slovenia": "slovenia slovenie",
    "Estonia": "estonia estonie",
    "Latvia": "latvia lettonie",
    "Lithuania": "lithuania lituanie",
    "Luxembourg": "luxembourg",
    "Malta": "malta malte",
    "Cyprus": "cyprus chypre",
}
CITY_GROUPS = {
    "Italy": ["Milan/Milano", "Rome/Roma", "Florence/Firenze", "Venice/Venise", "Turin/Torino"],
    "France": ["Paris", "Lyon", "Bordeaux", "Nice", "Marseille", "Chamonix"],
    "Portugal": ["Lisbon/Lisbonne/Lisboa", "Porto"],
    "Spain": ["Madrid", "Barcelona/Barcelone", "Valencia/Valence", "Seville/Sevilla"],
    "Germany": ["Berlin", "Munich", "Frankfurt/Francfort", "Hamburg/Hambourg"],
    "United Kingdom": ["London/Londres"],
    "Netherlands": ["Amsterdam", "Rotterdam"],
    "Belgium": ["Brussels/Bruxelles"],
    "Switzerland": ["Geneva/Geneve", "Zurich", "Lausanne", "Zermatt", "Interlaken"],
    "Austria": ["Vienna/Vienne"],
    "Czechia": ["Prague"],
    "Denmark": ["Copenhagen/Copenhague"],
    "Sweden": ["Stockholm"],
    "Norway": ["Oslo"],
    "Ireland": ["Dublin"],
    "Greece": ["Athens/Athenes"],
}
CITIES = {
    alias: (group.split("/")[0], country)
    for country, groups in CITY_GROUPS.items()
    for group in groups
    for alias in normalize(group).split("/")
}
MONTHS = [
    "january janvier",
    "february fevrier",
    "march mars",
    "april avril",
    "may mai",
    "june juin",
    "july juillet",
    "august aout",
    "september septembre",
    "october octobre",
    "november novembre",
    "december decembre",
]


def country_name(value: str | None) -> str | None:
    """Canonical English country name for an English/French/local name or ISO2 code."""
    if not value:
        return None
    text = normalize(value).strip(" .")
    codes = {"it": "Italy", "fr": "France", "es": "Spain", "pt": "Portugal", "ch": "Switzerland",
             "de": "Germany", "be": "Belgium", "nl": "Netherlands", "at": "Austria",
             "gb": "United Kingdom", "uk": "United Kingdom", "ie": "Ireland"}
    if text in codes:
        return codes[text]
    return next((country for country, aliases in COUNTRIES.items()
                 if text in {normalize(country), *aliases.split()}), None)


def contains(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def bare_city(text: str) -> str | None:
    match = CITIES.get(normalize(text).strip(" .!"))
    return match[0] if match else None


FR_CUES = (
    r"\b(?P<fr>le|la|les|un|une|en|au|aux|des|du|de|depuis|pour|avec|et|ou|mais|pas|oui|non|"
    r"printemps|ete|automne|hiver|nuits?|plutot|finalement|bonjour|merci|je|tu|peu|veux|voudrais|"
    r"courir|cherche|quel|quelle|quoi|payer|creer|accepter|raconte|salut|parle|sans|"
    r"ignore(?=\s+les))\b"
)
EN_CUES = (
    r"\b(?P<en>the|in|from|next|this|summer|spring|winter|autumn|fall|half|nights?|actually|"
    r"instead|i|i'?m|want|would|like|run|looking|for|and|with|without|please|thanks|tell|what|"
    r"which|hello|whatever|you|my|to|of|yes|but|ignore(?=\s+previous)|pay|create|accept|submit|"
    r"bypass)\b"
)


class Intent(Model):
    distance: str | None = None
    year: int | None = None
    months: list[str] = Field(default_factory=list)
    country: str | None = None
    city: str | None = None
    named: bool = False
    origin_city: str | None = None
    nights: int | None = None
    budget_eur: int | None = None
    travelers: int | None = None
    correction: bool = False
    lang: str = "fr"
    fr_cues: int = 0
    en_cues: int = 0
    problem: str | None = None
    problems: list[str] = Field(default_factory=list)
    deferred: bool = False
    switch_language: str | None = None


def parse_intent(text: str, *, today: date) -> Intent:
    text = scrub_text(text)
    t = normalize(text)
    for wrong, right in {
        "marathn": "marathon", "marat+h?o+n+": "marathon", "itali": "italie",
        "printemp": "printemps", "semi+": "semi", "espagn+e*": "espagne", "spai+n+": "spain",
        "lisbone": "lisbonne", "suise": "suisse", "trai+l+": "trail",
    }.items():
        t = re.sub(r"\b" + wrong + r"\b", right, t)
    cues = list(re.finditer(FR_CUES + "|" + EN_CUES, t))
    fr_cues = sum(1 for cue in cues if cue.lastgroup == "fr")
    en_cues = len(cues) - fr_cues
    if en_cues != fr_cues:
        lang = "en" if en_cues > fr_cues else "fr"
    else:
        lang = "en" if cues and cues[0].lastgroup == "en" else "fr"
    result = Intent(lang=lang, fr_cues=fr_cues, en_cues=en_cues)
    result.correction = bool(re.search(r"\b(plutot|actually|instead)\b", t))
    result.deferred = bool(re.search(
        r"peu importe|je (?:ne )?sais pas|tu en penses quoi|whatever|i don.?t know|"
        r"you choose|what do you think|comme tu veux|a toi de choisir", t,
    ))
    if re.search(r"(?:in english|en anglais)(?: please| s.il te plait)?", t):
        result.switch_language = "en"
    elif re.search(r"(?:en francais|in french)", t):
        result.switch_language = "fr"
    for pattern, distance in [
        (r"\b(ultra)\b", "ultra"),
        (r"\btrail\b", "trail"),
        (r"\b(semi|half)\b", "half"),
        (r"\b10\s?k(m)?\b", "10k"),
        (r"\bmarathon\b", "marathon"),
    ]:
        if re.search(pattern, t):
            result.distance = distance
            break
    origin = re.search(r"\b(?:depuis|from|je pars de)\s+([\w -]+)", t)
    destination_text = t
    if origin:
        for alias, (city, _) in CITIES.items():
            if re.match(re.escape(alias) + r"(?!\w)", origin[1]):
                result.origin_city = city
                destination_text = t[: origin.start()] + t[origin.start(1) + len(alias) :]
                break
    for country, aliases in COUNTRIES.items():
        if any(
            contains(destination_text, alias) for alias in [normalize(country), *aliases.split()]
        ):
            result.country = country
    for alias, (city, country) in CITIES.items():
        if result.country and result.country != country:
            continue
        if alias == "nice" and not (
            re.search(r"\b(?:in|to|de|at)\s+nice\b", destination_text)
            or re.search(r"\bà\s+nice\b", text, re.IGNORECASE)
            or re.search(r"\ba\s+Nice\b", text)
            or re.search(r"\bNice\s+(?:marathon|trail|half|semi|10k|ultra)\b", text)
            or re.search(r"\b(?:marathon|trail|half|semi|10k|ultra)\s+Nice\b", text)
        ):
            continue
        if contains(destination_text, alias):
            result.city, result.country = city, country
            result.named = result.distance is not None
            break
    selected = []
    season = False
    season_count = 0
    for month, aliases in enumerate(MONTHS, 1):
        if any(contains(t, alias) for alias in aliases.split()):
            selected.append(month)
    for aliases, months in [
        ("printemps spring", [3, 4, 5]),
        ("ete summer", [6, 7, 8]),
        ("automne autumn fall", [9, 10, 11]),
        ("hiver winter", [12, 1, 2]),
    ]:
        if any(contains(t, alias) for alias in aliases.split()):
            selected = months
            season = True
            season_count += 1
    explicit = next(
        (
            match
            for match in re.finditer(r"\b((?:19|20)\d{2})\b", t)
            if not re.match(
                r"\s*(?:€|euros?\b|eur\b|nuits?\b|nights?\b|personnes?\b|people\b)",
                t[match.end() :],
            )
            and not re.search(r"\bbudget\s*(?:de\s*)?$", t[: match.start()])
            and (
                result.distance
                or result.city
                or result.country
                or selected
                or re.search(r"\b(?:edition|year|annee|en|in|pour|for)\s*$", t[: match.start()])
            )
        ),
        None,
    )
    if explicit:
        result.year = int(explicit[1])
    if selected:
        year = int(explicit[1]) if explicit else today.year
        if season and today.month in selected and year == today.year and not contains(t, "next"):
            selected = selected[selected.index(today.month) :]
        if not explicit and (max(selected) < today.month or contains(t, "next")):
            year += 1
        result.months = [f"{year + (1 if m < selected[0] else 0):04d}-{m:02d}" for m in selected]
    for field, pattern in [
        ("nights", r"(?<!\w)(-?\d+)\s*(?:nuits?|nights?)\b"),
        ("budget_eur", r"(?<!\w)(-?\d+)\s*(?:euros?|eur\b|€)"),
        ("travelers", r"(?<!\w)(-?\d+)\s*(?:personnes?|people|travelers?)\b"),
    ]:
        match = re.search(pattern, t)
        if match:
            setattr(result, field, int(match[1]))
    budget = re.search(r"\bbudget\s+(-?\d+)", t)
    travelers = re.search(r"\ba\s+(\d+)\b", t)
    if budget:
        result.budget_eur = int(budget[1])
    if travelers:
        result.travelers = int(travelers[1])
    countries = {
        country for country, aliases in COUNTRIES.items()
        if any(contains(destination_text, alias) for alias in [normalize(country), *aliases.split()])
    }
    cities = {
        city for alias, (city, _) in CITIES.items()
        if contains(destination_text, alias) and alias != "nice"
    }
    mismatched_city = any(
        contains(destination_text, alias) and country not in countries
        for alias, (_, country) in CITIES.items() if alias != "nice"
    ) if countries else False
    explicit_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", t)
    years = {
        match[0] for match in re.finditer(r"\b(?:19|20)\d{2}\b", t)
        if not re.match(r"\s*(?:€|euros?\b|eur\b|nuits?\b|nights?\b)", t[match.end():])
        and not re.search(r"\bbudget\s*(?:de\s*)?$", t[:match.start()])
    }
    if len(countries) > 1 or len(cities) > 1 or mismatched_city:
        result.problem = "destination_conflict"
    elif len(set(explicit_dates)) > 1 or season_count > 1 or len(years) > 1:
        result.problem = "date_conflict"
    elif explicit_dates:
        try:
            event_day = date.fromisoformat(explicit_dates[0])
            result.problem = "past_date" if event_day < today else "exact_date"
        except ValueError:
            result.problem = "date_conflict"
    elif re.search(r"\b(?:tomorrow|demain)\b", t):
        result.problem = "tomorrow"
    elif result.nights is not None and not 1 <= result.nights <= 14:
        result.problem = "nights_range"
    elif result.budget_eur is not None and result.budget_eur <= 0:
        result.problem = "budget_range"
    elif result.travelers is not None and result.travelers < 1:
        result.problem = "travelers_range"
    elif result.year and result.year < today.year:
        result.problem = "past_date"
    elif re.search(r"\b(?:free|gratuit|teleport|teleporter|impossible)\b", t):
        result.problem = "unsupported"
    result.problems = list(dict.fromkeys(problem for problem, active in [
        (result.problem, result.problem is not None and result.problem != "exact_date"),
        ("tomorrow", bool(re.search(r"\b(?:tomorrow|demain)\b", t))),
        ("nights_range", result.nights is not None and not 1 <= result.nights <= 14),
        ("budget_range", result.budget_eur is not None and result.budget_eur <= 0),
        ("travelers_range", result.travelers is not None and result.travelers < 1),
    ] if active))
    return result
