import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = json.loads((ROOT / "docs/tickets/index.json").read_text())
IDS = [f"R4-0{n}" for n in range(1, 6)]


def test_queue_has_exactly_the_five_r4_tickets_with_unique_ids():
    ids = [ticket["id"] for ticket in QUEUE]
    assert ids == IDS
    assert len(set(ids)) == len(ids)
    for ticket in QUEUE:
        assert ticket["round"] == 4
        assert ticket["priority"] in {"P0", "P1"}
        assert ticket["title"].startswith(ticket["id"] + ": ")
        assert ticket["merge_note"].strip()


def test_file_lists_are_exact_unique_and_disjoint():
    owner = {}
    for ticket in QUEUE:
        files = ticket["files"]
        assert files and len(files) == len(set(files)), ticket["id"]
        for path in files:
            assert not path.startswith("/") and ".." not in path and "*" not in path
            assert path not in owner, f"{path} owned by {owner.get(path)} and {ticket['id']}"
            owner[path] = ticket["id"]
        assert f"docs/handoff/{ticket['id']}.md" in files
    integration = next(t["files"] for t in QUEUE if t["id"] == "R4-01")
    for path in ("CONTRACTS.md", "AGENTS.md", "HANDOFF.md", "runai/agents/hclient.py",
                 "docs/eval/round-4-acceptance.md"):
        assert path in integration, path


def test_dependencies_and_merge_order_are_valid():
    by_id = {ticket["id"]: ticket for ticket in QUEUE}
    for ticket in QUEUE:
        assert isinstance(ticket["merge_order"], int) and ticket["merge_order"] >= 1
        for dep in ticket["depends_on"]:
            assert dep in by_id and dep != ticket["id"]
            assert by_id[dep]["merge_order"] < ticket["merge_order"]
    assert "PR-B" in by_id["R4-01"]["merge_note"]


def test_ticket_documents_match_queue():
    for ticket in QUEUE:
        text = (ROOT / f"docs/tickets/{ticket['id']}.md").read_text()
        assert text.startswith(f"# {ticket['title']}\n")
        listed = re.findall(r"^- `([^`]+)`$", text.split("## Allowed files", 1)[1], re.MULTILINE)
        assert listed == ticket["files"]


def test_owner_feedback_records_round_four_requirements():
    text = (ROOT / "docs/feedback/owner.md").read_text()
    round4 = text.split("## Round 4", 1)[1].split("\n## Round 3", 1)[0]
    for marker in ("(a)", "(b)", "(c)", "(d)", "ChatGPT", "BELOW", "JSON", "Strava",
                   "near-perfect", "live success definition", "pre-payment", "parallel"):
        assert marker in round4, marker
    assert text.index("## Round 4") < text.index("## Round 3")


def test_shared_docs_reference_current_queue_not_frozen_scope():
    for name in ("AGENTS.md", "PLAN.md", "HANDOFF.md", "README.md"):
        text = (ROOT / name).read_text()
        assert "R4-01" in text and "R4-05" in text, name
        assert not re.search(r"\bR3-0[1-5]\b", text), name
        assert not re.search(r"Milan[- ]only (?:journey|scope)|frozen journey", text, re.IGNORECASE), name
    contract = (ROOT / "CONTRACTS.md").read_text()
    for marker in ("background", "reason_code", "load_registry", "coverage(", "language",
                   "P7", "alternatives", "P8", "registration_coverage", "P9", "preparation",
                   "P10", "handoff-only"):
        assert marker in contract, marker
