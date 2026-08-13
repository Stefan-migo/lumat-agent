```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:6c6a34e6f8a139ed7922365678db3bb1f5f571a6308d846306cb0aee2363596c
verdict: pass
blockers: 0
critical_findings: 0
requirements: 18/18
scenarios: 25/25
test_command: pytest tests/
test_exit_code: 0
test_output_hash: sha256:6c6a34e6f8a139ed7922365678db3bb1f5f571a6308d846306cb0aee2363596c
build_command: .venv/bin/python -c "import app.main; from app.services.customers import get_or_create_customer, set_customer_state; from app.services.kb import ingest_document, retrieve; from app.services.send import send_text, deliver_outbound; from app.services.costs import record_llm_cost, conversation_spend, daily_spend; from app.chat.state import ConversationState; from app.chat.graph import build_graph, run_conversation; from app.chat.nodes.classify_intent import classify_intent, is_injection; from app.chat.nodes.respond import respond, log_unresolved; from app.chat.nodes.capture import capture; from app.chat.nodes.summary import summary; print('import OK')" (with test env set)
build_exit_code: 0
build_output_hash: sha256:73e65cba19528ade3fd463248a9ba2c44e92c41810caef6a0bba624cefc54219
```

# Verification Report — hito-1-setup-whatsapp

**Change**: hito-1-setup-whatsapp · **Project**: LumatAgent (lumat) · **Phase**: sdd-verify
**Latest verified slice**: **Batch 3 (PR 4)** — commits `c3226c49..ef8aba74` (T3.1 customers · T3.2 chat state/graph · T3.3 KB · T3.4 intent · T3.5 nodes · T3.6 send/costs; T2.1 remains blocked on client credentials)
**Mode**: **STRICT TDD** (config.yaml `apply.tdd: true`, runner `pytest tests/`)
**Artifact store**: hybrid (this file + Engram `sdd/hito-1-setup-whatsapp/verify-report`)
**Ledger token (verify run)**: `sha256:5782326ac5cd2959814531e5d584d769070b5c193f58a8ff04b48b7fed97a037` (orchestrator settles)
**Cumulative verified**: 27 requirements / 37 scenarios across B0+B1+B2+B3 slices. Slice-scoped envelope for B3 = 18/18 reqs, 25/25 scenarios.

---
## Previous Slices — B0 (PR 1) PASS, B1 (PR 2) PASS, B2 (PR 3) PASS — preserved verbatim

B0 (f8357e5f..0894f5c7): PASS, 3/3 reqs, 5/5 scenarios (WH-1..WH-3), 12/12 tests. B1 (d405dcab..45565e3f): PASS, 3/3 reqs, 3/3 scenarios (WH-5 schema, SH-5, SH-2), 38/38 tests. B2 (54c61829..a2ee2a62): PASS, 5/5 reqs, 6/6 scenarios (WH-3..WH-7 delivery path), 62/62 tests. Full B0+B1+B2 bodies preserved in this file below the B3 section and in the prior Engram revision (obs #1375). Key carried findings: 1 WARNING (real OPENAI_API_KEY in dev shell) — **mechanism now fixed in B3** (see WARNING-1); deferred items SH-5 login → T5.1, SH-2 read-only fs → T7.1, KB-3 manager view → T5.4, HH-3 persona-menu trigger → T4.4, SH-4 tool-whitelist suite → T6.3.

# Batch 3 (PR 4) — THIS VERIFY RUN

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
