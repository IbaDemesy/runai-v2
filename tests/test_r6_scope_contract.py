import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
QUEUE = json.loads((ROOT / "docs/tickets/index.json").read_text())
IDS = [f"R6-0{n}" for n in range(1, 6)]
INFERRED = "(spec inferred by R6-01 from round-5 eval; planner may amend)"
INTEGRATION_FILES = [
    "runai/agents/hclient.py", "runai/agents/scrub.py", "runai/agents/hotel.py",
    "runai/app.py", "runai/models.py", "runai/providers.py",
    "fixtures/synthetic-journey.json", "docs/site-policy.d/hotel.json",
    "tests/test_hclient.py", "tests/test_scrub.py", "tests/test_agent_hotel.py",
    "tests/test_api_guided.py", "tests/test_units.py", "tests/test_journey_e2e.py",
    "tests/test_api_privacy.py", "tests/test_api_discovery_progress.py",
    "tests/test_r5_scope_contract.py", "tests/test_r6_scope_contract.py",
    "tests/fixtures/h_checkpoint_observations.json",
    "tests/fixtures/h_vueling_observations.json", "tests/fixtures/h_ihg_observations.json",
    "docs/evidence/h-client.md", "docs/evidence/hotel.md", "AGENTS.md", "PLAN.md",
    "CONTRACTS.md", "README.md", "HANDOFF.md", "docs/feedback/owner.md",
    "docs/tickets/index.json", "docs/tickets/R6-01.md", "docs/tickets/R6-02.md",
    "docs/tickets/R6-03.md", "docs/tickets/R6-04.md", "docs/tickets/R6-05.md",
    "docs/handoff/R6-01.md",
]
UI_FILES = [
    "static/app.js", "static/index.html", "static/styles.css", "tests/test_static_ui.py",
    "docs/evidence/R6-05-ui.md", "docs/handoff/R6-05.md",
]
OWNER_FEEDBACK = (
    "(a) Suggestions must be redesigned like ChatGPT/OpenAI suggestion UI: elegant, clear, "
    "clickable suggestion pills/cards under the assistant reply, not raw buttons. "
    "(b) Each new assistant question must appear BELOW the latest proposals in the thread "
    "(chronological chat flow), never appended next to the initial question. "
    "(c) After launch: keep the 3 agent cards, and below them the user must ONLY SEE THE "
    "AGENTS ACTING LIVE (live browser view / animated screenshots) through to the final "
    "pre-payment step. NEVER show raw task text, prompts, JSON or technical logs to the "
    "user; at most short human-friendly status lines. "
    "(d) First reply takes ~1 min with no feedback: add immediate streaming/typing/progress "
    "feedback. The owner wants by morning a fully functional, beautiful, near-perfect site."
)
LIVE_SUCCESS = (
    "the assistant itself proposes the race (user never supplies the date), then the 3 H "
    "agents run LIVE in parallel (race bib/registration + hotel + transport), each reaching "
    "the pre-payment stop, and the user SEES all three agents working live on the page."
)


def test_queue_has_exactly_the_five_r6_tickets_with_unique_ids():
    ids = [ticket["id"] for ticket in QUEUE]
    assert ids == IDS
    assert len(set(ids)) == len(ids)
    for ticket in QUEUE:
        assert ticket["round"] == 6
        assert ticket["priority"] in {"P0", "P1"}
        assert ticket["title"].startswith(f"{ticket['id']}: {ticket['priority']} ")
        assert ticket["spec"].strip() and ticket["acceptance"].strip()
        assert ticket["merge_note"].strip()


def test_file_lists_are_exact_unique_and_disjoint():
    owner = {}
    for ticket in QUEUE:
        files = ticket["files"]
        assert files and len(files) == len(set(files)), ticket["id"]
        for path in files:
            relative = PurePosixPath(path)
            assert not relative.is_absolute() and relative.as_posix() == path
            assert ".." not in relative.parts and not any(c in path for c in "*?[]\\:")
            assert path not in owner, f"{path} owned by {owner.get(path)} and {ticket['id']}"
            owner[path] = ticket["id"]
        assert f"docs/handoff/{ticket['id']}.md" in files
    by_id = {ticket["id"]: ticket["files"] for ticket in QUEUE}
    assert by_id["R6-01"] == INTEGRATION_FILES
    assert by_id["R6-05"] == UI_FILES
    assert owner["docs/site-policy.json"] == "R6-02"
    assert owner["docs/site-policy.d/registration.json"] == "R6-04"


def test_dependencies_and_merge_order_are_valid_and_allow_any_order():
    by_id = {ticket["id"]: ticket for ticket in QUEUE}
    for ticket in QUEUE:
        assert isinstance(ticket["merge_order"], int) and ticket["merge_order"] >= 1
        for dep in ticket["depends_on"]:
            assert dep in by_id and dep != ticket["id"]
            assert by_id[dep]["merge_order"] < ticket["merge_order"]
        assert ticket["depends_on"] == []
        assert ticket["merge_order"] == 1
        assert "Any merge order" in ticket["merge_note"]


def test_ticket_documents_match_queue_and_identify_inferred_specs():
    for ticket in QUEUE:
        text = (ROOT / f"docs/tickets/{ticket['id']}.md").read_text()
        assert text.startswith(f"# {ticket['title']}\n")
        section = text.split("## Allowed files", 1)[1].split("## Acceptance", 1)[0]
        listed = re.findall(r"^- `([^`]+)`$", section, re.MULTILINE)
        assert listed == ticket["files"]
        assert ticket["spec"] in text and ticket["acceptance"] in text
        if ticket["id"] in {"R6-02", "R6-03", "R6-04"}:
            assert INFERRED in ticket["spec"] and INFERRED in text


def test_owner_feedback_records_round_six_requirements_verbatim():
    text = (ROOT / "docs/feedback/owner.md").read_text()
    assert text.startswith("## Round 6")
    round6 = text.split("\n## Round 5", 1)[0]
    assert OWNER_FEEDBACK in round6
    assert LIVE_SUCCESS in round6
    for marker in ("single most important criterion", "Strava", "Accor", "adversarial",
                   "FR/EN", "vague", "contradictory", "off-topic", "injection", "130",
                   "unknown/expired", "robots.txt is not", "in_session_only",
                   "ONE MISSION AT A TIME", "41/100", "0/5", "7.5/10"):
        assert marker in round6, marker
    assert text.index("## Round 6") < text.index("## Round 5") < text.index("## Round 4")


def test_shared_docs_reference_current_queue_not_stale_scope():
    for name in ("AGENTS.md", "PLAN.md", "HANDOFF.md", "README.md"):
        text = (ROOT / name).read_text()
        assert "R6-01" in text and "R6-05" in text, name
        assert not re.search(r"\bR[1-5]-0[1-5]\b", text), name
        assert not re.search(
            r"(?:Milan|Milano)[- ]only|frozen[- ]journey|round[- ]5 queue|round-five queue",
            text, re.IGNORECASE,
        ), name
    contract = (ROOT / "CONTRACTS.md").read_text()
    for marker in ("background", "reason_code", "load_registry", "coverage(", "language",
                   "P7", "alternatives", "P8", "registration_coverage", "P9", "preparation",
                   "P10", "handoff-only", "P11", "checkpoint", "force_answer", "P12",
                   "gateway_city", "keep_fragment", "blocked_url_host", "P13",
                   "checkpoint_unverified", "checkpoint_reached"):
        assert marker in contract, marker
