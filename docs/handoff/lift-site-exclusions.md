# Lift site exclusions

- Owner decision: lift site exclusions for read/prepare-only runs; not a claim
  that the sites granted permission. Historical terms evidence remains intact.
- All 124 registry entries use allowed_owner_rule; expired review dates do not
  expire the owner decision. Unknown default-policy HTTPS hosts may be opened
  on their exact host. Malformed configs and explicit custom-policy denials
  still fail closed. Existing per-task navigation scopes remain enforced.
- Removed the separate H-client Accor prohibition. No action/payment/consent/
  CAPTCHA/privacy/checkpoint guardrail changed. No new adapter or live run.
- Existing hotel adapters: IHG (2), NH (1), B&B (7). Existing transport adapters:
  CP (1), Vueling (9), NS International (6), SBB (6). After PR44 integration,
  verified-render primary gating remains unchanged: SBB has four verified-render
  routes, NS has two; CP/Vueling are unverified alternatives, not primary routes.
  Registration adapters and existing
  generic sourced-page handling can now use formerly excluded registered sites.
- No hotel/transport adapter exists for Accor, Booking, Hilton, Trainline, SNCF,
  Omio, Google Travel or Trenitalia. Policy permission alone does not make
  those sites executable by the hotel/transport builders.
- Rebased onto merged PR44; all 124 entries, including transport.json, follow
  the owner rule. Preserved transport rendering rank, checkpoint protections
  and all new PR44 regression tests (updated site-exclusion expectations).
  providers.py is untouched here.
- Validation: `uv run ruff check .` -> `All checks passed!`
- Validation after rebase: `uv run pytest -q` -> `2102 passed, 1 warning in 42.23s`.
  Warning is Starlette's existing httpx TestClient deprecation.
- Environment: Node existed under ~/.nvm but was absent from default PATH.
  Exposed the installed v24.22.2 binary through ~/.local/bin/node; all 36
  executable UI tests then ran successfully. No dependency/config changes.
- No live evidence or browser visual verification claimed. Next: integrate via
  PR and separately scope missing adapters.
