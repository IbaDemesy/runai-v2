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
  CP (1), Vueling (9), NS International (5). Registration adapters and existing
  generic sourced-page handling can now use formerly excluded registered sites.
- No hotel/transport adapter exists for Accor, Booking, Hilton, Trainline, SNCF,
  Omio, Google Travel, Trenitalia or SBB. Policy permission alone does not make
  those sites executable by the hotel/transport builders.
- PR43 changes discovery/guide only; PR44 overlaps site_policy.py, registry and
  tests/test_site_policy.py. providers.py is untouched here. Reconcile PR44's
  new registry entries with the owner decision when integrating.
- Validation: `uv run ruff check .` -> `All checks passed!`
- Validation: `uv run pytest -q` -> `2031 passed, 1 warning in 44.35s`.
  Warning is Starlette's existing httpx TestClient deprecation.
- Environment: Node existed under ~/.nvm but was absent from default PATH.
  Exposed the installed v24.22.2 binary through ~/.local/bin/node; all 36
  executable UI tests then ran successfully. No dependency/config changes.
- No live evidence or browser visual verification claimed. Next: integrate via
  PR, resolve registry overlap with PR44, separately scope missing adapters.
