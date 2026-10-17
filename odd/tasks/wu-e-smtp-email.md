# ODD — WU-E: real configurable SMTP email

Objective: make the system email configurable and actually deliver in production, with one
unified send path (today two divergent implementations exist and the fallback path is
hardcoded to `localhost`).
Branch: `odd/wu-e-smtp-email` (worktree `../lumat-agent-odd-wu-e-smtp-email`).
Delivery strategy: `ask-on-risk` (default). Forecast at creation: ~590 authored lines
(additions+deletions, generated files excluded) → over the ~400 advisory ⇒ chain strategy
must be chosen once before the first work-unit commit.
Test runner: `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q` (backend);
`npm test` + `npm run build` in `web/` (frontend, `tsc -b` lives only inside build).

## Specs

- **S1 — SMTP settings are configurable KV keys.** `app/services/settings.py`
  `SETTINGS_DEFAULTS` gains `notify.smtp_port` (int, default `25`), `notify.smtp_user`
  (str, default `""`), `notify.smtp_tls` (str, default `"none"`; allowed
  `"none" | "starttls" | "ssl"`). Existing `notify.smtp_host` (default `localhost`) and
  `notify.smtp_from` (default `notificaciones@lumat.cl`) unchanged. No migration: KV rows
  materialize on first `set_setting`. The `notify.*` keys stay out of
  `ASSISTANT_WRITABLE_SETTINGS`.
- **S2 — SMTP password is an encrypted panel secret.** Stored in `panel_secrets` under key
  `smtp_password`, encrypted with `app/services/crypto` (`encrypt`/`decrypt`), reusing the
  `app/services/model_secrets.py` pattern (keyed upsert, audit, masked status). Status is
  `{configured: bool, masked: "…<last4>"}` and the plaintext is NEVER returned by any API.
- **S3 — one unified send path.** `app/services/notifications.py::send_email` stops using
  `smtplib.SMTP("localhost")` hardcoded and delegates to the settings-aware path; exactly one
  SMTP transport implementation remains in the codebase. `notifications.send_email` gains the
  `session` argument it needs to read settings (`notifications.py:351` call site updated).
- **S4 — transport honors host, port, TLS and auth.** The transport connects with the
  configured host+port; when `notify.smtp_tls == "starttls"` it calls `starttls()`; when
  `"ssl"` it uses `smtplib.SMTP_SSL`; when `notify.smtp_user` and the stored password are both
  set it calls `login(user, password)`. With defaults (`localhost:25`, no user, `tls=none`)
  the observable behavior is identical to today.
- **S5 — panel API for email config.** `GET /settings` payload gains
  `email: {host, port, from_address, user, tls, password: {configured, masked}}`.
  `POST /settings/email` body `{host, port, from_address, user, tls}` upserts the five KV keys
  (validated: port 1..65535, tls in the allowed set, host/user/from non-empty rules) and audits
  via `set_setting`. `POST /settings/email/password` body `{password}` sets the secret;
  `DELETE /settings/email/password` clears it. All admin-only (`require_admin_json`): operador →
  403, unauthenticated → 401 JSON. Add `"email"` to `_KNOWN_SECTIONS`; unknown section stays 400.
- **S6 — frontend "Correo" section.** `web/src/components/pages/Settings.tsx` gains a `Correo`
  tab (SECTIONS entry `{ id: "email", label: "Correo" }`) to edit host, port, from, user, TLS
  and the password, showing the masked password and its origin, mirroring the existing
  `model-api-key` section. `web/src/api.ts` gains the helpers/types; `web/src/types.ts` gains
  the `email` shape. UI copy stays Spanish, consistent with the rest of the page.
- **S7 — tests pin the behavior (RED before GREEN).** Unit tests assert config loading and the
  exact transport args (host, port, `starttls`, `login`, `SMTP_SSL`); a test asserts
  `notifications.send_email` no longer hardcodes `localhost` and delegates. Integration tests
  cover `GET`/`POST`/`DELETE` of the email section + password, admin-only enforcement, and that
  the plaintext password never appears in any response. Existing SMTP fakes
  (`tests/integration/test_emergency_notify.py`, `tests/integration/test_cost_guardrails.py`)
  must still pass — the fake only implements `sendmail`, so default-config paths must not call
  `starttls`/`login`.
- **S8 — docs.** `docs/hardening.md` §6 ("Secrets — env-only (SH-2)") updated: the SMTP password
  is now stored encrypted in the panel, not env-only. Document the new keys and the cPanel
  values (host `mail.<dominio>`, port `587` STARTTLS or `465` SSL, user = full email, password
  = account password).
- **S9 — end-to-end delivery (owner-run).** With real credentials: send one real email and
  observe a `notification.operation_sent` audit row for the `NotificationOperation`. This cannot
  run in CI; it is executed by the owner against production values and its result recorded here.

## Tasks

| ID | Spec | Task | Route | Status |
|----|------|------|-------|--------|
| T1 | S1,S2 | `app/services/smtp.py` (config loader + password secret helpers) + new settings keys | inline | done |
| T2 | S3,S4 | Transport honors port/TLS/auth in `notify.send_email`; unify `notifications.send_email` | inline | done |
| T3 | S5 | Panel API `/settings/email` + `/settings/email/password` + `GET` payload | inline | done |
| T4 | S6 | Frontend "Correo" section (Settings.tsx + api.ts + types.ts) | inline | done |
| T5 | S7,S8,S9 | Docs, ponytail pass, focused + suite verification, owner e2e | inline | done (S9 owner-pending) |

Delivery: one PR, `odd/wu-e-smtp-email` → `main`, with the three slices as its three commits
(see L10 for the final commit map). The owner chose `feature-branch-chain`, but the branch already
carried every slice, so slice branches would have produced empty diffs; the slices are documented
as reviewable commit boundaries instead.

## Log

### L1 — user request (verbatim, 2026-10-16)
> hey chat continuamos desde aca. 📄 odd/handoffs/automation-wu-d-wu-e.md  dame un overview para continuar

### L2 — user authorization (verbatim, 2026-10-16)
> ok perfecto. vamos con WU-e

### L3 — setup evidence (2026-10-16)
- `git pull --ff-only` in main: `9f6da17e` → `a9860e11` (19 commits, fast-forward, clean).
- Worktree created: `rapso worktree create wu-e-smtp-email --yes` →
  `/home/stefan/repos/lumat-agent-odd-wu-e-smtp-email`, branch `odd/wu-e-smtp-email`.
- Provisioned: `cp ../lumat-agent/infra/.env infra/.env`, `uv sync`, `npm ci --prefix web`,
  `infra/test-db.sh up`. Smoke: `tests/unit/test_model_secrets.py` → 6 passed.
- Read-only map (explore worker + inline reads): the two divergent `send_email`
  (`notifications.py:142-149` hardcoded localhost; `notify.py:98-113` settings-aware but no
  port/auth/TLS), settings KV (`settings.py:200-264`), secret pattern
  (`model_secrets.py` + `crypto.py` + `panel_secrets` mig 053), panel routes
  (`app/panel/api/routes/settings.py`), frontend (`Settings.tsx`, `api.ts`).
- Key finding: the frontend/backend settings path needs NO migration — settings is a KV table
  and secrets are keyed upserts; S1/S2 add zero DDL.

### L4 — T1 + T2 (slice 1)
- T1 — `app/services/smtp.py` + new settings keys. RED first: 7 new tests in
  `tests/integration/test_smtp.py` failed on `cannot import name 'smtp'`, then GREEN.
- T2a — transport honors port/TLS/auth. RED first: 5 tests in
  `tests/integration/test_smtp_transport.py` failed, then GREEN.
- T2b — unification: `notifications.send_email` delegates to `notify.send_email`; the
  `process_operation` dispatch now passes the session to the email branch.
- **Suite-found defect**: `test_emergency_notify.py` and `test_cost_guardrails.py` had a narrow
  `clean_db` that did not truncate `panel_secrets`, so a stored SMTP password leaked into them
  and `crypto.decrypt` raised `SETTINGS_ENCRYPTION_KEY is required`. Fixed by adding
  `panel_secrets` to both truncate lists (not by weakening the transport — a configured password
  with a missing key must stay loud).
- Full backend suite `uv run pytest tests/ -q`: all green.

### L5 — T3 (slice 2)
- RED first: 7 tests in `tests/functional/test_api_settings_email.py` failed, then GREEN.
- `GET /settings` now carries `email` (config + `password: {configured, masked}`); the connection
  settings and the password are separate writes, so saving the config can never blank a stored
  credential.
- One pinned test updated: `test_api_kb_settings.py::test_settings_get_returns_all_sections_and_snapshot`
  asserts the exact section set and now includes `email`.
- **Test-hygiene fix**: the functional conftest's `TRUNCATE_TABLES` did not include
  `panel_secrets` (same leak class as L4); added so a stored SMTP password cannot bleed into
  `test_api_model_api_key.py`'s `assert session.scalar(select(PanelSecret)) is None`.
- `tests/functional/` suite: all green.

### L6 — T4 (slice 3, UI)
- RED first: the section test and the two Correo behaviour tests failed, then GREEN.
- Slice 3 ships both layers together: the typed contract (`Settings.email`, api helpers, story
  mock) and the Correo section with its tests.
- **Suite-found defect**: `data?.email.password` threw on a partial payload — the AppShell
  fixture omits `email`. Fixed with `data?.email?.password` (the SPA must tolerate an older
  payload shape).
- Frontend suite: 1246 passed; `npm run build` (`tsc -b` included) green.

### L7 — T5 (docs + ponytail + verification)
- `docs/hardening.md` §6 documents the panel-stored secrets exception and the SMTP keys/cPanel
  values; S9 stays an unchecked owner item.
- Ponytail: no over-engineering found. One reported (not fixed) finding: `_mask` is duplicated
  as a one-liner in `smtp.py` and `model_secrets.py` — extracting it would couple two unrelated
  domains for one line, so it stays.
- Final verification (each suite run ALONE — running the backend and frontend suites
  concurrently starved both and produced 5 spurious frontend failures):
  - `uv run pytest tests/ -q` → exit 0, zero failures.
  - `npm test` → 1246 passed (110 files).
  - `npm run build` → green (`tsc -b` type check included).
- **S9 remains open (owner):** real SMTP credentials are required to send a live email and
  observe the `notification.operation_sent` audit row.

### L8 — T6 (verifier correction batch)
Independent verifier (`gentle-ai-verify`) ran the whole feature against baseline `a9860e11`:
S1-S8 met, S9 not verifiable. One blocker, three advisories.
- **Blocker (fixed in the slice-1 commit)**: unifying the transport changed the generic sender's `From`
  header from a bare `notificaciones@lumat.cl` to `Lumat Emergencias <…>`. `send_email` gained
  a `from_name` argument and the generic sender passes `None`, restoring both baselines. Pinned
  by tests for both headers.
- **Advisory A1 (fixed)**: `POST /settings/email` silently dropped a stray `password` field and
  returned 200; `EmailBody` now sets `extra="forbid"` so it fails loudly (422).
- **Advisory A2/A3**: not defects (documented section list; envelope-from equivalent).
- Verifier probe tests committed as regression pins:
  `tests/functional/test_verifier_wue_api.py` (S2, S5) and
  `tests/integration/test_verifier_wue_transport.py` (S3, S4). Focused run: 29 passed.
- Recheck limited to the blockers + the pre-existing email suites: green. Full backend
  `uv run pytest tests/ -q` → exit 0.
- Verifier environment notes: `/tmp` has an exhausted per-user quota, so scratch copies went to
  `$HOME`; `tests/_testdb.py` derives the test DB port from the repo directory name, so a scratch
  copy must keep the worktree's name; `test_infra.py::test_deploy_scripts_tracked_as_executable`
  cannot run without `.git`.

### L9 — native review (approved, authority burned)
- `gentle-ai review assess` returned `medium` / `under_budget`; raised to high risk with
  `--escalate-item 2` (stores an SMTP credential and adds TLS/auth to the mail transport) →
  `review_due: true`, reason `high_risk`.
- Owner granted candidate consent through the typed `consent/v3` envelope (relayed losslessly).
- Transaction `review-53da14b017f74f48`, 4 lenses (`review-risk`, `review-resilience`,
  `review-readability`, `review-reliability`), base `a9860e11 --committed-only`, 26 paths,
  1446 changed lines, correction budget 200.
- The `review-resilience` slot's first attempt was refused (`inspection.status=unavailable`); the
  slot was NOT consumed. Per contract: re-queried the same-lineage STATUS, which re-offered that
  one slot, and relaunched only it. All four lenses then admitted.
- Outcome: **approved**, zero findings across all four lenses. Acknowledgement burned authority:
  `gentle-ai.review-acknowledged/v1`, `action: acknowledged`, `authority: burned`,
  `consumed_revision: sha256:c9369cb564920a47514f5172ae8a8e5e72c558047304d18ec44a4a14b0f938f9`.
- Delivery (commit/push/PR/merge) stays the owner's decision under ordinary repository policy;
  the review receipt is informational and authorizes no delivery.

### L10 — secret scanner (accepted false positive)
- GitGuardian flagged the SMTP and panel-login test fixtures. The scan is per commit and matches
  the *shape*: in a file about SMTP settings, any occurrence of the `password` key reads as a
  hardcoded credential, whatever its value, so the finding is irreducible in test code.
- Two fix-forward commits that re-shaped the fixtures (plain placeholder values, a
  `_password_body()` helper, a split login body) did not clear it and only made the tests less
  natural; they were reverted, which restores the exact test bytes the review approved.
- `.gitguardian.yaml` scopes the exclusion to those fixture paths instead of contorting the tests,
  and the finding stays visible on the PR as an accepted false positive. No production path is
  excluded.
- With the owner's explicit approval the branch was rebuilt as the commits below and force-pushed;
  apart from `.gitguardian.yaml` and this document the tree equals the tip the verifier and the
  native review saw.
- Final commit map: slice 1 (T1+T2) `697b7471`, slice 2 (T3) `312970bf`, slice 3 (T4+T5) `0de9d42c`,
  scanner config `a433e762`. T6's corrections are folded into the slice they fix, and T7's review
  record is this document.
