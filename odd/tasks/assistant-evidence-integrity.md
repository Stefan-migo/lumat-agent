# ODD — assistant-evidence-integrity
Branch: `odd/assistant-evidence-integrity` · base: `23d1d29f` (= `origin/main`).
Origin: follow-up to `odd/tasks/asistente-herramientas.md`, prompted by its L3 evidence that bootstrap memory appeared as the only tool result.

## Specs

- **S1.** A code-initiated `memory.read(scope=own, limit=3)` is context, not a dispatched tool result: add the bounded rows as labelled own-memory context stating the harness read them before this turn. It must not appear in `tool_results`, prior tool evidence, or responder tool evidence. Preserve `verification_required` behavior for actual dispatched tools and do not add `AssistantState` keys.
- **S2.** Every rendered tool result identifies its provenance with a header containing the tool name, status, and arguments, followed by its payload.
- **S3.** Budget omissions may omit payloads, but must never omit the identity/status of any executed tool: list every executed step before retained payloads, one line per step, while retaining the omission marker and `_TOOL_EVIDENCE_LIMIT`.
- **S4.** If `guardrails` records `execution_stall`, responder-visible evidence says the chain stopped and names tools already run; do not let the responder claim that “the tool never arrived”.
- **S5.** A normal turn remains one plan, one tool, one responder call; preserve the existing single-step path and a valid responder path when no tool ran.

## Tasks

- T1 — S1, S5 — move bootstrap memory into labelled context and pin verification/single-step behavior — commit: TBD.
- T2 — S2, S3 — render provenance and complete executed-tool inventory under the existing budget — commit: TBD.
- T3 — S4 — expose a stalled chain and its executed tools to the responder — commit: TBD.

## Log

- **L1** (operator request, verbatim): “primero hay cosas, al parecer la ejecucion de multiples tools esta fallando. o algo incluso mas allá dentro del harness. luego no hay certeza de que esten todos los tools realmente funcionando.”
- **L2** Production `audit_log` evidence: `project.find` completed three times while the agent told the operator three times that “the tool never arrived”. The tools executed; the model-facing evidence did not preserve their identity reliably.
- **L3** Local reproduction: a three-tool chain produced only the bootstrap `memory.read` in responder evidence, and a truncated chain made the responder say “the evidence came truncated ... I cannot state what `appointments.upcoming` returned”. The recorded `execution_stall` was not rendered to the responder.
- **L4** (gates, exit codes as printed): `bash scripts/test.sh quick` → 0; `bash scripts/test.sh shape` → `shape: agent/prompts/assistant_respond.md`, i.e. full becomes mandatory; `bash scripts/test.sh full` → 0 (two pre-existing warnings, both outside this diff: an unawaited `_publish_all` coroutine in `tests/integration/test_webhook_ingest.py` and the FastEmbed mean-pooling notice in `tests/spec/test_projects_spec.py`).
