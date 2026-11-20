# ODD — asistente-operador

- Status: done
- Branch: `odd/asistente-operador`
- Worktree: `../lumat-agent-odd-asistente-operador`
- Engram mirror: `odd/asistente-operador/tasks`
- Created: 2026-11-20

## Objective

Give the panel assistant write tools over the DB-backed levers the WhatsApp bot reads every turn, so
an operator can diagnose and correct chatbot behaviour from the chat surface without a release:
knowledge (KB), wording/policy (settings), plus verification (`simulate`, `eval_regression`) and
reversibility (`revert`).

## Problem / Why

The assistant today reads almost everything that determines how the bot answers
(`analytics.chatbot_metrics`, `analytics.chatbot_conversations`, `conversations.transcript`,
`kb.retrieve`) and can write only 11 keys (`ASSISTANT_WRITABLE_SETTINGS`, `app/services/settings.py:1396`):
`tone.style`, seven `messages.*`, `hours.timezone`, `hours.schedule`. Fourteen behaviour levers it can
see, it cannot touch. The panel exposes them to humans only (`app/panel/api/routes/settings.py`), and
the KB is entirely out of reach.

The mechanism to write safely already exists and needs no invention: `APPROVED_WRITE_ALLOWLIST`
(`app/chat/assistant/tools/registry.py:32`), plan → `approval_pending` → `POST
/chat/threads/{id}/approval` → `validate_execution` (`app/chat/assistant/approval.py:221`). The
settings version history is also already generic over any key (`setting_versions`, `app/services/settings.py:1620`),
even though the panel route only names `persona` and `emergency` (`app/panel/api/routes/settings.py:266`).

## Scope

**In:** S1 `kb.propose_document`, S2 extended `settings.propose`, S3 `chatbot.simulate`,
S4 `chatbot.eval_regression`, S5 `settings.revert`, plus registry/role/skill wiring and closing checks.

**Out (deliberately):** panel UI changes; code-level levers (prompts under `agent/prompts/`, graph
nodes and gates, `_INTENT_LABELS`, `agent/registry.yaml` model), credentials (`notify.smtp_*`,
`smtp_password`, API keys), auto-ingestion triggered by `kb_miss`, any autonomous write without owner
approval, and any delivery action (commit/push/PR/merge/deploy beyond what ODD authorizes).

## Specs

**S1 — KB write.** The assistant can propose a new knowledge-base document from text (title, content,
visibility) and, after owner approval, ingest it so `kb.retrieve` returns its chunks on the next
inbound WhatsApp turn with no release. Ingestion uses the local embedder (`embed_texts`,
`app/services/kb.py:136`) and records cost 0. A document the assistant proposed never becomes
retrievable before approval, and a rejected/expired proposal writes nothing.

**S2 — Settings write, widened.** The assistant can propose a change to any key in a curated list of
the remaining behaviour levers: `scope_rules`, `chat.conduct`, `capture.questions`, `messages.templates`,
`reply.texts`, `persona.texts`, `emergency.keywords`, `emergency.protocol`, `coverage.communes`,
`booking.service_durations`, `booking.lead_minutes`, `tarifa.precios`, `cost.conversation_limit`,
`cost.daily_limit`. Each proposal is validated by the same shape rules the panel routes enforce, and
every write stays behind owner approval. Credentials and keys outside the list are refused with the
existing `setting key is not assistant-writable` error shape.

**S3 — Simulation.** The assistant can run the real conversation brain
(`app.chat.graph.run_conversation`) over a supplied list of customer turns and return, per turn, the
reply, the recorded intent and the events, plus a boolean saying whether any reply would have been
delivered. It sends nothing through WhatsApp and touches no outbox row; the run lives in its own
conversation so an operator's real thread is never mutated.

**S4 — Regression measurement.** The assistant can run the versioned conversation corpus
(`scripts/conv_eval_corpus.yaml`) and return the score diff against a named baseline: per-scenario
scores, which scenarios moved, and the gate failures. Deterministic gates always run; the rubric
judge always runs too (owner decision, 2026-11-20), so the result reports its LLM cost. A run that
cannot reach the judge reports that failure instead of scoring the conversation anyway.

**S5 — Revert.** The assistant can revert one settings key to a previously audited version, or to the
built-in default (version 0), reusing `setting_versions`/`setting_version_content`. A revert is a
write like any other: validated, approved, audited, and refused for keys outside the writable list.
After a revert the stored value equals the target version's value.

**S6 — Wiring and roles.** Every new tool is declared once in `TOOL_REGISTRY` with a typed
`args_model`, appears in `assistant.capabilities`, is listed in the assistant whitelist of
`agent/registry.yaml`, is bounded by `ROLE_TOOL_ALLOWLIST` (admin-only for the behaviour-changing
writes), and is documented in `agent/skills/assistant/tools.md`. A write tool that is missing any of
these fails closed: unknown tool, denied role, or no approval means no write.

## Slices

Delivery strategy (owner, 2026-11-20): five chained PRs, one per tool. Each slice stays inside one
review's budget and leaves the suite green on its own.

| Slice | Task | PR subject | Commit |
|---|---|---|---|
| 1 | T1 | `kb.propose_document` + opening the feature | `3ae71cfb3`, `72efba470` |
| 2 | T2 | widened settings allowlist and validators | `421c37572` (+ this record) |
| 3 | T3 | `chatbot.simulate` | `a20e09105` (+ this record) |
| 4 | T4 | `chatbot.eval_regression` | `<feat commit>` (+ this record) |
| 5 | T5 + T6 + T7 | `settings.revert`, registry/roles/skill doc, closing checks | `68c94caa6` + closure record |

Slices 1 and 2 are already past the ~400-line review budget when counted together (`610` authored
lines at `421c37572`), which is why they are separate PRs instead of one.

## Tasks

- T1 — S1 `kb.propose_document` draft → approval → ingest. Commit: `3ae71cfb3`
- T2 — S2 extend the writable allowlist and its validators for the fourteen keys. Commit: `421c37572`
- T3 — S3 `chatbot.simulate` over an isolated conversation. Commit: `a20e09105`
- T4 — S4 `chatbot.eval_regression` with gates + judge and a baseline diff. Commit: `<feat commit>`
- T5 — S5 `settings.revert` over the audited version history. Commit: `68c94caa6`
- T6 — S6 registry, role allowlist, `registry.yaml` whitelist and skill doc. Commit: `68c94caa6`
- T7 — Closing checks: `bash scripts/test.sh quick`, `full` at closure, panel build only if `web/` changes. Commit: this closure record

## Log

- L1 (owner, verbatim): "ok perfecto me parece bien eso. vamos a implementar entonces todas desde p1 a p5. con eso quedariamos con un asistente con capacidades para poder modifciar el comportamiento del chatbot dentro de las posibilidades configurables??"
- L2 (owner decisions, 2026-11-20): worktree authorized — "Sí: ../lumat-agent-odd-asistente-operador"; delivery — "5 slices encadenados (uno por tool)"; P4 depth — "Siempre gates + juez".
- L3 (orchestrator, evidence): approval pipeline and settings version history already exist, so S1/S2/S5 extend declarations rather than build a new boundary. `registry.py:32`, `approval.py:134/221`, `settings.py:1620`, `routes/settings.py:266`.
- L4 (orchestrator, boundary): "configurable" means DB-backed. Code-level levers stay out and are named in Scope so no task claims them.
- L5 (orchestrator, evidence 2026-11-20): the approval boundary digests the raw plan arguments (`app/chat/assistant/nodes.py:843`) while execution digests `model_dump()` (`registry.py:1383`), where a defaulted field is materialized. Any write tool whose args model has a default would therefore refuse its own approval. S1 answers it by making `visibility` required. Latent, pre-existing case for a follow-up: `ProjectFileSaveArgs.folder` (`registry.py:327`). Not in this feature's scope.
- L6 (orchestrator, ruling): a worker stopped because `graphify-out/GRAPH_REPORT.md` was built from an earlier commit than `HEAD`, reading the Graph Check as "rebuild before editing". The correct reading of `AGENTS.md` is that the per-task `graphify query`/`graphify path` calls satisfy steps 1-2 and the `graphify . --update` refresh runs once per session at close, never per commit; a feature branch is therefore always "stale" by commit distance and that is not a blocker. The parent owns the session-close refresh.
- L7 (orchestrator, evidence 2026-11-20, T2): `validate_assistant_setting` now returns the normalized value and `_update_setting` stores and echoes that value, matching the panel routes, which store each validator's return. Two unit tests pinned the old allowlist as a literal and two more listed now-writable keys as "outside"; all four were updated with the change, not around it.
- L8 (orchestrator, evidence 2026-11-20, T3): isolation could not come from a transaction. The graph nodes open their own sessions and commit (`scripts/chat_harness.py:120`), so a rollback in the caller undoes nothing. The invisibility therefore rests on never stamping `last_message_at`, which is exactly the field the panel's active list filters on (`app/panel/api/routes/conversations.py:238-241`) and which the harness stamps deliberately for the opposite reason. One reserved synthetic customer is shared across runs and the conversation is fresh each time: a per-run customer litters the customer list, a reused conversation leaks the earlier context into the next run.
- L9 (orchestrator, evidence 2026-11-20, T4): the tool compares against a report under `odd/evals/`
  (`report_paths`, `scripts/conv_eval.py:1412`). No JSON baseline is committed today — `odd/evals/` holds
  markdown reports only — so the tool refuses until one exists. Producing it is the existing CLI action
  (`scripts/conv_eval.py`), not a panel action; whether to commit a baseline JSON is left to the owner.
- L10 (orchestrator, evidence 2026-11-20, T4): the corpus engine stamps `last_message_at`, so a regression
  run is visible in the operator inbox. The service reports `appears_in_inbox` rather than hiding it, and
  patching the engine stays out of scope.
- L11 (orchestrator, evidence 2026-11-20, T7): `bash scripts/test.sh shape origin/main` reports `agent/registry.yaml` as a changed shape surface, so `full` is required by the project's own rule and was run. `web/` was not touched, so the panel build does not apply. A first `full` run was piped into `tail`, which discarded pytest's exit code, so it was re-run with the exit captured explicitly instead of inferring a pass from the progress bar.
- L12 (orchestrator, closing evidence 2026-11-20): `bash scripts/test.sh full` re-run with the exit code captured (`FULL_EXIT=0`), progress reached `[100%]`, no `FAILED` marker in the log. pytest's final count line is absent from the captured output, so the evidence recorded here is the exit code, the progress bar and the absence of failures, not an inferred count. `quick` is green, `shape origin/main` named `agent/registry.yaml` as the changed shape surface, `web/` was untouched so the panel build does not apply.
- L13 (orchestrator, open items for the owner, not defects of this feature): (1) T4 needs a committed baseline JSON under `odd/evals/` before it can compare anything in a fresh checkout; producing one is the existing `scripts/conv_eval.py` action. (2) `ProjectFileSaveArgs.folder` keeps the defaulted-field approval mismatch from L5, unrelated to this feature and worth its own fix.
