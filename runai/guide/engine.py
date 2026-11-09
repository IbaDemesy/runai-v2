import asyncio
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
FIRST_DISCOVERY_TIMEOUT_S = 20.0
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
        names["Austria"] = "Autriche"
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

    def _month_label(self, state, day):
        months = self._say(state,
            "Janvier Février Mars Avril Mai Juin Juillet Août Septembre Octobre Novembre Décembre",
            "January February March April May June July August September October November December")
        return f"{months.split()[day.month - 1]} {day.year}"

    def _race_chips(self, state, races=None):
        choices = list(state.candidates if races is None else races)
        choices.sort(key=lambda r: (not self._default_race(state, r), not self._eligible(r),
                                    self._unavailable(r), not self._same_country(state, r),
                                    self._preparation_rank(state, r)))
        chips = [
            self._chip(
                r.id,
                f"{r.name} — {r.race_date if r.date_status == 'official' and r.race_date else self._say(state, 'date à confirmer', 'date to be confirmed')}"
                + self._access_warning(state, r),
                "choose_race",
                "synthetic" if r.synthetic else "source",
            )
            for r in choices
            if not state.draft.race or r.id != state.draft.race.id
        ]
        for chip in chips:
            race = next(r for r in state.candidates if r.id == chip.value)
            if not self._matches_distance(state, race):
                chip.group = self._say(state, "Autre distance", "Another distance")
        return chips

    def _default_race(self, state, race):
        return (self._eligible(race) and self._matches_distance(state, race)
                and self._preparation_rank(state, race)[-1] == 0)

    def _same_country(self, state, race):
        return (not state.requested_country or bool(race.country and
                normalize(country_name(race.country) or race.country) == normalize(state.requested_country)))

    def _official_hint(self, race):
        if race.synthetic:
            return {}
        try:
            hint = import_module("runai.discovery.linkup").official_search_hint(
                race.name, race.distance_km, race.race_date.year if race.race_date else None)
            if not hint and race.official_url:
                hint = {"race_name": race.name, "country": race.country,
                        "official_domains": urlsplit(race.official_url).hostname or ""}
            return hint
        except (ImportError, AttributeError):
            return {}

    def _race_identity(self, race):
        hint = self._official_hint(race)
        name = normalize(hint.get("race_name", race.name))
        if race.race_date:
            name = re.sub(rf"\b{race.race_date.year}\b", "", name)
        return " ".join(re.findall(r"\w+", name))

    def _named_match(self, state, race):
        city = state.hints.get("city")
        if not state.hints.get("named") or not city:
            return True
        if race.city:
            return normalize(bare_city(race.city) or race.city) == normalize(city)
        aliases = [alias for groups in CITY_GROUPS.values() for group in groups
                   if bare_city(group.split("/")[0]) == city for alias in group.split("/")]
        return any(re.search(r"(?<!\w)" + re.escape(normalize(alias)) + r"(?!\w)",
                             normalize(race.name)) for alias in [city, *aliases])

    def _named_not_found(self, state):
        city = state.hints["city"]
        year = f" {state.hints['year']}" if state.hints.get("year") else ""
        kind = {"marathon": "marathon", "half": "semi-marathon", "10k": "10 km"}.get(
            state.hints.get("distance"), "course")
        prefix = "d'" if normalize(city)[0] in "aeiou" else "de "
        article = "la" if kind == "course" else "le"
        return self._say(state, f"Je ne trouve pas {article} {kind} {prefix}{city}{year}.",
                         f"I couldn't find {state.query}{year}.")

    def _resolve_date_conflicts(self, state):
        groups = {}
        for race in state.candidates:
            key = (self._race_identity(race), normalize(race.city or ""),
                   self._dedupe_distance(race), race.race_date.year if race.race_date else race.edition,
                   None if race.city else race.race_date)
            groups.setdefault(key, []).append(race)
        resolved = []
        for races in groups.values():
            if len({r.race_date for r in races if r.race_date}) <= 1:
                resolved.extend(races)
                continue
            official = [r for r in races if r.date_status == "official" and r.official_url
                        and any(urlsplit(url).hostname == urlsplit(r.official_url).hostname
                                for url in r.source_urls)]
            if len({r.race_date for r in official}) == 1:
                resolved.append(official[0])
            else:
                race = races[0].model_copy(deep=True)
                race.date_status, race.race_date = "conflicting", None
                resolved.append(race)
        state.candidates = resolved

    def _matches_distance(self, state, race):
        distance = state.hints.get("distance")
        target = {"half": 21.1, "5k": 5}.get(distance)
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
                    status = result.get("registration", result.get("status"))
                    result = ("covered" if result.get("covered") is True
                              and status == "open" else status)
                    if result == "open":
                        result = "uncovered"
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
        parts = [(True if p.registration == "covered" else None if p.registration == "unknown"
                  else False, "l'inscription", "registration"),
                 (p.hotel, "l'hôtel", "hotel"),
                 (p.transport, "le transport", "transport")]
        covered = [self._say(state, fr, en) for ok, fr, en in parts if ok]
        missing = [self._say(state, fr, en) for ok, fr, en in parts if ok is False]
        message = self._say(
            state, f" Je peux préparer {', '.join(covered)} pour {race.name}." if covered
            else f" Aucune préparation couverte pour {race.name}.",
            f" I can prepare {', '.join(covered)} for {race.name} (covered agents)." if covered
            else f" No preparation is covered for {race.name}.")
        if missing:
            message += self._say(state, f" Non couverts : {', '.join(missing)}.",
                                 f" Not covered: {', '.join(missing)}.")
        unknown = [self._say(state, fr, en) for ok, fr, en in parts if ok is None]
        if unknown:
            message += self._say(state, f" À vérifier : {', '.join(unknown)}.",
                                 f" To check: {', '.join(unknown)}.")
        alternatives = [r for r in state.candidates if r.id != race.id and self._eligible(r)
                        and self._preparation_rank(state, r)[-1] == 0]
        if (missing or unknown) and alternatives:
            message += self._say(state, f" Je propose plutôt {alternatives[0].name}, préparable.",
                                 f" Try {alternatives[0].name} instead: all three agents are covered.")
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
        def canonical(value):
            for standard in (21.1, 42.195):
                if abs(value - standard) < 0.01:
                    return standard
            return round(value, 3)

        if race.distance_km is not None:
            return (canonical(race.distance_km),)
        label = normalize(race.distance_label)
        label = re.sub(r"(?<=\d)\s*[-–—]\s*(?=k(?:m)?\b)", " ", label)
        if re.fullmatch(r"\d+(?:[.,]\d+)?", label):
            return (canonical(float(label.replace(",", "."))),)
        values = self._distance_values(re.sub(r"(?<=\d)\s*k\b", " km", label))
        if values:
            return tuple(sorted(canonical(value) for value in values))
        label = " ".join(re.sub(r"[-–—]", " ", label).split())
        named = {"marathon": 42.195, "half marathon": 21.1, "semi marathon": 21.1,
                 "semi": 21.1, "half": 21.1}
        if label in named:
            return (named[label],)
        return label or None

    def _pending_distances(self, state):
        race = state.draft.race
        return (self._sourced_distances(state)
                if self._eligible(race) and race.distance_km is None else [])

    def _default_distances(self, state, values):
        minimum = {"half": 21.1, "marathon": 42.195, "10k": 10}.get(
            state.hints.get("distance"), 0)
        return [value for value in values if value >= minimum - 0.01]

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
            state.stage in {"confirm", "confirmed"}
            and
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
            if not d.race and not any(self._eligible(r) and not self._unavailable(r) and (
                not state.hints.get("prefer_requested_country") or self._same_country(state, r)
            ) for r in state.candidates):
                chips = ([] if state.hints.get("retry_count") else [self._chip("alternative", self._say(
                    state, "Chercher une course préparable", "Find a preparable race"), "retry")])
                chips += self._recovery_chips(state) + self._race_chips(state)
            if not d.race and (
                state.hints.get("retry_count") and not any(self._eligible(r) for r in state.candidates)
                or not any(r.race_date for r in state.candidates)
            ):
                chips += (self._recovery_chips(state) if state.hints.get("retry_count") else
                          [self._chip("retry", self._say(state, "Relancer", "Try again"), "retry")])
            if d.race:
                chips = self._race_chips(state, [r for r in state.candidates
                                                 if self._eligible(r)])
                if state.hints.get("prefer_requested_country") and not any(
                    self._eligible(r) and self._same_country(state, r) for r in state.candidates
                ):
                    chips = [c for c in self._recovery_chips(state) if c.value == "same_country"] + chips
                explanation = self._say(
                    state,
                    "Les sources actuelles ne permettent pas de confirmer la date de cette course ; choisissons une autre option.",
                    "This race's date cannot be confirmed from the current sources; let's try another option.",
                )
                message = (message + " " if message else "") + explanation
                if not state.hints.get("retry_count"):
                    chips += [self._chip("retry", self._say(state, "Relancer", "Try again"),
                                         "retry")]
                chips += [c for c in self._recovery_chips(state) if c.value not in {s.value for s in chips}]
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
            source = next((urlsplit(url).hostname for url in d.race.source_urls
                           if urlsplit(url).hostname), None)
            evidence = self._say(state, "date synthétique" if d.race.synthetic else "date officielle",
                                 "synthetic date" if d.race.synthetic else "official date")
            summary = self._say(
                state,
                f"Je pars sur {d.race.name} ({evidence} : {d.race.race_date}, {d.race.distance_km:g} km), départ de {d.origin_city}, {d.nights} nuits, budget {d.budget_eur} € pour {d.travelers} {people_fr}, du {d.arrival_date} au {d.departure_date}. Tu peux modifier un point.",
                f"Let's plan on {d.race.name} ({evidence}: {d.race.race_date}, {d.race.distance_km:g} km), leaving from {d.origin_city}, {d.nights} nights, budget €{d.budget_eur} for {d.travelers} {people_en}, {d.arrival_date} to {d.departure_date}. You can change any detail.",
            )
            if source:
                summary += self._say(state, f" Source : {source}.", f" Source: {source}.")
            message = ((message + " ") if message and error else "") + summary
            if any(item["race_id"] == d.race.id
                   for item in state.hints.get("_race_distances", [])):
                message += self._say(
                    state, f" Début de l'événement : {d.race.race_date}.",
                    f" Event start date: {d.race.race_date}.")
            if state.stage == "confirm":
                question = self._say(
                    state,
                    "On lance la préparation ?",
                    "Shall we start preparation?",
                )
                chips = [self._chip("confirm", self._say(state, "Confirmer et préparer", "Confirm and prepare"), "confirm")]
                chips += [
                    self._chip(f, self._say(state, fr, en), "edit")
                    for f, fr, en in [
                        ("origin", "Modifier le départ", "Edit origin"),
                        ("nights", "Modifier les nuits", "Edit nights"),
                        ("budget", "Modifier le budget", "Edit budget"),
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
                state, " Attention : date non vérifiée, à confirmer sur le site officiel.",
                " Warning: unverified date, to be confirmed on the official site."
            )
        profile = getattr(state, "profile_status", None)
        complete = profile.get("complete") is True if isinstance(profile, dict) else (
            getattr(profile, "complete", False) is True)
        if ready and not complete and not state.profile_invited:
            state.profile_invited = True
            message += self._say(
                state, "\nRemplis une seule fois la fiche profil coureur sécurisée pour aider les agents à préremplir l'inscription, l'hôtel et le transport, sans soumettre de formulaire.",
                "\nFill in the secure runner profile card once to help agents prefill registration, hotel and transport, without submitting any forms.")
            chips.append(self._chip("continue_without_profile", self._say(
                state, "Continuer sans profil", "Continue without profile")))
        message = self._display_text(state, scrub_text(message))
        previous = next((row["text"] for row in reversed(state.history)
                         if row.get("role") == "assistant"), None)
        if message == previous:
            message += self._say(state, " Précisons une autre piste.",
                                 " Let's refine another option.")
        question = self._display_text(state, scrub_text(question)) if question else None
        for chip in chips:
            chip.id += f":turn-{len(state.history)}"
            if re.fullmatch(r"\d{4}-\d{2}", chip.label):
                chip.label = self._month_label(state, date.fromisoformat(chip.label + "-01"))
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
        if self._eligible(d.race):
            if d.race.distance_km is None:
                requested = {"marathon": 42.195, "half": 21.1, "10k": 10}.get(
                    state.hints.get("_requested_distance"))
                options = [value for value in self._sourced_distances(state)
                           if requested is not None and abs(value - requested) < 0.01]
                value = options[0] if options else (
                    requested if not self._sourced_distances(state) else None)
                if value is not None:
                    d.race = d.race.model_copy(deep=True)
                    d.race.distance_km = value
                    d.race.distance_label = f"{value:g} km"
                    d.provenance["distance_km"] = "source" if options else "suggested_default"
            if d.race.distance_km is not None:
                for field, value in [("origin_city", "Paris"), ("nights", 2),
                                     ("budget_eur", 150 + 150 * (d.nights or 2))]:
                    if getattr(d, field) is None and field not in state.hints.get("_invalid_fields", []):
                        setattr(d, field, value)
                        d.provenance[field] = "suggested_default"
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
                invalid = state.hints.get("_invalid_fields", [])
                if field in invalid:
                    invalid.remove(field)

    async def _collect(self, state, hints, *, broadened=False, deadline=None):
        flags = {"past": False, "unsafe": False, "unsourced": False}
        if deadline is not None:
            remaining = max(0, deadline - asyncio.get_running_loop().time())
            hints = dict(hints, depth="standard", search_timeout_s=min(
                FIRST_DISCOVERY_TIMEOUT_S * 0.75, remaining * 0.8))
        async with asyncio.timeout_at(deadline):
            rows = await self.discover(state.query, hints)
        previous_edition = getattr(rows, "previous_edition_date", None)
        if isinstance(previous_edition, date):
            state.hints["_previous_edition_date"] = previous_edition.isoformat()
            flags["past"] = True
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
            key = f"{self._race_identity(race)}|{race.race_date}|{self._dedupe_distance(race)}"
            cached = state.verification_cache.get(key)
            if cached and cached.date_status == "official":
                race.date_status = "official"
                race.source_urls = list(dict.fromkeys([*cached.source_urls, *race.source_urls]))
                race.official_url = race.official_url or cached.official_url
                race.registration_url = race.registration_url or cached.registration_url
            elif race.date_status == "official":
                state.verification_cache[key] = race.model_copy(deep=True)
            duplicate = next((r for r in state.candidates
                              if self._race_identity(r) == self._race_identity(race)
                              and normalize(r.city or "") == normalize(race.city or "")
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
                    duplicate.official_url = race.official_url or duplicate.official_url
                    duplicate.registration_url = race.registration_url or duplicate.registration_url
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
        if state.hints.get("_timeout_recovery"):
            previous = {s.value for s in state.pending_suggestions}
            start = date.fromisoformat(min(state.hints.get("months") or [self.today.strftime("%Y-%m")]) + "-01")
            chips = []
            for offset in range(1, 13):
                index = start.year * 12 + start.month - 1 + offset
                month = date(index // 12, index % 12 + 1, 1)
                value = "month:" + month.strftime("%Y-%m")
                if value not in previous:
                    chips.append(self._chip(value, self._month_label(state, month), "retry"))
                if len(chips) == 3:
                    break
            return chips
        chips = [self._chip(value) for value in self._say(
            state, ["En Suisse", "En juillet", "Un marathon"],
            ["In Switzerland", "In July", "A marathon"])
                if state.recovery_failures.get(normalize(value), 0) < 2]
        if state.hints.get("prefer_requested_country") and state.requested_country and (
            state.recovery_failures.get("same_country", 0) < 2
        ):
            country = self._display_text(state, state.requested_country)
            chips.insert(0, self._chip("same_country", self._say(
                state, f"Autres courses en {country}", f"Other races in {country}"), "retry"))
        return chips

    def _escalate(self, state):
        attempt = state.hints.get("retry_count", 0) + 1
        state.hints["retry_count"] = attempt
        state.hints["depth"] = "deep"
        state.hints["official_date_required"] = True
        state.query = re.sub(r" recovery \d+ official alternatives$", "", state.query)
        state.query += f" recovery {attempt} official alternatives"
        if attempt >= 2:
            state.hints["broaden"] = True
            state.hints["alternative_scope"] = "same country, other cities and neighbouring months"

    async def _discover(self, state):
        previous = next((row["text"] for row in reversed(state.history)
                         if row.get("role") == "assistant"), None)
        recovery = state.hints.pop("_recovery_action", None)
        state, turn = await self._search_races(state)
        if recovery and not any(self._default_race(state, r) for r in state.candidates):
            state.recovery_failures[recovery] = state.recovery_failures.get(recovery, 0) + 1
        if recovery and sum(state.recovery_failures.values()) >= 2:
            state, turn = await self._preparable_alternative(state, turn)
        months = state.hints.get("months")
        if months and not turn.error and not any(
            r.race_date and r.race_date.strftime("%Y-%m") in months for r in state.candidates
        ):
            requested = ", ".join(months)
            turn.message = self._say(
                state, f"Aucune course sourcée en {requested}. ",
                f"No sourced race in {requested}. ") + turn.message
            first = date.fromisoformat(min(months) + "-01")
            last = date.fromisoformat(max(months) + "-01")
            adjacent = [(first - timedelta(days=1)).replace(day=1),
                        (last + timedelta(days=32)).replace(day=1)]
            turn.suggestions += [self._chip("month:" + day.strftime("%Y-%m"),
                                            day.strftime("%Y-%m")) for day in adjacent]
            previous = next((row["text"] for row in reversed(state.history[:-1])
                             if row.get("role") == "assistant"), None)
            if turn.message == previous:
                turn.message += self._say(state, " Précisons une autre piste.",
                                          " Let's refine another option.")
            state.pending_suggestions = turn.suggestions
            state.history[-1]["text"] = turn.message
        turn.suggestions = [s for s in turn.suggestions
                            if state.recovery_failures.get(normalize(s.value), 0) < 2]
        if not state.draft.race and not any(self._default_race(state, r) for r in state.candidates):
            turn.suggestions.sort(key=lambda s: s.kind == "choose_race")
        if turn.message == previous:
            turn.message += self._say(state, " Précisons une autre piste.",
                                      " Let's refine another option.")
        if not turn.suggestions and state.recovery_failures.get("alternative", 0) < 2:
            turn.suggestions = [self._chip("alternative", self._say(
                state, "Chercher une course préparable", "Find a preparable race"), "retry")]
        state.pending_suggestions = turn.suggestions
        state.history[-1]["text"] = turn.message
        if (state.hints.get("country") == "Spain" and state.hints.get("distance") == "marathon"
                and state.hints.get("months") and not state.draft.race
                and any(self._eligible(r) for r in state.candidates)):
            state, turn = await self._recommend(state, allow_search=False)
            alternatives = self._race_chips(state)
            for chip in alternatives:
                chip.group = self._say(state, "Alternatives", "Alternatives")
            turn.suggestions += alternatives
        return state, turn

    async def _preparable_alternative(self, state, turn):
        original = state.candidates
        try:
            seeds = import_module("runai.discovery.linkup").RACE_SEARCH_SEEDS
            country = state.requested_country or state.hints.get("country")
            names = seeds.get(country, seeds["Italy"])
            attempt = sum(state.recovery_failures.values()) - 2
            name = names[attempt % len(names)]
            hints = {"race_name": name, "named": True, "depth": "standard", "country": country,
                     "search_timeout_s": FIRST_DISCOVERY_TIMEOUT_S * 0.9,
                     "retry_count": state.hints.get("retry_count", 0),
                     "official_date_required": True, "broaden": True,
                     "alternative_scope": "open registration and covered hotel and transport"}
            query = state.query
            state.query = (name + " official open registration preparable alternative"
                           f" recovery {state.hints.get('retry_count', 0)}")
            state.candidates = []
            try:
                await self._collect(state, hints, broadened=True)
            finally:
                state.query = query
            self._prepare_candidates(state)
            alternatives = [r for r in state.candidates if self._default_race(state, r)
                            and self._same_country(state, r)]
        except Exception:  # noqa: BLE001 -- optional recovery never invents an alternative
            alternatives = []
        state.candidates = alternatives + [r for r in original
                                           if r.id not in {a.id for a in alternatives}]
        if alternatives:
            state.draft.race = None
            self._advance(state)
            return self._turn(state, self._say(
                state, f"Je propose {alternatives[0].name} : date officielle, trois agents couverts.",
                f"Try {alternatives[0].name}: official date, all three agents covered."))
        return state, turn

    async def _search_races(self, state):
        deadline = (asyncio.get_running_loop().time() + FIRST_DISCOVERY_TIMEOUT_S
                    if not state.discovery_started or state.hints.get("official_domains")
                    or state.hints.get("verification_only") else None)
        state.discovery_started = True
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
        alternative_ids = set()
        try:
            try:
                flags = await self._collect(state, hints, deadline=deadline)
            except Exception as exc:
                if hints.get("verification_only") or not isinstance(exc, TimeoutError):
                    raise
                narrowed = dict(hints, depth="standard", official_date_required=True,
                                alternative_scope="organizer domain only; preserve city and distance")
                hint = import_module("runai.discovery.linkup").official_search_hint(state.query)
                narrowed.update(hint)
                state.hints["_timeout_recovery"] = True
                state.query += " organizer official date retry"
                flags = await self._collect(state, narrowed, deadline=(
                    asyncio.get_running_loop().time() + FIRST_DISCOVERY_TIMEOUT_S))
                if not state.candidates:
                    raise TimeoutError from exc
            if (state.candidates and not any(self._eligible(r) and self._same_country(state, r)
                                            for r in state.candidates)
                    and not hints.get("verification_only")):
                alternatives = dict(hints, official_date_required=True, depth="deep",
                                    alternative_scope="official dated alternatives", broaden=True)
                target = next((r for r in state.candidates if not self._eligible(r)
                               and self._same_country(state, r) and self._official_hint(r)), None)
                if target:
                    alternatives.update(self._official_hint(target), depth="standard", verification_only=True,
                                        named=True, year=target.race_date.year if target.race_date else self.today.year + 1)
                    state.hints["prefer_requested_country"] = True
                original_candidates = state.candidates
                state.candidates = []
                try:
                    verification_deadline = deadline
                    if target and verification_deadline is None:
                        verification_deadline = asyncio.get_running_loop().time() + FIRST_DISCOVERY_TIMEOUT_S
                    await self._collect(state, alternatives, broadened=True, deadline=verification_deadline)
                except Exception:  # noqa: BLE001 -- optional alternatives must not discard initial results
                    state.candidates = []
                official = [r for r in state.candidates if self._eligible(r)]
                alternative_ids.update(r.id for r in official)
                state.candidates = official + [r for r in original_candidates
                                               if r.id not in {a.id for a in official}
                                               if not any(self._race_identity(r) == self._race_identity(a)
                                                          and r.race_date == a.race_date
                                                          and self._dedupe_distance(r) == self._dedupe_distance(a)
                                                          for a in official)]
                if official:
                    months = hints.get("months")
                    if not months:
                        broadened = "criteria"
                    elif not any(r.race_date and r.race_date.strftime("%Y-%m") in months
                                 for r in official):
                        broadened = "months"
            if (not state.candidates and not flags["past"] and not flags["unsafe"]
                    and not state.hints.get("exact_date") and not hints.get("retry_count")
                    and not hints.get("verification_only")):
                broad = {key: value for key, value in hints.items()
                         if key not in {"months", "month_from", "month_to"}}
                if "year" not in state.hints:
                    broad.pop("year", None)
                broad["broaden"] = True
                if hints.get("named"):
                    try:
                        organizer = import_module("runai.discovery.linkup").official_search_hint(state.query)
                    except (ImportError, AttributeError):
                        organizer = {}
                    if organizer.get("official_domains"):
                        broad.update(organizer, depth="standard", official_date_required=True)
                        broad.pop("broaden", None)
                broadened = "months" if state.hints.get("months") else "criteria"
                if hints.get("named") and not broad.get("broaden"):
                    broadened = None
                flags = await self._collect(state, broad, broadened=True, deadline=deadline)
                if not state.candidates and not broad.get("broaden"):
                    broad = dict(hints, broaden=True)
                    broadened = "criteria"
                    flags = await self._collect(state, broad, broadened=True, deadline=deadline)
            past_found, unsafe_source = flags["past"], flags["unsafe"]
            unsourced_date_found = flags["unsourced"]
        except Exception as exc:  # noqa: BLE001 -- provider failures are returned as scrubbed turns
            previous_chips = state.pending_suggestions.copy()
            state.stage = "discover"
            state, turn = self._turn(
                state,
                self._say(
                    state,
                    "La recherche n'a pas abouti à temps ; essayons une autre piste."
                    if isinstance(exc, TimeoutError) else "La recherche a rencontré un souci, on peut réessayer.",
                    "The search did not finish in time; let's try another query."
                    if isinstance(exc, TimeoutError) else "Search hit a snag; let's try again.",
                ),
                "discovery_failed",
            )
            state.pending_suggestions = previous_chips
            turn.suggestions = self._recovery_chips(state) if (
                hints.get("retry_count") or isinstance(exc, TimeoutError)) else [
                self._chip("retry", self._say(state, "Réessayer", "Retry"), "retry")
            ]
            state.pending_suggestions = turn.suggestions
            if hints.get("named"):
                turn.message += self._say(state, f" Je n'ai pas pu vérifier {state.query} ; je garde cette demande.",
                                         f" I could not verify {state.query}; I am keeping that request.")
                state.history[-1]["text"] = turn.message
            for suggestion in turn.suggestions:
                suggestion.id += f":turn-{len(state.history)}"
            return state, turn
        if not state.candidates:
            state.stage = "discover"
            state, turn = self._turn(
                state,
                self._named_not_found(state) if hints.get("named") and hints.get("city") else self._say(
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
            turn.suggestions = self._recovery_chips(state)
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
        self._resolve_date_conflicts(state)
        self._prepare_candidates(state)
        state.candidates.sort(key=lambda race: (not self._same_country(state, race),
                                                self._preparation_rank(state, race)))
        if (len(state.candidates) == 1 and self._matches_distance(state, state.candidates[0])
                and state.candidates[0].id not in alternative_ids
                and state.hints.get("named") and not hints.get("verification_only") and not broadened) and not (
            state.candidates[0].registration_access and (
                state.candidates[0].registration_access.account_required is True
                or state.candidates[0].registration_access.captcha is True
            )
        ) and self._named_match(state, state.candidates[0]):
            state.draft.race = state.candidates[0]
            state.draft.provenance["race"] = "source"
        self._advance(state)
        found = self._say(
            state,
            "Voici les options sourcées correspondant à ta recherche.",
            "Here are sourced options matching your search.",
        )
        in_period = [r for r in state.candidates if r.race_date
                     and r.race_date.strftime("%Y-%m") in state.hints.get("months", [])]
        if any(self._eligible(r) for r in in_period):
            broadened = None
        if broadened == "months" and in_period:
            found = self._say(
                state, "Une option dans la période reste à confirmer ; voici aussi des éditions officielles à d'autres dates.",
                "An option in the period is still to be confirmed; here are official editions on other dates too.")
        elif broadened == "months":
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
        if state.hints.get("named") and not any(self._named_match(state, r)
                                               for r in state.candidates):
            kind = {"marathon": "marathon", "half": "semi-marathon", "10k": "10 km"}.get(
                state.hints.get("distance"), "course")
            alternatives = "marathons" if kind == "marathon" else "courses"
            found = self._named_not_found(state) + self._say(
                state, f" Voici des {alternatives} proches de ta demande :",
                " Here are "
                f"{'marathons' if kind == 'marathon' else 'races'} close to your request:")
            state.draft.race = None
            self._advance(state)
        if self._preparation_rank(state, state.candidates[0])[-1] != 0:
            found += self._preparation_message(state, state.candidates[0])
        if unsourced_date_found:
            found += " " + self._say(
                state,
                "Certaines dates n'ont aucune source publique : elles restent non vérifiées.",
                "Some dates have no public source: they remain unverified.",
            )
        result, turn = self._turn(state, found)
        if state.hints.get("named"):
            for chip in turn.suggestions:
                race = next((r for r in state.candidates if r.id == chip.value), None)
                if race and not self._named_match(state, race):
                    chip.group = self._say(state, "Alternatives", "Alternatives")
        return result, turn

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

    async def _recommend(self, state, *, allow_search=True):
        direction = None
        if (not state.draft.race and state.hints.get("named") and state.hints.get("city")
                and state.candidates and not any(self._named_match(state, r) for r in state.candidates)):
            state, turn = self._turn(state, self._named_not_found(state) + self._say(
                state, " Choisis une alternative ci-dessous pour changer de course.",
                " Choose an alternative below to change races."))
            for chip in turn.suggestions:
                if chip.kind == "choose_race":
                    chip.group = "Alternatives"
            return state, turn
        if not state.candidates:
            if state.query and not allow_search:
                return self._turn(state, self._say(
                    state, "Gardons cette recherche ; choisis une piste ci-dessous pour continuer.",
                    "Let's keep this search; choose an option below to continue."))
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
        self._prepare_candidates(state)
        suitable.sort(key=lambda r: self._preparation_rank(state, r))
        suitable.sort(key=lambda r: (not (r.race_date and 0 <= (r.race_date - self.today).days <= 300),
                                     r.race_date or date.max))
        if state.draft.race:
            suitable.sort(key=lambda r: r.id != state.draft.race.id)
        if not suitable:
            if not allow_search:
                return self._turn(state, self._say(
                    state, "Choisissons une option ci-dessous ; aucune nouvelle recherche n'est lancée.",
                    "Let's choose an option below; no new search has been started."))
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
        for field, value in [("origin_city", "Paris"),
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
        state, turn = await self._step(state, action)
        unique = []
        seen = set()
        for chip in turn.suggestions:
            if re.fullmatch(r"\d{4}-\d{2}", chip.label):
                chip.label = self._month_label(state, date.fromisoformat(chip.label + "-01"))
            key = (chip.kind, chip.value)
            if key not in seen:
                seen.add(key)
                unique.append(chip)
        if len(unique) > 4:
            races = [s for s in unique if s.kind == "choose_race"]
            distances = [s for s in unique if s.kind == "distance"]
            months = [s for s in unique if s.value.startswith("month:")]
            if turn.ready_to_confirm:
                essential = [s for s in unique if s.kind == "confirm"
                             or s.value == "continue_without_profile"] + races[:1]
            elif distances:
                essential = distances[:3] + races[:1]
            elif months:
                essential = months[:2] + races[:2]
            elif races:
                essential = races
            else:
                essential = months
            selected = (essential + [s for s in unique if s not in essential])[:4]
            unique = [s for s in unique if s in selected]
        turn.suggestions = unique
        state.pending_suggestions = unique.copy()
        previous = state.hints.get("_previous_edition_date")
        if previous and not any(str(previous) in row.get("text", "") for row in state.history[:-1]
                                if row.get("role") == "assistant"):
            turn.message = self._say(state, f"L'édition du {previous} est passée. ",
                                     f"The {previous} edition is over. ") + turn.message
            state.history[-1]["text"] = turn.message
        return state, turn

    async def _step(self, state: GuideState, action: dict):
        original = state
        state = GuideState.model_validate(self._scrub_data(state.model_dump()))
        raw_text = action.get("text", "") or ""
        personal = re.search(
            r"[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}|"
            r"\b(?:je m['’]appelle|my name is|i['’]m called|moi c['’]est)\s+\S+|"
            r"\b(?:ne[e]?\s+le|born\s+on|born\s+in\s+(?:19|20)\d{2}|"
            r"date\s+of\s+birth|date\s+de\s+naissance)\b|"
            r"\b(?:birth|birthday|born|naissance)\s*(?:(?:is|est|le|on)\s+|[:=]\s*)?\d|"
            r"\b(?:my\s+address\s+is|mon\s+adresse)\b|"
            r"\b\d{1,2}[/.-]\d{1,2}[/.-]19\d{2}\b|"
            r"\b(?:19\d{2})-\d{2}-\d{2}\b|"
            r"\b\d+\s+(?:(?:rue|avenue|boulevard|street|road|lane)\b|"
            r"[\w -]+\s+(?:street|road|lane|avenue|st|ave|rd|blvd)\b)",
            normalize(raw_text),
        )
        date_text = re.sub(
            r"\b(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})\b",
            lambda match: f"{match[3]}-{int(match[2]):02d}-{int(match[1]):02d}",
            raw_text,
        )
        text = scrub_text(date_text).strip()
        if personal or "[redacted email]" in text or "[redacted phone]" in text:
            intent = parse_intent(raw_text, today=self.today)
            state.lang = intent.lang
            if intent.city and intent.distance and re.search(r"inscris|register me|sign me up", normalize(raw_text)):
                safe_intent = (f"le {'semi' if intent.distance == 'half' else intent.distance} de {intent.city}"
                               if intent.lang == "fr" else named_query(intent.city, intent.distance))
                state, turn = await self.step(state, {"text": safe_intent})
                state.lang = intent.lang
                refusal = self._say(state, "Je ne conserve pas les données personnelles du chat. Utilise la fiche profil sécurisée.",
                                    "I do not retain personal details from chat. Use the secure profile card.")
                turn.message = refusal + " " + turn.message
                turn.error = "safety_refusal"
                turn.language = state.lang
                state.history[0]["text"] = "[redacted personal data]"
                state.history[-1]["text"] = turn.message
                return state, turn
            if re.search(r"\b(?:my|birth|born|i|phone|address|previous|pay|called)\b", normalize(raw_text)):
                state.lang = "en"
            state.history.append({"role": "user", "text": "[redacted personal data]"})
            return self._turn(state, self._say(
                state, "Je ne peux pas traiter de données personnelles dans le chat. Utilise la fiche profil coureur sécurisée. Je ne conserve pas ces informations.",
                "I cannot process personal details in chat. Please use the secure runner profile card. I do not retain those details."), "safety_refusal")
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
            if chip.value == "continue_without_profile":
                return self._turn(state)
            if chip.kind == "retry" or chip.value.startswith("month:"):
                state.hints["_recovery_action"] = normalize(chip.value)
                self._escalate(state)
                if chip.value == "same_country":
                    state.hints.update(country=state.requested_country, depth="standard")
                    for key in ("city", "race_name", "named", "verification_only", "official_domains"):
                        state.hints.pop(key, None)
                    state.query = (f"{state.requested_country} {state.hints.get('distance', 'marathon')} "
                                   f"official dates recovery {state.hints['retry_count']}")
                if chip.value.startswith("month:"):
                    month = chip.value.removeprefix("month:")
                    state.hints["months"] = [month]
                    state.hints["year"] = int(month[:4])
                    state.hints.pop("exact_date", None)
                    state.hints.pop("broaden", None)
                    state.query = re.sub(r"\s+month:\d{4}-\d{2}", "", state.query)
                    state.query += " " + chip.value
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
                if not self._eligible(state.draft.race):
                    race = state.draft.race
                    key = f"{self._race_identity(race)}|{race.race_date}|{self._dedupe_distance(race)}"
                    if key not in state.verification_attempts:
                        state.verification_attempts.append(key)
                        state.query = race.name + " official edition date"
                        original_candidates = state.candidates
                        state.hints.update(race_name=race.name, named=True, depth="standard",
                                           official_date_required=True, verification_only=True,
                                           year=race.race_date.year if race.race_date else self.today.year + 1)
                        state.hints.update(self._official_hint(race))
                        state.hints["prefer_requested_country"] = True
                        try:
                            state, turn = await self._discover(state)
                        finally:
                            state.hints.pop("official_domains", None)
                            state.hints.pop("verification_only", None)
                        selected = next((r for r in state.candidates
                                         if self._race_identity(r) == self._race_identity(race)
                                         and (self._dedupe_distance(race) is None
                                              or self._dedupe_distance(r) == self._dedupe_distance(race))), None)
                        returned = state.candidates
                        state.draft.race = selected or race
                        state.draft.race.id = race.id
                        state.candidates = [state.draft.race if r.id == race.id else r
                                            for r in original_candidates]
                        for alternative in returned:
                            if any(self._race_identity(r) == self._race_identity(alternative)
                                   and r.race_date == alternative.race_date
                                   and self._dedupe_distance(r) == self._dedupe_distance(alternative)
                                   for r in state.candidates):
                                continue
                            used_ids = {r.id for r in state.candidates}
                            base_id, suffix = alternative.id, 2
                            while alternative.id in used_ids:
                                alternative.id = f"{base_id}:{suffix}"
                                suffix += 1
                            state.candidates.append(alternative)
                        self._advance(state)
                        return self._turn(state, turn.message, turn.error)
                    return self._turn(state, self._say(
                        state, "Date à confirmer : choisis une alternative officielle ou une autre recherche.",
                        "Date to confirm: choose an official alternative or another search."))
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
            text = chip.label if chip.value.startswith("resolve_distance:") else chip.value
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
            r"(?:print|reveal|show|affiche|donne).*(?:system prompt|prompt system|instructions? syst[eè]me|api_key)|"
            r"\b(?:hai_api_key|linkup_api_key|gladia_api_key)\b",
            normalize(text),
        )
        if unsafe:
            safe = text[:unsafe.start()].strip(" ,.;")
            intent = parse_intent(safe, today=self.today)
            if not state.history:
                self._set_language(state, parse_intent(text, today=self.today), typed=True)
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
        if chip and chip.value.startswith("resolve_distance:"):
            intent.distance = chip.value.removeprefix("resolve_distance:")
            intent.correction = True
        if introduction and not intent.fr_cues and not intent.en_cues:
            intent.switch_language = introduced_language
        if re.search(r"\b(?:meteo|weather|poeme?|poetry)\b", normalize(text)) and not (
            intent.distance or intent.named
        ):
            if not state.history:
                self._set_language(state, intent, typed=True)
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
        self._set_language(state, intent, typed=chip is None)
        state.history.append({"role": "user", "text": text})
        if bare_city(text) and (state.stage in {"origin", "confirm", "confirmed"}
                                or (state.query and not state.draft.origin_city)):
            intent.origin_city = bare_city(text)
            intent.city = intent.country = None
        if text.isdecimal() and state.stage in {"nights", "budget"}:
            setattr(intent, "nights" if state.stage == "nights" else "budget_eur", int(text))
        if (intent.nights is not None and not 1 <= intent.nights <= 14
                and intent.problem not in {"distance_conflict", "terrain_conflict"}):
            intent.problem = "nights_range"
        if (intent.budget_eur is not None and intent.budget_eur <= 0
                and intent.problem not in {"distance_conflict", "terrain_conflict"}):
            intent.problem = "budget_range"
        self._update(state, intent)
        if intent.problem and intent.problem != "exact_date":
            problems = list(dict.fromkeys([intent.problem, *intent.problems]))
            explanations = {
                "distance_conflict": ("Un marathon fait 42,2 km, pas 5 km. Choisis la distance.",
                                      "A marathon is 42.2 km, not 5 km. Choose the distance."),
                "terrain_conflict": ("Amsterdam est plate : un trail de montagne y est contradictoire.",
                                     "Amsterdam is flat: a mountain trail there is contradictory."),
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
                state.hints.setdefault("_invalid_fields", []).append("nights")
                state.draft.nights = None
                state.draft.arrival_date = state.draft.departure_date = None
                self._advance(state)
            if "budget_range" in problems:
                state.hints.setdefault("_invalid_fields", []).append("budget_eur")
                state.draft.budget_eur = None
                self._advance(state)
            if set(problems) & {"past_date", "tomorrow", "destination_conflict", "date_conflict",
                                "travelers_range", "unsupported"}:
                state.draft.race = None
                state.draft.arrival_date = state.draft.departure_date = None
                state.candidates = []
                state.stage = "discover"
            state, turn = self._turn(state, " ".join(dict.fromkeys(messages)), intent.problem)
            if intent.problem == "distance_conflict":
                turn.question = self._say(state, "Un marathon de 42,2 km ou une course de 5 km ?",
                                          "A 42.2 km marathon or a 5 km race?")
                turn.suggestions = [self._chip("resolve_distance:marathon", self._say(
                    state, "Un marathon", "A marathon")),
                    self._chip("resolve_distance:5k", self._say(
                        state, "Une course de 5 km", "A 5 km race"))]
                state.pending_suggestions = turn.suggestions
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
                defaults = self._default_distances(state, options)
                if defaults:
                    value = min(defaults)
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
            dodge = bool(re.search(
                r"je (?:ne )?sais pas|aucune idee|i don.?t know|peu importe|whatever",
                normalize(text)))
            return await self._recommend(state, allow_search=not dodge)
        if has_constraints:
            previous_city = (state.draft.race.city if state.draft.race else None) or state.hints.get("city")
            previous_country = (state.draft.race.country if state.draft.race else None) or state.hints.get("country")
            if (intent.same_place or intent.correction and intent.distance) and not intent.city and not intent.country:
                intent.city = bare_city(previous_city) or previous_city if previous_city else None
                intent.country = previous_country
                intent.named = bool(intent.city and intent.distance)
            recovery = normalize(text) in {
                "en suisse", "in switzerland", "en juillet", "in july", "un marathon",
                "a marathon",
            } and bool(state.query) and (state.stage == "discover"
                                         or not self._eligible(state.draft.race))
            if recovery and chip:
                state.hints["_recovery_action"] = normalize(chip.value)
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
                    state.hints.pop("official_domains", None)
                    state.hints.pop("verification_only", None)
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
            if intent.distance:
                state.hints["_requested_distance"] = intent.distance
            if not recovery and intent.country:
                state.requested_country = intent.country
            if recovery:
                place = state.hints.get("city") or state.hints.get("country", "")
                state.query = named_query(place, state.hints.get("distance", "race"))
                state.query += " " + " ".join(state.hints.get("months", []))
                state.query += f" search {state.hints.get('retry_count', 0)}"
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
            values = []
            if intent.origin_city:
                city = self._display_text(state, intent.origin_city)
                values.append(self._say(state, f"départ de {city}", f"leaving from {city}"))
            if intent.nights:
                values.append(self._say(state, f"{intent.nights} nuits", f"{intent.nights} nights"))
            if intent.budget_eur:
                values.append(f"{intent.budget_eur} €")
            if intent.travelers:
                values.append(self._say(state, f"{intent.travelers} voyageurs", f"{intent.travelers} travelers"))
            return self._turn(state, self._say(state, "D'accord, je retiens : ", "Saved: ")
                              + ", ".join(values) + ".")
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
