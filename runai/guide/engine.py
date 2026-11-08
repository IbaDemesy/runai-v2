import re
from collections.abc import Awaitable, Callable
from datetime import date, timedelta

from pydantic import ValidationError

from .parse import bare_city, normalize, parse_intent
from .types import GuidedTurn, GuideState, RaceOption, Suggestion

Discover = Callable[[str, dict], Awaitable[list[dict]]]


class GuideEngine:
    def __init__(self, discover: Discover, *, today: date | None = None):
        self.discover = discover
        self.today = today or date.today()

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
                f"{r.name} — {r.race_date or self._say(state, 'date à confirmer', 'date to confirm')}",
                "choose_race",
                "synthetic" if r.synthetic else "source",
            )
            for r in state.candidates
            if not state.draft.race or r.id != state.draft.race.id
        ]

    def _turn(self, state, message=None, error=None):
        d = state.draft
        ready = bool(
            d.race
            and d.race.race_date
            and d.race.date_status in {"official", "unverified"}
            and d.origin_city
            and d.nights
            and d.budget_eur
        )
        question = None
        chips = []
        if state.stage == "choose_race":
            question = self._say(state, "Laquelle te tente ?", "Which one catches your eye?")
            chips = self._race_chips(state)
            if d.race:
                message = self._say(
                    state,
                    "La date de cette course reste à confirmer ; choisissons une autre option.",
                    "This race's date needs confirmation; let's try another option.",
                )
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
            message = self._say(
                state,
                f"Voilà ton idée de séjour : {d.race.name}, au départ de {d.origin_city}, {d.nights} nuits, budget {d.budget_eur} € pour {d.travelers} personne(s), du {d.arrival_date} au {d.departure_date}.",
                f"Here's your trip: {d.race.name}, leaving from {d.origin_city}, {d.nights} nights, budget €{d.budget_eur} for {d.travelers} traveler(s), {d.arrival_date} to {d.departure_date}.",
            )
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
        if d.race and d.race.date_status == "unverified":
            message += self._say(
                state, " Attention : date non vérifiée.", " Warning: unverified date."
            )
        message = message.replace("?", ".")
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
        elif not d.race.race_date or d.race.date_status not in {"official", "unverified"}:
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
        try:
            rows = await self.discover(state.query, state.hints)
            for row in rows:
                try:
                    race = RaceOption.model_validate(row)
                except ValidationError:
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
            return state, turn
        if len(state.candidates) == 1 and state.hints.get("named"):
            state.draft.race = state.candidates[0]
            state.draft.provenance["race"] = "source"
        self._advance(state)
        return self._turn(
            state,
            self._say(
                state,
                f"Bonne idée ! Pour « {state.query} », voici ce que j'ai trouvé.",
                f"Great idea! For “{state.query}”, here's what I found.",
            ),
        )

    async def start(self, text):
        return await self.step(GuideState(), {"text": text})

    async def step(self, state: GuideState, action: dict):
        original = state
        state = state.model_copy(deep=True)
        text = action.get("text", "").strip()
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
                return original, turn
        elif normalize(text) in {"oui", "ok", "parfait", "yes", "sounds good"}:
            chip = next(
                (s for s in state.pending_suggestions if s.kind in {"answer", "confirm"}), None
            )
        if chip:
            if chip.kind == "retry":
                return await self._discover(state)
            if chip.kind == "confirm":
                self.trip_payload(state)
                state.stage = "confirmed"
                return self._turn(state)
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
        state.history.append({"role": "user", "text": text})
        intent = parse_intent(text, today=self.today)
        if state.stage == "discover" or intent.lang == "en":
            state.lang = intent.lang
        if bare_city(text) and state.stage in {"origin", "confirm", "confirmed"}:
            intent.origin_city = bare_city(text)
            intent.city = intent.country = None
        if text.isdecimal() and state.stage in {"nights", "budget"}:
            setattr(intent, "nights" if state.stage == "nights" else "budget_eur", int(text))
        self._update(state, intent)
        if intent.distance or intent.city or intent.country or intent.months or intent.year:
            state.query = text
            if intent.distance or intent.country or intent.city:
                state.hints = {}
            elif intent.year:
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
            return await self._discover(state)
        if state.draft.race and any(
            getattr(intent, f) is not None
            for f in ["origin_city", "nights", "budget_eur", "travelers"]
        ):
            self._advance(state)
        return self._turn(
            state,
            self._say(
                state,
                f"Bien reçu : « {text} ». On peut ajuster tout ça ensemble, les raccourcis restent là pour t'aider.",
                f"Got it: “{text}”. We can adjust this together; the shortcuts are here to help.",
            ),
        )

    def trip_payload(self, state):
        d = state.draft
        if not (
            d.race
            and d.race.race_date
            and d.race.date_status in {"official", "unverified"}
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
