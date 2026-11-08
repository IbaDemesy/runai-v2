import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = json.loads((ROOT / "docs/tickets/index.json").read_text())
IDS = [f"R2-0{n}" for n in range(1, 6)]


def test_queue_has_exactly_the_five_r2_tickets_with_unique_ids():
    ids = [ticket["id"] for ticket in QUEUE]
    assert ids == IDS
    assert len(set(ids)) == len(ids)
    for ticket in QUEUE:
        assert ticket["round"] == 2
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
    assert "CONTRACTS.md" in next(t["files"] for t in QUEUE if t["id"] == "R2-05")


def test_dependencies_and_merge_order_are_valid():
    by_id = {ticket["id"]: ticket for ticket in QUEUE}
    for ticket in QUEUE:
        assert isinstance(ticket["merge_order"], int) and ticket["merge_order"] >= 1
        for dep in ticket["depends_on"]:
            assert dep in by_id and dep != ticket["id"]
            assert by_id[dep]["merge_order"] < ticket["merge_order"]
    assert set(by_id["R2-05"]["depends_on"]) == set(IDS[:4])


def test_ticket_documents_match_queue():
    for ticket in QUEUE:
        text = (ROOT / f"docs/tickets/{ticket['id']}.md").read_text()
        assert text.startswith(f"# {ticket['title']}\n")
        listed = re.findall(r"^- `([^`]+)`$", text.split("## Allowed files", 1)[1], re.MULTILINE)
        assert listed == ticket["files"]


def test_owner_feedback_records_round_two_requirements():
    text = (ROOT / "docs/feedback/owner.md").read_text()
    for marker in ("(a)", "(b)", "(c)", "(d)", "ChatGPT", "BELOW", "JSON",
                   "Adversarial", "Accor", "live success definition", "pre-payment"):
        assert marker in text, marker


def test_shared_docs_reference_current_queue_not_frozen_scope():
    for name in ("AGENTS.md", "PLAN.md", "HANDOFF.md", "README.md"):
        text = (ROOT / name).read_text()
        assert "R2-05" in text, name
        assert not re.search(r"Milan[- ]only (?:journey|scope)|frozen journey", text, re.IGNORECASE), name
    assert "background" in (ROOT / "CONTRACTS.md").read_text()
