```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:27518b818a16dd25375bef79845b2a9f6db5abced46d366beb1f05416895e504
verdict: pass
blockers: 0
critical_findings: 0
requirements: 20/20
scenarios: 26/26
test_command: .venv/bin/pytest tests/
test_exit_code: 0
test_output_hash: sha256:27518b818a16dd25375bef79845b2a9f6db5abced46d366beb1f05416895e504
build_command: .venv/bin/python -c "import app.main; from app.panel.deps import require_user, require_admin, get_current_user, templates; from app.panel.routes.auth import router; from app.panel.routes.clients import router; from app.panel.routes.conversations import router; from app.panel.routes.cases import router; from app.panel.routes.kb import router; from app.panel.routes.settings import router; from app.panel.routes.dashboard import compute_kpis; from app.panel.routes.export import _csv_stream; from app.panel.seed_admin import seed_admin; from app.services.users import hash_password, verify_password, is_locked, record_failed_login, reset_login_state; from app.services.cases import list_open_cases, update_case; from app.services.notify import acknowledge_case; from app.services.customers import search_customers; from app.services.costs import spend_snapshot; from app.services.settings import get_setting, set_setting; from app.services.kb import ingest_document, update_document, restore_version, disable_document; from app.models import User, UserRole, Case; print('import OK')" (with test env set)
build_exit_code: 0
build_output_hash: sha256:73e65cba19528ade3fd463248a9ba2c44e92c41810caef6a0bba624cefc54219
```

# Verification Report — hito-1-setup-whatsapp

**Change**: hito-1-setup-whatsapp · **Project**: LumatAgent (lumat) · **Phase**: sdd-verify
**Latest verified slice**: **Batch 5 (PR 6)** — commits `fc8dc067..f300c4b0` (+ `b36adce4` chore marking T5.5): 5 feat(panel) + 5 chore(sdd) + migration 007 — T5.1 panel auth+roles · T5.2 clients/conversations views · T5.3 cases view + emergency ack · T5.4 KB manager + settings views · T5.5 dashboard KPIs + CSV export; T2.1 remains blocked on client credentials
**Mode**: **STRICT TDD** (config.yaml `apply.tdd: true`, runner `pytest tests/`)
**Artifact store**: hybrid (this file + Engram `sdd/hito-1-setup-whatsapp/verify-report`)
**Ledger token (verify run)**: B5 run token held by orchestrator (verify-B5, NOT re-acquired); prior B3 token `sha256:5782326ac5…7a037` settled by orchestrator
**Cumulative verified**: 49 requirements / 68 scenarios across B0+B1+B2+B3+B4+B5 slices. Slice-scoped envelope for B5 = 20/20 reqs, 26/26 scenarios.

---
# Batch 5 (PR 6) — THIS VERIFY RUN

**Verified slice**: commits `fc8dc067..f300c4b0` (8 commits) + `b36adce4` chore(T5.5 mark): `fc8dc067` feat(panel) signed-cookie auth + roles + lockout (AP-1, AP-2, SH-5) · `dbf5cb85` chore(sdd) T5.1 · `d024f83b` feat(panel) clients list/search + conversation threads (AP-3, AP-4, CR-3..5) · `c14066a6` chore(sdd) T5.2 · `a3c29aa3` feat(panel) cases view + state/assign + emergency ack (HH-4, AP-5, EM-4) + migration 007 · `2691aaaf` chore(sdd) T5.3 · `b402c92c` feat(panel) KB manager + settings views (AP-6, KB-3/4, SS-1..5) · `4fd06901` chore(sdd) T5.4 · `f300c4b0` feat(panel) dashboard KPIs + streaming CSV export (AP-7, AP-8) · `b36adce4` chore(sdd) T5.5
**Runtime harness**: `lumat-pg-test` container UP (localhost:5432, pgvector) — all suites executed live against the real DB; OpenAI embeddings respx-mocked (`mock_openai_embeddings`); the panel flows touch no Meta/SMTP path (send/notify not exercised by panel routes).

### Completeness (B5 slice)

| Metric | Value |
|--------|-------|
| Tasks total (change) | 33 (header says 34 — pre-existing discrepancy, SUGGESTION-1 carried) |
| Tasks complete | 23/33 (B0: 3 + B1: 3 + B2: 2 + B3: 6 + B4: 5 + B5: 5, of which T2.1 stays `[ ]` **blocked**) |
| B5 tasks complete | 5/5 — T5.1 [x], T5.2 [x], T5.3 [x], T5.4 [x], T5.5 [x] (tasks.md, flipped by this verify) |
| B5 requirements verified | 20/20 slice-scope: AP-1..8 (8) · SS-1..5 (5) · KB-3, KB-4 (2) · HH-4 (1) · EM-4 ack (1) · CR-3, CR-4, CR-5 (3) |
| B5 scenarios verified | 26/26 slice-scope: AP 10 · SS 7 (incl. SS-4 "Spend visible" — first time counted) · KB-3 1 + KB-4 2 · HH-4 1 · EM-4 ack 1 · CR-3 2 + CR-4 1 + CR-5 1 |
| T2.1 blocked verdict | ✅ PASS for this slice — ops dependency on client credentials, unchanged from B2/B3/B4 |

Full-spec totals for context: admin-panel = 8 reqs / 10 scenarios (ALL first counted here) · settings-scope-limits = 5 reqs / 7 scenarios (SS-4 "spend visible" NEW; other 6 re-verified at panel surface) · knowledge-base = 4 reqs / 7 scenarios (KB-3 NEW; KB-4 re-verified at panel surface) · human-handoff = 5 reqs / 7 scenarios (HH-4 NEW) · emergency-detection = 5 reqs / 7 scenarios (EM-4 ack re-verified at panel button; mechanism proven B4) · customer-records = 6 reqs / 8 scenarios (CR-3/4/5 re-verified at ficha surface). **Cumulative B0+B1+B2+B3+B4+B5: 49 reqs / 68 scenarios verified** (+10 new reqs: AP×8, KB-3, HH-4; +13 new scenarios: AP 10, SS-4 1, KB-3 1, HH-4 1 — CR-3/4/5, SS-1/2/3/5, KB-4, EM-4 already counted in prior batches; this slice adds their panel-surface evidence without double-counting).

### Build & Tests Execution (B5)

**Build-equivalent**: ✅ Passed (exit 0)
```text
.venv/bin/python -c "import app.main; from app.panel.deps import require_user, require_admin, ...; from app.services.users import ...; from app.services.cases import ...; from app.services.notify import ...; from app.services.customers import ...; from app.services.costs import ...; from app.services.settings import ...; from app.services.kb import ...; print('import OK')" (with test env set)
-> import OK   (hash sha256:73e65cba…4cefc54219 — same canonical 'import OK' digest as B4)
```

**Focused suites** (live pgvector, exit 0):
```text
$ .venv/bin/pytest tests/functional/test_auth.py -q           -> 14 passed
$ .venv/bin/pytest tests/functional/test_clients.py -q        -> 11 passed
$ .venv/bin/pytest tests/functional/test_cases.py -q          -> 8 passed
$ .venv/bin/pytest tests/functional/test_kb_settings.py -q    -> 14 passed
$ .venv/bin/pytest tests/functional/test_dashboard_export.py -q -> 7 passed
$ .venv/bin/pytest tests/functional/ -q                       -> 54 passed in 39.56s
$ .venv/bin/pytest tests/integration/test_migrations.py -q    -> 10 passed in 1.19s (007 approved)
```

**Full suite**: ✅ **300 passed / 0 failed / 0 skipped** in 76.72s, exit 0 — matches expected 300 (246 B0-B4 baseline + 54 B5), no regressions.
Output hash (canonical capture): `sha256:27518b818a16dd25375bef79845b2a9f6db5abced46d366beb1f05416895e504` (last-line `======================== 300 passed in 76.72s (0:01:16) ========================`).

**Migration check** (live): `schema_migrations` = [001_init .. 007_case_created_at] (7); `\d cases` shows `created_at timestamptz NOT NULL DEFAULT now()` + `acknowledged_at`/`ack_by`/`escalated_at`/`responsible_id FK->users`; `db/migrate.sh` re-run is idempotent ("skip 007_case_created_at (already applied)" → "migrations up to date"); `test_migrations.py` 10/10 green.

**Secrets check** (all passed):
```text
git grep -iE "sk-[A-Za-z0-9]{10,}|EAAG[A-Za-z0-9]{10,}|AKIA|ghp_" app/ db/ infra/ (excl. sk-test)  -> no matches
git ls-files | grep -i env                                          -> only infra/.env.example (SH-2 intact)
```
Both conftests FORCE `OPENAI_API_KEY=sk-test` (`os.environ[...] = "sk-test"`, no setdefault) and set `PANEL_SESSION_SECRET`; respx mocks only `https://api.openai.com/v1/embeddings` for KB tests — full suite green confirms zero real external calls.

**Coverage**: ➖ Not available (config.yaml `verify.coverage_threshold: 0`; no coverage tooling — consistent with B0-B4).

### Spec Compliance Matrix (B5 slice)

| Requirement | Scenario | Covering test (runtime, all passing) | Result |
|-------------|----------|--------------------------------------|--------|
| AP-1 Authentication | Authorized login | `test_authorized_login_sets_session_and_audits` (302 → /panel/, signed `session` cookie set, `auth.login` audit row) + `test_authorized_login_resets_failed_counter` | ✅ COMPLIANT |
| AP-1 Authentication | Failed login | `test_failed_login_audited_and_counted` (no cookie, counter 1, `auth.login_failed` audit) + `test_unknown_username_failed_login_audited` (no user oracle) + `test_lockout_after_five_failures` (5th → locked, `auth.login_locked` audit) + `test_lock_expiry_allows_login_again` (15-min window) + `test_inactive_user_cannot_login` | ✅ COMPLIANT |
| AP-2 Roles and Permissions | Operador permissions | `test_operador_cannot_access_kb_manager` (403 GET+POST /panel/kb) + `test_operador_cannot_access_settings` (403 GET+POST /panel/settings) + `test_operador_can_access_panel_home` (shared routes 200) + `test_dashboard_and_export_require_login` | ✅ COMPLIANT |
| AP-2 Roles and Permissions | Admin permissions | `test_admin_can_access_kb_manager_and_settings` (200 both) + `test_admin_can_access_panel_home` | ✅ COMPLIANT |
| AP-3 Clients List and Search | Search customer | `test_clients_search_by_name` + `test_clients_search_by_phone_digits` ("1111" finds +56911112222) + `test_clients_search_no_matches` + `test_clients_list_lists_customers_with_state` | ✅ COMPLIANT |
| AP-4 Conversation View | View conversation | `test_conversation_thread_shows_messages_in_order` (chronological) + `test_conversation_thread_renders_media_links` (media_url as link, read-only, HH-5 no-reply note) | ✅ COMPLIANT |
| AP-5 Cases View | Assign and update case | `test_case_update_status_and_responsible_audited` (`case.updated` snapshot with actor) + `test_case_update_clears_responsible` (`_UNSET` sentinel keep-vs-clear) | ✅ COMPLIANT |
| AP-6 KB Manager Access | Admin opens KB manager | `test_kb_add_document` (upload md/pdf/csv, ingest + audit) + `test_kb_edit_creates_new_version` + `test_kb_disable_document` + `test_kb_restore_previous_version` + `test_kb_list_shows_provider_model_cost` (KB-1 provider/model/cost visible) | ✅ COMPLIANT |
| AP-7 CSV/Excel Export | Export clients | `test_export_clients_csv` (text/csv, Content-Disposition, header + panel-visible rows) + `test_export_cases_csv` (+ customer name/phone, responsible, emergency, summary) | ✅ COMPLIANT |
| AP-8 Basic KPIs | KPIs rendered | `test_dashboard_shows_kpi_counts` (contacts/motivos/derived/visits counts) + `test_dashboard_motivos_table_breaks_down_by_service` (grouped) + `test_dashboard_respects_settings_time_window` (window from `kpi.window_days`; out-of-window excluded) + `test_dashboard_empty_state_shows_zero_kpis` | ✅ COMPLIANT |
| SS-1 Bot-Resolves vs Always-Escalate | Owner changes a rule | `test_settings_save_scope_rules` (scope_rules JSONB saved via set_setting + `settings.change` audit; effect on conversation proven in B4) | ✅ COMPLIANT (panel save surface; behavior B4) |
| SS-1 Bot-Resolves vs Always-Escalate | Rule change takes effect | B4 `test_scope_always_escalate_category_escalates` + panel save round-trip (`test_settings_save_scope_rules` asserts stored value read back on GET) | ✅ COMPLIANT (re-verified at panel) |
| SS-2 Configurable Emergency Keywords | Keyword added | `test_settings_save_emergency_keywords` (list saved + audited; T4.2 gate recompiles per run → immediate effect, no cache to invalidate) | ✅ COMPLIANT (panel save; immediate detection B4) |
| SS-3 Cost Guardrails | Conversation limit reached | `test_settings_save_spend_limits` (cost.*_limit saved + audited; threshold enforcement B4) | ✅ COMPLIANT (view; enforcement B4) |
| SS-3 Cost Guardrails | Daily limit reached | `test_settings_save_spend_limits` (daily_limit save surface) + B4 `test_daily_cost_state_blocked_at_100`/`test_daily_blocked_escalates_no_llm` | ✅ COMPLIANT (re-verified at panel) |
| SS-4 Cost Tracking and Meta Pricing Awareness | Spend visible | `test_settings_page_shows_spend_snapshot` (GET /panel/settings renders `spend_snapshot` — "daily" section + default meta cost 0.01 + limits) + `test_settings_save_meta_pricing` (`meta_pricing.service_message_cost` saved + audited) | ✅ COMPLIANT (**NEW** — panel visibility proven) |
| SS-5 Adjustable Tone and Messages | Message edited | `test_settings_save_tone` (tone.style saved + audited; reply effect proven B4) | ✅ COMPLIANT (view; behavior B4) |
| KB-3 KB Manager | Admin edits a document | `test_kb_add_document` (upload → ingest, no redeploy) + `test_kb_edit_creates_new_version` (edit → new version + re-embed) + `test_kb_disable_document` (excluded from retrieval) | ✅ COMPLIANT (**NEW**) |
| KB-4 Versioning and Re-Ingestion | Re-ingestion on update | `test_kb_edit_creates_new_version` (panel edit → version+1 + re-embed via mocked embeddings; v1 preserved) | ✅ COMPLIANT (re-verified at panel; mechanics B3) |
| KB-4 Versioning and Re-Ingestion | Restore previous version | `test_kb_restore_previous_version` (panel restore → active_version flip, D8) | ✅ COMPLIANT (re-verified at panel) |
| HH-4 Case Visibility in Panel | Case appears in panel | `test_cases_list_shows_customer_summary_status` (customer/summary/status columns, escalated-first order) + `test_cases_list_excludes_closed_cases` | ✅ COMPLIANT (**NEW**) |
| EM-4 Immediate Notification | Notification acknowledged | `test_emergency_case_shows_flag_and_ack_button` (⚠ flag + ack button only when unacked) + `test_ack_button_records_ack_and_audits` (acknowledged_at + ack_by="oper" + `case.acknowledged` audit with actor + channel=panel) + `test_ack_button_hidden_after_ack` | ✅ COMPLIANT (panel button on the T4.3 columns — same mechanism, no new columns) |
| CR-3 Lifecycle States | State progression | `test_state_change_updates_and_audits` (ficha POST state → `customer.state_change` audit with actor, flash) | ✅ COMPLIANT (re-verified at panel; mechanics B3) |
| CR-3 Lifecycle States | Invalid transition rejected | `test_invalid_state_transition_rejected` (nuevo→postventa → flash error, no audit, state unchanged) | ✅ COMPLIANT (re-verified at panel) |
| CR-4 Internal Notes | Staff adds note | `test_add_internal_note` (POST note → CustomerNote author+timestamp, rendered on ficha, staff-only table) | ✅ COMPLIANT (re-verified at panel) |
| CR-5 History Linkage | History complete | `test_ficha_lists_history` (conversations/cases/messages chronological on ficha) | ✅ COMPLIANT (re-verified at panel) |

**Compliance summary (B5 slice)**: 26/26 scenarios compliant for the verified scope; 20/20 requirements mapped to passing tests (54/54 focused). SH-5 panel-side: every mutating action audited — login/failure/lock/logout (`auth.*`), customer state (`customer.state_change`), case update/ack (`case.updated`, `case.acknowledged`), settings (`settings.change`), KB (`kb.document_ingest/update/restore/disable` with actor), seed (`user.seed_admin`) — verified by code inspection + harness audit-row assertions. Deferred per tasks.md: none for this slice (T6.2 functional re-runs the AP suite at batch level).

### Correctness (Static Evidence — B5)

| Design item | Status | Notes |
|-------------|--------|-------|
| `app/services/users.py` — bcrypt + lockout (AP-1) | ✅ Implemented | `hash_password`/`verify_password` (bcrypt, constant-time, malformed-hash safe), `is_locked` (UTC window), `record_failed_login` 5→lock+reset, `reset_login_state` |
| `app/panel/deps.py` — server-side auth deps (AP-2) | ✅ Implemented | `get_current_user` re-reads the user row per request (deactivated/locked loses access immediately), `require_user`/`require_admin` (403 server-side); tampered/absent cookie → 302 login; role NEVER client-trusted |
| `app/panel/routes/auth.py` — login/logout (AP-1, SH-5) | ✅ Implemented | bcrypt verify → signed session (12 h); every outcome audited (auth.login / auth.login_failed / auth.login_locked / auth.logout); generic "invalid credentials" (no user oracle) |
| `app/main.py` — SessionMiddleware (D7, AP-1) | ✅ Implemented | `max_age=12*60*60`, `same_site=lax`, `https_only=False` (nginx terminates TLS — reviewer note WARNING-3); secret from `panel_session_secret` (required config) |
| `app/panel/seed_admin.py` (AP-1, T7.2) | ✅ Implemented | standalone idempotent script (first seed wins), bcrypt, env PANEL_ADMIN_USERNAME/PASSWORD, audited `user.seed_admin` |
| `app/panel/routes/clients.py` + `customers.search_customers` (AP-3, CR-3/4/5) | ✅ Implemented | list/search name-ILIKE or phone-digit substring (limit 100); ficha renders history (conversations/cases/messages) + notes; POST state → `set_customer_state` audited with actor, invalid transition → flash + no audit; POST notes → `add_note` author+timestamp |
| `app/panel/routes/conversations.py` (AP-4) | ✅ Implemented | read-only thread, messages in created_at/id order, media_url links, HH-5 no-reply note |
| `app/panel/routes/cases.py` + `cases.list_open_cases`/`update_case` (HH-4, AP-5) | ✅ Implemented | open cases (closed excluded), escalated-first ordering, joined with customer; update_case status/responsible with `_UNSET` sentinel, audited `case.updated` snapshot |
| `notify.acknowledge_case` (EM-4 panel ack) | ✅ Implemented | SAME columns/audit as T4.3 reply-keyword ack (acknowledged_at/ack_by + `case.acknowledged`, channel=panel); no new mechanism; no-op on non-emergency/already-acked |
| `app/panel/routes/kb.py` (AP-6, KB-3/4) | ✅ Implemented | admin-only (require_admin); upload (pdf/md/txt/csv by extension) → `ingest_document`; edit → `update_document` (new version + re-embed KB-4); disable (KB-3); restore (active_version flip D8); provider/model/cost shown; all audited with acting admin |
| `app/panel/routes/settings.py` (SS-1..5, SH-5) | ✅ Implemented | admin-only; every save via `set_setting` (UPSERT + `settings.change` audit); GET renders scope/keywords/tone/limits/meta + `costs.spend_snapshot` (SS-4); numeric validation 400 on invalid/negative; keywords save = the SS-2 trigger (gate recompiles per run) |
| `app/panel/routes/dashboard.py` (AP-8) | ✅ Implemented | `compute_kpis` = pure SQL COUNTs over `kpi.window_days` (default 7, in SETTINGS_DEFAULTS): contacts (distinct conversations w/ inbound in window), motivos (cases by service), derivados (escalated_at in window), visit_requests (service='visita'); NO chart library |
| `app/panel/routes/export.py` (AP-7) | ✅ Implemented | streaming CSV via stdlib `csv` generator (`_csv_stream` — StringIO per row, yield); clients.csv + cases.csv with panel-visible fields only; `StreamingResponse` text/csv + Content-Disposition |
| Templates (D7) | ✅ Implemented | Jinja2 + inline vanilla JS only; NO static dir, NO CDN, NO chart/htmx/React; base.html layout + login/dashboard/clients(ficha)/conversations/cases/kb/settings views |
| Migration 007 `cases.created_at` | ✅ Implemented | `ALTER TABLE cases ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT now()` — applied live, idempotent (migrate.sh "skip"), model column + `test_migrations.py` approval list updated |
| Deps (D7) | ✅ Implemented | only bcrypt, jinja2, itsdangerous, python-multipart added (pyproject + uv.lock); no chart/export/framework dep |
| Config/env wiring | ✅ Implemented | `PANEL_SESSION_SECRET` required in app/config.py + infra/.env.example + docker-compose + BOTH conftests |

### Coherence (Design — B5)

| Design decision | Followed? | Notes |
|-----------------|-----------|-------|
| D7 panel stack = FastAPI + Jinja2 + vanilla JS, signed-cookie sessions, bcrypt | ✅ Yes | SessionMiddleware (12 h, lax) + bcrypt + Jinja2Templates + inline JS; no client framework, no chart lib, no htmx |
| D7 CSV export via stdlib `csv` (Excel cut by ponytail review) | ✅ Yes | `_csv_stream` generator over io.StringIO + StreamingResponse; AP-7 "CSV or Excel" satisfied with CSV |
| AP-1 lockout (5 fails → 15 min) on `users` | ✅ Yes | users table columns from 001_init; `MAX_FAILED_LOGINS=5`, `LOCK_MINUTES=15`; lock is a clean window (counter resets at lock) |
| AP-2 server-side-only role enforcement | ✅ Yes | require_admin 403 on /panel/settings + /panel/kb (GET+POST); role in session is informational — user re-read per request |
| KPI = SQL COUNTs, time window from settings | ✅ Yes | `kpi.window_days` default 7 registered; window respected (out-of-window excluded — test) |
| Design users table / cases.responsible_id FK | ✅ Yes | responsible dropdown of users, outerjoin in cases.csv, FK verified in `\d cases` |
| EM-4 ack via panel button on same columns (D9) | ✅ Yes | acknowledge_case reuses acknowledged_at/ack_by/`case.acknowledged` — no new mechanism, no new migration |
| D8 restore = pointer flip (no re-embed) | ✅ Yes | panel restore → restore_version; embedding call-count proven in B3 |
| SS-2 immediate effect without cache invalidation | ✅ Yes | T4.2 emergency_gate recompiles per run; settings save is the trigger (documented in settings.py docstring) |
| HH-5 no reply-from-panel in H1 | ✅ Yes | conversation thread is read-only; no compose UI |
| Deviation 1: `https_only=False` on session cookie | ✅ Acceptable | nginx terminates TLS in the designed topology (design architecture diagram); MUST flip to True if the panel is ever served directly — WARNING-3 |
| Deviation 2: `.txt` uploads mapped to MD format | ✅ Acceptable | pragmatic extension; FORMAT_BY_EXTENSION documented in kb.py |
| Rollback boundary | ✅ Yes | B5 = 10 commits fc8dc067..b36adce4; reset to e4563d87 (pre-B5) removes the slice cleanly; B0-B4 suites still green (246 in full run) |

### Strict TDD Compliance (Step 5a + expanded)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | tasks.md T5.1..T5.5 done-annotations (per-task files, focused counts 14/11/8/14/7, full-suite progression 260→271→279→293→300, commits) + Engram obs #1455 (B5 apply summary). NOTE: the B5 apply did NOT mirror the formatted TDD-table into the Engram apply-progress topic (B4's #1424 format); evidence is carried by tasks.md annotations — SUGGESTION-9 |
| All tasks have tests | ✅ | 5/5 B5 code tasks have test files (functional: test_auth, test_clients, test_cases, test_kb_settings, test_dashboard_export) — verified on disk |
| RED confirmed (tests exist) | ✅ | 5/5 test files present; RED phase documented in per-task annotations ("tests written first" per task notes) |
| GREEN confirmed (tests pass) | ✅ | 54/54 B5 tests pass on execution NOW (cross-ran, not trusted blindly): 14+11+8+14+7 |
| Triangulation adequate | ✅ | 54 distinct cases with multiple expectations each: auth ×14 (session/audit/lock/reset/inactive/logout/seed/role), clients ×11 (list/search-by-name/search-by-phone/no-match/ficha/notes/state/invalid-transition/thread/media/require-login), cases ×8 (list/excludes-closed/update-audit/clear-responsible/flag+ack-button/ack-audit/hidden-after/require-login), kb_settings ×14 (role matrix ×3, KB add/edit/disable/restore/list ×5, settings scope/keywords/tone/limits/meta/snapshot ×6), dashboard_export ×7 (KPIs ×4 incl. window-respect, CSV ×2, require-login) |
| Safety Net for modified files | ✅ | app/services/{customers,cases,notify,kb,settings}.py + models.py + main.py modified: full suite stays green (300 = 246 baseline + 54 new); new test files "N/A (new)" correct; both conftests updated together (PANEL_SESSION_SECRET) or collection fails — noted in obs #1455 |
| Assertion quality audit (5f) | ✅ | 212 asserts across 54 tests (~4/test); no tautologies, no ghost loops, no smoke-only, no type-only-alone. Strongest: lockout asserts exact locked_until window + `auth.login_locked` audit; ack test asserts acknowledged_at + ack_by + audit actor AND after["ack_by"]; CSV asserts content-type + exact header prefix + row content; window test asserts out-of-window case NOT rendered |

**TDD Compliance**: 7/7 checks passed.

### Test Layer Distribution (B5)

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 0 new | 0 new (test_migrations.py +1 line approval) | — |
| Functional | 54 | 5 (+ shared conftest) | FastAPI TestClient over real app + live pgvector; respx OpenAI embeddings; bcrypt hashing |
| **Total** | **54 (B5)** | **5** | suite total 300 (246 B0-B4 + 54 B5) |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config.yaml `verify.coverage_threshold: 0`, no pytest-cov in pyproject). Informational only (strict-TDD module).

### Quality Metrics

**Linter**: ➖ Not available · **Type Checker**: ➖ Not available. Informational only — never blocking.

### Issues Found (B5 slice)

**CRITICAL**: None

**WARNING**:
1. **(Carried from B1/B2/B3/B4 — mechanism resolved, hygiene remains)** Real `OPENAI_API_KEY` still exported in the dev shell (`~/.bashrc`); conftest FORCES `os.environ["OPENAI_API_KEY"] = "sk-test"` (no setdefault), so tests can never pick it up — verified: full suite green = zero real network calls. Dev-shell hygiene only.
2. **(Carried, informational)** Authored diff size: B5 = 3,601 insertions / 12 deletions across 43 files (incl. uv.lock 182; ~3.4k authored) vs the pre-approved PR 6 slice note. Large deltas are test bodies (~1.4k), templates, and the panel routes — not unexpected architecture. Reviewer awareness only.
3. **(NEW)** Session cookie `https_only=False`: correct for the designed topology (nginx terminates TLS in front of the API container — design architecture diagram), but MUST be flipped to True if the panel is ever exposed directly or TLS is offloaded differently. Reviewer note for PR 6.

**SUGGESTION**:
1. (Carried) `tasks.md` header claims "34 tasks" vs 33 rows (line 4). Fix on next tasks.md edit.
2. (Carried) WH-1 "Token mismatch" scenario log clause — no `caplog` assertion yet. Close in T6.x.
3. (Carried) README curl proof manual — spec-marker count check in T6.1.
4. (Carried) `test_infra.py::test_db_service_uses_pgvector_image` double-condition assert — cosmetic.
5. (Carried) Rate limiter counts duplicate deliveries before dedup — revisit at next ingest touch.
6. (Carried) Non-JSON body → 200+drop has no covering test — add in T6.2.
7. (Carried from B4) `test_handoff.py::test_cr5_closed_opens_new_conversation_through_ingest` psycopg rowcount quirk — documented, not blocking.
8. (Carried) EM-4 "Notification sent" scenario fully verified in B4; B5 counts only the ack scenario (no double-count in cumulative).
9. (NEW) B5 apply did not publish the formatted TDD Cycle Evidence table into the Engram apply-progress topic (B4 #1424 format). Evidence exists in tasks.md annotations + obs #1455 and verify re-ran everything; mirror the table format on the next apply for consistency.
10. (NEW) `graphify` code-level edges for `app/panel/*` land at archive-time refresh (orchestrator-owned, per repo AGENTS.md); until then `graphify path` between panel code and services degenerates to task/spec paths — recorded below.

### Graphify Context (B5)

- Graph check: `graphify-out/graph.json` present (1297 nodes / 2520 edges), B4 code snapshot — `app/panel/*` route files appear as nodes from tasks.md/spec extraction but code-level import/call edges land at archive refresh (per orchestration: "panel nodes not yet added; that happens at archive"). NO rebuild performed (per instructions). GRAPH_REPORT.md read at session start (god nodes/communities).
- Query `graphify query "app panel routes deps auth"` (BFS, 143 nodes) — start nodes: `app/panel/routes/auth.py`, `Task T5.1 — Panel auth + roles`, `Batch 5 — Admin panel`; consulted nodes: app/panel/routes/{auth,clients,settings,dashboard,conversations,cases,kb}.py, app/panel/deps.py, app/panel/templates/dashboard.html, tests/functional/test_auth.py, Requirements AP-1..AP-6, SS-1..SS-5, KB-4, EM-4, HH-4, SH-5, CR-3..CR-5, Tasks T5.1..T5.4, `PR 6 (delivers Batch 5)` — all [EXTRACTED]; key edges: `Task T5.1 --implements--> AP-1/AP-2/SH-5`, `T5.2 --implements--> AP-3/AP-4/CR-3/CR-4/CR-5`, `T5.3 --implements--> AP-5/EM-4` + `--references--> HH-4`, `Batch 5 --conceptually_related_to--> PR 6`.
- Query `graphify query "services users settings kb cases customers costs"` (BFS, 115 nodes) — consulted: costs.py (`daily_spend()`), customers.py (`get_or_create_customer()`, `normalize_phone_e164()`), `Settings` (app/models.py L309), `Conversation` (L146), tests/integration/{test_migrations,test_customers,test_send_costs}.py, `T4.1 Settings` — [EXTRACTED].
- Path queries: `path "app/panel/deps.py" "app/models.py"` and `path "app/panel/routes/cases.py" "app/services/notify.py"` — code-level edges absent in the B4 snapshot, so shortest-path degenerates to giant task/spec chains (902 hops); recorded as archive-refresh work (SUGGESTION-10). Structural understanding came from the BFS queries + direct source inspection.
- Communities consulted: Conversation Manager (EM/SS/HH cluster), T4.1 Settings, T3.1 Customers, T3.3 KB pipeline, T3.6 Send + cost services, community 34 (emergency).

### Runtime Harness Spot-Check (live)

```text
docker ps                                       -> lumat-pg-test UP (26 h), 0.0.0.0:5432->5432
psql schema_migrations                          -> [001_init .. 007_case_created_at] (7)
psql \d cases                                   -> created_at NOT NULL DEFAULT now() + ack columns present
db/migrate.sh re-run                            -> "skip 007_case_created_at (already applied)" / "migrations up to date"
pytest tests/functional/                        -> 54 passed in 39.56s (real DB, TRUNCATE-reset)
pytest tests/integration/test_migrations.py     -> 10 passed in 1.19s
pytest tests/                                   -> 300 passed in 76.72s (246 B0-B4 + 54 B5), exit 0
build import (test env)                         -> import OK, exit 0 (hash sha256:73e65cba…)
secrets grep (sk-/EAAG/AKIA/ghp_)               -> no credential values in app/ db/ infra/
```

**B5 runtime harness** (TestClient over the real app, live test DB, /tmp/opencode/b5_harness.py — 23/23 steps PASS):
```text
[1]  unauthenticated /panel/ -> 302 /panel/login
[2]  admin login -> 302 + signed session cookie (bcrypt verified)
[3]  dashboard 200 -> Contacts/Motivos/Derived cases/Visit requests rendered (AP-8)
[4]  clients search "1111" and "Ana" -> ficha found (AP-3)
[5]  add internal note -> rendered on ficha (CR-4); state change pendiente->agendado audited (CR-3)
[6]  settings limits save -> Saved + audit (SS-3); settings page renders spend_snapshot (SS-4)
[7]  cases list shows customer/summary/status + emergency flag + ack button (HH-4, EM-4)
[8]  POST /panel/cases/{id}/ack -> acknowledged (EM-4 panel ack)
[9]  clients.csv + cases.csv -> text/csv streaming with panel-visible rows (AP-7)
[10] operador login -> /panel/settings 403, /panel/kb 403, /panel/clients 200 (AP-2)
[11] audit_log rows present: auth.login, customer.state_change, settings.change,
     case.acknowledged, auth.logout (SH-5)
HARNESS PASS (23/23)
```

### Verdict (B5 slice)

**PASS** — Batch 5 (T5.1 panel auth+roles, T5.2 clients/conversations, T5.3 cases+ack, T5.4 KB manager+settings, T5.5 dashboard+CSV) is complete (5/5 tasks [x]), fully tested (54/54 focused, 300/300 full suite, live against the pgvector container with OpenAI embeddings respx-mocked), and matches specs AP-1..8, SS-1..5 (views incl. NEW SS-4 spend visible), KB-3 (NEW) + KB-4, HH-4 (NEW), EM-4 ack, CR-3/4/5 (ficha), the design D7 decisions (Jinja2 + vanilla JS, signed-cookie sessions, stdlib CSV, SQL-count KPIs, no chart lib), server-side-only role enforcement (AP-2), and task acceptance criteria. Strict TDD evidence validated 7/7. Runtime harness proved login → KPIs → search → note/state → settings save → case ack → CSV export → role matrix end-to-end through the real app. Migration 007 applies cleanly and idempotently (approval test 10/10). No CRITICAL findings; 2 carried WARNINGs + 1 NEW WARNING (https_only=False — correct for the nginx-terminated topology, reviewer note). T2.1 remains `[ ]` **blocked on client credentials** — blocked is a PASS for this slice. **Cumulative: 49 reqs / 68 scenarios across B0+B1+B2+B3+B4+B5.** Recommended next: create PR 6 (B5 slice, stacked to main), archive B5 slice (orchestrator) + graphify refresh (adds app/panel code edges), then Batch 6 apply (T6.1 test harness, T6.2 functional suite, T6.4/6.5 docs, T6.6 ops scripts), and unblock T2.1 when Meta credentials arrive.

## Previous Slice — Batch 4 (PR 5) PASS — preserved verbatim

**Verified slice**: commits `e43c6b46..c0823e6e` (18 commits: e43c6b46 feat(settings) KV+audit · 269323a2 feat(settings) scope/keywords/tone · ec582bf4 feat(emergency) regex engine · 0885e62e feat(chat) emergency gate+nodes · e2919bfa feat(notify) notification service · 76f21dec feat(chat) ack+reminders · 82d241f3 feat(chat) state model+handoff gate · e82c52cf feat(services) cases+deriva node · 3ea3d90e feat(costs) guardrails · 807cc7b6 feat(chat) cost gate · 08c90d32 refactor(send) settings-consolidation · c0823e6e refactor(costs) _limit dedupe + chore commits)
**Runtime harness**: `lumat-pg-test` container UP (localhost:5432, pgvector) — all suites executed against the real DB; OpenAI/Meta/SMTP calls respx-mocked or patched.

### Completeness (B4 slice)

| Metric | Value |
|--------|-------|
| Tasks total (change) | 33 (header says 34 — pre-existing discrepancy, SUGGESTION-1 carried) |
| Tasks complete | 18/33 (B0: 3 + B1: 3 + B2: 2 + B3: 6 + B4: 5, of which T2.1 stays `[ ]` **blocked**) |
| B4 tasks complete | 5/5 — T4.1 [x], T4.2 [x], T4.3 [x], T4.4 [x], T4.5 [x] (tasks.md, flipped by this verify) |
| B4 requirements verified | 16/16 slice-scope: SS-1..5 (5) · EM-1..5 (5) · HH-1, HH-2, HH-3, HH-5 (4) · CR-5 (1) · SH-5 (1) |
| B4 scenarios verified | 21/21 slice-scope: SS 6 (SS-4 0 — basis/snapshot, panel → T5.4) · EM 7 · HH 6 · CR-5 1 · SH-5 1 |
| T2.1 blocked verdict | ✅ PASS for this slice — ops dependency on client credentials, unchanged from B2/B3 |

Full-spec totals for context: settings-scope-limits = 5 reqs / 7 scenarios (SS-4 visibility → T5.4) · emergency-detection = 5 reqs / 7 scenarios · human-handoff = 5 reqs / 7 scenarios (HH-4 panel → T5.3) · customer-records = 6 reqs / 8 scenarios (B4 re-verifies CR-5 closed→new at ingest) · security-hardening = 5 reqs / 8 scenarios (SH-5 login → T5.1). **Cumulative B0+B1+B2+B3+B4: 39 reqs / 55 scenarios verified** (27+12 new reqs, 37+18 new scenarios; CR-5/SH-5/HH-3 counted once — B4 adds ingest-level and service-level evidence).

### Build & Tests Execution (B4)

**Build-equivalent**: ✅ Passed (exit 0)
```text
.venv/bin/python -c "import app.main; from app.services.settings import ...; from app.services.emergency import ...; from app.services.notify import ...; from app.services.cases import ...; from app.services.costs import ...; from app.chat.nodes.{emergency_gate,emergency,cost_gate,handoff_gate,handoff} import ...; from app.chat.graph import ...; from app.chat.state import ...; print('import OK')" (with test env set)
-> import OK   (hash sha256:73e65cba…4cefc54219)
```

**Focused suites** (live pgvector, exit 0):
```text
$ pytest tests/integration/test_settings.py -v          -> 17 passed
$ pytest tests/integration/test_emergency.py -v         -> 32 passed
$ pytest tests/integration/test_emergency_notify.py -v  -> 29 passed
$ pytest tests/integration/test_handoff.py -v           -> 18 passed
$ pytest tests/integration/test_cost_guardrails.py -v   -> 22 passed
Total: 118 passed in 15.81s   (hash sha256:38a7fbdc…89f43dd6)
```

**Full suite**: ✅ **246 passed / 0 failed / 0 skipped** in 41.64s, exit 0 — matches expected 246 (128 B0-B3 + 118 B4), no regressions.
Output hash: `sha256:c4d5a2b23909c3be1749e8854b0ddf74b320ff70b7fd61b2bfdca8777b3a7129`.

**Migration check** (live): `schema_migrations` = [001_init, 002_customer_notes, 003_conversation_captured_data, 004_case_emergency, 005_case_emergency_ack, 006_handoff_deriva]; `cases.emergency/notified_at/acknowledged_at/ack_by/reminder_count/bundle/escalated_at` + `conversation_events.actor` present in live `\d`; `test_migrations.py` 10/10 green (004/005/006 expected).

**Secrets check** (all passed):
```text
git grep -iE "sk-[A-Za-z0-9]{10,}" app/ db/ infra/ (excl. sk-test)  -> no matches
git grep -iE "EAAG[A-Za-z0-9]{10,}" / "AKIA" / "ghp_"               -> no matches
git ls-files | grep -i env                                          -> only infra/.env.example (SH-2 intact)
```
No test makes a real call to api.openai.com / graph.facebook.com / SMTP: conftest FORCES `OPENAI_API_KEY=sk-test` (fail-fast 401), Meta is respx-mocked, SMTP patched (`no_real_smtp` fixture in test_cost_guardrails, `_capturing_smtp`/`_failing_smtp` in test_emergency_notify) — full suite green confirms zero real external calls.

**Coverage**: ➖ Not available (config.yaml `verify.coverage_threshold: 0`; no coverage tooling — consistent with B0-B3).

### Spec Compliance Matrix (B4 slice)

| Requirement | Scenario | Covering test (runtime, all passing) | Result |
|-------------|----------|--------------------------------------|--------|
| SS-1 Bot-Resolves vs Always-Escalate | Owner changes a rule | `test_scope_mode_per_category_override` (valores→always_escalate stored; calefont keeps bot_resolve) + `test_scope_mode_invalid_stored_mode_falls_back_to_default` | ✅ COMPLIANT |
| SS-1 Bot-Resolves vs Always-Escalate | Rule change takes effect | `test_scope_always_escalate_category_escalates` (graph run: always_escalate category → handoff; no LLM answer) + `test_scope_bot_resolve_category_does_not_escalate` (companion) | ✅ COMPLIANT |
| SS-2 Configurable Emergency Keywords | Keyword added | `test_emergency_keywords_override_round_trip` (list round-trips through KV) + `test_custom_keyword_from_settings_detected` (settings change → next message detects; 0 LLM calls) | ✅ COMPLIANT |
| SS-3 Cost Guardrails | Conversation limit reached | `test_conversation_cost_state_conservative_at_80` (exact 80.0%) + `test_conversation_cost_state_blocked_at_100` (exact 100%) + `test_conversation_blocked_escalates_no_llm` (blocked→handoff, HANDOFF_REPLY, 0 LLM calls, `cost.alert.conversation.100` audit) | ✅ COMPLIANT |
| SS-3 Cost Guardrails | Daily limit reached | `test_daily_cost_state_blocked_at_100` + `test_daily_blocked_escalates_no_llm` (daily 100% → escalate cost_daily_limit, no paid LLM, deterministic fallback) + `test_maybe_alert_owner_daily_scoped_by_date` (per-UTC-day dedupe) | ✅ COMPLIANT |
| SS-4 Cost Tracking and Meta Pricing Awareness | (tracking + snapshot basis) | `test_spend_snapshot_exposes_spend_limits_and_mode` + `test_spend_snapshot_without_conversation_scope` (date/spend/limits/percent/mode read model) + `test_meta_message_cost_uses_stored_settings_value` (meta_pricing via settings) + `test_daily_spend_scoped_to_day` (B3) | ✅ COMPLIANT (basis; "spend visible in panel" scenario → T5.4) |
| SS-5 Adjustable Tone and Messages | Message edited | `test_tone_override` + `test_message_override_wins_over_caller_default` (edited greeting/cannot_answer win; unset falls back to caller default) | ✅ COMPLIANT (service surface; panel UI → T5.4) |
| EM-1 Deterministic Keyword Detection | Emergency keyword detected | `test_strong_hit_each_default_keyword` (13/13 SS-2 default keywords) + `test_accent_folded_variants_are_strong` (explosión==explosion, monóxido==monoxido, eléctrico==electrico) + `test_benign_text_no_hit` (fuga de agua ≠ hit) | ✅ COMPLIANT |
| EM-1 Deterministic Keyword Detection | Keyword configured | `test_custom_keyword_from_settings_detected` (SS-2 list change → strong hit next message, before any LLM) | ✅ COMPLIANT |
| EM-2 Flow Interrupt | Interrupt mid-capture | `test_strong_hit_mid_capture_interrupts` (capture in progress; emergency message → protocol replies, `_pending` NOT advanced, 0 additional LLM calls) | ✅ COMPLIANT |
| EM-3 Safety Instructions | Safety guidance delivered | `test_strong_hit_mid_capture_interrupts` (INSTRUCCIONES DE SEGURIDAD + CONTACTOS DE EMERGENCIA incl. Bomberos 132 + "notificado"; case.emergency=True, status=escalado, state→human) | ✅ COMPLIANT |
| EM-4 Immediate Owner/Technician Notification | Notification sent | `test_emergency_node_fires_notification_on_strong_hit` (template to `notify.owner_whatsapp`, notified_at set, `notification.sent` audit) + `test_template_goes_to_owner_with_phone_and_context` (customer phone + location + context params) + `test_email_fallback_on_whatsapp_failure` | ✅ COMPLIANT |
| EM-4 Immediate Owner/Technician Notification | Notification acknowledged | `test_acknowledge_records_ack_on_case` (acknowledged_at + ack_by=customer_reply + `case.acknowledged` audit) + `test_ack_hooked_in_ingest_process_message` (webhook path) + `test_ack_ignored_when_already_acknowledged` | ✅ COMPLIANT |
| EM-5 Conservative Default | Ambiguous risk | `test_weak_hit_escalates_not_ignored` (huele raro / no me llega gas / olor a quemado → weak) + `test_weak_hit_escalates_to_human` (weak → handoff deriva case, HH-2 bundle, state→human, never ignored; no emergency protocol flags) | ✅ COMPLIANT |
| HH-1 Per-Conversation State Model | Bot to human | `test_state_transition_bot_to_human_records_event` (state_change event with cause+actor) + `test_persona_escalates_to_human_with_deriva_case` (state→human via handoff) | ✅ COMPLIANT |
| HH-1 Per-Conversation State Model | Close conversation | `test_state_transition_close_records_closure` (→closed + closed_at stamped + event recorded) + `test_state_transition_same_state_is_noop` | ✅ COMPLIANT |
| HH-2 Deriva with History and Summary | Handoff bundle complete | `test_handoff_bundle_contains_history_summary_customer_captured` (bundle: history ≥4 msgs, summary on case+conv, customer phone, captured fields, escalate_reason=complaint) | ✅ COMPLIANT |
| HH-3 Escalation Triggers | Customer requests a person | `test_gate_persona_trigger` (deterministic pre-LLM) + `test_persona_escalates_to_human_with_deriva_case` (escalated with history+summary) | ✅ COMPLIANT (this B4 scenario; "two failed comprehension" verified in B3, re-confirmed here by `test_two_unknown_intents_escalate_to_human`) |
| HH-5 Human Response Channel | Webhook keeps recording during human phase | `test_hh5_human_state_persists_without_bot_reply` (inbound during human → persisted, status processed, NO bot reply, no LLM) + `test_hh5_human_state_graph_direct_still_persists_events` (no re-escalation) | ✅ COMPLIANT |
| CR-5 History Linkage | History complete | `test_cr5_closed_opens_new_conversation_through_ingest` (closed conversation never reopens; next inbound → NEW conversation, same customer, history linked) + B3 history test | ✅ COMPLIANT (re-verified at ingest path; counted in B3, B4 adds ingest evidence) |
| SH-5 Audit Log | Settings change audited | `test_set_creates_row_and_audits_change` (actor/action/entity_id/before/after) + `test_set_update_upserts_in_place` (2 writes → 2 audit entries, before/after on each) + `test_semantic_writes_are_audited` (scope_rules + keywords audited) + notification/handoff audits (`notification.sent`, `case.acknowledged`, `conversation.handoff`) | ✅ COMPLIANT |

**Compliance summary (B4 slice)**: 21/21 scenarios compliant for the verified scope; 16/16 requirements mapped to passing tests. Deferred per tasks.md traceability: SS-4 "spend visible" panel → T5.4 · SS-5 panel UI → T5.4 · HH-4 case visibility → T5.3 · SH-5 login audit → T5.1.

### Correctness (Static Evidence — B4)

| Design item | Status | Notes |
|-------------|--------|-------|
| `app/services/settings.py` — KV + scope/keywords/tone (D5, SS-1/2/5, SH-5) | ✅ Implemented | `get_setting`/`set_setting` (UPSERT + one audit entry per write, actor+updated_by); `get_scope_mode` (SS-1, invalid mode → default), `get_emergency_keywords` (SS-2, EM-1 defaults), `get_tone`/`get_message` (SS-5); SETTINGS_DEFAULTS incl. meta_pricing (SS-4) + cost limits (SS-3) + notify/safety defaults |
| `app/services/emergency.py` — regex engine (EM-1, EM-5, SS-2) | ✅ Implemented | accent-folded (NFD) + IGNORECASE compile, longest-first; strong/weak/None (EM-5 weak markers); benign-qualifier exclusion ("fuga de agua" ≠ hit); read-only default list |
| `emergency_gate` node — before any LLM (EM-1/2/5) | ✅ Implemented | runs on every inbound incl. mid-capture; per-run settings read (SS-2 immediate); weak → escalate_reason=emergency_weak_hit |
| `emergency` node — safety protocol (EM-2/3/4) | ✅ Implemented | safety instructions + contacts + notify_message from settings; case flagged (migration 004); state→human (HH-1 actor=system); notification via notify service (dedup on notified_at); never blocks on notification failure |
| `app/services/notify.py` — EM-4 + D9 | ✅ Implemented | `emergency_alert` template to `notify.owner_whatsapp` (customer phone + location + context), email fallback (stdlib smtplib), every attempt audited (SH-5), never raises; `is_ack_message`/`acknowledge_emergency_if_ack` (reply-keyword ack, audited); `send_pending_emergency_reminders` (>15 min, max 2, audited) |
| Ack + reminders wiring | ✅ Implemented | `acknowledge_emergency_if_ack` before the graph in ingest `process_message`; `send_pending_emergency_reminders` inside `sweep_received` (no new scheduler); migration 005 columns |
| `handoff_gate` — deterministic triggers (HH-3) | ✅ Implemented | persona/media/complaint pre-LLM; 2× unknown + SS-1 always_escalate post-classification; all converge on handoff node |
| `handoff` node — deriva (HH-1/2) | ✅ Implemented | CM-5 summary (failure degrades, never blocks), `create_handoff_case` bundle (history+summary+customer+captured+reason), state→human with cause+actor, audit + ConversationEvent; under cost block skips the summary LLM |
| `app/services/cases.py` — HH-2 bundle | ✅ Implemented | `get_or_create_case` + `build_deriva_bundle` + `create_handoff_case`; replaces T3.4 `_get_or_create_case` ponytail debt |
| State model (HH-1) | ✅ Implemented | `set_conversation_state` writes state_change event (cause+actor, migration 006); closed stamps closed_at; `get_or_create_conversation` never reopens closed (CR-5) |
| HH-5 ingest guard | ✅ Implemented | `process_message`: human-state conversation → persist + PROCESSED, no graph run, no outbound; media-only inbound now runs the graph (evidence → handoff) |
| `cost_gate` node (SS-3) | ✅ Implemented | after emergency_gate, before handoff_gate; combined mode worst-wins; blocked → escalate + reason cost_daily_limit/cost_conversation_limit; 80%/100% alerts fire here |
| `costs.py` guardrails (SS-3/4) | ✅ Implemented | `conversation_cost_state`/`daily_cost_state` (Decimal exact 80/100 boundaries), `_limit` deduped read path, `maybe_alert_owner` (audit-deduped: audit row + email, never raises), `spend_snapshot` (SS-4 panel read model) |
| Graph ordering | ✅ Implemented | START→emergency_gate→(strong→emergency | weak→handoff | miss→cost_gate)→(blocked→handoff | else→handoff_gate)→(trigger→handoff | else→receive); safety > budget > handoff > LLM; documented in graph.py |
| `respond` conservative mode (SS-3) | ✅ Implemented | BRIEF_MODE_SUFFIX appended to system prompt when cost_mode=="conservative" (one-line replies; deterministic) |
| send.py consolidation (T4.1.1 debt) | ✅ Implemented | `meta_message_cost` reads via `get_setting` (stored/malformed/missing → DEFAULT_META_COST); send/notify share one settings read path |
| Migrations 004/005/006 | ✅ Implemented | apply cleanly, idempotent, live-verified (columns present); migration tests updated (10/10) |

### Coherence (Design — B4)

| Design decision | Followed? | Notes |
|-----------------|-----------|-------|
| D4 no LLM on safety path | ✅ Yes | emergency path proven zero-LLM (call-count assertions in tests + runtime harness); weak → deterministic escalate |
| D5 single settings KV table | ✅ Yes | scope_rules/keywords/tone/limits/safety/notify all in `settings` JSONB; one UPSERT + one audit entry |
| D9 notification = WhatsApp template + email fallback; ack keyword | ✅ Yes | `emergency_alert` template to owner + smtplib fallback; ack via reply keyword (panel button → T5.3) |
| Gate ordering (emergency → cost → handoff → LLM) | ✅ Yes | design drew gates abstractly; concrete order documented in graph.py and proven by `test_emergency_wins_over_daily_block` (safety beats budget) |
| HH-1 every transition recorded with timestamp+cause | ✅ Yes | state_change events with actor (migration 006); no-op transitions write nothing |
| HH-2 deriva bundle self-contained | ✅ Yes | JSONB bundle snapshot on case (history/summary/customer/captured/reason); panel renders without re-join |
| HH-5 persist during human, no panel reply in H1 | ✅ Yes | ingest boundary guard; no bot loop |
| CR-5 closed→new, history linked | ✅ Yes | get_or_create_conversation never reopens closed; ingest-level test |
| Deviation 1 (EM-4/D9): notification recipient = OWNER (`notify.owner_whatsapp`), not the customer | ✅ Acceptable | Spec text "notify the configured owner/technician contact"; template carries customer phone as a parameter. Matches EM-4 and D9 — the customer's own emergency reply is the customer-facing channel |
| Deviation 2: gate ordering gate-first (emergency_gate before receive) | ✅ Acceptable | Keeps the greeting/menu out of the safety protocol (EM-2 full interrupt); recorded in graph.py |
| Deviation 3: HH-5 persist-only (no reply from bot during human) | ✅ Acceptable | Spec: "In H1 the human responds through the same WhatsApp number"; ingest marks PROCESSED, no graph run |
| Deviation 4: conservative mode only in respond | ✅ Acceptable | Summary node is internal and already "breve y conciso"; documented in apply-progress |
| Deviation 5: blocked path reuses existing handoff node | ✅ Acceptable | Single escalation flow (T4.4 principle); handoff skips summary LLM under block — no fake-answer generator |
| Deviation 6: owner cost alert = audit + email only (no WhatsApp template) | ✅ Acceptable | Cost-alert utility template needs Meta approval (T2.1); email is the T4.3 fallback channel already in place; documented in maybe_alert_owner docstring |
| Deviation 7: cost block reply = existing HANDOFF_REPLY | ✅ Acceptable | Same no-LLM reply family as CANNOT_ANSWER_REPLY/CLARIFICATION_REPLY; deterministic, SS-3 "escalate to human" |
| Rollback boundary | ✅ Yes | B4 = 18 commits e43c6b46..c0823e6e; reset to ef8aba74 removes slice cleanly; B0-B3 suites still green (128/128 in full run) |

### Strict TDD Compliance (Step 5a + expanded)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | apply-progress obs #1372/#1424 (topic sdd/hito-1-setup-whatsapp/apply-progress) "TDD Cycle Evidence" tables present (T4.1..T4.5 rows, RED→GREEN→TRIANGULATE→SAFETY NET→REFACTOR) |
| All tasks have tests | ✅ | 5/5 B4 code tasks have test files (settings/emergency/emergency_notify/handoff/cost_guardrails); T2.1 ops-blocked (no tests expected) |
| RED confirmed (tests exist) | ✅ | 5/5 test files verified on disk (RED = failing/import errors per apply-progress) |
| GREEN confirmed (tests pass) | ✅ | 118/118 B4 tests pass on execution now — cross-referenced against live runs, not trusted blindly |
| Triangulation adequate | ✅ | 118 distinct cases: settings ×17 (KV read/write/audit, scope ×3, keywords ×2, tone/messages ×4) · emergency ×32 (13 keywords + 5 accent + 3 weak + 3 benign + 2 pair + 4 graph) · notify ×29 (template ×4, fallback ×2, ack ×8+3, reminders ×3, graph ×2) · handoff ×18 (transitions ×3, gate ×5, scope ×2, graph ×7) · cost ×22 (thresholds ×8, snapshot ×2, alerts ×4, gate ×6) — multiple distinct expectations per behavior; no single-case task with multi-scenario spec |
| Safety Net for modified files | ✅ | test_webhook_ingest.py modified (ack hook + media evidence + HH-5 guard): B0-B3 suites still green in full run (128 baseline); new files "N/A (new)" correct; ingest/state/graph/send modified — full 246 green |
| Assertion quality audit (5f) | ✅ | No tautologies, no ghost loops, no smoke-only, no type-only-alone. Strongest: cost-block tests assert zero LLM calls under block; `test_emergency_wins_over_daily_block` asserts the cost gate NEVER ran (no alert audit rows); Decimal-exact 80.0/100.0 boundary asserts; `test_weak_hit_escalates_to_human` asserts customer text NEVER in an LLM user slot; SMTP patched via fixtures (never real) |

**TDD Compliance**: 7/7 checks passed.

### Test Layer Distribution (B4)

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 118 | 5 (+ shared conftest) | real pgvector container + respx (OpenAI chat, Meta template/send) + SMTP patched (smtplib fixture) |
| E2E | 0 | 0 | — |
| **Total** | **118 (B4)** | **5** | suite total 246 (128 B0-B3 + 118 B4) |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config.yaml `verify.coverage_threshold: 0`, no pytest-cov in pyproject). Informational only (strict-TDD module).

### Quality Metrics

**Linter**: ➖ Not available · **Type Checker**: ➖ Not available. Informational only — never blocking.

### Issues Found (B4 slice)

**CRITICAL**: None

**WARNING**:
1. **(Carried from B1/B2/B3 — MECHANISM RESOLVED, hygiene remains)** Real `OPENAI_API_KEY` still exported in the dev shell (`~/.bashrc`). conftest FORCES `os.environ["OPENAI_API_KEY"] = "sk-test"` (no setdefault), so tests can never pick up the real key — verified: zero real network calls (full suite green). Remaining risk is dev-shell hygiene only (an unmocked manual script could spend tokens). Downgraded, unchanged.
2. (NEW, informational) B4 diff (authored, excl. graphify artifacts + verify report) = 3,620 insertions / 79 deletions across 32 files vs B4 forecast ~1,150 lines (tests excluded from forecast per tasks.md). Within the chained-PR contract; flagging for PR-time reviewer awareness only — the large deltas are the graphify `graph.json`/`graph.html` artifacts and the migration/test bodies, not unexpected architecture.

**SUGGESTION**:
1. (Carried) `tasks.md` header claims "34 tasks" vs 33 rows (line 4). Fix on next tasks.md edit.
2. (Carried) WH-1 "Token mismatch" scenario log clause — no `caplog` assertion yet. Close in a later batch or T6.1.
3. (Carried) README curl proof manual — spec-marker count check in T6.1.
4. (Carried) `test_infra.py::test_db_service_uses_pgvector_image` double-condition assert — cosmetic simplification.
5. (Carried) Rate limiter counts duplicate deliveries against the per-phone budget BEFORE dedup — consider counting newly-inserted rows when ingest is next touched.
6. (Carried) Non-JSON body → 200+drop has no covering test — add in T6.2 functional suite.
7. (Carried from B3) Media-only inbound now runs the graph (B4 fixed the silent no-reply gap) — a photo-only first contact escalates as evidence via the handoff gate; covered by `test_media_evidence_escalates_through_process_message`. RESOLVED in B4.
8. (NEW) `test_handoff.py::test_cr5_closed_opens_new_conversation_through_ingest` comments note a latent psycopg rowcount quirk (`persist_message` boolean returns False even for new rows) — the acceptance asserts the row landed in a NEW conversation, so the quirk is documented not blocking; worth a look in T6.x.

### Graphify Context (B4)

- Graph check: `graphify-out/graph.json` present (876 nodes / 1623 edges / 66 communities; report header "built from commit c3226c49", `.graphify_analysis.json` regenerated 2026-08-13 08:19 post-B4 — B4 nodes ARE present in queries; semantic extraction blocked without a real OpenAI key per apply-progress; AST pass current; orchestrator owns the final refresh).
- Query `graphify query "emergency detection regex gate"` (BFS depth=2, 82 nodes): start nodes `Emergency Detection`, `Emergency Detection Specification`, `app/chat/nodes/emergency_gate.py`, `services/emergency.py`, `Task T4.2 — emergency detection + gate`, `EM-1..EM-5` — all [EXTRACTED]; communities: Conversation Manager, 34 (emergency nodes).
- Query `graphify query "handoff deriva cases escalation"` (BFS depth=2, 131 nodes): `HH-1..HH-5`, `Task T4.4 — Handoff + deriva + gates + tests`, `cases`, `Case Record`, `Human Handoff` — [EXTRACTED].
- Query `graphify query "cost guardrails spend limit gate"` (BFS depth=2, 204 nodes): `Cost guardrails (spend limits + alerts)` (design), `costs.py` + `daily_spend()`/`conversation_spend()`/`_sum_columns()`, `tests/integration/test_cost_guardrails.py`, `Task T4.5 — Cost guardrails`, `SS-1..SS-4` — [EXTRACTED].
- Path `graphify path "costs.py" "send.py" --undirected` → 2 hops: `costs.py --imports_from--> models.py <--imports_from-- send.py` ✓ (settings-service consolidation keeps the same 2-hop shape).
- Path `graphify path "emergency_gate.py" "handoff" --undirected` → 7 hops via `Task T4.2 → Task T4.1 → Task T1.2 → T2.2 → WH-3 → WhatsApp Webhook → Human Handoff` (task→spec edges present).
- Communities consulted: Conversation Manager (EM/SS/HH cluster), 34 (emergency nodes), 33 (cost guardrails), T3.6 Send + cost services, T4.4 Handoff.
- Cosmetic: graphify skill 0.6.1 vs package version-mismatch warning — ignore (carried).

### Runtime Harness Spot-Check (live)

```text
docker ps                                       -> lumat-pg-test UP (23 h), 0.0.0.0:5432->5432
psql schema_migrations                          -> [001_init .. 006_handoff_deriva] (6)
psql \d cases / \d conversation_events          -> emergency/notified_at/acknowledged_at/ack_by/reminder_count/bundle + actor present
pytest tests/integration/{settings,emergency,emergency_notify,handoff,cost_guardrails}.py -> 118 passed (real DB, TRUNCATE-reset)
pytest tests/                                   -> 246 passed in 41.64s (128 B0-B3 + 118 B4), exit 0
build import (test env)                         -> import OK, exit 0
secrets grep (sk-/EAAG/AKIA/ghp_)               -> no credential values in app/ db/ infra/
```

**B4 runtime harness** (signed webhook, Meta/OpenAI respx-mocked, /tmp/opencode/b4_harness.py):
```text
[1] emergency "huele a gas en el calefont" via signed POST ->
    state=human, case.emergency=True, notified_at set,
    audit=[customer.auto_created, conversation.emergency_detected, notification.sent],
    outbound safety replies x3 (INSTRUCCIONES DE SEGURIDAD / CONTACTOS / notificado),
    LLM calls=0, Meta template to owner=+56912345678 (name=emergency_alert) OK
[2] customer reply "ok gracias" -> acknowledged_at set, ack_by=customer_reply,
    case.acknowledged audit row (SH-5) OK
[3] seeded daily spend >= $5.00 -> benign message from a FRESH phone ->
    LLM calls before=0 after=0 (no LLM under block), reply='Un asesor revisará tu caso...',
    state=human, bundle escalate_reason=cost_daily_limit OK
HARNESS PASS: emergency->notify->ack->cost-block all verified live
```
(Note: the harness intentionally has no SMTP server, so the SS-3 100% alert email to localhost is refused — `maybe_alert_owner` catches it and never raises, proving the never-raises contract; the alert audit row is still written.)

### Verdict (B4 slice)

**PASS** — Batch 4 (T4.1 settings/scope/tone, T4.2 emergency engine+gates, T4.3 notification+ack+reminders, T4.4 handoff+deriva, T4.5 cost guardrails) is complete (5/5 tasks [x]), fully tested (118/118 focused, 246/246 full suite, live against the pgvector container with OpenAI/Meta/SMTP mocked/patched), and matches specs SS-1..5, EM-1..5, HH-1/2/3/5, CR-5, SH-5, the design D4/D5/D9 decisions, the gate-ordering (safety > budget > handoff > LLM), and task acceptance criteria. Strict TDD evidence validated 7/7. Runtime harness proved the EM-4 notification (Meta template to owner, mocked), the reply-keyword ack, and the SS-3 daily cost block end-to-end through the signed webhook. No CRITICAL findings; 1 carried WARNING (dev-shell key hygiene — test-override mechanism fixed). T2.1 remains `[ ]` **blocked on client credentials** — blocked is a PASS for this slice. **Cumulative: 39 reqs / 55 scenarios across B0+B1+B2+B3+B4.** Recommended next: create PR 5 (B4 slice, stacked to main), archive B4 slice (orchestrator), then Batch 5 apply (T5.1 panel auth … T5.5 dashboard; T5.4 settings view consumes spend_snapshot), and unblock T2.1 when Meta credentials arrive.

## Previous Slices — B0 (PR 1) PASS, B1 (PR 2) PASS, B2 (PR 3) PASS — preserved verbatim

B0 (f8357e5f..0894f5c7): PASS, 3/3 reqs, 5/5 scenarios (WH-1..WH-3), 12/12 tests. B1 (d405dcab..45565e3f): PASS, 3/3 reqs, 3/3 scenarios (WH-5 schema, SH-5, SH-2), 38/38 tests. B2 (54c61829..a2ee2a62): PASS, 5/5 reqs, 6/6 scenarios (WH-3..WH-7 delivery path), 62/62 tests. Full B0+B1+B2 bodies preserved in this file below the B3 section and in the prior Engram revision (obs #1375). Key carried findings: 1 WARNING (real OPENAI_API_KEY in dev shell) — **mechanism now fixed in B3** (see WARNING-1); deferred items SH-5 login → T5.1, SH-2 read-only fs → T7.1, KB-3 manager view → T5.4, HH-3 persona-menu trigger → T4.4, SH-4 tool-whitelist suite → T6.3.

## Previous Slice — Batch 3 (PR 4) PASS — preserved verbatim

**Verified slice**: commits `c3226c49..ef8aba74` (8 commits: 7dd1d796 feat(customers) · c309238b feat(chat state+receive) · ceffdef6 feat(kb) · addceb7c feat(chat intent+route) · f5a83d4b feat(chat capture+respond+summary) · 8693b6a3 fix(route injection) · 9b7aa710 feat(send+costs) · ef8aba74 fix(webhook claim-pattern sweep))
**Runtime harness**: `lumat-pg-test` container UP (localhost:5432, pgvector) — all suites executed against the real DB; OpenAI/Meta calls respx-mocked.

### Completeness (B3 slice)

| Metric | Value |
|--------|-------|
| Tasks total (change) | 33 (header says 34 — pre-existing discrepancy, SUGGESTION-1 carried) |
| Tasks complete | 13/33 (B0: 3 + B1: 3 + B2: 2 + B3: 6, of which T2.1 stays `[ ]` **blocked**) |
| B3 tasks complete | 6/6 — T3.1 [x], T3.2 [x], T3.3 [x], T3.4 [x], T3.5 [x], T3.6 [x] (tasks.md) |
| B3 requirements verified | 18/18 slice-scope: CR-1..6 (6) · CM-1..6 (6) · KB-1, KB-2, KB-4 (3) · HH-3 (1, partial) · SH-4 (1, partial) · SS-4 (1, tracking basis) |
| B3 scenarios verified | 25/25 slice-scope: CR 8 · CM 9 · KB 6 · HH-3 1 · SH-4 1 · SS-4 0 (basis only, panel visibility deferred) |
| T2.1 blocked verdict | ✅ PASS for this slice — ops dependency on client credentials, unchanged from B2 |

Full-spec totals for context: customer-records = 6 reqs / 8 scenarios · conversation-manager = 6 reqs / 9 scenarios · knowledge-base = 4 reqs / 7 scenarios (KB-3 manager view → T5.4) · human-handoff = 5 reqs / 7 scenarios (B3 covers HH-3 scenario "two failed comprehension") · security-hardening = 5 reqs / 8 scenarios (B3 covers SH-4 scenario "injection treated as data") · settings-scope-limits = 5 reqs / 5 scenarios (B3 covers SS-4 tracking basis; visibility → T4.5/T5.4). **Cumulative B0+B1+B2+B3: 27 reqs / 37 scenarios verified.**

### Build & Tests Execution (B3)

**Build-equivalent**: ✅ Passed (exit 0)
```text
.venv/bin/python -c "import app.main; from app.services.customers import ...; from app.services.kb import ...; from app.services.send import ...; from app.services.costs import ...; from app.chat.state import ConversationState; from app.chat.graph import build_graph, run_conversation; from app.chat.nodes.classify_intent import classify_intent, is_injection; from app.chat.nodes.respond import respond, log_unresolved; from app.chat.nodes.capture import capture; from app.chat.nodes.summary import summary; print('import OK')"
-> import OK   (hash sha256:73e65cba…4cefc54219)
```

**Focused suites** (live pgvector, exit 0):
```text
$ pytest tests/integration/test_customers.py -v      -> 17 passed
$ pytest tests/integration/test_chat_state.py -v     -> 8 passed
$ pytest tests/integration/test_kb.py -v             -> 11 passed
$ pytest tests/integration/test_chat_intent.py -v    -> 12 passed
$ pytest tests/integration/test_chat_capture.py -v   -> 7 passed
$ pytest tests/integration/test_send_costs.py -v     -> 11 passed
Total: 66 passed in 12.74s   (hash sha256:784d49d9…0ed1b1eb15)
```

**Full suite**: ✅ **128 passed / 0 failed / 0 skipped** in 19.76s, exit 0 — matches expected 128 (12 B0 + 26 B1 + 24 B2 + 66 B3), no regressions.
Output hash: `sha256:6c6a34e6f8a139ed7922365678db3bb1f5f571a6308d846306cb0aee2363596c`.

**Migration check** (live): `schema_migrations` = [001_init, 002_customer_notes, 003_conversation_captured_data]; `\dt` shows 12 tables (11 business incl. `customer_notes` + schema_migrations); `conversations.captured_data` JSONB present; `test_migrations.py` 10/10 green (002/003 expectations updated).

**Secrets check** (all passed):
```text
git grep -iE "sk-|EAAG|ghp_|AKIA" app/ db/ infra/ (excl. sk-test)  -> no credential values
git grep -E "sk-[A-Za-z0-9]{10,}" / "EAAG[A-Za-z0-9]{10,}"         -> no matches
git ls-files | grep -i env                                          -> only infra/.env.example (SH-2 intact)
```
No test makes a real call to api.openai.com: every LLM-touching test takes a respx mock fixture; conftest FORCES `OPENAI_API_KEY=sk-test` so an unmocked call fails fast (401) instead of hitting the network — full suite green confirms zero real calls (dev shell has a real key, apply-progress issue 2).

**Coverage**: ➖ Not available (config.yaml `verify.coverage_threshold: 0`; no coverage tooling — consistent with B0/B1/B2).

### Spec Compliance Matrix (B3 slice)

| Requirement | Scenario | Covering test (runtime, all passing) | Result |
|-------------|----------|--------------------------------------|--------|
| CR-1 Auto-Ficha | First contact creates ficha | `test_cr1_first_contact_creates_ficha` + `test_cr1_unknown_phone_creates_exactly_one_row` (auto row + audit on create) | ✅ COMPLIANT |
| CR-2 Phone-Based Dedup | Known customer returns | `test_cr2_same_number_reuses_record` (id equality + count 1) | ✅ COMPLIANT |
| CR-2 Phone-Based Dedup | Different formatting | `test_cr2_different_formatting_dedups` (`+56 9 1234 5678` vs local `912345678` → same ficha) + `test_cr2_full_international_format_dedups` (`+569...` vs `569...`) | ✅ COMPLIANT |
| CR-3 Lifecycle States | State progression | `test_cr3_valid_transition_updates_state` (nuevo→pendiente) + `test_cr3_postventa_reachable_only_after_finalizado` + `test_cr3_state_change_audited` (actor/action/before/after in audit_log) | ✅ COMPLIANT |
| CR-3 Lifecycle States | Invalid transition rejected | `test_cr3_invalid_transition_rejected` (nuevo→postventa raises InvalidStateTransition, state unchanged) | ✅ COMPLIANT |
| CR-4 Internal Notes | Staff adds note | `test_cr4_add_note_stores_author_and_timestamp` + `test_cr4_list_notes_chronological` + `test_cr4_notes_are_staff_only_no_customer_exposure` (separate customer_notes table) | ✅ COMPLIANT |
| CR-5 History Linkage | History complete | `test_cr5_history_lists_conversations_cases_messages` (chronological dicts) + chat-state `test_cr5_closed_conversation_opens_new` (closed → new conv, history linked) | ✅ COMPLIANT |
| CR-6 Data and Consent Recording | Captured data persisted | `test_cr6_captured_data_persisted_on_ficha` + `test_cr6_consent_recorded_with_timestamp` + `test_cr6_consent_withdrawn` + capture `test_cm2_complete_capture_persists_and_confirms` (end-to-end consent → ficha) | ✅ COMPLIANT |
| CM-1 Single-Agent Flow with Menu | First contact | `test_cm1_first_contact_greeting_with_menu` (greeting + 8-category menu) + `test_cm1_menu_has_exactly_8_categories` (exact CM-1 category list) | ✅ COMPLIANT |
| CM-1 Single-Agent Flow with Menu | Repeat contact resumes | `test_cm1_repeat_contact_resumes_not_from_scratch` (2nd reply is NOT a fresh greeting — resumes state) | ✅ COMPLIANT |
| CM-2 Progressive Capture | Complete capture | `test_cm2_progressive_capture_asks_fields_in_order` (8 fields, one per turn) + `test_cm2_complete_capture_persists_and_confirms` (all fields stored, completion reply) | ✅ COMPLIANT |
| CM-2 Progressive Capture | Customer skips a field | `test_cm2_skip_is_unknown_and_non_blocking` (skip → "unknown", flow continues) + evidence skip inside complete-capture test | ✅ COMPLIANT |
| CM-3 Intent and Case Classification | Inbound message classified | `test_cm3_intent_classified` + `test_cm3_case_classification_stored` (service/priority/status on case row) + `test_cm3_state_case_holds_classification` | ✅ COMPLIANT |
| CM-4 Authorized Technical Guidance | In-scope guidance | `test_cm4_kb_grounded_answer_with_kb_tags` (answer from `<kb>` chunks only; KB content never in system prompt; `<user_input>` slot) | ✅ COMPLIANT |
| CM-4 Authorized Technical Guidance | No reliable answer | `test_cm4_kb_miss_cannot_answer_and_logs_unresolved` (CANNOT_ANSWER_REPLY + unresolved flag + escalation) | ✅ COMPLIANT |
| CM-5 Conversation Summary | Summary after flow | `test_cm5_summary_stored_on_conversation_and_case` (conversation.summary + case.summary) | ✅ COMPLIANT |
| CM-6 Unresolved Response Logging | Unresolved question logged | `test_cm4_kb_miss_cannot_answer_and_logs_unresolved` (payload unresolved + context + ts) + `test_cm6_no_unresolved_when_kb_hits` (companion: no flag on hit) | ✅ COMPLIANT |
| KB-1 Ingestion Pipeline | Document ingested | `test_kb1_ingest_markdown_chunks_stored` + `test_kb1_ingest_pdf_extracts_text` + `test_kb1_ingest_csv_row_grouped` + `test_kb1_chunk_count_for_long_document` (3 formats, chunking, pgvector storage) | ✅ COMPLIANT |
| KB-1 Ingestion Pipeline | Provider and model named | `test_kb1_ingest_markdown_chunks_stored` asserts provider="openai", model=EMBED_MODEL, cost_meta > 0 on kb_documents | ✅ COMPLIANT |
| KB-2 Semantic Retrieval | Relevant retrieval | `test_kb2_retrieval_relevant_hit` (top chunks returned above threshold) + `test_kb2_retrieval_top_k_limits_results` (top_k=5) | ✅ COMPLIANT |
| KB-2 Semantic Retrieval | No relevant content | `test_kb2_retrieval_threshold_miss` (below 0.65 → []) + `test_kb2_min_sim_configurable` + respond test (KB miss → cannot-answer + unresolved) | ✅ COMPLIANT |
| KB-4 Versioning and Re-Ingestion | Re-ingestion on update | `test_kb4_update_creates_new_version_and_reembeds` (v2 created + re-embedded, v1 preserved, retrieval uses active v2) | ✅ COMPLIANT |
| KB-4 Versioning and Re-Ingestion | Restore previous version | `test_kb4_restore_previous_version_flip_no_reembed` (pointer flip, ZERO embedding calls — D8 verified by call count) | ✅ COMPLIANT |
| HH-3 Escalation Triggers | Two failed comprehension attempts | `test_hh3_unknown_intent_increments_counter` + `test_hh3_second_unknown_escalates` (unknown_count persisted as conversation_events, escalate at 2 with reason unknown_intent_twice) | ✅ COMPLIANT (partial req — persona-menu trigger deferred to T4.4) |
| SH-4 Prompt-Injection Mitigations | Injection attempt treated as data | `test_sh4_injection_escalates_without_llm_call` (deterministic pattern → escalate, injection text NEVER sent to LLM, audit row) + `test_sh4_injection_detected_by_llm_also_escalates` + `test_sh4_user_text_only_in_user_input_slot` (input-as-data proven) | ✅ COMPLIANT (partial req — tool-whitelist suite deferred to T6.3) |
| SS-4 Cost Tracking and Meta Pricing Awareness | (tracking basis) | `test_send_text_posts_to_meta_and_returns_wamid` + `test_deliver_outbound_sends_and_records_cost_meta` (wamid + cost_meta per row) + `test_record_llm_cost_computes_token_rate` + `test_conversation_spend_sums_cost_columns` + `test_daily_spend_sums_all_conversations` (SQL SUM, D6) | ✅ COMPLIANT (basis; "spend visible in panel" scenario → T5.4) |

**Compliance summary (B3 slice)**: 25/25 scenarios compliant for the verified scope; 18/18 requirements mapped to passing tests. Deferred per tasks.md traceability: KB-3 (manager view) → T5.4 · HH-3 "customer requests a person" → T4.4 · SH-4 "tool whitelist enforced" → T6.3 · SS-4 panel visibility → T5.4/T4.5.

### Correctness (Static Evidence — B3)

| Design item | Status | Notes |
|-------------|--------|-------|
| `app/services/customers.py` — E.164 normalize + get-or-create (CR-1/2) | ✅ Implemented | Canonical `normalize_phone_e164` (moved from ingest, re-exported); auto-ficha + audit on create; UNIQUE(phone_e164) |
| CR-3 state enum + transition map + validation + audit | ✅ Implemented | `CUSTOMER_STATE_TRANSITIONS` (nuevo→postventa absent → InvalidStateTransition); every change → audit_log before/after |
| CR-4 notes (author+timestamp) | ✅ Implemented | Migration 002 `customer_notes` + CustomerNote model + grants; staff-only table |
| CR-5 history query | ✅ Implemented | conversations/cases/messages chronological dicts; closed→new conversation (chat state) |
| CR-6 captured data + consent | ✅ Implemented | update_captured_data + record_consent on ficha; wired from capture node |
| `ConversationState` 10 design fields + D2 rebuild | ✅ Implemented | customer_id/conversation_id/phone/turn/intent/case/captured/summary/emergency/escalate/escalate_reason/window[10]; `from_db` rebuilds from DB (no checkpointer) |
| receive: first-contact greeting + 8-category menu (CM-1) | ✅ Implemented | turn<=1 → greeting_with_menu (exact 8 categories); repeat → no reply here (downstream owns) |
| KB pipeline (KB-1/2/4) | ✅ Implemented | pypdf/MD/CSV-row-grouped → RecursiveCharacterTextSplitter 500/50 → embeddings 1536d → kb_chunks version-tagged; retrieval top_k=5 min_sim=0.65 over ACTIVE versions; provider/model/cost on kb_documents |
| Versioning D8: edit re-embeds, restore = flip, disable excludes | ✅ Implemented | update_document (v+1 re-embed, prior kept), restore_version (active_version flip, no re-embed), disable_document (active=false); all audited |
| classify_intent (CM-3, HH-3 partial, SH-4 partial) | ✅ Implemented | static system prompt + `<user_input>` slot; deterministic injection pre-check → escalate WITHOUT LLM (audit); LLM injection flag → escalate; unknown → conversation_events counter, escalate at 2; case service/priority/status stored |
| route (capture vs retrieval vs escalate) | ✅ Implemented | CAPTURE_INTENTS/RETRIEVAL_INTENTS; persona/emergencia/injection → escalate; unknown non-escalated → respond (clarification) |
| capture: progressive fields + skip + consent (CM-2, CR-6) | ✅ Implemented | 8 fields one-per-turn; `_pending` persisted via migration 003 (survives D2 rebuild); skip → unknown non-blocking; consent → ficha |
| respond: KB-grounded + cannot-answer + unresolved (CM-4/6) | ✅ Implemented | `<kb>` + `<user_input>` slots; system prompt forbids invented prices/guarantees/diagnoses; KB miss → CANNOT_ANSWER_REPLY + payload unresolved flag (no SQL view, per ponytail cut 6) + escalate; list_unresolved_questions filter query |
| summary: completion/escalation (CM-5) | ✅ Implemented | LLM summary → conversation.summary + case.summary; cost_llm recorded |
| send: Meta outbound + wamid + cost_meta (SS-4 basis) | ✅ Implemented | send_text (v20.0 POST, Bearer) → wamid; deliver_outbound (wamid-NULL rows only — no double-send) + deliver_all_pending |
| costs: cost_llm tokens×rate + SQL SUM (D6) | ✅ Implemented | record_llm_cost accumulates per message; conversation_spend/daily_spend SUM(cost_llm)+SUM(cost_meta); daily = UTC day |
| Webhook wiring: graph run + delivery + claim-pattern sweep | ✅ Implemented | process_message → run_conversation + deliver_outbound; claim (received→processing, release locks) + per-message own session (deadlock fix); reset_stale_processing at boot |
| Migrations 002/003 | ✅ Implemented | apply cleanly, idempotent, grants correct (verified live + 10/10 migration tests) |

### Coherence (Design — B3)

| Design decision | Followed? | Notes |
|-----------------|-----------|-------|
| D2 no checkpointer — rebuild state from DB per message | ✅ Yes | `ConversationState.from_db` per run; tested (test_d2_state_rebuilt_from_db, window cap 10) |
| D6 cost on messages columns + SQL SUM (no spend_ledger) | ✅ Yes | cost_llm/cost_meta on messages; conversation_spend/daily_spend SUM — exactly D6 |
| D8 versioning: restore = active_version flip, no re-embed | ✅ Yes | verified by embedding call-count in test (0 calls on restore) |
| D3 OpenAI gpt-4o-mini + text-embedding-3-small | ✅ Yes | CHAT_MODEL/EMBED_MODEL; reference rates in costs.py; per-call httpx client (respx-interceptable) |
| Design Data Flow: receive → classify_intent → route → capture/kb_retrieve/respond → summary | ✅ Yes | graph.py wiring matches; `_flow_start`/`_after_capture`/`_after_respond` conditionals |
| Design conversation state field list | ✅ Yes | 10 design fields + escalate_reason; `unknown_count` (HH-3), `next_step`, `replies` added (documented deviations 3/4) |
| CM-1 menu exactly 8 categories | ✅ Yes | MENU_CATEGORIES verbatim from spec |
| KB chunking 500/50 RecursiveCharacterTextSplitter | ✅ Yes | `ponytail:` chars-not-tokens ceiling documented (deviation 8) |
| Deviation 1: migration 002 customer_notes (CR-4) | ✅ Acceptable | Design 10-table model lacked notes storage; documented in apply-progress |
| Deviation 2: migration 003 conversations.captured_data (CM-2) | ✅ Acceptable | D2 rebuild needs capture persistence; documented |
| Deviation 3/4: next_step field + replies Annotated[list, add] reducer | ✅ Acceptable | Standard LangGraph accumulator; without it last-write-wins drops replies |
| Deviation 5: receive returns no reply on repeat | ✅ Acceptable | Downstream nodes own replies (CM-1 resume honored — no restart) |
| Deviation 6: mid-capture skips re-classification | ✅ Acceptable | Saves an LLM call per capture turn; T4.2 emergency_gate runs before receive and can interrupt |
| Deviation 7: injection detection in classify_intent | ✅ Acceptable | The LLM boundary; mid-capture text stored as data, never executed (SH-4) |
| Deviation 9/10: cost_llm on classify too; costs.py born in T3.5 | ✅ Acceptable | All LLM calls tracked (D6); T3.6 completed the SUMs |
| Deviation 11: claim-pattern sweep (processing status) | ✅ Acceptable | B2 note reserved `processing` for graph runs; required to fix FOR UPDATE deadlock |
| Rollback boundary | ✅ Yes | B3 = 8 commits 7dd1d796..ef8aba74; reset to c3226c49 removes slice cleanly; B0-B2 suites still green (128/128) |

### Strict TDD Compliance (Step 5a + expanded)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | apply-progress #1372 "TDD Cycle Evidence" table present (6 rows: T3.1..T3.6) |
| All tasks have tests | ✅ | 6/6 B3 code tasks have test files (customers/chat_state/kb/chat_intent/chat_capture/send_costs); T2.1 ops-blocked (no tests expected) |
| RED confirmed (tests exist) | ✅ | 6/6 test files verified on disk (RED = import errors per apply-progress) |
| GREEN confirmed (tests pass) | ✅ | 66/66 B3 tests pass on execution now — cross-referenced against live runs, not trusted blindly |
| Triangulation adequate | ✅ | 66 distinct cases: CR ×17 (dedup ×4, transitions ×4, notes ×3, history, consent ×3), CM ×8+7+12, KB ×11 (3 formats, counts, threshold, top_k, min_sim, restore, disable), send/costs ×11 — multiple distinct expectations per behavior; no single-case task with multi-scenario spec |
| Safety Net for modified files | ✅ | conftest.py, test_migrations.py, test_webhook_ingest.py, app/webhook/ingest.py, app/main.py modified: B0-B2 suites 62/62 still green in full run (128 total); new files "N/A (new)" correct |
| Assertion quality audit (5f) | ✅ | No tautologies, no ghost loops, no smoke-only, no type-only-alone. Strongest: SH-4 injection test asserts the injection text NEVER reaches the LLM user slot; input-as-data asserted (user text == `<user_input>...` exactly); KB-restore D8 verified by embedding call count (legitimate design-decision assertion); respx stubs external OpenAI/Meta URLs only |

**TDD Compliance**: 7/7 checks passed.

### Test Layer Distribution (B3)

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 66 | 6 (+ shared conftest) | real pgvector container + respx (OpenAI chat/embeddings, Meta send) |
| E2E | 0 | 0 | — |
| **Total** | **66 (B3)** | **6** | suite total 128 (12 B0 + 26 B1 + 24 B2 + 66 B3) |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config.yaml `verify.coverage_threshold: 0`, no pytest-cov in pyproject). Informational only (strict-TDD module).

### Quality Metrics

**Linter**: ➖ Not available · **Type Checker**: ➖ Not available. Informational only — never blocking.

### Issues Found (B3 slice)

**CRITICAL**: None

**WARNING**:
1. **(Carried from B1/B2 — MECHANISM RESOLVED, hygiene remains)** Real `OPENAI_API_KEY` still exported in the dev shell (`~/.bashrc`). The B3 conftest change FORCES `os.environ["OPENAI_API_KEY"] = "sk-test"` (no more `setdefault` override), so tests can no longer pick up the real key — the silent-override risk is gone (verified: no real network call, full suite green). Remaining risk is dev-shell hygiene only (an unmocked manual script could spend tokens); stop exporting the real key or scope it per-process. Downgraded from the B1/B2 form.
2. (NEW, informational) B3 diff = 3,890 insertions / 93 deletions (~3.8k authored lines, 66 tests + 6 nodes + 5 services + 2 migrations + graph/state) vs B3 forecast ~1,600 authored lines (tests excluded from forecast per tasks.md). Within the chained-PR contract (auto-chain, stacked-to-main), flagging for PR-time reviewer awareness only — not a defect.

**SUGGESTION**:
1. (Carried) `tasks.md` header claims "34 tasks" vs 33 rows (line 4). Fix on next tasks.md edit.
2. (Carried) WH-1 "Token mismatch" scenario log clause — no `caplog` assertion yet. Close in a later batch or T6.1.
3. (Carried) README curl proof manual — spec-marker count check in T6.1.
4. (Carried) `test_infra.py::test_db_service_uses_pgvector_image` double-condition assert — cosmetic simplification.
5. (Carried) Rate limiter counts duplicate deliveries against the per-phone budget BEFORE dedup (B2 SUGGESTION-5) — untouched in B3; consider counting newly-inserted rows when ingest is next touched, or document in docs/ops.md.
6. (Carried) Non-JSON body → 200+drop has no covering test (B2 deviation 5) — add in T6.2 functional suite.
7. (NEW) Media-only inbound messages (`direction==inbound` with no text) skip the graph run entirely — no greeting on a media-only first contact, and no media-evidence handoff until T4.4 (HH-3 "evidence requiring technical review"). Matches design (media → handoff review in T4.4); suggest a deterministic reply or gate coverage in T4.4/T6.2 so a photo-only customer is not left unanswered.

### Graphify Context (B3)

- Graph check: `graphify-out/graph.json` present (636 nodes / 1211 edges / 39 communities; built at d405dcab — B3 file nodes may lag; background refresh in progress, orchestrator owns final refresh; used current graph as-is per instructions).
- Query `graphify query "customers E164 dedup ficha state notes history consent"` (BFS): start nodes `customers.phone_e164 UNIQUE (design Data Model, CR-2 dedup).`, `test_customers_phone_e164_unique()`, `CustomerState` — subgraph includes `app/models.py`, `ConversationState`, `normalize_phone_e164()`, `app/webhook/ingest.py` — all [EXTRACTED].
- Paths (directed where possible): T3.2 → CM-1 (5 hops via Batch 3 → T3.5 → CM-5 → CM-1) · T3.3 → KB-2 (5 hops via Conversation Manager) · T3.4 → SH-4 (5 hops via HH-3 → T4.4 → SH-5 → SH-4) · T3.6 → SS-4 (5 hops via T1.2 → SH-5 → Security Hardening) — task→spec edges present via intermediate nodes.
- Communities consulted: Customer Records (CR cluster), Chat Graph Routing, Knowledge Base Pipeline, Cost Tracking and Sending, WhatsApp API Onboarding.
- Cosmetic: graphify skill 0.6.1 vs package version-mismatch warning — ignore (carried).

### Runtime Harness Spot-Check (live)

```text
docker ps                                     -> lumat-pg-test UP (13 h), 0.0.0.0:5432->5432
psql schema_migrations                        -> [001_init, 002_customer_notes, 003_conversation_captured_data]
psql \dt                                      -> 12 tables (11 business incl. customer_notes + schema_migrations)
pytest tests/integration/{customers,chat_state,kb,chat_intent,chat_capture,send_costs}.py -> 66 passed (real DB, TRUNCATE-reset)
pytest tests/                                 -> 128 passed in 19.76s (12 B0 + 26 B1 + 24 B2 + 66 B3), exit 0
build import (test env)                       -> import OK, exit 0
secrets grep (sk-/EAAG/AKIA/ghp_)             -> no credential values in app/ db/ infra/
```

### Verdict (B3 slice)

**PASS** — Batch 3 (T3.1 customers, T3.2 chat state/graph/receive, T3.3 KB pipeline, T3.4 intent+routing, T3.5 capture+respond+summary, T3.6 send/costs) is complete (6/6 tasks [x]), fully tested (66/66 focused, 128/128 full suite, live against the pgvector container with OpenAI/Meta respx-mocked), and matches specs CR-1..6, CM-1..6, KB-1/2/4, HH-3 (partial), SH-4 (partial), SS-4 (tracking basis), the design D2/D6/D8 decisions and conversation graph wiring, and task acceptance criteria. Strict TDD evidence validated 7/7. No CRITICAL findings; 1 carried WARNING (dev-shell key hygiene — test-override mechanism now fixed). B2's FOR UPDATE deadlock was fixed with the claim-pattern sweep (ef8aba74) and is covered by the full suite. T2.1 remains `[ ]` **blocked on client credentials** — blocked is a PASS for this slice. **Cumulative: 27 reqs / 37 scenarios across B0+B1+B2+B3.** Recommended next: archive B3 slice (orchestrator), then proceed to Batch 4 apply (T4.1 settings · T4.2 emergency · T4.3 notify · T4.4 handoff · T4.5 cost guardrails), and unblock T2.1 when Meta credentials arrive.

## Previous Slice — Batch 0 (PR 1) PASS — preserved verbatim

**Verified slice**: commits `f8357e5f..0894f5c7` (scaffold, app factory, webhook verify/signature) · Mode: Standard (B0)

```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:0373751e8d7c944e1a270e25972d54d080ed3d345d405a618733667f7f245d2b
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 5/5
test_command: pytest tests/ ; pytest tests/integration/test_webhook_verify.py -v
test_exit_code: 0
test_output_hash: sha256:0373751e8d7c944e1a270e25972d54d080ed3d345d405a618733667f7f245d2b
build_command: .venv/bin/python -c "import app.main"
build_exit_code: 0
build_output_hash: sha256:29ac96f0f0140d10a79b55231d14e65a2759e0c42f091f7c9d961f4ddf8716b7
```

**B0 summary**: PASS — T0.1–T0.3 complete; 12/12 tests green; WH-1..WH-3 compliant (5/5 scenarios); WH-4..7 deferred to B1/B2 per tasks.md. No CRITICAL/WARNING code findings. Issues carried: SUGGESTION-1 (WH-1 caplog assertion), SUGGESTION-2 (tasks.md "34 tasks" vs 33 rows), SUGGESTION-3 (conftest `setdefault` leak), SUGGESTION-4 (spec markers). Full B0 detailed body preserved in git history (file state at commit d405dcab).

---

## Previous Slice — Batch 1 (PR 2) PASS — preserved verbatim

**Verified slice**: commits `d405dcab..45565e3f` (4 commits: dc9c9078 migration · af741c8a ORM/audit · bde1d4b8 compose/env · 45565e3f tasks [x])
**Runtime harness**: `lumat-pg-test` container UP (localhost:5432, pgvector ext 0.8.6) — integration suites executed against real DB.

```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:79e45e36542eaac05418dc9f1efe11d8843f8e115aaa1bcb40059d59e5e6b7b5
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 3/3
test_command: pytest tests/ ; pytest tests/integration/test_migrations.py -v ; pytest tests/integration/test_db.py -v ; pytest tests/integration/test_infra.py -v
test_exit_code: 0
test_output_hash: sha256:79e45e36542eaac05418dc9f1efe11d8843f8e115aaa1bcb40059d59e5e6b7b5
build_command: .venv/bin/python -c "import app.main" (with test env set)
build_exit_code: 0
build_output_hash: sha256:196c321bf8e43723e10f86032bd62cbafc1155df016ca950341fa8113e633550
```

### Completeness (B1 slice)

| Metric | Value |
|--------|-------|
| Tasks total (change) | 33 (header says 34 — pre-existing discrepancy, SUGGESTION-1) |
| Tasks complete | 6/33 (B0: 3 + B1: 3) |
| B1 tasks complete | 3/3 — T1.1 [x], T1.2 [x], T1.3 [x] (tasks.md) |
| B1 requirements verified | 3/3 slice-scope: WH-5 (schema mechanism), SH-5 (audit foundation), SH-2 (secrets-in-repo part) |
| B1 scenarios verified | 3/3 slice-scope: WH-5 retry (schema), SH-5 settings-change (service), SH-2 secrets-not-in-repo |
| Deferred (not B1 scope) | SH-5 login → T5.1 · SH-2 read-only fs → T7.1 · WH-5 full delivery path → T2.2 |

Full-spec totals for context: whatsapp-webhook spec = 7 reqs / 10 scenarios; security-hardening spec = 5 reqs / 8 scenarios. Cumulative B0+B1 verified: 6 reqs / 8 scenarios; remaining scenarios land per tasks.md traceability (B2–B7).

### Build & Tests Execution (B1)

**Build-equivalent**: ✅ Passed (exit 0)
```text
.venv/bin/python -c "import app.main; from app.db import Base; from app.models import <10 models>"
-> import OK, 10 mapped tables   (hash sha256:196c321b…e633550)
Bare `import app.main` without env fails with pydantic ValidationError naming missing vars
-> expected T0.2 fail-fast, unchanged from B0
```

**Focused suites** (all live against pgvector container, exit 0):

```text
$ pytest tests/integration/test_migrations.py -v      -> 10 passed in 1.78s
$ pytest tests/integration/test_db.py -v              -> 8 passed in 1.61s
$ pytest tests/integration/test_infra.py -v           -> 8 passed in 0.17s
```

**Full suite**: ✅ **38 passed / 0 failed / 0 skipped** (12 B0 + 26 B1) in 2.89s, exit 0 — matches expected 38.
Output hash: `sha256:79e45e36542eaac05418dc9f1efe11d8843f8e115aaa1bcb40059d59e5e6b7b5`.

**Static checks** (all passed):
```text
git ls-files | grep -i env                          -> only infra/.env.example (SH-2)
docker compose -f infra/docker-compose.yml config    -> valid with required vars injected
   (without infra/.env the :?required interpolation fails fast — intended SH-2 fail-fast, not a defect)
git grep -iE "secret|change-me|sk-|AKIA|ghp_|xoxb-" infra/ db/ app/ (excluding .env.example)
   -> only comments and env-var references; no credential values
```

**Live DB evidence** (docker exec lumat-pg-test):
```text
\dt                          -> 11 tables (10 design + schema_migrations)
schema_migrations            -> [001_init]
app grants on audit_log      -> INSERT=t UPDATE=f DELETE=f SELECT=t   (append-only, SH-5)
db/migrate.sh re-run         -> "skip 001_init (already applied)" / "migrations up to date" (exit 0)
```

**Coverage**: ➖ Not available (config.yaml `verify.coverage_threshold: 0`; no coverage tooling — consistent with B0).

### Spec Compliance Matrix (B1 slice)

| Requirement | Scenario | Covering test (runtime) | Result |
|-------------|----------|-------------------------|--------|
| WH-5 Deduplicate by WAMID | Meta retries a delivery | `test_migrations.py > test_messages_wamid_partial_unique_inbound_only` (dup inbound wamid → UniqueViolation; outbound wamid repeat allowed) + live indexdef | ✅ COMPLIANT (schema mechanism — partial unique index inbound-only proven at runtime; full delivery-path dedup completes in T2.2 per tasks.md `WH-5 → T1.1, T2.2`) |
| SH-5 Audit Log | Settings change audited | `test_db.py > test_audit_record_writes_before_after` (actor/action/entity/before/after persisted) + `test_audit_is_append_only_via_grants` (UPDATE/DELETE denied) + `test_app_role_audit_log_insert_and_select_only` | ✅ COMPLIANT (service + grant mechanism proven; admin-change wiring to settings service completes in T4.1 per tasks.md `SH-5 → T1.2, T4.1…`) |
| SH-2 Container and Secrets Hardening | Secrets not in repo | `test_infra.py > test_env_example_has_no_real_secrets` + `test_gitignore_covers_secrets_and_runtime_data` + `git ls-files` + `git grep` | ✅ COMPLIANT (only `.env.example` tracked; `change-me` placeholders; zero real keys in repo) |
| SH-5 Audit Log | Login audited | — (auth layer does not exist until T5.1) | ⏸️ DEFERRED — T5.1 (tasks.md `SH-5 → T5.1`) |
| SH-2 Container and Secrets Hardening | Read-only agent filesystem | — (prod compose `read_only` lands in T7.1) | ⏸️ DEFERRED — T7.1 (tasks.md `SH-2 → T1.3, T6.4, T7.1`) |

**Compliance summary (B1 slice)**: 3/3 scenarios compliant for the verified scope. 2 scenarios explicitly deferred to T5.1/T7.1 per tasks.md — not failures of this slice.

### Correctness (Static Evidence — B1)

| Design item | Status | Notes |
|-------------|--------|-------|
| 10 tables per design Data Model | ✅ Implemented | `001_init.sql` + `app/models.py`: customers, users, conversations, messages, cases, conversation_events, kb_documents, kb_chunks, settings, audit_log. Tested + live `\dt` (11 incl. schema_migrations) |
| `customers.phone_e164 UNIQUE` (CR-2) | ✅ Implemented | SQL `UNIQUE` + `test_customers_phone_e164_unique` (UniqueViolation raised) |
| Partial unique `messages.wamid` inbound-only (WH-5) | ✅ Implemented | `uq_messages_wamid_inbound ... WHERE direction='inbound' AND wamid IS NOT NULL`; mirrored in ORM `Index(..., postgresql_where=...)`; tested |
| HNSW `kb_chunks.embedding` (vector_cosine_ops, m=16, ef_construction=64) | ✅ Implemented | Exact params in SQL; `test_kb_chunks_embedding_hnsw_index` asserts `USING hnsw`, `vector_cosine_ops`, `m='16'`, `ef_construction='64'` |
| `vector(1536)` | ✅ Implemented | SQL + `Vector(1536)` ORM + `test_kb_chunk_vector_round_trip` (1536-dim round-trip) + `test_kb_chunks_accepts_1536d_vector` |
| App role INSERT+SELECT only on `audit_log` (SH-5 append-only) | ✅ Implemented | Grants + service surface; tested (InsufficientPrivilege on UPDATE/DELETE) + live `has_table_privilege` (I=t U=f D=f S=t) |
| Full CRUD grants on business tables | ✅ Implemented | SQL grants + `test_app_role_full_crud_on_business_tables` |
| `db/migrate.sh` idempotent + `schema_migrations` | ✅ Implemented | Python+psycopg runner, per-migration transaction, version tracking; `test_migrate_applies_cleanly_twice` (2nd run prints `skip 001_init`); live re-run confirmed |
| ORM: 10 models, PG-native enums, JSONB | ✅ Implemented | `pg_enum()` helper with `values_callable` (member values); 7 enums; JSONB on `payload`/`source_meta`/`value`/`before`/`after`; tested |
| Audit service `record(actor, action, entity, before/after)` + admin read | ✅ Implemented | `app/services/audit.py`: `record_audit` + `list_audit_entries` (newest-first); append-only by surface + grants; tested |
| Compose api + pgvector, db/media/backups volumes, healthcheck, migrate-then-serve | ✅ Implemented | `infra/docker-compose.yml`; `docker compose config` valid; `test_infra.py` structural checks; command = `uv sync --frozen && migrate.sh && uvicorn` |
| `.env.example` placeholders committed, secrets never in repo (SH-2) | ✅ Implemented | `change-me-*` placeholders only; `.env` gitignored; `!infra/.env.example` whitelisted; tested + verified via `git ls-files` |

### Coherence (Design — B1)

| Design decision | Followed? | Notes |
|-----------------|-----------|-------|
| Data Model 10 tables / enums / jsonb / vector / audit append-only | ✅ Yes | Matches design Data Model section field-for-field; append-only enforced by grants (design: "app DB role = INSERT+SELECT only") |
| HNSW index params (m=16, ef_construction=64, vector_cosine_ops) | ✅ Yes | Exact match to design KB Pipeline |
| Partial unique wamid inbound-only | ✅ Yes | Matches design Webhook Pipeline Dedup row + WH-5 |
| migrate.sh runner + schema_migrations (alembic deferred to H2) | ✅ Yes | Design: "Numbered SQL migrations + migrate.sh (schema_migrations table; alembic deferred — H2)" |
| Compose topology + volumes (design Deployment step 1) | ✅ Yes | api + postgres pgvector; db/media/backups volumes; healthcheck; migrate in container |
| Deviation 1: `pgvector>=0.3` python dep | ✅ Acceptable | Design mandates Vector via SQLAlchemy types; T0.1 dep list omitted the client package — required for `Vector(1536)` (documented in apply-progress #1372) |
| Deviation 2: migrate.sh python+psycopg (not psql) | ✅ Acceptable | psycopg already a dep; runs in api container without postgresql-client; handles role creation with env password (SH-2) — documented |
| Deviation 3: conftest DATABASE_URL → db `lumat` | ✅ Acceptable | Compose uses db `lumat`; B0 tests never connect — no behavior change — documented |
| Deviation 4: api `.venv` named-volume shadow | ✅ Acceptable (required fix) | Prevents container `uv sync` clobbering host venv (broken symlinks); verified host venv intact — documented |
| Deviation 5/6: extra test files + APP_DB_PASSWORD in .env.example | ✅ Acceptable | Strict TDD (tests ship with unit); migrate.sh needs APP_DB_PASSWORD — documented |
| Rollback boundary | ✅ Yes | B1 = 4 commits dc9c9078..45565e3f; reset to d405dcab removes slice cleanly; nothing outside B1 depends on these files (isolated set verified) |

### Strict TDD Compliance (Step 5a + expanded)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | apply-progress #1372 "TDD Cycle Evidence" table present (3 rows: T1.1, T1.2, T1.3) |
| All tasks have tests | ✅ | 3/3 tasks have test files (test_migrations.py, test_db.py, test_infra.py) |
| RED confirmed (tests exist) | ✅ | 3/3 test files verified on disk (RED = failing before impl per apply-progress: rc=127, ModuleNotFoundError, 7 failed) |
| GREEN confirmed (tests pass) | ✅ | 26/26 B1 tests pass on execution now (10+8+8) — cross-referenced against live runs, not trusted blindly |
| Triangulation adequate | ✅ | T1.1: 10 cases (idempotency, tables, uniqueness, indexdef, grants, enums) · T1.2: 8 cases (CRUD, jsonb, vector, audit ×3) · T1.3: 8 checks — multiple distinct expectations per behavior; no single-case task with multi-scenario spec |
| Safety Net for modified files | ✅ | conftest.py (B0 file) extended: B0 suites 12/12 still green in full run; new files "N/A (new)" correct |
| Assertion quality audit (5f) | ✅ | No tautologies, no ghost loops, no smoke-only, no type-only-alone, no mock-heavy tests (zero mocks — real DB). All assertions verify real behavior |

**TDD Compliance**: 6/6 checks passed.

### Test Layer Distribution (B1)

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 26 | 3 (+ shared conftest) | real pgvector container + psycopg/SQLAlchemy; no external mocks |
| E2E | 0 | 0 | — |
| **Total** | **26 (B1)** | **3** | suite total 38 (12 B0 + 26 B1) |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config.yaml `verify.coverage_threshold: 0`, no pytest-cov in pyproject). Not a failure (strict-TDD module: informational only).

### Quality Metrics

**Linter**: ➖ Not available (no lint config/runner in repo) · **Type Checker**: ➖ Not available. Informational only — never blocking.

### Issues Found (B1 slice)

**CRITICAL**: None

**WARNING**:
1. **Real `OPENAI_API_KEY` exported in the dev shell** (`~/.bashrc`) — combined with `tests/integration/conftest.py` `os.environ.setdefault(...)`, the real key silently overrides the `sk-test` placeholder in test env (confirmed: pytest runs picked up the real key; pydantic error revealed it in `input_value`). No B1 test calls OpenAI, so zero result impact, and the key is NOT in the repo (`git grep` clean — SH-2 intact). This elevates B0 SUGGESTION-3 to material: fix in T6.1 by forcing values (`os.environ[...] = ...`, no setdefault) and stop exporting the real key in the dev shell (direnv/scoped env file).
2. B0 WARNING-1 (stale graphify) → **RESOLVED**: graph refreshed at 636 nodes/1211 edges/39 communities; B1 file nodes present in queries.

**SUGGESTION**:
1. (Carried, still open) `tasks.md` header claims "34 tasks" vs 33 rows (line 4). Fix on next tasks.md edit.
2. (Carried, still open) WH-1 "Token mismatch" scenario log clause — no `caplog` assertion yet (B1 untouched router.py); close in a later batch or T6.1.
3. (Carried, still open) README curl proof manual — spec-marker count check in T6.1.
4. `test_infra.py::test_db_service_uses_pgvector_image` (lines 61-62) — convoluted double-condition assert for POSTGRES_PASSWORD presence; works, could be simplified to a key-presence assert. Cosmetic.
5. B1 diff size: 1,437 insertions / 5 deletions (~1.4k authored lines) vs B1 forecast ~800+test-files — within chained-PR work-unit contract (review budget guard is a delivery-strategy concern, already resolved as auto-chain; flagging for PR-time awareness only).

### Graphify Context (B1)

- Graph check: `graphify-out/graph.json` present and fresh (orchestrator-refreshed; 636 nodes / 1211 edges / 39 communities; B1 code nodes present — no refresh needed for verify).
- Query `graphify query "db schema migration ORM audit"` (BFS depth=2): 114 nodes; start nodes `Audit Log`, `db/migrations/001_init.sql`, `T1.2 ORM + session + audit service`, `SH-5 Audit Log`; subgraph includes `app/models.py`, `app/services/audit.py`, `pgvector`, `T1.1 Schema + migrations`, `T2.2` — all [EXTRACTED] from code/specs.
- Path `graphify path "T1.1" "WH-5"` → 1 hop: `T1.1 --implements[EXTRACTED]--> WH-5 Deduplicate by WAMID` ✓
- Path `graphify path "SH-5" "T1.2" --undirected` → 1 hop: `T1.2 --implements[EXTRACTED]--> SH-5 Audit Log` ✓ (directed query fails because the edge direction is T1.2→SH-5 — expected)
- Cosmetic: graphify skill 0.6.1 vs package 0.9.40 version-mismatch warning — ignore.

### Runtime Harness Spot-Check (live)
```text
docker exec lumat-pg-test psql -U lumat -d lumat -c "\dt"            -> 11 tables (10 + schema_migrations)
has_table_privilege('app','audit_log', I/U/D/S)                       -> t / f / f / t   (append-only confirmed)
SELECT version FROM schema_migrations                                 -> [001_init]
DATABASE_URL=... APP_DB_PASSWORD=app bash db/migrate.sh               -> "skip 001_init" exit 0 (idempotent)
docker compose -f infra/docker-compose.yml config (vars injected)     -> valid
```

### Verdict (B1 slice)

**PASS** — Batch 1 (T1.1 schema+migrations, T1.2 ORM+audit, T1.3 compose+env) is complete (3/3 tasks [x]), fully tested (26/26 focused, 38/38 full suite, all live against the pgvector container), and matches the design Data Model, WH-5 (schema mechanism), SH-5 (audit foundation), SH-2 (secrets), and task acceptance criteria. Strict TDD evidence validated 6/6. No CRITICAL findings; 1 WARNING (dev-shell secret hygiene, no repo impact). Deferred items (SH-5 login → T5.1, SH-2 read-only fs → T7.1, WH-5 full path → T2.2) remain deferred per tasks.md — not failures of this slice. Recommended next: archive B1 slice (orchestrator) then proceed to Batch 2 apply (T2.2 webhook ingest).

---

# Batch 2 (PR 3) — THIS VERIFY RUN

**Verified slice**: commits `54c61829..a2ee2a62` (3 commits: 27377a72 feat(webhook) ingest pipeline · c029059f docs(ops) T2.1 checklist · a2ee2a62 tasks [x])
**Runtime harness**: `lumat-pg-test` container UP (localhost:5432) — focused suite executed against real pgvector DB.

### Completeness (B2 slice)

| Metric | Value |
|--------|-------|
| Tasks total (change) | 33 (header says 34 — pre-existing discrepancy, SUGGESTION-1 carried) |
| Tasks complete | 8/33 (B0: 3 + B1: 3 + B2: 2, of which T2.1 stays `[ ]` **blocked**) |
| B2 tasks complete | T2.2 [x] · T2.1 [ ] (blocked: client credentials — documented in tasks.md + docs/ops.md) |
| B2 requirements verified | 5/5 slice-scope: WH-3, WH-4, WH-5 (full path), WH-6, WH-7 (+ WH-2 HMAC gate re-confirmed intact) |
| B2 scenarios verified | 6/6 slice-scope: WH-3 slow-downstream · WH-4 crash-after-200 · WH-5 meta-retries · WH-6 unsupported-event · WH-6 error-131051 · WH-7 burst-of-retries |
| T2.1 blocked verdict | ✅ PASS for this slice — ops dependency on client, checklist delivered, no credentials fabricated, task remains [ ] |

Full-spec totals for context: whatsapp-webhook spec = 7 reqs / 10 scenarios. **Cumulative B0+B1+B2: whatsapp-webhook 7/7 reqs, 10/10 scenarios fully verified** (B0: WH-1, WH-2; B1: WH-5 schema; B2: WH-3..7 delivery path) + SH-2/SH-5 foundations from B1 = 9 reqs / 12 scenarios cumulative.

### Build & Tests Execution (B2)

**Build-equivalent**: ✅ Passed (exit 0)
```text
.venv/bin/python -c "import app.main; from app.webhook.ingest import ingest_payload, sweep_received, RateLimiter, normalize_phone_e164; print('import OK')"
-> import OK   (hash sha256:73e65cba…4cefc54219)
```

**Focused suite** (live against pgvector container, exit 0):
```text
$ pytest tests/integration/test_webhook_ingest.py -v   -> 24 passed in 2.65s
   (normalize ×7, sig gate ×3, phone dedup ×1, 200-before-process ×2, wamid dedup ×1,
    retry storm ×1, 131051 value+message ×2, unsupported event ×1, rate limit ×1,
    sweep recovery ×2, media retry + bearer ×2, startup sweep ×1)
   Output hash: sha256:46c702e7fd0a39bd3500dca25b391d1d36e374ec98c29af2565b7e5a26b8d9d2
```

**Full suite**: ✅ **62 passed / 0 failed / 0 skipped** in 4.72s, exit 0 — matches expected 62 (12 B0 + 26 B1 + 24 B2), no regressions.
Output hash: `sha256:2d26aa4fc2e51bbf7edd77874535344ddf8d1054f4d771d74c7f4c1534de9513`.

**Static checks** (all passed):
```text
git grep -i "EAAG|token|secret" app/ infra/ db/ docs/ (filtered)  -> only comments, identifiers, env-var names; zero credential VALUES
git grep -iE "EAAG[A-Za-z0-9]{10,}"                               -> no matches (Meta tokens)
git grep -E "sk-[A-Za-z0-9]{10,}" (excl. sk-test)                 -> no matches (OpenAI keys)
git grep -iE "AKIA|ghp_|xox[bap]-|sha256=[0-9a-f]{32,}"            -> no matches
git ls-files | grep -i env                                         -> only infra/.env.example (change-me placeholders, SH-2 intact)
```

**Coverage**: ➖ Not available (config.yaml `verify.coverage_threshold: 0`; no coverage tooling — consistent with B0/B1).

### Spec Compliance Matrix (B2 slice)

| Requirement | Scenario | Covering test (runtime, all passing) | Result |
|-------------|----------|--------------------------------------|--------|
| WH-3 Immediate 200 | Slow downstream processing | `test_200_returned_before_processing_runs` (200 returned, row still `received`, sweep stub no-op) + `test_post_valid_message_persists_normalized_row` + `test_background_task_processes_message_after_200` (real BackgroundTask runs post-response) | ✅ COMPLIANT — 200 before any processing; decoupled via FastAPI BackgroundTask |
| WH-4 Persist Before Process | Crash after 200 but before processing | `test_post_valid_message_persists_normalized_row` (payload JSONB persisted, status `received` at 200) + `test_sweep_recovers_stuck_received_messages` (sweep reprocesses 2 stuck rows) + `test_startup_sweep_reprocesses_received` (lifespan sweep via TestClient) + `test_processing_failure_marks_failed` | ✅ COMPLIANT — persist→200→sweep; crash recovery via startup sweep `FOR UPDATE SKIP LOCKED` |
| WH-5 Deduplicate by WAMID | Meta retries a delivery | `test_wamid_dedup_keeps_single_row` (same payload twice → 1 row) + `test_retry_storm_single_processing_pass` (10× batch → 3 rows, all processed once) + B1 schema test `test_messages_wamid_partial_unique_inbound_only` | ✅ COMPLIANT — full delivery-path dedup now proven at runtime (schema mechanism from B1 + `ON CONFLICT (wamid) DO NOTHING` with partial index predicate match) |
| WH-6 Filter Unsupported Events | Unsupported event type | `test_unsupported_event_type_acknowledged_not_persisted` (field="statuses" → 200, 0 rows) | ✅ COMPLIANT — filtered before persist, debug log only, no 500 |
| WH-6 Filter Unsupported Events | Error 131051 message | `test_error_131051_value_skipped` (value-level) + `test_error_131051_on_message_object_skipped` (message-level errors array) | ✅ COMPLIANT — both filter levels, debug log only, no 500 |
| WH-7 Retry-Storm Tolerance | Burst of retries | `test_retry_storm_single_processing_pass` (10× re-delivery → exactly one processing pass per wamid) + `test_rate_limit_drops_overflow_after_15_per_minute` (per-phone 15/min guard) | ✅ COMPLIANT — no duplicates, no loss on dedup path, bounded queue (status column), service responsive |
| WH-2 Signature Verification (regression) | Invalid signature | `test_post_invalid_signature_rejected_and_dropped` + `test_post_missing_signature_rejected` (403, 0 rows persisted) + B0 `test_webhook_verify.py` 10/10 still green | ✅ INTACT — HMAC gate unchanged in router diff, 403 + drop before any ingest |

**Compliance summary (B2 slice)**: 6/6 scenarios compliant; HMAC gate (WH-2) re-confirmed intact. **whatsapp-webhook spec now 7/7 reqs, 10/10 scenarios cumulative.**

### Correctness (Static Evidence — B2)

| Design item | Status | Notes |
|-------------|--------|-------|
| Data flow: verify → filter → normalize → INSERT received → 200 → BackgroundTask | ✅ Implemented | `router.py` POST: HMAC gate → json.loads → `ingest_payload` → `background_tasks.add_task(sweep_received)` → 200. Matches design Data Flow line-for-line |
| `ON CONFLICT (wamid) DO NOTHING` + partial unique index predicate | ✅ Implemented | `index_elements=[Message.wamid], index_where=text("direction = 'inbound' AND wamid IS NOT NULL")` — exactly matches B1 schema predicate; verified by dedup + retry-storm tests (no inference error) |
| E.164 phone normalization (CR-2 dedup basis) | ✅ Implemented | `normalize_phone_e164`: full international, digits-only, Chilean local mobile 9XXXXXXXX→+56, stray chars; tested ×3 + via normalize_message |
| WH-6 filter before persist (value-level + message-level 131051 + non-messages field) | ✅ Implemented | `_change_is_message_event`, `_value_error_131051`, `_message_error_131051`, `iter_inbound_messages`; debug-log only; no 500 path |
| In-memory per-phone rate limit 15 msg/min (design Webhook Pipeline row) | ✅ Implemented | `RateLimiter` sliding window (deque), module-level `rate_limiter`, reset per test; `ponytail:` ceiling documented (resets on restart, single worker D1) |
| Media → media_url + download to `media/` volume (Bearer token, retry via sweep) | ✅ Implemented | `download_media` (httpx, Bearer header, MIME→ext map), failure raises `MediaDownloadError` → row stays `received` → next sweep retries; `media_dir` config added (default "media", matches compose volume) |
| Startup sweep crash recovery (`status='received' FOR UPDATE SKIP LOCKED`) | ✅ Implemented | `app/main.py` lifespan runs `sweep_received()`; `sweep_received` uses `.with_for_update(skip_locked=True)`; tested (startup sweep + recovery) |
| Processing failure → `failed` (raw payload retained) | ✅ Implemented | `except Exception` → `MessageStatus.FAILED`; tested |
| Minimal get-or-create customer+conversation (messages FK) | ✅ Implemented | Inline in ingest.py; one customer per E.164, one open conversation (closed → new conversation, CR-5); `ponytail:` replaced by formal service in T3.1 — documented deviation 1 |
| Non-JSON body with valid HMAC → 200 + drop | ✅ Implemented | `json.loads` except → 200 acknowledged, dropped (WH-6 spirit; documented deviation 5) — no test yet (noted SUGGESTION-6) |

### Coherence (Design — B2)

| Design decision | Followed? | Notes |
|-----------------|-----------|-------|
| In-process BackgroundTask + startup sweep (D1, no broker) | ✅ Yes | Exactly as designed: persist → 200 → BackgroundTask sweep; startup recovery |
| Dedup via partial unique wamid + ON CONFLICT DO NOTHING | ✅ Yes | Design Webhook Pipeline Dedup row; predicate matches B1 schema exactly |
| 131051/unsupported filtered before persist, debug log only | ✅ Yes | WH-6 row; value-level AND message-level both handled (stronger than design sketch) |
| Rate limit 15 msg/min per phone, in-memory, single worker | ✅ Yes | Design row verbatim; `ponytail:` ceiling noted |
| Media retry via sweep on download failure | ✅ Yes | `MediaDownloadError` path keeps `received`; second sweep succeeds (tested) |
| Deviation 1: get-or-create customer/conversation inline | ✅ Acceptable | Design assumes conversation exists; customers service is T3.1. FK satisfied, CR-5 respected, `ponytail:` documented |
| Deviation 2: media download sync httpx in BackgroundTask (threadpool) | ✅ Acceptable | "async" = not in request path; 200 never waits (WH-3 satisfied); respx-mocked in tests |
| Deviation 3: no `processing` status written in B2 sweep | ✅ Acceptable | received → processed directly; `processing` enum reserved for T3.2+ graph runs |
| Deviation 4: `media_dir` config added | ✅ Acceptable | Matches compose `media:/app/media` volume mount; relative default resolves in container |
| Deviation 5: non-JSON body → 200 + drop | ✅ Acceptable | WH-6 spirit (ack, no retry-storm); Meta never sends malformed bodies |
| Rollback boundary | ✅ Yes | B2 = 3 commits 27377a72..a2ee2a62; reset/revert to 54c61829 removes slice cleanly; B0/B1 webhook tests unaffected (62/62 green) |

### Strict TDD Compliance (Step 5a + expanded)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | apply-progress #1372 "TDD Cycle Evidence" table present (1 row: T2.2) |
| All tasks have tests | ✅ | 1/1 B2 code task (T2.2) has test file; T2.1 is ops (blocked, no code tests expected) |
| RED confirmed (tests exist) | ✅ | `tests/integration/test_webhook_ingest.py` exists (new in 27377a72); RED documented (ingest import → ModuleNotFoundError) |
| GREEN confirmed (tests pass) | ✅ | 24/24 B2 tests pass on execution now — cross-referenced against live run, not trusted blindly |
| Triangulation adequate | ✅ | 24 cases: normalize ×7, sig ×3, dedup ×3 (phone/wamid/storm), 131051 ×2 (value+message), unsupported ×1, rate ×1, sweep ×2, media ×2, startup ×1 — multiple distinct expectations per behavior |
| Safety Net for modified files | ✅ | router.py/config.py/main.py (B0/B1 files) modified: B0+B1 suites 38/38 still green in full run; new files "N/A (new)" correct |
| Assertion quality audit (5f) | ✅ | No tautologies, no ghost loops, no smoke-only, no type-only-alone. All assertions verify real behavior (status codes, persisted rows, dedup counts, Bearer header on real httpx request). respx mocks only stub the external Meta URL (2 tests) |

**TDD Compliance**: 7/7 checks passed.

### Test Layer Distribution (B2)

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 24 | 1 (+ shared conftest) | real pgvector container + respx (media stub only) |
| E2E | 0 | 0 | — |
| **Total** | **24 (B2)** | **1** | suite total 62 (12 B0 + 26 B1 + 24 B2) |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config.yaml `verify.coverage_threshold: 0`, no pytest-cov in pyproject). Not a failure (strict-TDD module: informational only).

### Quality Metrics

**Linter**: ➖ Not available (no lint config/runner in repo) · **Type Checker**: ➖ Not available. Informational only — never blocking.

### Issues Found (B2 slice)

**CRITICAL**: None

**WARNING**:
1. (Carried from B1) Real `OPENAI_API_KEY` still exported in the dev shell (`~/.bashrc`) + `tests/integration/conftest.py` still uses `os.environ.setdefault(...)` — the real key silently overrides `sk-test` in test env (re-confirmed: env shows OPENAI_API_KEY set). **No B2 test calls OpenAI** (media is respx-stubbed, no LLM), so zero result impact, and the key is NOT in the repo (`git grep` clean — SH-2 intact). Fix deferred to T6.1 (force values, stop exporting real key).

**SUGGESTION**:
1. (Carried) `tasks.md` header claims "34 tasks" vs 33 rows (line 4). Fix on next tasks.md edit.
2. (Carried) WH-1 "Token mismatch" scenario log clause — no `caplog` assertion yet (B2 untouched the GET path). Close in a later batch or T6.1.
3. (Carried) README curl proof manual — spec-marker count check in T6.1.
4. (Carried) `test_infra.py::test_db_service_uses_pgvector_image` double-condition assert — cosmetic simplification.
5. (NEW) Rate limiter counts duplicate deliveries against the per-phone budget BEFORE dedup: a retry storm of the SAME wamid consumes the 15 msg/min slots, so a genuinely new message from that phone in the same window can be dropped. Design-level tradeoff (15/min is generous; duplicates→dedup keeps rows correct — proven by tests), but WH-7's "no message loss" is technically softened. Consider counting only newly-inserted rows when the ingest path is next touched (T3.x), or document the tradeoff in docs/ops.md.
6. (NEW) Non-JSON body with valid HMAC → 200 + drop (deviation 5) has no covering test. Add one in T6.2 functional suite (spec-marker tests) to lock the behavior.

### Graphify Context (B2)

- Graph check: `graphify-out/graph.json` present, 636 nodes / 1211 edges / 39 communities (background refresh PID running — orchestrator owns final refresh; using current graph as-is per instructions).
- Query `graphify query "webhook ingest pipeline wamid dedup rate limit media"` (BFS depth=2): 102 nodes; start nodes `WH-5 Deduplicate by WAMID`, `app/webhook/ingest.py`, `tests/integration/test_webhook_ingest.py`, `T2.2 Webhook ingest + tests`, `WH-3 Immediate 200` — all [EXTRACTED] from code/specs.
- Path `graphify path "T2.2 Webhook ingest + tests" "WH-4 Persist Before Process"` → 1 hop: `T2.2 --implements[EXTRACTED]--> WH-4 Persist Before Process` ✓
- Path `graphify path "app/webhook/ingest.py" "WH-7 Retry-Storm Tolerance" --undirected` → 2 hops: `app/webhook/ingest.py <--references[EXTRACTED]-- T2.2 --implements[EXTRACTED]--> WH-7` ✓
- Path `graphify path "app/webhook/ingest.py" "WH-5 Deduplicate by WAMID" --undirected` → 2 hops: `app/webhook/ingest.py <--references-- T2.2 --implements--> WH-5` ✓
- Communities consulted: webhook/ingest (WH-3..7 cluster), Backend Routes and Services (ingest.py, models.py, db.py), Infrastructure and Deployment (T2.2, tests).
- Cosmetic: graphify skill 0.6.1 vs package version-mismatch warning — ignore.

### Runtime Harness Spot-Check (live)

```text
docker ps                                    -> lumat-pg-test UP (43 min), 0.0.0.0:5432->5432
pytest tests/integration/test_webhook_ingest.py -v  -> 24 passed in 2.65s (real DB, TRUNCATE-reset per test)
pytest tests/                                 -> 62 passed in 4.72s (12 B0 + 26 B1 + 24 B2), exit 0
build import (test env)                       -> import OK, exit 0
secrets grep                                  -> no EAAG / sk- / AKIA / ghp_ values anywhere in app/ infra/ db/ docs/
```

### Verdict (B2 slice)

**PASS** — Batch 2 (T2.2 webhook ingest) is complete ([x]), fully tested (24/24 focused, 62/62 full suite, live against the pgvector container), and matches specs WH-3..WH-7, the design Webhook Pipeline data flow, and task acceptance criteria. T2.1 (Meta onboarding) remains `[ ]` **blocked on client credentials** with `docs/ops.md` checklist delivered — **blocked is a PASS for this slice** (ops dependency, documented, zero credentials fabricated, SH-2 intact). Strict TDD evidence validated 7/7. No CRITICAL findings; 1 carried WARNING (dev-shell secret hygiene, no repo or test impact). **Cumulative: whatsapp-webhook spec 7/7 reqs / 10/10 scenarios verified across B0+B1+B2.** Recommended next: archive B2 slice (orchestrator), then proceed to Batch 3 apply (T3.1 customers · T3.2 chat state/graph · T3.3 KB · T3.4 intent · T3.5 nodes · T3.6 send/costs), and unblock T2.1 as soon as Meta credentials arrive.
