import re
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from importlib import import_module
from urllib.parse import urlsplit

from pydantic import ValidationError

from runai.agents.scrub import (
    _ASSIGNED_KEY,
    _DATE,
    _EMAIL,
    _FINANCIAL,
    _IBAN,
    _JWT,
    _KEY_PREFIX,
    _PHONE,
    scrub_text,
    scrub_url,
)

from .fake import FakeDiscovery
from .parse import CITY_GROUPS, bare_city, country_name, named_query, normalize, parse_intent
from .types import GuidedTurn, GuideState, RaceOption, RacePreparation, Suggestion

Discover = Callable[[str, dict], Awaitable[list[dict]]]
DEFAULT_ORIGINS = ["Paris", "Lyon", "Bruxelles", "Genève"]
STANDARD_DISTANCES = [5.0, 10.0, 21.1, 42.195]
_SKIP_CONFIRMATION = re.compile(
    r"(?:skip|without|bypass|sans|saute[rz]?|zappe[rz]?|pas besoin d.?|no need (?:for|to))"
    r"\W+(?:\w+\W+){0,3}(?:la |ma |the |my )?(?:confirm|valid)|"
    r"(?:lance|launch|start|demarre|run)[rz]?\W+(?:\w+\W+){0,2}(?:agents?|tout|everything)"
    r"\W+(?:\w+\W+){0,2}(?:maintenant|now|direct|tout de suite|right away|immediately)|"
    r"(?:ne |don.?t |do not )(?:me )?(?:demande|ask)\w*\W+(?:\w+\W+){0,3}(?:confirm|valid)"
)
_FORBIDDEN_SITE = re.compile(
    r"\bbooking(?:\.com)?\b|\baccor\w*\b|\bibis\b|\bnovotel\b|\bsofitel\b|\bmercure\b|"
    r"\bairbnb\b|\bexpedia\b"
)


class GuideEngine:
    def __init__(self, discover: Discover, *, today: date | None = None):
        self.discover = discover
        self.today = today or date.today()
        if isinstance(discover, FakeDiscovery):
            discover.today = self.today

    def _say(self, state, fr, en):
        return en if state.lang == "en" else fr

    def _display_text(self, state, text):
        names = {"Geneva": "Genève", "Lisbon": "Lisbonne", "Barcelona": "Barcelone",
                 "The Hague": "La Haye", "Brussels": "Bruxelles", "London": "Londres",
                 "Valencia": "Valence", "Italy": "Italie", "Germany": "Allemagne",
                 "Switzerland": "Suisse", "Netherlands": "Pays-Bas", "Spain": "Espagne",
                 "Belgium": "Belgique", "United Kingdom": "Royaume-Uni"}
        pairs = names.items() if state.lang == "fr" else ((v, k) for k, v in names.items())
        for source, target in pairs:
            text = re.sub(r"(?<!\w)" + re.escape(source) + r"(?!\w)", target, text)
        return text

    def _display_race(self, state, race):
        race = race.model_copy(deep=True)
        for field in ("name", "city", "country", "distance_label"):
            if getattr(race, field):
                setattr(race, field, self._display_text(state, getattr(race, field)))
        if race.preparation and race.preparation.origin_city:
            race.preparation.origin_city = self._display_text(state, race.preparation.origin_city)
        return race

    def _chip(self, value, label=None, kind="answer", provenance="suggested_default"):
        return Suggestion(
            id=f"{kind}:{value}",
            value=str(value),
            label=label or str(value),
            kind=kind,
            provenance=provenance,
        )

    def _race_chips(self, state, races=None):
        chips = [
            self._chip(
                r.id,
                f"{r.name} — {r.race_date or self._say(state, 'date à confirmer', 'date to confirm')}"
                + self._access_warning(state, r),
                "choose_race",
                "synthetic" if r.synthetic else "source",
            )
            for r in (state.candidates if races is None else races)
            if not state.draft.race or r.id != state.draft.race.id
        ]
        for chip in chips:
            race = next(r for r in state.candidates if r.id == chip.value)
            if not self._matches_distance(state, race):
                chip.group = self._say(state, "Autre distance", "Another distance")
        return chips

    def _matches_distance(self, state, race):
        distance = state.hints.get("distance")
        target = {"half": 21.1}.get(distance)
        return target is None or race.distance_km is None or abs(race.distance_km - target) < 0.2

    def _access_warning(self, state, race):
        label = self._preparation_label(state, race)
        access = race.registration_access
        if access and (access.account_required is True or access.captcha is True):
            return label + self._say(state, " — compte ou captcha requis : arrêt humain",
                             " — account or captcha required: human handoff")
        if not access or access.account_required is None or access.captcha is None:
            return label
        return label + self._say(state, " — observation d'accès, pas une autorisation",
                         " — access observation, not permission")

    def _preparation_label(self, state, race):
        status = race.preparation.registration if race.preparation else "unknown"
        labels = {
            "sold_out": ("complet (liste d'attente)", "sold out (waitlist)"),
            "not_open": ("inscriptions pas encore ouvertes", "registration not open yet"),
            "closed": ("inscriptions closes", "registration closed"),
            "prohibited": ("préparation interdite", "preparation prohibited"),
            "uncovered": ("inscription non couverte", "registration not covered"),
        }
        return " — " + self._say(state, *labels[status]) if status in labels else ""

    def _prepare_candidates(self, state):
        races = list(state.candidates)
        if state.draft.race and all(race is not state.draft.race for race in races):
            races.append(state.draft.race)
        for race in races:
            origin = state.draft.origin_city or self._origin_choices(race)[0]
            preparation = RacePreparation(origin_city=origin)
            try:
                registration = import_module("runai.agents.registration").registration_coverage
                result = registration(race.model_dump(mode="json", exclude={"preparation"}))
                if isinstance(result, dict):
                    result = result.get("status", result.get("registration"))
                if isinstance(result, str):
                    preparation.registration = RacePreparation(registration=result).registration
            except Exception:  # noqa: BLE001 -- optional coverage fails closed
                preparation.registration = "unknown"
            for kind in ("hotel", "transport"):
                try:
                    coverage = import_module("runai.agents.site_policy").coverage
                    result = coverage(kind, country=race.country, city=race.city,
                                      origin_city=origin)
                    covered = result.get("covered") if isinstance(result, dict) else None
                    if type(covered) is bool:
                        setattr(preparation, kind, covered)
                except Exception:  # noqa: BLE001 -- optional coverage fails closed
                    setattr(preparation, kind, None)
            race.preparation = preparation

    def _preparation_rank(self, state, race):
        p = race.preparation or RacePreparation()
        fully = p.registration == "covered" and p.hotel is True and p.transport is True
        partial = p.registration == "covered" or p.hotel is True or p.transport is True
        return (self._unavailable(race), not self._matches_distance(state, race),
                0 if fully else 1 if partial else 2)

    def _unavailable(self, race):
        return bool(race.preparation and race.preparation.registration in {
            "sold_out", "closed"})

    def _preparation_message(self, state, race):
        p = race.preparation or RacePreparation()
        parts = [(p.registration == "covered", "l'inscription", "registration"),
                 (p.hotel is True, "l'hôtel", "hotel"),
                 (p.transport is True, "le transport", "transport")]
        covered = [self._say(state, fr, en) for ok, fr, en in parts if ok]
        missing = [self._say(state, fr, en) for ok, fr, en in parts if not ok]
        message = self._say(
            state, f" Je peux préparer {', '.join(covered)} pour {race.name}." if covered
            else f" Aucune préparation couverte pour {race.name}.",
            f" I can prepare {', '.join(covered)} for {race.name}." if covered
            else f" No preparation is covered for {race.name}.")
        if missing:
            message += self._say(state, f" Non couverts : {', '.join(missing)}.",
                                 f" Not covered: {', '.join(missing)}.")
        return message

    def _eligible(self, race):
        return bool(race and race.race_date and race.race_date >= self.today
                    and race.date_status == "official"
                    and (race.synthetic or any(scrub_url(url) for url in race.source_urls)))

    def _distance_values(self, label):
        numbers = []
        for match in re.finditer(
            r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s*(?:[-–—/,;]|and|et)\s*"
            r"\d+(?:[.,]\d+)?)*\s*km\b", label, re.IGNORECASE,
        ):
            numbers.extend(float(value.replace(",", "."))
                           for value in re.findall(r"\d+(?:[.,]\d+)?", match[0]))
        return list(dict.fromkeys(value for value in numbers if value > 0))

    def _sourced_distances(self, state):
        race = state.draft.race
        if race:
            return next((item["distances"] for item in state.hints.get("_race_distances", [])
                         if item["race_id"] == race.id), [])
        return []

    def _dedupe_distance(self, race):
        if race.distance_km is not None:
            return (round(race.distance_km, 3),)
        label = normalize(race.distance_label)
        values = self._distance_values(re.sub(r"\bk\b", "km", label))
        if values:
            return tuple(sorted(round(value, 3) for value in values))
        named = {"marathon": 42.195, "half marathon": 21.1, "semi marathon": 21.1}
        if label in named:
            return (named[label],)
        return label or None

    def _pending_distances(self, state):
        race = state.draft.race
        return (self._sourced_distances(state)
                if self._eligible(race) and race.distance_km is None else [])

    def _needs_distance(self, state):
        race = state.draft.race
        return self._eligible(race) and race.distance_km is None

    def _distance_alternatives(self, state):
        return [race for race in state.candidates
                if self._eligible(race) and race.distance_km is not None and race.distance_km > 0
                and (not state.draft.race or race.id != state.draft.race.id)]

    def _turn(self, state, message=None, error=None, *, recommended_distance=None):
        d = state.draft
        ready = bool(
            self._eligible(d.race)
            and d.origin_city
            and d.nights
            and d.budget_eur
            and d.race.distance_km is not None
        )
        question = None
        chips = []
        if self._needs_distance(state):
            sourced = self._pending_distances(state)
            question = (self._say(state, "Quelle distance ?", "Which distance?")
                        if sourced else self._say(
                            state, "Quelle distance souhaites-tu courir ? Distances standard "
                            "en suggestion, à vérifier sur le site officiel.",
                            "Which distance would you like to run? Standard distances as "
                            "suggestions, to check on the official site."))
            if recommended_distance is not None:
                choices, provenance = [recommended_distance], "suggested_default"
            elif sourced:
                choices, provenance = sourced, "source"
            else:
                choices, provenance = STANDARD_DISTANCES, "suggested_default"
            chips = [self._chip(f"{value:g} km", self._distance_label(state, value, provenance),
                                "distance", provenance)
                     for value in choices]
            others = self._race_chips(state, self._distance_alternatives(state))
            for chip in others:
                chip.group = self._say(state, "Autres courses", "Other races")
            chips += others
        elif state.stage == "choose_race":
            question = self._say(state, "Laquelle te tente ?", "Which one catches your eye?")
            chips = self._race_chips(state)
            if not d.race and (
                state.hints.get("retry_count") and not any(self._eligible(r) for r in state.candidates)
                or not any(r.race_date for r in state.candidates)
            ):
                chips += (self._recovery_chips(state) if state.hints.get("retry_count") else
                          [self._chip("retry", self._say(state, "Relancer", "Try again"), "retry")])
            if d.race:
                explanation = self._say(
                    state,
                    "Les sources actuelles ne permettent pas de confirmer la date de cette course ; choisissons une autre option.",
                    "This race's date cannot be confirmed from the current sources; let's try another option.",
                )
                message = (message + " " if message else "") + explanation
                chips += (self._recovery_chips(state) if state.hints.get("retry_count")
                          else [self._chip("retry", self._say(state, "Relancer", "Try again"),
                                           "retry")])
        elif state.stage in {"origin", "nights", "budget"}:
            if state.stage == "origin":
                choices = self._origin_choices(d.race)
                question = self._say(
                    state,
                    "Tu pars d'où ? Je propose d'abord " + choices[0] + ".",
                    "Where are you leaving from? My first suggestion is " + choices[0] + ".",
                )
            elif state.stage == "nights":
                choices = ["2", "1", "3"]
                question = self._say(
                    state,
                    "Combien de nuits te feraient plaisir ?",
                    "How many nights would suit you?",
                )
            else:
                budget = 150 + 150 * d.nights
                choices = [str(budget), str(max(100, budget - 150)), str(budget + 300)]
                question = self._say(
                    state,
                    "Quel budget en euros te conviendrait ?",
                    "What budget in euros feels right?",
                )
            chips = [self._chip(c) for c in choices]
        elif state.stage in {"confirm", "confirmed"}:
            people_fr = "personne" if d.travelers == 1 else "personnes"
            people_en = "traveler" if d.travelers == 1 else "travelers"
            summary = self._say(
                state,
                f"Voilà ton idée de séjour : {d.race.name}, au départ de {d.origin_city}, {d.nights} nuits, budget {d.budget_eur} € pour {d.travelers} {people_fr}, du {d.arrival_date} au {d.departure_date}.",
                f"Here's your trip: {d.race.name}, leaving from {d.origin_city}, {d.nights} nights, budget €{d.budget_eur} for {d.travelers} {people_en}, {d.arrival_date} to {d.departure_date}.",
            )
            message = (message + " " if message else "") + summary
            if any(item["race_id"] == d.race.id
                   for item in state.hints.get("_race_distances", [])):
                message += self._say(
                    state, f" Début de l'événement : {d.race.race_date}.",
                    f" Event start date: {d.race.race_date}.")
            if state.stage == "confirm":
                question = self._say(
                    state,
                    "Ça te va comme point de départ ?",
                    "Does that sound like a good starting point?",
                )
                chips = [self._chip("confirm", self._say(state, "Confirmer", "Confirm"), "confirm")]
                chips += [
                    self._chip(f, self._say(state, fr, en), "edit")
                    for f, fr, en in [
                        ("origin", "Changer le départ", "Change origin"),
                        ("nights", "Changer la durée", "Change nights"),
                        ("budget", "Changer le budget", "Change budget"),
                    ]
                ]
            else:
                message += self._say(
                    state,
                    " C'est confirmé, sans réservation ni paiement.",
                    " Confirmed, without booking or payment.",
                )
        else:
            question = self._say(
                state, "Quelle course te ferait envie ?", "What race would you like to explore?"
            )
            chips = [
                self._chip(v)
                for v in self._say(
                    state,
                    [
                        "Un marathon en Italie au printemps",
                        "Un trail en Suisse cet été",
                        "Le semi de Lisbonne",
                    ],
                    [
                        "A marathon in Italy in spring",
                        "A trail in Switzerland this summer",
                        "Lisbon half marathon",
                    ],
                )
            ]
        if not message:
            options = self._say(
                state,
                [
                    "Super, on construit ça ensemble.",
                    "Avec plaisir, avançons à ton rythme.",
                    "Bien reçu, je t'aide à préciser ton séjour.",
                ],
                [
                    "Lovely, let's put this together.",
                    "Happy to help, let's take it one step at a time.",
                    "Got it, let's shape your trip.",
                ],
            )
            message = options[len(state.history) % len(options)]
        if d.race and d.race.synthetic:
            message += self._say(state, " Dates synthétiques, non vérifiées en direct.",
                                 " Synthetic dates, not live-verified.")
        if d.race:
            message += self._access_warning(state, d.race)
            if self._unavailable(d.race):
                message += self._say(
                    state, " L'agent d'inscription peut seulement atteindre la liste d'attente "
                    "ou la page officielle, pas obtenir une place.",
                    " The registration agent can only reach the waitlist or official page, "
                    "not secure an entry.")
                chips += self._race_chips(state, [r for r in state.candidates
                                                  if not self._unavailable(r)])
            if d.race.distance_km is None and not self._sourced_distances(state):
                message += self._say(state, " Distance inconnue dans les sources.",
                                     " Distance is unknown in the sources.")
        if d.race and d.race.date_status == "unverified":
            message += self._say(
                state, " Attention : date non vérifiée.", " Warning: unverified date."
            )
        message = self._display_text(state, scrub_text(message))
        previous = next((row["text"] for row in reversed(state.history)
                         if row.get("role") == "assistant"), None)
        if message == previous:
            message += self._say(state, " Précisons une autre piste.",
                                 " Let's refine another option.")
        question = self._display_text(state, scrub_text(question)) if question else None
        for chip in chips:
            chip.id += f":turn-{len(state.history)}"
            chip.label = self._display_text(state, scrub_text(chip.label))
            chip.value = (self._scrub_identifier(chip.value) if chip.kind == "choose_race"
                          else scrub_text(chip.value))
        state.pending_suggestions = chips
        state.history.append({"role": "assistant", "text": message})
        display_draft = d.model_copy(deep=True)
        if display_draft.race:
            display_draft.race = self._display_race(state, display_draft.race)
        if display_draft.origin_city:
            display_draft.origin_city = self._display_text(state, display_draft.origin_city)
        return state, GuidedTurn(
            message=message,
            question=question,
            suggestions=chips,
            candidates=[self._display_race(state, r) for r in state.candidates],
            draft=display_draft,
            ready_to_confirm=ready,
            error=error,
            language=state.lang,
        )

    def _distance_label(self, state, value, provenance):
        if provenance == "source":
            return f"{value:g} km"
        name = {21.1: self._say(state, "Semi-marathon", "Half marathon"),
                42.195: "Marathon"}.get(value)
        return f"{name} · {value:g} km" if name else f"{value:g} km"

    def _origin_choices(self, race):
        base = [c for c in DEFAULT_ORIGINS if not race or bare_city(c) != race.city]
        try:
            coverage = getattr(import_module("runai.agents.site_policy"), "coverage", None)
        except ImportError:
            coverage = None
        if not callable(coverage) or not race:
            return base[:4]
        country = country_name(race.country) if race.country else None
        local = [group.split("/")[0] for group in CITY_GROUPS.get(country, [])]
        pool = list(dict.fromkeys(
            c for c in [*base, *local] if bare_city(c) != race.city and c != race.city
        ))

        def covered(city):
            try:
                result = coverage("transport", country=race.country, city=race.city,
                                  origin_city=city, today=self.today)
            except Exception:  # noqa: BLE001 -- coverage is an optional ordering hint
                return False
            return isinstance(result, dict) and result.get("covered") is True

        ranked = [c for c in pool if covered(c)]
        if not ranked:
            return base[:4]
        return list(dict.fromkeys([*ranked, *base]))[:4]

    def _set_language(self, state, intent, typed):
        if not state.history:
            state.lang = intent.lang
        elif typed:
            other = "en" if state.lang == "fr" else "fr"
            other_cues = intent.en_cues if other == "en" else intent.fr_cues
            same_cues = intent.fr_cues if other == "en" else intent.en_cues
            if other_cues >= 2 and (same_cues == 0 or other_cues >= 2 * same_cues + 1):
                state.lang = other
        if intent.switch_language:
            state.lang = intent.switch_language

    def _advance(self, state):
        d = state.draft
        races = [*state.candidates, *([d.race] if d.race else [])]
        if d.origin_city and any(
            not race.preparation or race.preparation.origin_city != d.origin_city for race in races
        ):
            self._prepare_candidates(state)
        if not d.race:
            state.stage = "choose_race" if state.candidates else "discover"
        elif not self._eligible(d.race) or self._needs_distance(state):
            state.stage = "choose_race"
        else:
            if d.nights:
                d.arrival_date = d.race.race_date - timedelta(days=1)
                d.departure_date = d.arrival_date + timedelta(days=d.nights)
                d.provenance.update(arrival_date="source", departure_date="source")
            state.stage = next(
                (
                    stage
                    for stage, field in [
                        ("origin", "origin_city"),
                        ("nights", "nights"),
                        ("budget", "budget_eur"),
                    ]
                    if not getattr(d, field)
                ),
                "confirm",
            )

    def _update(self, state, intent):
        for field in ["origin_city", "nights", "budget_eur", "travelers"]:
            value = getattr(intent, field)
            if value is not None and (field == "origin_city" or value > 0):
                if field == "nights" and value > 14:
                    continue
                setattr(state.draft, field, value)
                state.draft.provenance[field] = "user"

    async def _collect(self, state, hints, *, broadened=False):
        flags = {"past": False, "unsafe": False, "unsourced": False}
        rows = await self.discover(state.query, hints)
        for row in rows:
            row = self._scrub_data(row)
            if self._source_instruction(row):
                flags["unsafe"] = True
                continue
            try:
                race = RaceOption.model_validate(row)
            except ValidationError:
                continue
            hosts = set()
            urls = []
            for source in race.source_urls:
                url = scrub_url(source)
                try:
                    host = (urlsplit(url).hostname or "").removeprefix("www.") if url else ""
                except ValueError:
                    host = ""
                if host and host not in hosts:
                    hosts.add(host)
                    urls.append(url)
            race.source_urls = urls
            if not race.synthetic and race.date_status == "official" and not race.source_urls:
                race.date_status = "unverified"
                flags["unsourced"] = True
            if race.race_date and race.race_date < self.today:
                flags["past"] = True
                continue
            def identity(name):
                return " ".join(re.findall(r"\w+", normalize(name)))
            duplicate = next((r for r in state.candidates
                              if identity(r.name) == identity(race.name)
                              and r.race_date == race.race_date
                              and (self._dedupe_distance(r) is None
                                   or self._dedupe_distance(race) is None
                                   or self._dedupe_distance(r) == self._dedupe_distance(race))), None)
            if duplicate:
                if self._dedupe_distance(duplicate) is None:
                    duplicate.distance_km = race.distance_km
                    duplicate.distance_label = race.distance_label
                duplicate.source_urls = list(dict.fromkeys(
                    [*duplicate.source_urls, *race.source_urls]))
                if race.date_status == "official":
                    duplicate.date_status = "official"
                continue
            if state.hints.get("exact_date") and (
                not race.race_date or race.race_date.isoformat() != state.hints["exact_date"]
            ):
                continue
            year = state.hints.get("year")
            months = None if broadened else state.hints.get("months")
            if months and race.race_date and race.race_date.isoformat()[:7] not in months:
                continue
            if (
                not months
                and year
                and (
                    (race.race_date and race.race_date.year != year)
                    or any(
                        int(y) != year for y in re.findall(r"\b20\d{2}\b", race.edition or "")
                    )
                )
            ):
                continue
            if len(state.candidates) < 4:
                used_ids = {candidate.id for candidate in state.candidates}
                base_id = race.id
                suffix = 2
                while race.id in used_ids:
                    tail = f":{suffix}"
                    race.id = base_id[:200 - len(tail)] + tail
                    suffix += 1
                distances = self._distance_values(race.distance_label)
                if race.distance_km is None:
                    state.hints.setdefault("_race_distances", []).append(
                        {"race_id": race.id, "distances": distances})
                if len(race.distance_label) > 24:
                    compact = " / ".join(f"{value:g}" for value in distances) + " km"
                    if re.search(r"\d\s*[–—-]\s*\d", race.distance_label) and len(distances) == 2:
                        compact = f"{distances[0]:g}–{distances[1]:g} km"
                    race.distance_label = compact if distances and len(compact) <= 24 else self._say(
                        state, "Plusieurs distances" if distances else "Distance inconnue",
                        "Several distances" if distances else "Distance unknown")
                state.candidates.append(race)
        return flags

    def _recovery_chips(self, state):
        return [self._chip(value) for value in self._say(
            state, ["En Suisse", "En juillet", "Un marathon"],
            ["In Switzerland", "In July", "A marathon"])]

    def _escalate(self, state):
        attempt = state.hints.get("retry_count", 0) + 1
        state.hints["retry_count"] = attempt
        state.hints["depth"] = "deep"
        state.hints["official_date_required"] = True
        if attempt >= 2:
            state.hints["broaden"] = True
            state.hints["alternative_scope"] = "same country, other cities and neighbouring months"

    async def _discover(self, state):
        state.draft.race = None
        state.draft.arrival_date = state.draft.departure_date = None
        state.candidates = []
        state.draft.provenance.pop("distance_km", None)
        state.hints.pop("_race_distances", None)
        hints = state.hints.copy()
        if hints.get("months"):
            hints["month_from"] = min(hints["months"])
            hints["month_to"] = max(hints["months"])
            hints.setdefault("year", int(hints["month_from"][:4]))
        if hints.get("named"):
            hints.setdefault("race_name", state.query)
        broadened = None
        try:
            flags = await self._collect(state, hints)
            if state.candidates and not any(self._eligible(r) for r in state.candidates):
                alternatives = dict(hints, official_date_required=True, depth="deep",
                                    alternative_scope="official dated alternatives", broaden=True)
                original_candidates = state.candidates
                state.candidates = []
                try:
                    await self._collect(state, alternatives, broadened=True)
                except Exception:  # noqa: BLE001 -- optional alternatives must not discard initial results
                    state.candidates = []
                official = [r for r in state.candidates if self._eligible(r)]
                if official:
                    broadened = "months" if hints.get("months") else "criteria"
                state.candidates = official + [r for r in original_candidates
                                               if r.id not in {a.id for a in official}]
            if (not state.candidates and not flags["past"] and not flags["unsafe"]
                    and not state.hints.get("exact_date") and not hints.get("retry_count")):
                broad = {key: value for key, value in hints.items()
                         if key not in {"months", "month_from", "month_to"}}
                if "year" not in state.hints:
                    broad.pop("year", None)
                broad["broaden"] = True
                broadened = "months" if state.hints.get("months") else "criteria"
                flags = await self._collect(state, broad, broadened=True)
            past_found, unsafe_source = flags["past"], flags["unsafe"]
            unsourced_date_found = flags["unsourced"]
        except Exception:  # noqa: BLE001 -- provider failures are returned as scrubbed turns
            state.stage = "discover"
            state, turn = self._turn(
                state,
                self._say(
                    state,
                    "La recherche a rencontré un souci, on peut réessayer.",
                    "Search hit a snag; let's try again.",
                ),
                "discovery_failed",
            )
            turn.suggestions = self._recovery_chips(state) if hints.get("retry_count") else [
                self._chip("retry", self._say(state, "Réessayer", "Retry"), "retry")
            ]
            state.pending_suggestions = turn.suggestions
            for suggestion in turn.suggestions:
                suggestion.id += f":turn-{len(state.history)}"
            return state, turn
        if not state.candidates:
            state.stage = "discover"
            state, turn = self._turn(
                state,
                self._say(
                    state,
                    "Je n'ai pas trouvé de course correspondante, élargissons un peu.",
                    "I couldn't find a matching race; let's broaden things a little.",
                ),
            )
            turn.question = self._say(
                state,
                "On essaie un autre pays, mois ou format ?",
                "Shall we try another country, month or distance?",
            )
            values = self._say(
                state,
                ["En Suisse", "En juillet", "Un marathon"],
                ["In Switzerland", "In July", "A marathon"],
            )
            turn.suggestions = [self._chip(v) for v in values]
            state.pending_suggestions = turn.suggestions
            if unsafe_source:
                turn.message = self._say(
                    state, "J'ai écarté des sources contenant des instructions non fiables.",
                    "I discarded sources containing untrusted instructions.",
                )
                turn.error = "unsafe_source"
                state.history[-1]["text"] = turn.message
            if past_found:
                turn.message = self._say(
                    state, "Cette édition est passée. Cherchons une nouvelle édition sourcée.",
                    "That edition is past. Let's search for a newly sourced next edition.",
                )
                turn.suggestions = [self._chip("next_edition", self._say(
                    state, "Chercher la prochaine édition", "Search next edition"), "retry")]
                state.pending_suggestions = turn.suggestions
                state.history[-1]["text"] = turn.message
            for suggestion in turn.suggestions:
                suggestion.id += f":turn-{len(state.history)}"
            return state, turn
        self._prepare_candidates(state)
        state.candidates.sort(key=lambda race: self._preparation_rank(state, race))
        if (len(state.candidates) == 1 and self._matches_distance(state, state.candidates[0])
                and state.hints.get("named") and not broadened) and not (
            state.candidates[0].registration_access and (
                state.candidates[0].registration_access.account_required is True
                or state.candidates[0].registration_access.captcha is True
            )
        ):
            state.draft.race = state.candidates[0]
            state.draft.provenance["race"] = "source"
        self._advance(state)
        found = self._say(
            state,
            "Voici les options sourcées correspondant à ta recherche.",
            "Here are sourced options matching your search.",
        )
        if broadened == "months":
            found = self._say(
                state,
                "Rien de sourcé sur la période demandée ; voici des éditions sourcées à d'autres dates.",
                "Nothing sourced in the requested period; here are sourced editions on other dates.",
            )
        elif broadened:
            found = self._say(
                state,
                "Rien avec ces critères exacts ; voici des options sourcées en élargissant un peu la recherche.",
                "Nothing with those exact criteria; here are sourced options from a slightly wider search.",
            )
        if self._preparation_rank(state, state.candidates[0])[-1] != 0:
            found += self._preparation_message(state, state.candidates[0])
        return self._turn(
            state,
            found if not unsourced_date_found else self._say(
                state,
                "Certaines dates n'ont aucune source publique : elles restent non vérifiées.",
                "Some dates have no public source: they remain unverified.",
            ),
        )

    async def start(self, text):
        return await self.step(GuideState(), {"text": text})

    def _scrub_identifier(self, value):
        if isinstance(value, str) and any(
            re.fullmatch(r"[A-Za-z0-9]{32,}", segment)
            or (len(segment) >= 24 and re.search(r"[A-Za-z]", segment)
                and re.search(r"\d", segment))
            for segment in re.split(r"[-_.:]", value)
        ):
            cleaned = scrub_text(value)
            return cleaned if cleaned != value else "[redacted key]"
        if isinstance(value, str) and (
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", value)
            and re.search(r"[A-Za-z]", value)
            and not any(pattern.search(value) for pattern in (
                _ASSIGNED_KEY, _EMAIL, _FINANCIAL, _IBAN, _JWT, _KEY_PREFIX,
            ))
            and not any(not _DATE.fullmatch(match.group()) for match in _PHONE.finditer(value))
        ):
            return value
        return scrub_text(value) if isinstance(value, str) else value

    def _scrub_data(self, value):
        if isinstance(value, str):
            return scrub_text(value)
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key == "id" and value.get("kind") == "choose_race" and isinstance(item, str):
                    match = re.fullmatch(r"choose_race:(.*)(:turn-\d+)", item)
                    item = (f"choose_race:{self._scrub_identifier(match[1])}{match[2]}"
                            if match else scrub_text(item))
                elif key == "id" or str(key).endswith("_id") or (
                    key == "value" and value.get("kind") == "choose_race"
                ):
                    item = self._scrub_identifier(item)
                else:
                    item = self._scrub_data(item)
                result[scrub_text(str(key))] = item
            return result
        if isinstance(value, list):
            return [self._scrub_data(v) for v in value]
        return value

    def _source_instruction(self, value):
        if isinstance(value, str):
            return bool(re.search(
                r"\b(?:ignore|disregard|override)\b.*\b(?:instructions?|rules|prompts?)|"
                r"(?:system|developer|assistant)\s*:|<\s*/?\s*(?:system|user_data|instructions)|"
                r"(?:declare|claim|report).*(?:booking completed|payment successful|booked)",
                normalize(value), re.DOTALL,
            ))
        if isinstance(value, dict):
            return any(self._source_instruction(item) for item in value.values())
        if isinstance(value, list):
            return any(self._source_instruction(item) for item in value)
        return False

    async def _recommend(self, state):
        direction = None
        if not state.candidates:
            if state.query:
                self._escalate(state)
            if not state.query:
                state.query = self._say(state, "Un marathon en Italie au printemps",
                                        "A marathon in Italy in spring")
                intent = parse_intent(state.query, today=self.today)
                state.hints = {k: v for k, v in intent.model_dump().items()
                               if k in {"distance", "country", "months"} and v}
                direction = self._say(
                    state, "Je propose de chercher un marathon en Italie au printemps.",
                    "I suggest searching for a spring marathon in Italy.")
            state, turn = await self._discover(state)
            if not state.candidates:
                if direction:
                    turn.message = direction + " " + turn.message
                    state.history[-1]["text"] = turn.message
                return state, turn
        matching = [r for r in state.candidates if self._matches_distance(state, r)]
        if not matching:
            state.draft.race = None
            state.draft.arrival_date = state.draft.departure_date = None
            self._advance(state)
            return self._turn(state, self._say(
                state, "Aucune course trouvée à la distance demandée ; voici les autres "
                "distances, à toi de choisir sans changement automatique.",
                "No race was found at the requested distance; here are other distances "
                "for you to choose, without switching automatically."))
        self._prepare_candidates(state)
        suitable = [r for r in matching if self._eligible(r)]
        available = [r for r in suitable if not self._unavailable(r)]
        if available:
            suitable = available
        elif not state.hints.get("named") and not state.draft.race:
            suitable = []
        if not state.hints.get("named"):
            suitable.sort(key=lambda r: bool(r.registration_access and (
                r.registration_access.account_required is True or r.registration_access.captcha is True
            )))
        if state.draft.race:
            suitable.sort(key=lambda r: r.id != state.draft.race.id)
        self._prepare_candidates(state)
        suitable.sort(key=lambda r: self._preparation_rank(state, r))
        if not suitable:
            self._escalate(state)
            return await self._discover(state)
        months = state.hints.get("months")
        if months and not state.draft.race:
            suitable = [r for r in suitable if r.race_date.strftime("%Y-%m") in months]
            if not suitable:
                return self._turn(state, self._say(
                    state, "Rien de sourcé sur la période demandée ; voici des éditions sourcées "
                    "à d'autres dates, à toi de choisir.",
                    "Nothing sourced in the requested period; here are sourced editions on "
                    "other dates for you to choose from."))
        race = suitable[0]
        host = None
        for url in race.source_urls:
            try:
                host = urlsplit(url).hostname
            except ValueError:
                continue
            if host:
                break
        date_kind = self._say(state, "synthétique" if race.synthetic else "officielle",
                             "synthetic" if race.synthetic else "official")
        reason = self._say(state, f"date {date_kind} du {race.race_date}",
                           f"{date_kind} date {race.race_date}")
        if host:
            reason += self._say(state, f", source : {host}", f", source: {host}")
        message = self._say(
            state, f"Je recommande {race.name} : {reason}.",
            f"I recommend {race.name}: {reason}.")
        message += self._preparation_message(state, race)
        if direction:
            message = direction + " " + message
        access = race.registration_access
        if access and (access.account_required is True or access.captcha is True):
            return self._turn(state, message + self._access_warning(state, race))
        state.draft.race = race
        state.draft.provenance["race"] = "source"
        applied = []
        for field, value in [("origin_city", bare_city(self._origin_choices(race)[0])
                             or self._origin_choices(race)[0]),
                             ("nights", 2), ("budget_eur", 450)]:
            if getattr(state.draft, field) is None:
                setattr(state.draft, field, value)
                state.draft.provenance[field] = "suggested_default"
                applied.append(self._say(state, {
                    "origin_city": f"départ de {value}", "nights": f"{value} nuits",
                    "budget_eur": f"budget de {value} €"}[field], {
                    "origin_city": f"leaving from {value}", "nights": f"{value} nights",
                    "budget_eur": f"a €{value} budget"}[field]))
        if applied:
            listed = (", ".join(applied[:-1]) + self._say(state, " et ", " and ") + applied[-1]
                      if len(applied) > 1 else applied[0])
            message += self._say(state, f" Valeurs par défaut proposées, modifiables : {listed}.",
                                 f" Editable defaults applied: {listed}.")
        self._advance(state)
        return self._turn(state, message)

    async def step(self, state: GuideState, action: dict):
        original = state
        state = GuideState.model_validate(self._scrub_data(state.model_dump()))
        text = scrub_text(action.get("text", "")).strip()
        introduction = re.search(
            r"\b(?:je m['’]appelle|my name is|i['’]m called|moi c['’]est)\s+", text,
            flags=re.IGNORECASE,
        )
        introduced_language = (
            "en" if introduction and normalize(introduction[0]).startswith(("my", "i")) else "fr"
        )
        race_token = r"(?:half|semi|marathon|trail|ultra|\d+(?:[.,]\d+)?\s*(?:km|k))\b"
        name_boundary = (
            r"\b(?:and|et|mais|but|je cherche|je veux|j['’]aimerais|je voudrais|cherche|"
            r"i want|i['’]m looking|i am looking|looking for|i['’]d like|i would like|inscris)\b|"
            r"[,.;!]|\b(?:(?:un|une|le|la|a|the)\s+)?" + race_token
        )
        text = re.sub(
            r"\b(?:je m['’]appelle|my name is|i['’]m called|moi c['’]est)\s+"
            r".*?(?=" + name_boundary + r"|$)", "", text,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        chip = None
        if "suggestion_id" in action:
            chip = next(
                (s for s in state.pending_suggestions if s.id == action["suggestion_id"]), None
            )
            if chip is None:
                _, turn = self._turn(
                    state,
                    self._say(
                        state,
                        "Ce raccourci n'est plus disponible, reprenons ici.",
                        "That shortcut isn't available; let's continue here.",
                    ),
                    "unknown_suggestion",
                )
                turn.suggestions = original.pending_suggestions.copy()
                return original, turn
        elif normalize(text) in {"oui", "ok", "parfait", "yes", "sounds good"}:
            distances = [s for s in state.pending_suggestions if s.kind == "distance"]
            chip = next(
                (s for s in state.pending_suggestions if s.kind in {"answer", "confirm"}),
                distances[0] if len(distances) == 1 else None,
            )
        if chip:
            if chip.kind == "retry":
                self._escalate(state)
                if chip.value == "next_edition":
                    state.hints.pop("year", None)
                    state.hints.pop("months", None)
                    state.hints.pop("exact_date", None)
                    state.hints.pop("race_name", None)
                    state.query = re.sub(r"\b20\d{2}\b", "", state.query) + " next edition"
                return await self._discover(state)
            if chip.kind == "confirm":
                self.trip_payload(state)
                return self._turn(state, self._say(
                    state, "Le plan est prêt. Seule la confirmation dédiée lance les agents.",
                    "The plan is ready. Only the dedicated confirmation starts agents."))
            if chip.kind == "edit":
                state.stage = chip.value
                return self._turn(state)
            if chip.kind == "choose_race":
                state.draft.race = next(r for r in state.candidates if r.id == chip.value)
                state.draft.provenance["race"] = "source"
                state.draft.provenance.pop("distance_km", None)
                if state.draft.race.distance_km is not None:
                    state.draft.provenance["distance_km"] = "source"
                self._advance(state)
                return self._turn(
                    state,
                    self._say(
                        state,
                        f"Très bon choix, partons sur {state.draft.race.name} !",
                        f"Lovely choice, let's go with {state.draft.race.name}!",
                    ),
                )
            if state.stage in {"origin", "nights", "budget"}:
                field = {"origin": "origin_city", "nights": "nights", "budget": "budget_eur"}[
                    state.stage
                ]
                setattr(
                    state.draft, field, (bare_city(chip.value) or chip.value)
                    if field == "origin_city" else int(chip.value)
                )
                state.draft.provenance[field] = "suggested_default"
                description = {
                    "origin_city": self._say(
                        state, f"un départ de {chip.value}", f"leaving from {chip.value}"
                    ),
                    "nights": self._say(
                        state, f"{chip.value} nuits sur place", f"{chip.value} nights away"
                    ),
                    "budget_eur": self._say(
                        state, f"un budget de {chip.value} €", f"a budget of €{chip.value}"
                    ),
                }[field]
                self._advance(state)
                return self._turn(
                    state,
                    self._say(
                        state,
                        f"D'accord, je retiens {description}. Tu peux toujours changer d'avis.",
                        f"Sounds good, let's plan on {description}. You can still change your mind.",
                    ),
                )
            text = chip.value
        if not text:
            if introduction:
                state.lang = introduced_language
            return self._turn(state)
        unsafe = re.search(
            r"ignore.*(?:instructions?|rules)|system\s*:|developer\s*:|override|"
            r"\b(?:pay|payer|paie|payment|paiement|buy|acheter|purchase|"
            r"submit|soumettre|envoyer|bypass|contourner)\b|"
            r"(?:create|creer|cree|ouvre|open).*(?:account|compte)|"
            r"(?:accept|accepter|accepte).*(?:terms|conditions|consent|cgu)|"
            r"(?:print|reveal|show|affiche|donne).*(?:system prompt|prompt system|api_key)|"
            r"\b(?:hai_api_key|linkup_api_key|gladia_api_key)\b",
            normalize(text),
        )
        if unsafe:
            safe = text[:unsafe.start()].strip(" ,.;")
            intent = parse_intent(safe, today=self.today)
            self._set_language(state, intent if safe else parse_intent(text, today=self.today),
                               typed=chip is None)
            refusal = self._say(
                state, "Je ne peux pas divulguer d'instructions ou de secrets, traiter des données personnelles ni effectuer d'action engageante.",
                "I cannot disclose instructions or secrets, process personal data or take binding actions.")
            # Extract race wishes independently of the unsafe instruction's position.
            race_clause = re.search(
                r"(?:un |une |a |the |le |la |au |du )?(?:half marathon|semi(?:-marathon)?|marathon|10\s*km|trail)"
                r"\s+(?:de |d'|in |of |a |à )?[\w-]+", text, re.IGNORECASE)
            if race_clause and race_clause.start() >= unsafe.start():
                safe = race_clause[0]
            for clause in re.split(r"[;.]", text):
                wish = parse_intent(clause, today=self.today)
                if wish.distance and wish.city and not self._source_instruction(clause):
                    distance = wish.distance.replace("half", "half marathon")
                    safe = self._say(state, f"le {distance} de {wish.city}",
                                     f"the {distance} in {wish.city}")
                    break
            if safe:
                recovered, turn = await self.step(state, {"text": safe})
                turn.message = refusal + " " + turn.message
                turn.error = "safety_refusal"
                recovered.history[-1]["text"] = turn.message
                return recovered, turn
            return self._turn(state, refusal, "safety_refusal")
        intent = parse_intent(text, today=self.today)
        if introduction and not intent.fr_cues and not intent.en_cues:
            intent.switch_language = introduced_language
        self._set_language(state, intent, typed=chip is None)
        if re.search(r"\b(?:meteo|weather|poeme?|poetry)\b", normalize(text)) and not (
            intent.distance or intent.named
        ):
            return self._turn(state, self._say(
                state, "Restons sur ton projet de course : dis-moi quelle course te tente.",
                "Let's focus on your running trip: tell me which race interests you."))
        if _FORBIDDEN_SITE.search(normalize(text)):
            return self._turn(state, self._say(
                state, "Je ne peux pas imposer ce site : les agents n'utilisent que des sites "
                "relus et autorisés, et Booking ou Accor en sont exclus. On continue avec ton projet.",
                "I can't use that site: agents only use reviewed, allowed sites, and Booking or "
                "Accor are excluded. Let's keep going with your plan."), "site_not_allowed")
        if _SKIP_CONFIRMATION.search(normalize(text)):
            return self._turn(state, self._say(
                state, "Rien ne démarre sans ta confirmation explicite du plan prêt, "
                "via le bouton dédié. Reprenons ici.",
                "Nothing starts without your explicit confirmation of the ready plan, "
                "via the dedicated button. Let's continue here."), "confirmation_required")
        state.history.append({"role": "user", "text": text})
        if bare_city(text) and (state.stage in {"origin", "confirm", "confirmed"}
                                or (state.query and not state.draft.origin_city)):
            intent.origin_city = bare_city(text)
            intent.city = intent.country = None
        if text.isdecimal() and state.stage in {"nights", "budget"}:
            setattr(intent, "nights" if state.stage == "nights" else "budget_eur", int(text))
        if intent.nights is not None and not 1 <= intent.nights <= 14:
            intent.problem = "nights_range"
        if intent.budget_eur is not None and intent.budget_eur <= 0:
            intent.problem = "budget_range"
        self._update(state, intent)
        if intent.problem and intent.problem != "exact_date":
            problems = list(dict.fromkeys([intent.problem, *intent.problems]))
            explanations = {
                "nights_range": (f"La durée de {intent.nights} nuits doit être entre 1 et 14 nuits.",
                                 f"A stay of {intent.nights} nights is outside the allowed 1–14 nights."),
                "budget_range": (f"Le budget de {intent.budget_eur} € doit être supérieur à zéro.",
                                 f"A budget of €{intent.budget_eur} must be greater than zero."),
                "tomorrow": ("Je n'ai pas d'événement sourcé pour demain.", "I have no sourced event for tomorrow."),
                "past_date": ("Cette date est passée ; cherchons une nouvelle édition sourcée.", "That date is past; let's find a newly sourced edition."),
            }
            messages = [self._say(state, *explanations.get(problem, (
                "Ces contraintes sont contradictoires ou non prises en charge ; précisons-les.",
                "Those requirements conflict or are unsupported; let's clarify them.")))
                for problem in problems]
            if "nights_range" in problems:
                state.draft.nights = None
                state.draft.arrival_date = state.draft.departure_date = None
                self._advance(state)
            if "budget_range" in problems:
                state.draft.budget_eur = None
                self._advance(state)
            if set(problems) & {"past_date", "tomorrow", "destination_conflict", "date_conflict",
                                "travelers_range", "unsupported"}:
                state.draft.race = None
                state.draft.arrival_date = state.draft.departure_date = None
                state.candidates = []
                state.stage = "discover"
            state, turn = self._turn(state, " ".join(dict.fromkeys(messages)), intent.problem)
            if intent.problem == "past_date":
                state.query = re.sub(r"\b(?:19|20)\d{2}(?:-\d{2}-\d{2})?\b", "", text)
                state.hints = {k: v for k, v in intent.model_dump().items()
                               if k in {"distance", "city", "country", "named"} and v}
                turn.suggestions = [self._chip("next_edition", self._say(
                    state, "Chercher la prochaine édition", "Search next edition"), "retry")]
                state.pending_suggestions = turn.suggestions
                for suggestion in turn.suggestions:
                    suggestion.id += f":turn-{len(state.history)}"
            return state, turn
        if self._needs_distance(state):
            options = self._pending_distances(state)
            if intent.deferred and not any((intent.distance, intent.city, intent.country,
                                            intent.months, intent.year, intent.problem)):
                if options:
                    value = min(options)
                    return self._turn(state, self._say(
                        state,
                        f"Je suggère {value:g} km : c'est la plus courte distance explicitement indiquée dans la source. Choisis-la pour valider cette distance.",
                        f"I suggest {value:g} km: it is the shortest distance explicitly listed in the source. Choose it to confirm this distance.",
                    ), recommended_distance=value)
                alternatives = self._distance_alternatives(state)
                message = self._say(
                    state, "Aucune distance sourcée n'est disponible pour cet événement.",
                    "No sourced distance is available for this event.")
                if alternatives:
                    race = alternatives[0]
                    evidence = self._say(state, "synthétique", "synthetic") if race.synthetic else self._say(
                        state, "sourcée", "sourced")
                    message += self._say(
                        state, f" Je propose plutôt {race.name}, avec une distance {evidence} de {race.distance_km:g} km ; sélectionne cette course pour changer.",
                        f" I suggest {race.name} instead, with a {evidence} distance of {race.distance_km:g} km; select that race to switch.")
                else:
                    message += self._say(
                        state, " Aucune autre course éligible n'a de distance connue ; indique la distance que tu souhaites courir, sans que j'en invente une.",
                        " No eligible alternative has a known distance; enter the distance you intend to run rather than having me invent one.")
                return self._turn(state, message)
            distance = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)?)\s*(?:km)?", text, re.IGNORECASE)
            if distance:
                value = float(distance[1].replace(",", "."))
                if not options and not 1 <= value <= 400:
                    return self._turn(state, self._say(
                        state, "La distance doit être un nombre entre 1 et 400 km.",
                        "Distance must be a number between 1 and 400 km."), "distance_range")
                if options and value not in options:
                    return self._turn(state, self._say(
                        state, "Choisissons une distance explicitement sourcée.",
                        "Please choose a distance explicitly listed in the source."))
                state.draft.race = state.draft.race.model_copy(deep=True)
                state.draft.race.distance_km = value
                state.draft.race.distance_label = f"{value:g} km"
                state.draft.provenance["distance_km"] = "user"
                self._advance(state)
                return self._turn(state, self._say(
                    state, f"Distance choisie : {value:g} km.",
                    f"Selected distance: {value:g} km."))
            if not any((intent.distance, intent.city, intent.country, intent.months, intent.year,
                        intent.problem, intent.origin_city, intent.nights, intent.budget_eur,
                        intent.travelers)):
                return self._turn(state, self._say(
                    state, "Indique une distance numérique en kilomètres, sans valeur inventée.",
                    "Please enter a numeric distance in kilometres; I won't invent one."), "distance_range")
        has_constraints = bool(intent.distance or intent.city or intent.country
                               or intent.months or intent.year or intent.problem == "exact_date")
        if intent.deferred and not has_constraints:
            return await self._recommend(state)
        if has_constraints:
            previous_city = (state.draft.race.city if state.draft.race else None) or state.hints.get("city")
            previous_country = (state.draft.race.country if state.draft.race else None) or state.hints.get("country")
            if intent.same_place and not intent.city:
                intent.city, intent.country = previous_city, previous_country
                intent.named = bool(intent.city and intent.distance)
            recovery = normalize(text) in {
                "en suisse", "in switzerland", "en juillet", "in july", "un marathon",
                "a marathon",
            } and bool(state.query) and (state.stage == "discover"
                                         or not self._eligible(state.draft.race))
            if (intent.distance or intent.country or intent.city) and not recovery:
                state.query = (named_query(intent.city, intent.distance)
                               if intent.named else text)
                state.hints = {}
            elif not state.query:
                state.query = text
            if recovery:
                self._escalate(state)
                if intent.country:
                    state.hints.pop("city", None)
                    state.hints.pop("race_name", None)
                    state.hints.pop("named", None)
            if intent.named:
                state.hints["race_name"] = state.query
            if intent.problem == "exact_date":
                state.hints.pop("months", None)
                state.hints.pop("year", None)
            if intent.months or intent.year:
                state.hints.pop("exact_date", None)
            if intent.year:
                state.hints.pop("months", None)
            elif intent.months and state.hints.get("year"):
                first_month = int(intent.months[0][-2:])
                intent.months = [
                    f"{state.hints['year'] + (int(month[-2:]) < first_month):04d}-{month[-2:]}"
                    for month in intent.months
                ]
            state.hints.update(
                {
                    k: v
                    for k, v in intent.model_dump().items()
                    if k in {"distance", "city", "country", "months", "named", "year"} and v
                }
            )
            if recovery:
                place = state.hints.get("city") or state.hints.get("country", "")
                state.query = named_query(place, state.hints.get("distance", "race"))
                if state.hints.get("named"):
                    state.hints["race_name"] = state.query
            if intent.problem == "exact_date":
                state.hints["exact_date"] = re.search(r"\d{4}-\d{2}-\d{2}", text)[0]
            state, turn = await self._discover(state)
            if intent.deferred and state.candidates:
                return await self._recommend(state)
            return state, turn
        if any(
            getattr(intent, f) is not None
            for f in ["origin_city", "nights", "budget_eur", "travelers"]
        ):
            self._advance(state)
            return self._turn(state, self._say(
                state, "D'accord, je retiens ces préférences. Tu peux toujours changer d'avis.",
                "Sounds good, I've saved those preferences. You can still change your mind."))
        return self._turn(
            state,
            self._say(
                state,
                "Restons sur ton projet de course ; les choix ci-dessous permettent d'avancer.",
                "Let's focus on your running trip; the choices below will help us move forward.",
            ),
        )

    def trip_payload(self, state):
        d = state.draft
        if not (
            self._eligible(d.race)
            and d.race.distance_km is not None
            and d.origin_city
            and d.nights
            and d.budget_eur
            and d.arrival_date
            and d.departure_date
        ):
            raise ValueError("Trip is not ready to confirm")
        payload = {
            key: value for key, value in d.model_dump(mode="json").items() if key != "provenance"
        }
        payload["race"].pop("preparation", None)
        return payload
