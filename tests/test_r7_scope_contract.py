import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
QUEUE = json.loads((ROOT / "docs/tickets/index.json").read_text())
IDS = [f"R7-0{n}" for n in range(1, 6)]
EXPECTED_FILES = {
    "R7-01": [
        "runai/agents/hclient.py",
        "runai/agents/scrub.py",
        "runai/app.py",
        "runai/models.py",
        "runai/providers.py",
        "fixtures/synthetic-journey.json",
        "tests/test_hclient.py",
        "tests/test_scrub.py",
        "tests/test_api_guided.py",
        "tests/test_api_privacy.py",
        "tests/test_api_profile.py",
        "tests/test_units.py",
        "tests/test_journey_e2e.py",
        "tests/test_api_discovery_progress.py",
        "tests/test_r6_scope_contract.py",
        "tests/test_r7_scope_contract.py",
        "tests/fixtures/h_checkpoint_observations.json",
        "tests/fixtures/h_prefill_observations.json",
        "docs/evidence/h-client.md",
        "AGENTS.md",
        "PLAN.md",
        "CONTRACTS.md",
        "README.md",
        "HANDOFF.md",
        "docs/feedback/owner.md",
        "docs/tickets/index.json",
        "docs/tickets/R7-01.md",
        "docs/tickets/R7-02.md",
        "docs/tickets/R7-03.md",
        "docs/tickets/R7-04.md",
        "docs/tickets/R7-05.md",
        "docs/handoff/R7-01.md"
    ],
    "R7-02": [
        "runai/agents/transport.py",
        "runai/agents/site_policy.py",
        "docs/site-policy.json",
        "docs/site-policy.d/transport.json",
        "tests/test_agent_transport.py",
        "tests/test_site_policy.py",
        "docs/evidence/transport.md",
        "docs/handoff/R7-02.md"
    ],
    "R7-03": [
        "runai/agents/hotel.py",
        "runai/agents/registration.py",
        "docs/site-policy.d/hotel.json",
        "docs/site-policy.d/registration.json",
        "tests/test_agent_hotel.py",
        "tests/test_agent_registration.py",
        "docs/evidence/hotel.md",
        "docs/evidence/registration.md",
        "docs/handoff/R7-03.md"
    ],
    "R7-04": [
        "runai/guide/engine.py",
        "runai/guide/parse.py",
        "runai/guide/fake.py",
        "runai/guide/types.py",
        "runai/discovery/linkup.py",
        "tests/test_guide_engine.py",
        "tests/test_guide_parse.py",
        "tests/test_guide_adversarial.py",
        "tests/test_discovery_linkup.py",
        "docs/handoff/R7-04.md"
    ],
    "R7-05": [
        "static/index.html",
        "static/app.js",
        "static/styles.css",
        "tests/test_static_ui.py",
        "docs/handoff/R7-05.md"
    ]
}
EXPECTED_TITLES = {
    "R7-01": "R7-01: P0 core/integration: P14 runner-profile prefill (in-memory, scrubbed) + safety update, runtime fallback to task alternatives after provider_error/site_unreachable_in_h, P13 verification fixes for Njuko form_individual-form and hotel-bb room list, Njuko white-label scrub, stale docs (AGENTS.md Accor/personal-data/Milan), owner decision record, R7 queue",
    "R7-02": "R7-02: P0 transport that covers every eval route from Paris and reaches a selected round-trip fare (and passenger page with prefill): big-site adapters (SNCF Connect, Trainline, Omio, Trenitalia, Google Flights/airline sites), demote Vueling, SBB Half-Fare drift fix, Brunnen/Stoos gateway",
    "R7-03": "R7-03: P0 hotel + registration reach further: Booking.com/Accor/Hilton hotel adapters (Berlin, Den Haag, Brunnen/Stoos, Lisbon), correct hotel location/dates, guest-details prefill; registration for majors (Berlin, Lisbon, NN CPC, Frankfurt, Valencia) with participant-form prefill up to the pre-payment/terms stop",
    "R7-04": "R7-04: P1 guide: fewest questions (auto-defaults, one-click confirm), origin correction never re-searches races (A04), nonexistent race said honestly (A05), Valencia/major races found (A03), dodge without failing re-search (A02), dedupe (A08/A09), runner-profile prompt once before confirm, clean synthetic labels, adversarial suite incl. R6 failures",
    "R7-05": "R7-05: P0 design polish to >=9/10 (Strava-grade): secure runner-profile card (once, privacy note, fake-safe), three live agent cards that never look broken at launch, honest CTA per covered agents, 'advanced as far as possible' end states (prefilled/at payment), copy/placeholder fixes, mobile"
}
OWNER_DECISION = (
    "OWNER DECISION (rounds 7-8, TOP PRIORITY, overrides older site-policy notes incl. "
    "the Accor note): NO site is excluded anymore for terms-of-service reasons "
    "(Booking, Trainline, SNCF Connect, Accor, Hilton, Omio, Google Flights/Hotels, "
    "Trenitalia, SBB... are all allowed; see docs/site-policy.json allowed_owner_rule "
    "and docs/handoff/lift-site-exclusions.md). Add adapters for the big sites where "
    "that makes runs reach further. Goal: H runs that ADVANCE AS FAR AS POSSIBLE "
    "(dates, room, fare, distance selected, cart/summary reached) and MINIMIZE THE "
    "CLIENT'S ACTIONS: the chatbot picks sensible defaults itself, asks as few "
    "questions as possible, the user ideally only confirms and then only has to "
    "review and pay. OWNER APPROVED PERSONAL-DATA PREFILL: the chatbot asks the "
    "runner profile ONCE (full name, email, phone, birth date, gender, nationality, "
    "address if needed) and the H agents may TYPE these into registration/hotel/"
    "transport forms (passenger/guest/participant details) to advance as far as "
    "possible. Never store that data in the repo, logs, evidence, screenshots "
    "committed to git or eval reports (use clearly fake test identities in "
    "evaluations, e.g. 'Test Runner'). Record this decision in docs/feedback/"
    "owner.md and update CONTRACTS.md/safety checks accordingly. Keep the hard "
    "guardrails: never pay, never create accounts, never accept terms/medical "
    "consent, never submit final forms, never bypass captchas; honest blocked states."
)


def test_queue_has_exactly_the_five_r7_tickets_with_unique_ids():
    ids = [ticket["id"] for ticket in QUEUE]
    assert ids == IDS
    assert len(set(ids)) == len(ids)
    for ticket in QUEUE:
        assert ticket["round"] == 7
        assert ticket["priority"] == ("P1" if ticket["id"] == "R7-04" else "P0")
        assert ticket["title"] == EXPECTED_TITLES[ticket["id"]]
        assert ticket["spec"].strip() and ticket["acceptance"].strip()
        assert ticket["merge_note"].strip()


def test_file_lists_are_exact_unique_and_disjoint():
    owner = {}
    for ticket in QUEUE:
        files = ticket["files"]
        assert files == EXPECTED_FILES[ticket["id"]]
        assert files and len(files) == len(set(files)), ticket["id"]
        for path in files:
            relative = PurePosixPath(path)
            assert not relative.is_absolute() and relative.as_posix() == path
            assert ".." not in relative.parts and not any(c in path for c in "*?[]\\:")
            assert path not in owner, f"{path} owned by {owner.get(path)} and {ticket['id']}"
            owner[path] = ticket["id"]
        assert f"docs/handoff/{ticket['id']}.md" in files
    assert owner["docs/site-policy.json"] == "R7-02"
    assert owner["runai/agents/site_policy.py"] == "R7-02"
    for kind in ("hotel", "registration"):
        assert owner[f"runai/agents/{kind}.py"] == "R7-03"
        assert owner[f"docs/site-policy.d/{kind}.json"] == "R7-03"
    assert owner["runai/guide/engine.py"] == "R7-04"
    assert owner["runai/discovery/linkup.py"] == "R7-04"


def test_dependencies_and_merge_order_are_valid_and_allow_any_order():
    by_id = {ticket["id"]: ticket for ticket in QUEUE}
    for ticket in QUEUE:
        assert type(ticket["merge_order"]) is int and ticket["merge_order"] >= 1
        for dep in ticket["depends_on"]:
            assert dep in by_id and dep != ticket["id"]
            assert by_id[dep]["merge_order"] < ticket["merge_order"]
        assert ticket["depends_on"] == []
        assert ticket["merge_order"] == 1
        assert "Any merge order" in ticket["merge_note"]
        assert "R7-01" in ticket["merge_note"] and "rebases last" in ticket["merge_note"]


def test_ticket_documents_match_queue():
    for ticket in QUEUE:
        text = (ROOT / f"docs/tickets/{ticket['id']}.md").read_text()
        assert text.startswith(f"# {ticket['title']}\n")
        assert f"Round: 7 · Priority: {ticket['priority']}" in text
        section = text.split("## Allowed files", 1)[1].split("## Acceptance", 1)[0]
        listed = re.findall(r"^- `([^`]+)`$", section, re.MULTILINE)
        assert listed == ticket["files"]
        assert ticket["spec"] in text and ticket["acceptance"] in text
        assert ticket["merge_note"] in text


def test_owner_feedback_records_round_seven_decision_verbatim_and_keeps_history():
    text = (ROOT / "docs/feedback/owner.md").read_text()
    assert text.startswith("## Round 7-8: owner decision (recorded 2026-11-09)\n")
    current = text.split("\n## Round 6", 1)[0]
    assert OWNER_DECISION in current
    assert "38/100" in current and "0/5 live" in current
    round6 = text.split("\n## Round 6", 1)[1].split("\n# Owner product feedback", 1)[0]
    assert "Accor and every prohibited entry stay denied" in round6
    assert "or consent/submit forms/enter personal data/bypass captchas." in round6
    assert "superseded by Round 7-8" in round6
    assert text.index("## Round 6") < text.index("## Round 5") < text.index("## Round 4")


def test_shared_docs_reference_current_queue_and_p14_contract():
    for name in ("AGENTS.md", "PLAN.md", "README.md", "HANDOFF.md"):
        text = (ROOT / name).read_text()
        assert "R7-01" in text and "R7-05" in text, name
        assert not re.search(r"\bR[1-6]-0[1-5]\b", text), name
        assert not re.search(
            r"(?:Milan|Milano)[- ]only|frozen[- ]journey|round[- ]6 queue|round-six queue",
            text, re.IGNORECASE,
        ), name
    contract = (ROOT / "CONTRACTS.md").read_text()
    for marker in ("background", "reason_code", "load_registry", "coverage(", "language",
                   "P7", "alternatives", "P8", "registration_coverage", "P9", "preparation",
                   "P10", "handoff-only", "P11", "checkpoint", "force_answer", "P12",
                   "gateway_city", "keep_fragment", "blocked_url_host", "P13",
                   "checkpoint_unverified", "checkpoint_reached", "P14 Runner profile prefill",
                   "runner_profile", "profile_status", "prefill_fields", "prefill_scope",
                   "prefill_patterns", "personal_data_entered", "prefilled", "stop_label",
                   "process memory", "Identifying fields", "Quasi-identifiers"):
        assert marker in contract, marker


def test_agents_has_current_owner_approved_prefill_rules_not_stale_prohibitions():
    text = (ROOT / "AGENTS.md").read_text()
    assert "Accor denied" not in text
    assert "enter personal data" not in text.casefold()
    assert not re.search(r"(?:Milan|Milano)[- ]only|only (?:Milan|Milano)", text, re.IGNORECASE)
    for marker in ("P14", "participant/guest/passenger", "process memory",
                   "fake", "final forms", "unknown/expired", "allowed_owner_rule"):
        assert marker.casefold() in text.casefold()
    assert OWNER_DECISION in (ROOT / "docs/feedback/owner.md").read_text()
