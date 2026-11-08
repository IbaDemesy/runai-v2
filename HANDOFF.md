# Handoff — round two

## Current implementation/evidence boundary (2026-11-08)
- Round 1 shipped generic guided discovery (Linkup), the FR/EN guide, the H
  client, task builders, the core API and the UI. Its live evaluation
  ([docs/eval/round-1.md](docs/eval/round-1.md)) found **0/5 visible live
  successes** and a design score of 5/10. That report stays as history.
- The main round-1 failures were: live panels showed H trajectory JSON instead
  of screenshots, hotel/transport searched with today's date, step limits,
  registration login walls, weak adversarial chat handling, an echoed card
  number, and 40-51 s of silent waiting.
- Owner hands-on feedback (a)-(d), the adversarial requirement, the Accor/site
  policy rule and the exact live-success definition are in
  [docs/feedback/owner.md](docs/feedback/owner.md). They are top priority.
- Live acceptance for round 2 is recorded in
  [docs/eval/round-2.md](docs/eval/round-2.md). Do not claim success beyond it.

## Round-two queue
The exact files, dependencies and merge notes are in
[docs/tickets/index.json](docs/tickets/index.json), validated by
`tests/test_r2_scope_contract.py`.

| Ticket | Responsibility | Merge |
| --- | --- | --- |
| [R2-01](docs/tickets/R2-01.md) | Premium chronological chat, ChatGPT-style suggestions, immediate feedback, screenshot-only live stage | 1, any order |
| [R2-02](docs/tickets/R2-02.md) | Site-policy registry, Accor denied, exact-date tasks with reachable safe stops | 1, any order |
| [R2-03](docs/tickets/R2-03.md) | Private screenshot-only H runtime, pre-run policy gate, verified outcomes | 1, any order |
| [R2-04](docs/tickets/R2-04.md) | Robust FR/EN guidance, adversarial suite, sourced recommendations | 1, any order |
| [R2-05](docs/tickets/R2-05.md) | Background discovery API, redaction, confirmation gate, docs, final live acceptance | 2, last |

Cross-ticket interfaces are pinned in [CONTRACTS.md](CONTRACTS.md) and are
additive: siblings import lazily and fail closed. R1-* and T* ticket files are
history. They grant no current scope.

## Checks
`uv sync --frozen && uv run ruff check . && uv run pytest -q`. CI is offline.
Per-ticket pasted output, evidence and blockers are in `docs/handoff/<id>.md`.

## Safety
The owner approval covers read/prepare-only H runs. It does not cover payment
or any other side effect. Site terms must be reviewed and dated in the policy
registry before any run. H trajectories are not published. Never pay, book,
create accounts, accept terms/consent, submit forms, enter personal data or
bypass captchas. Report blockers honestly, and never expose secrets, private
H URLs or personal data.
