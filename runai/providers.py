import asyncio
import json
from pathlib import Path
from typing import Protocol

from runai.models import Framing, JourneyPlan, Kind, StepResult

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/synthetic-journey.json"
SITES = {
    Kind.registration: "https://www.milanomarathon.it/",
    Kind.hotel: "https://all.accor.com/",
    Kind.transport: "https://www.trenitalia.com/",
}


class SearchProvider(Protocol):
    async def search(self, framing: Framing) -> JourneyPlan: ...


class AgentRunner(Protocol):
    async def run(self, kind: Kind, plan: JourneyPlan) -> StepResult: ...


class VoiceProvider(Protocol):
    async def transcribe(self, audio: bytes) -> str: ...


class FakeSearch:
    async def search(self, framing: Framing) -> JourneyPlan:
        return JourneyPlan(framing=framing, sites=SITES)


class FakeVoice:
    async def transcribe(self, audio: bytes) -> str:
        if not audio:
            raise ValueError("Empty audio")
        return "SYNTHETIC: Milano Marathon, Paris, 2 nuits, budget 600 EUR"


class FakeRunner:
    async def run(self, kind: Kind, plan: JourneyPlan) -> StepResult:
        await asyncio.sleep(0)
        return StepResult(
            kind=kind,
            status="ready_for_payment",
            summary="SYNTHETIC: preparation simulated; open official site to continue manually.",
            handoff_url=plan.sites[kind],
            synthetic=True,
        )


class ReplayRunner:
    def __init__(self, path: Path = FIXTURE):
        trace = json.loads(path.read_text())
        if trace.get("schema_version") != 1:
            raise ValueError("Unsupported replay schema_version")
        if trace.get("provenance") != "synthetic":
            raise ValueError("Only the checked-in synthetic trace is supported")
        self.results = {Kind(row["kind"]): StepResult.model_validate(row) for row in trace["results"]}
        if set(self.results) != set(Kind):
            raise ValueError("Replay must contain all three steps")
        for result in self.results.values():
            if not result.synthetic or not result.handoff_url:
                raise ValueError("Invalid synthetic replay")

    async def run(self, kind: Kind, plan: JourneyPlan) -> StepResult:
        await asyncio.sleep(0)
        return self.results[kind].model_copy(deep=True)


class LiveSearch:
    async def search(self, framing: Framing) -> JourneyPlan:
        raise NotImplementedError("Live Linkup search not implemented; requires LINKUP_API_KEY")


class LiveRunner:
    async def run(self, kind: Kind, plan: JourneyPlan) -> StepResult:
        raise NotImplementedError("Live H runner not implemented; requires HAI_API_KEY")


class LiveVoice:
    async def transcribe(self, audio: bytes) -> str:
        raise NotImplementedError("Live Gladia voice not implemented; requires GLADIA_API_KEY")
