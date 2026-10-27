# Handoff — resume chatbot defects with T5c review, not another implementation

> Resume update: this is the historical session-start snapshot. See `odd/tasks/chatbot-defectos.md` L18–L23 and later entries for current delivery state. The authorized second independent verifier also failed without a verdict. Owner then explicitly authorized parent manual verification without Gentle AI review tools; focused unit/integration and corrected differential probes passed. This is NOT independent approval. T5c is being preserved in cohesive local commits; the full real-model evaluation remains required after T2b/T6 and has not run.

The owner explicitly stopped this conversation. Preserve the uncommitted work in the existing worktree.
Next: resolve T5c's missing independent review, then implement T2b and T6; run the full conversational evaluation after the code changes.

## Start here

| Item | State |
|---|---|
| Worktree | `/home/stefan/repos/lumat-agent-odd-chatbot-defectos` |
| Branch | `odd/chatbot-defectos-t5c` |
| HEAD / baseline | `3fa72711d76fa6f15afe508b6d6f8a4e5d000cd2` |
| Source of truth | `odd/tasks/chatbot-defectos.md`: read through `## Log`, then L9–L17 |
| Prior PRs | #697 merged as `82e311c6`; #698 merged as `3fa72711`; both delivery branches deleted |
| T5c delivery | Local changes only: NO commit, push, or PR for T5c |
| Other work | T2b and T6 not implemented; the feature is NOT finished |

Recover Engram context and the full `odd/chatbot-defectos/tasks` mirror, reconcile with the task file and `git diff`, and keep all local edits. Do not recreate the worktree or reimplement T5c.

## Decisions already settled

1. **T2b / S2:** route the customer's question to the relevant knowledge document. The deterministic topic map is the planned first implementation, not a claim of measured success. Do not merely lower similarity thresholds. Preserve the washing-machine negative control.
2. **T5c / S5, governing L14:** name the corrected equipment and provide the applicable published service price, or explain that a quotation is required, **before** transferring to an advisor. After transfer, keep the bot silent. The owner chose: «si las 2» for “Responder antes de transferir”. Do not infer boiler maintenance from the equipment alone when the customer requested repair.
3. **T6 / S6:** explicit refusal means skip the field. Keep email in the capture order, but do not insist or block after refusal. No new `campo_rechazado` escalation cause.
4. **L17, agreed next-work order:** independent code review of T5c → T2b → T6 → complete conversational evaluation with the actual model. Deferring that complete evaluation does NOT waive the independent review or prove real-classifier behavior.

Do not reopen these product questions. This is not a request for another planning session.

## T5c implementation already present

| File | Local change |
|---|---|
| `app/chat/nodes/handoff.py` | Prefer corrected `equipment_type`, fallback to equipment/“equipo”; match only explicit tariff service keys/labels; use the current configured tariff and timezone; quotation fallback otherwise; advisor coordination with no date/hour promise |
| `app/services/settings.py` | Optional `{{equipo}}` slot and default coverage copy; old custom copy without that slot remains valid |
| `tests/integration/test_handoff.py` | Equipment/fallback, configured boiler maintenance price, repair/ambiguous-service no-price fallback, legacy copy, HUMAN state/event |
| `tests/integration/test_webhook_ingest.py` | Public `process_message` boundary: inbound after transfer persists without graph invocation or outbound delivery |
| `tests/unit/test_reply_texts.py` | Optional slot and legacy custom text validation |
| `tests/unit/test_handoff_replies.py` | Only the two coverage-copy expectations updated; other reason contracts retained |
| `odd/tasks/chatbot-defectos.md` | Current decisions, implementation status, RED/GREEN and proof limitations, L12–L17 |

This handoff is also a new, uncommitted file. Snapshot before closure documentation: 7 modified tracked files, +397/-21. The complete slice including closure notes/handoff is larger; recompute honestly before committing. Repository policy asks for cohesive slices around 400 authored lines and <=5 files per atomic commit. Do not compress documentation/tests to game the budget, silently waive the policy, or commit the current seven-file unit without resolving its delivery split.

## Evidence — do not turn missing checks into passes

| Check | Observed result |
|---|---|
| RED integration | Six new assertions failed before implementing equipment/quotation behavior |
| RED slots | Expected `{comuna, equipo}`, observed `{comuna}` |
| `bash scripts/test.sh db tests/integration/test_handoff.py tests/integration/test_webhook_ingest.py` | Exit 0; 79 passed |
| `bash scripts/test.sh focused tests/unit/test_reply_texts.py` | Exit 0; 22 passed |
| `bash scripts/test.sh quick` | First run failed on two obsolete copy expectations. After their bounded correction, one rerun exit 0, reached 100%; no aggregate count printed |
| `bash scripts/test.sh full` | Parent job-6: exit 0, 5m50s, reached 100%; no aggregate count printed |
| `bash scripts/test.sh shape` | Exit 0, no shape surfaces touched |
| `git diff --check` | Exit 0 before final documentation-only edits |
| Independent verifier | `mvqzuyqp-5-5etq` failed with `assistant reported an error`; NO verdict, no admitted review evidence |
| Real classifier / corpus | NOT run; no real-model transcript established |

Full-suite warnings: unawaited `_publish_all` coroutine in `test_startup_sweep_reprocesses_received`; FastEmbed CLS-to-mean pooling warning in `test_project_slug_is_normalized_and_unique`. Neither was a test failure. Do not fix unrelated warnings in T5c.

Independent review must be resolved before progressing past T5c. Do not automatically retry the failed verifier or claim the writer's self-review replaces it; obtain an available independent review route, such as human review, with any required authorization. The previous session stopped with proof unavailable, not with a negative review finding.

Native ASSESS over this diff: native medium, agent escalation item 3 (shared owner-editable reply contract) → independentVerifier required. RDD on. `reviewDue: false`, `reviewDueReason: under_budget`; no native review transaction was started. Reassess any materially changed candidate; do not invent authority or force a native review merely to replace the failed verifier.

## Critical correction: the corpus is not WhatsApp

`app/webhook/ingest.py:396–402` suppresses bot execution for `HUMAN`/`CLOSED` conversations. Coverage handoff sets HUMAN. `scripts/conv_eval.py` calls the conversation brain directly and explicitly excludes the webhook/channel. Repeated bot replies after transfer in that evaluator do NOT prove production WhatsApp behavior.

The older S5 assertion “every next turn must get a bot reply” was withdrawn in L14. Preserve the production ownership guard. Do not add `_derived` state or an after-transfer bot exception to make the old evaluator expectation green. Corpus YAML is unchanged. Report any instrument mismatch transparently; changing it requires separately authorized scope.

## Environment and graph

- Test Postgres is worktree-derived, port **5907**. Recheck availability on resume; do not assume it survived.
- One DB-backed suite at a time per worktree: concurrent runs deadlock on TRUNCATE.
- Use `bash scripts/test.sh db …`, not direct `uv run pytest` (the wrapper supplies required test DB environment).
- Tests clear KB documents and may leave settings rows. Before future conversational measurement, reseed KB and reconcile test contamination. Do not indiscriminately delete provider secrets/settings.
- Actual active provider observed by the worker: **DeepSeek**. Its environment credentials were absent; the isolated test DB had no matching provider-secret row. No secrets were printed. An OPENAI_API_KEY search alone is NOT evidence of availability. Configure the actual provider through the project's supported path before final live evaluation; do not search outside authorized project paths.
- Parent ran `graphify update .` once successfully: 22,852 nodes, 40,976 edges, 1,527 communities. Warnings: 57 SQL files omitted because `tree_sitter_sql` is absent; five JSON files yielded no nodes. No dependency was installed.
- Graph report provenance is `bd8754f5`, prior to source-identical merge HEAD `3fa72711`. The T5c edits are now uncommitted; inspect real diff, query graph per task, and follow refresh policy without inventing graph freshness. Do not regenerate after every batch.
- Consulted graph nodes: `capture()`, `_reask_pending()`, `_ask_next()`, `handoff()`, `derivation_reply()`, `get_reply_texts()`, `tarifa_vigente()`. Confirmed edge: `handoff() --calls [EXTRACTED]--> derivation_reply()` (one hop). No directed capture→handoff path was found in the static graph; inspect actual routing rather than infer absence of behavior.

## Resume request to paste

> Leé `odd/handoffs/chatbot-defectos-t5c-continuacion.md` y `odd/tasks/chatbot-defectos.md` (hasta `## Log`, después L9–L17) en `/home/stefan/repos/lumat-agent-odd-chatbot-defectos`. Recuperá la memoria de `odd/chatbot-defectos/tasks` y reconciliá el diff local. T5c ya está implementado sin commit; los tests enfocados, quick y full pasaron. Primero resolvamos su revisión independiente pendiente, que falló sin emitir verdict. Después seguimos con T2b y T6; la evaluación conversacional completa con el modelo real va al final. Conservá el silencio del bot después de transferir y no rehagas la implementación ni declares probado el clasificador real.
