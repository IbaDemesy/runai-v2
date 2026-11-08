import re
from collections.abc import Awaitable, Callable
from datetime import date, timedelta
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
)

from .fake import FakeDiscovery
from .parse import bare_city, normalize, parse_intent
from .types import GuidedTurn, GuideState, RaceOption, Suggestion

Discover = Callable[[str, dict], Awaitable[list[dict]]]


class GuideEngine:
    def __init__(self, discover: Discover, *, today: date | None = None):
        self.discover = discover
        self.today = today or date.today()
        if isinstance(discover, FakeDiscovery):
            discover.today = self.today

    def _say(self, state, fr, en):
        return en if state.lang == "en" else fr

    def _chip(self, value, label=None, kind="answer", provenance="suggested_default"):
        return Suggestion(
            id=f"{kind}:{value}",
            value=str(value),
            label=label or str(value),
            kind=kind,
            provenance=provenance,
        )

    def _race_chips(self, state):
        return [
            self._chip(
                r.id,
                f"{r.name} — {r.race_date or self._say(state, 'date à confirmer', 'date to confirm')}"
                + self._access_warning(state, r),
                "choose_race",
                "synthetic" if r.synthetic else "source",
            )
            for r in state.candidates
            if not state.draft.race or r.id != state.draft.race.id
        ]

    def _access_warning(self, state, race):
        access = race.registration_access
        if access and (access.account_required is True or access.captcha is True):
            return self._say(state, " — compte ou captcha requis : arrêt humain",
                             " — account or captcha required: human handoff")
        if not access or access.account_required is None or access.captcha is None:
            return self._say(state, " — accès inconnu", " — access unknown")
        return self._say(state, " — observation d'accès, pas une autorisation",
                         " — access observation, not permission")

    def _eligible(self, race):
        return bool(race and race.race_date and race.race_date >= self.today
                    and race.date_status == "official")

    def _distance_values(self, label):
        numbers = []
        for match in re.finditer(
            r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s*(?:[-–—/,;]|and|et)\s*"
            r"\d+(?:[.,]\d+)?)*\s*km\b", label, re.IGNORECASE,
        ):
            numbers.extend(float(value.replace(",", "."))
                           for value in re.findall(r"\d+(?:[.,]\d+)?", match[0]))
        return list(dict.fromkeys(value for value in numbers if value > 0))

    def _pending_distances(self, state):
        race = state.draft.race
        if race and race.distance_km is None:
            return state.hints.get("_race_distances", {}).get(race.id, [])
        return []

    def _turn(self, state, message=None, error=None):
        d = state.draft
        ready = bool(
            self._eligible(d.race)
            and d.origin_city
            and d.nights
            and d.budget_eur
            and not self._pending_distances(state)
        )
        question = None
        chips = []
        if self._pending_distances(state):
            question = self._say(state, "Quelle distance ?", "Which distance?")
            chips = [self._chip(f"{value:g} km", kind="answer", provenance="source")
                     for value in self._pending_distances(state)]
        elif state.stage == "choose_race":
            question = self._say(state, "Laquelle te tente ?", "Which one catches your eye?")
            chips = self._race_chips(state)
            if d.race:
                explanation = self._say(
                    state,
                    "La date de cette course reste à confirmer ; choisissons une autre option.",
                    "This race's date needs confirmation; let's try another option.",
                )
                message = (message + " " if message else "") + explanation
                chips.append(
                    self._chip("retry", self._say(state, "Relancer", "Try again"), "retry")
                )
        elif state.stage in {"origin", "nights", "budget"}:
            if state.stage == "origin":
                choices = [
                    c
                    for c in ["Paris", "Lyon", "Bruxelles", "Genève"]
                    if bare_city(c) != d.race.city
                ][:4]
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
            if d.race.id in state.hints.get("_event_start_ids", []):
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
            if d.race.distance_km is None and not self._pending_distances(state):
                message += self._say(state, " Distance inconnue dans les sources.",
                                     " Distance is unknown in the sources.")
        if d.race and d.race.date_status == "unverified":
            message += self._say(
                state, " Attention : date non vérifiée.", " Warning: unverified date."
            )
        message = scrub_text(message)
        question = scrub_text(question) if question else None
        for chip in chips:
            chip.id += f":turn-{len(state.history)}"
            chip.label = scrub_text(chip.label)
            chip.value = (self._scrub_identifier(chip.value) if chip.kind == "choose_race"
                          else scrub_text(chip.value))
        state.pending_suggestions = chips
        state.history.append({"role": "assistant", "text": message})
        return state, GuidedTurn(
            message=message,
            question=question,
            suggestions=chips,
            candidates=state.candidates,
            draft=d.model_copy(deep=True),
            ready_to_confirm=ready,
            error=error,
        )

    def _advance(self, state):
        d = state.draft
        if not d.race:
            state.stage = "choose_race" if state.candidates else "discover"
        elif not self._eligible(d.race) or self._pending_distances(state):
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

    async def _discover(self, state):
        state.draft.race = None
        state.draft.arrival_date = state.draft.departure_date = None
        state.candidates = []
        state.draft.provenance.pop("distance_km", None)
        state.hints.pop("_race_distances", None)
        state.hints.pop("_event_start_ids", None)
        hints = state.hints.copy()
        if hints.get("months"):
            hints["month_from"] = min(hints["months"])
            hints["month_to"] = max(hints["months"])
            hints.setdefault("year", int(hints["month_from"][:4]))
        if hints.get("named"):
            hints.setdefault("race_name", state.query)
        past_found = False
        unsafe_source = False
        try:
            rows = await self.discover(state.query, hints)
            for row in rows:
                row = self._scrub_data(row)
                if self._source_instruction(row):
                    unsafe_source = True
                    continue
                try:
                    race = RaceOption.model_validate(row)
                except ValidationError:
                    continue
                if race.race_date and race.race_date < self.today:
                    past_found = True
                    continue
                if state.hints.get("exact_date") and (
                    not race.race_date or race.race_date.isoformat() != state.hints["exact_date"]
                ):
                    continue
                year = state.hints.get("year")
                months = state.hints.get("months")
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
                        state.hints.setdefault("_race_distances", {})[race.id] = distances
                        state.hints.setdefault("_event_start_ids", []).append(race.id)
                    if len(race.distance_label) > 24:
                        compact = " / ".join(f"{value:g}" for value in distances) + " km"
                        if re.search(r"\d\s*[–—-]\s*\d", race.distance_label) and len(distances) == 2:
                            compact = f"{distances[0]:g}–{distances[1]:g} km"
                        race.distance_label = compact if distances and len(compact) <= 24 else self._say(
                            state, "Plusieurs distances" if distances else "Distance inconnue",
                            "Several distances" if distances else "Distance unknown")
                    state.candidates.append(race)
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
            turn.suggestions = [
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
        if len(state.candidates) == 1 and state.hints.get("named") and not (
            state.candidates[0].registration_access and (
                state.candidates[0].registration_access.account_required is True
                or state.candidates[0].registration_access.captcha is True
            )
        ):
            state.draft.race = state.candidates[0]
            state.draft.provenance["race"] = "source"
        self._advance(state)
        return self._turn(
            state,
            self._say(
                state,
                "Voici les options sourcées correspondant à ta recherche.",
                "Here are sourced options matching your search.",
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
        suitable = [r for r in state.candidates if self._eligible(r)]
        if not state.hints.get("named"):
            suitable.sort(key=lambda r: bool(r.registration_access and (
                r.registration_access.account_required is True or r.registration_access.captcha is True
            )))
        if state.draft.race:
            suitable.sort(key=lambda r: r.id != state.draft.race.id)
        if not suitable:
            return self._turn(state, self._say(
                state, "Aucune date future vérifiée ; il faut une nouvelle source.",
                "No verified future date is available; we need a new source."))
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
        if direction:
            message = direction + " " + message
        access = race.registration_access
        if access and (access.account_required is True or access.captcha is True):
            return self._turn(state, message + self._access_warning(state, race))
        state.draft.race = race
        state.draft.provenance["race"] = "source"
        for field, value in [("origin_city", "Paris" if race.city != "Paris" else "Lyon"),
                             ("nights", 2), ("budget_eur", 450)]:
            if getattr(state.draft, field) is None:
                setattr(state.draft, field, value)
                state.draft.provenance[field] = "suggested_default"
        self._advance(state)
        return self._turn(state, message)

    async def step(self, state: GuideState, action: dict):
        original = state
        state = GuideState.model_validate(self._scrub_data(state.model_dump()))
        text = scrub_text(action.get("text", "")).strip()
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
            chip = next(
                (s for s in state.pending_suggestions if s.kind in {"answer", "confirm"}), None
            )
        if chip:
            if chip.kind == "retry":
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
                    state.draft, field, chip.value if field == "origin_city" else int(chip.value)
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
            return self._turn(state)
        intent = parse_intent(text, today=self.today)
        if not state.history:
            state.lang = intent.lang
        if intent.switch_language:
            state.lang = intent.switch_language
        if re.search(
            r"ignore.*(?:instructions?|rules)|system\s*:|developer\s*:|override|"
            r"\b(?:pay|payer|paie|payment|paiement|buy|acheter|purchase|"
            r"submit|soumettre|envoyer|bypass|contourner)\b|"
            r"(?:create|creer|cree|ouvre|open).*(?:account|compte)|"
            r"(?:accept|accepter|accepte).*(?:terms|conditions|consent|cgu)",
            normalize(text),
        ):
            return self._turn(state, self._say(
                state, "Je ne peux pas payer, créer de compte, accepter des conditions, "
                "soumettre un formulaire, contourner un captcha ou ignorer les règles. "
                "Je peux aider à préparer un déplacement sans engagement.",
                "I cannot pay, create accounts, accept terms, submit forms, bypass captchas "
                "or override rules. I can help prepare a trip without commitment."), "safety_refusal")
        state.history.append({"role": "user", "text": text})
        if self._pending_distances(state):
            distance = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:km)?", text, re.IGNORECASE)
            if distance:
                value = float(distance[1].replace(",", "."))
                if value not in self._pending_distances(state):
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
        if bare_city(text) and state.stage in {"origin", "confirm", "confirmed"}:
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
        has_constraints = bool(intent.distance or intent.city or intent.country
                               or intent.months or intent.year or intent.problem == "exact_date")
        if intent.deferred and not has_constraints:
            return await self._recommend(state)
        if has_constraints:
            if intent.distance or intent.country or intent.city:
                state.query = text
                state.hints = {}
            elif not state.query:
                state.query = text
            if intent.named:
                state.hints["race_name"] = text
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
            if intent.problem == "exact_date":
                state.hints["exact_date"] = re.search(r"\d{4}-\d{2}-\d{2}", text)[0]
            state, turn = await self._discover(state)
            if intent.deferred and state.candidates:
                return await self._recommend(state)
            return state, turn
        if state.draft.race and any(
            getattr(intent, f) is not None
            for f in ["origin_city", "nights", "budget_eur", "travelers"]
        ):
            self._advance(state)
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
            and not self._pending_distances(state)
            and d.origin_city
            and d.nights
            and d.budget_eur
            and d.arrival_date
            and d.departure_date
        ):
            raise ValueError("Trip is not ready to confirm")
        return {
            key: value for key, value in d.model_dump(mode="json").items() if key != "provenance"
        }
