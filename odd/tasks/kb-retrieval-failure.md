# ODD: kb-retrieval-failure

## Objective

Make a failing knowledge-base retrieval **honest** on both chat paths. Today `kb.retrieve` is called
with no protection, so a database outage or an embedder that cannot initialise raises out of the
graph. The panel surfaces a generic agent-level error; the customer-facing WhatsApp chat drops the
message with **no reply at all**. In neither case does the system distinguish "the knowledge base
failed" from "the knowledge base had nothing".

The unit closes the advisory finding `R3-kb-retrieval-failure` left by the native review of PR #299
(lineage `review-b25a68eace7bf9af`, authority burned; Engram #4654).

## Problem

Measured on `main` = `9760a1e7`, not recited. (Base note: this branch was cut from `9760a1e7`. The
handoff claimed `5f7d9033`; `main` advanced twice while the session ran — `0fe3eae7` = PR #301,
`9760a1e7` = PR #300. `git diff --stat 5f7d9033..9760a1e7 -- app/chat/ app/services/kb.py` is
**empty**, so every measurement below holds on the newer base.)

**1. The unprotected call — panel.**

- `app/chat/assistant/nodes.py:596-621` (`retrieve_kb`) calls `kb.retrieve(...)` at `:598-604` with
  **no `try`/`except`**.
- `app/services/kb.py:322-370` (`retrieve`) has no internal handler. It calls `embed_texts`
  (`:341`) → `get_embedder().embed(...)` (`kb.py:139`) and `session.execute(...)` (`:353-359`).
  Therefore embedder import / model init / inference errors and DB / SQLAlchemy / pgvector errors all
  propagate. `kb.retrieve` uses **local** `fastembed` (`kb.py:121-126`, `:10-13`): there is no API key
  and no remote provider, so the realistic failures are local model and database, not network.
- `run_assistant` has no catch (`app/chat/assistant/graph.py:178-190`), so the exception leaves the
  graph.
- Consequence: `app/services/agent_chat.py:633,743-763` catches it, marks the message `failed`, and
  shows the operator the agent-level text `"El agente no pudo procesar este mensaje. Reinténtalo."`
  The turn dies and the panel never reaches its own deterministic refusal.

**2. The unprotected call — customer chat (worse).**

- `app/chat/nodes/respond.py:129-137` calls `kb.retrieve` directly, also with no `try`/`except`. It
  handles only the **successful empty** result as `kb_miss` (`:138-150`), which sets
  `escalate=True, escalate_reason="kb_miss"`.
- `run_conversation` has no catch (`app/chat/graph.py:281-290`) and the caller
  `app/webhook/ingest.py:378` has none either. The exception reaches the sweep loop's blanket
  handler at `app/webhook/ingest.py:443-447`: `logger.exception(...)` then
  `message.status = MessageStatus.FAILED`.
- `deliver_outbound(session, ...)` (`ingest.py:379`) is **never called**. `message.status =
  PROCESSED` (`:380`) is skipped.
- Consequence: the customer receives **silence**. No answer, no escalation, no handoff, no log line
  the operator sees. The CM-4 escalation that a clean miss triggers never fires, because it lives in
  the branch that returns.

**3. Malformed chunks — real, and the reviewer was imprecise.**

- `nodes.py:605` filters `isinstance(chunk, dict) and chunk.get("content", "").strip()`. The
  non-dict and missing-content cases **are** handled (the review claim was imprecise there).
- But `.get("content", "")` only applies its default when the key is **absent**. A present
  `{"content": None}` or `{"content": 5}` yields `None` / `5`, and `.strip()` raises `AttributeError`.
  Measured: both raise. `isinstance(chunk, dict)` is not sufficient.

**4. `session` is `None` by default — a trap the reviewer did not see.**

- `run_assistant(..., session=None)` (`graph.py:153`) and `retrieve_kb` reads
  `state.get("session")` (`nodes.py:599`).
- Production passes it (`app/services/agent_chat.py:665`), so it does not explode today. But before
  PR #299 the `respond` path never needed a session; any caller that omits it now raises inside
  `kb.retrieve` at `session.execute`. The customer chat avoids this by opening its own
  `session_scope()` (`respond.py:129`).

**Structural corroboration.** The knowledge graph has **no directed path**
`retrieve() -> collect_evidence()` and **no directed path** `retrieve_kb() -> session_scope()`. Both
negative results were reproduced with `graphify path` on this unit. The first confirms that retrieval
and evidence never meet structurally; the second confirms that the panel, unlike the customer chat,
never opens its own session.

## Why

The grounding contract built in PR #299 exists so the panel never answers without evidence. It has a
deterministic refusal for "the KB returned nothing" and **nothing** for "the KB could not be
consulted". Wrapping the call and reusing the refusal would make an outage indistinguishable from a
clean miss — declaring "no encontré evidencia" when the truth is "no pude buscar". That is the
declared-vs-consumed pattern this repository has been hunting. And on the customer path the same
defect is strictly worse: a real customer is left with no reply and no escalation.

## Authorized scope

Human-authorized in this session, per feature, before `rapso worktree create`:

1. **Panel failure surface: a distinct, honest message.** Not the clarification copy. `evidence`
   records the failure as `degraded`, and the turn does not pretend to be a grounded miss.
2. **Shared unit.** One unit fixes the panel (`nodes.py:598`) **and** the customer chat
   (`respond.py:130`). Same root, two different honest outcomes: the panel reports the KB as
   unavailable; the customer turn must not claim "no encontré" and must escalate to a human, because
   an unreachable KB is an escalation case, not a miss.
3. **`session=None` is repaired, not masked.** `retrieve_kb` opens its own `session_scope()` when it
   receives no session — the robust form the customer chat already uses. The alternative (letting a
   missing session fall into the new `except`) would disguise a programming error as a KB outage.

Worktree `odd/kb-retrieval-failure`, one PR, one type label.

**Rejected alternatives, with their evidence:**

| Rejected | Why |
|---|---|
| Reuse `PANEL_GROUNDING_REFUSAL` on failure | The user's decision. It states "no encontré evidencia suficiente" when retrieval never ran. Audit-distinguishable but user-facing false — the exact pattern this repo hunts. |
| A new `messages.<key>` panel setting | Adds a setting declaration (`settings.py:146-149`), the panel settings API, and the UI "Mensajes" card. The advisory did not ask for a configurable surface, and the existing panel refusal is a module constant (`nodes.py:38-41`). Scope creep. |
| Wrap the call and let the miss branch handle it | Structural: the miss branch returns the refusal and `END`; it cannot express "degraded". A distinct outcome needs its own return. |
| Fix only the panel | The user's decision was the shared unit. The customer instance is strictly worse (silent drop) and the "mirror contract" #299 declared would stay violated on the failure path. |

## Design decision (the contract)

**Precedent, found by measurement — this unit mirrors an existing decision.** PR #298
(`fix(assistant): degrade a failed read-only tool instead of ending the turn`) already answered this
question for read-only tools, in `app/chat/assistant/nodes.py:676-690`:

```
tool result status == "error" and tool is read_only
  -> logger.warning("Read-only tool %s failed: %s", ...)
  -> tool_result becomes {"unavailable": True, "degraded_reason": "Read-only tool unavailable"}
  -> evidence: make_evidence(status="degraded", detail="Read-only tool unavailable")
  -> response: "Tool {name} unavailable."
  -> status: "degraded"
```

`collect_evidence` (`nodes.py:807-826`) propagates `degraded` into the final status (`:825`). The
vocabulary is therefore already established:

| status | meaning |
|---|---|
| `completed` | the capability ran and produced a result (including "nothing found") |
| `degraded` | the capability could not be consulted |
| `error` | a write-capable tool failed |

`kb.retrieve` is a read-only retrieval capability, so its failure belongs to `degraded`.

Flow on the panel path:

```
guardrails
  -> retrieve_kb
        kb.retrieve raises        -> degraded: PANEL_KB_UNAVAILABLE, evidence degraded, status degraded, END
        chunks empty (no raise)   -> deterministic clarification (UNCHANGED, IAC-14)
        chunks present            -> respond_stream with the <kb> block (UNCHANGED)
```

Flow on the customer path:

```
respond
  -> kb.retrieve raises        -> log unresolved + escalate to a human, with a distinct reason
                                  (NOT "kb_miss") and copy that does not claim nothing was found
  -> chunks empty (no raise)   -> cannot_answer + escalate, reason "kb_miss"   (UNCHANGED)
  -> chunks present            -> answer from the retrieved block             (UNCHANGED)
```

- **`make_evidence` does not validate `status`** (`app/chat/assistant/evidence.py:6-7` — it returns a
  plain dict). The status vocabulary is convention, not type. The fix must align by discipline; the
  type checker will not catch a wrong string.
- **The clarification path is untouched.** A clean miss stays exactly as IAC-14 specifies. This unit
  only adds the failure outcome.
- **Emergency precedence is preserved.** The customer chat's deterministic emergency gate runs before
  the LLM (`app/chat/nodes/emergency*.py`); this unit does not touch it and must not move it.

## Acceptance criteria

1. A raising `kb.retrieve` on the panel path returns the KB-unavailable message, **not**
   `PANEL_GROUNDING_REFUSAL`, and does not call the responder.
2. That turn emits `evidence` with `status == "degraded"` and `tool == "kb.retrieve"`, and logs a
   warning. The failure is distinguishable from a clean miss in the audit trail.
3. A clean empty retrieval is **behaviorally unchanged** on both paths (IAC-14 and `kb_miss`).
4. Chunks whose `content` is present but not a usable string (`None`, `5`) do not raise; they are
   filtered out like a malformed chunk.
5. `retrieve_kb` with no session opens its own `session_scope()` instead of passing `None` into
   `kb.retrieve`.
6. A raising `kb.retrieve` on the customer path escalates to a human with a reason distinct from
   `kb_miss`, logs the unresolved response, and does **not** emit copy claiming nothing was found.
7. The canonical specs carry the new outcomes (delta to IAC-14 and to CM-4).

## Applicable checks

- **Strict TDD mode: ACTIVE.** Source: `openspec/config.yaml` (`testing.strict_tdd: true` at `:38`,
  `apply.tdd: true` at `:28`). Cycle is RED -> GREEN -> REFACTOR; **observed RED is required before
  implementation**. Do not fall back to Standard Mode.
- Test runner: `uv run pytest tests/` (`openspec/config.yaml:29,31`). `testpaths = ["tests"]`,
  `addopts = "-q"` (`pyproject.toml:44,46`) — read the exit code and the pass count, not a suppressed
  count line.
- Integration tests need the test DB: `bash infra/test-db.sh up` (wait `healthy`), then
  `eval "$(bash infra/test-db.sh env)"`.
- **Run the FULL suite before freezing, not the subset this unit touches.** Recorded lesson from the
  previous unit: a green subset is not evidence the branch is green (the grounded-gate unit shipped a
  subset that passed while the full suite had 3 failures).
- Graph Check (project Step 1) before editing each task: `graphify query` / `graphify path`, then
  record the nodes consulted below. Note: `graphify-out/` is gitignored (`.gitignore:24`), so this
  worktree has no graph; queries run against the main worktree root, whose code for this area is
  identical, and the check is still recorded.

## Checklist

- [x] **T1** — Pin the mirrored contract. Route: inline (2 files, read to decide). **Done — see
      "Pinned contract" below.**
- [x] **T2** — RED. Route: delegated writer. **Done — 5 tests, observed RED before any implementation
      change** (4 panel + 1 customer; `app/` untouched, verified by an empty `git diff -- app/`).
- [x] **T3** — GREEN, panel (`nodes.py`, `graph.py` routing). Route: delegated writer (same writer as
      T2). **Done.**
- [x] **T4** — GREEN, customer chat (`respond.py`). Route: delegated writer (same writer as T2/T3).
      **Done.**
- [x] **T5** — Spec deltas: IAC-14 (`openspec/specs/internal-agent-chat/spec.md`) and CM-4
      (`openspec/specs/conversation-manager/spec.md`). **Done — commit `17c859d7`.**
- [x] **T6** — Verify. **Done — see "Verification evidence" below.**
- [ ] **T7** — Record committed, branch pushed, PR open against `main` with the single type label.
      **The merge remains the human's decision.**

## Pinned contract (T1)

Read directly from the pinned base, not recited.

**Panel — `app/chat/assistant/nodes.py`**

- `PANEL_GROUNDING_REFUSAL` (`:38-41`) is a module constant, **not** a `messages.<key>` setting. The
  new failure copy is the same shape.
- The #298 degraded pattern (`:676-690`) is the precedent for a failed read-only capability:
  `logger.warning`, `{"unavailable": True, "degraded_reason": ...}`, `make_evidence(status="degraded")`,
  `status="degraded"`.
- `collect_evidence` (`:807-826`) propagates `degraded` to the final status at `:825`.
- `make_evidence` (`app/chat/assistant/evidence.py:6-7`) returns a plain dict and **does not validate
  `status`**.
- `_after_retrieve_kb` (`graph.py:89-90`) routes refusal to `END`, otherwise `respond_stream`. A
  degraded return has no `kb_chunks`, so it **must** get its own routing to `END` — falling through to
  `respond_stream` would answer ungrounded and violate IAC-14.

**Customer — `app/chat/nodes/respond.py`**

- `CANNOT_ANSWER_REPLY = MESSAGE_DEFAULTS["cannot_answer"]` (`:31`), resolved through
  `get_message(session, "cannot_answer", CANNOT_ANSWER_REPLY)` — a **client-editable setting**
  (`app/services/settings.py:47-61`, declared at `:146-149`).
- Measured copy: *"Lo siento, no puedo responder con seguridad a eso. Un asesor de Lumat revisará tu
  consulta y te contactará."* It does **not** claim the KB was searched and found empty — an earlier
  justification in this session claimed otherwise and was imprecise.
- **Decision, corrected by that measurement:** the failure still gets its **own constant**, because
  `messages.cannot_answer` is client-editable and its honesty would otherwise be coupled to a future
  edit. Consistency with the panel also argues for a dedicated string.
- `escalate_reason` is free-form metadata: `handoff.py:43-45` returns it, `cases.py:91` and
  `prompts.py:91` render it. **Nothing branches on the literal `kb_miss`**, so a new reason is safe.
- `graph.py:170` routes `"handoff" if state.escalate else END` — the escalation path already exists.
- `log_unresolved` (`:39-48`) sets `payload.unresolved = True`; `list_unresolved_questions`
  (`:51-57`) queries it for the CM-6 KB-improvement review. A **KB outage must not** call it: the
  question was not unresolved, the KB was unreachable. Log it instead.

## Graph nodes/edges consulted

Queried against the main worktree root (`graphify-out/GRAPH_REPORT.md` marked `Built from commit:
0fe3eae7`; `main` is `9760a1e7` — the two intervening commits are `docs/` + `infra/` only and do not
touch `app/chat/`, so the relevant subgraph is current).

- `graphify query "panel assistant retrieve_kb grounding evidence refusal"` — 315 nodes; the
  structural spine for this unit:
  `retrieve_kb() [app/chat/assistant/nodes.py:596]`,
  `retrieve() [app/services/kb.py:322]`,
  `session_scope() [app/db.py:27]`,
  `build_assistant_graph() [app/chat/assistant/graph.py:105]`,
  `AssistantState [app/chat/assistant/state.py:154]`,
  community `assistant/graph.py`.
- `graphify path "retrieve()" "collect_evidence()"` -> **no directed path**. Corroborates that
  retrieval and evidence never meet structurally.
- `graphify path "retrieve_kb()" "session_scope()"` -> **no directed path**. Corroborates that the
  panel never opens its own session, unlike the customer chat.

## Outcome

Both chat paths now distinguish "the knowledge base had nothing" from "the knowledge base could not be
consulted", and neither disguises the second as the first.

- **Panel** — a failing `kb.retrieve` returns `PANEL_KB_UNAVAILABLE` with `degraded` evidence and routes
  to `END`; the clarification stays reserved for a clean miss. A present-but-non-string chunk `content`
  is filtered instead of raising, and `retrieve_kb` opens its own `session_scope()` when it receives
  none, so the latent `session=None` trap is repaired rather than masked.
- **Customer** — a failing `kb.retrieve` returns `KB_UNAVAILABLE_REPLY` and escalates with reason
  `kb_unavailable`. It does not reuse the client-editable `cannot_answer` copy, and it does not write
  the CM-6 unresolved flag, which would have recorded a reachable question as unanswerable. The
  logger keeps the traceback, because this path has no evidence entry and the log is the only record.

Nothing pre-existing changed behavior: the clean miss on both paths, the conversational exemption, the
emergency gate, and the tool-turn path are untouched.

## Verification evidence

Strict TDD, RED observed before implementation, then GREEN. The full suite was run before freezing —
not just the subset this unit touches.

**RED (before any `app/` change).** `git diff --stat -- app/` was empty. Five new tests, each failing on
its assertion — none on an import, fixture, or symbol error:

| Test | RED evidence |
|---|---|
| `test_kb_retrieval_failure_reports_degraded_unavailability_without_responder` | `isinstance(RuntimeError('database unavailable'), dict)` was False — the node returned the raised exception |
| `test_kb_retrieval_filters_non_string_content_without_raising[None]` | `AttributeError: 'NoneType' object has no attribute 'strip'` |
| `test_kb_retrieval_filters_non_string_content_without_raising[5]` | `AttributeError: 'int' object has no attribute 'strip'` |
| `test_kb_retrieval_without_session_opens_its_own_scope` | `assert [None] == [<opened session>]` |
| `test_kb_retrieval_failure_escalates_without_logging_unresolved` | `isinstance(RuntimeError('database unavailable'), dict)` was False |

Focused unit file at RED: 34 collected, 30 passed, 4 failed. Full suite at RED: 1204 collected,
1199 passed, 5 failed.

**GREEN (frozen candidate).** `uv run pytest tests/ --tb=no -p no:warnings` ->
**1204 passed, 0 failed, exit 0.**

**Count reconciliation.** The handoff recorded 1194 passing for the previous unit. PR #301 added
`tests/integration/test_migrations.py` (5 tests) -> baseline 1199; this unit adds 5 -> 1204. No
pre-existing test broke at any point.

**Regression guards, unchanged and passing.**
- `test_empty_kb_retrieval_returns_deterministic_clarification_without_responder` — clean miss, panel.
- `test_cannot_answer_override_is_used_on_a_kb_miss` — clean miss, customer, with the
  `messages.cannot_answer` override still applied.

**Parent corrections applied after the writer's GREEN and before freeze.** The writer's implementation
passed every test but carried three defects of the exact kind this unit exists to remove:
1. `state["content"].strip()` sat **inside** the `try`, so a caller error (a missing `content`) would
   have been caught and reported as a knowledge-base outage. The query is now resolved before the `try`.
2. `logger.warning("Read-only tool %s failed: %s", "kb.retrieve", detail)` passed a literal through a
   placeholder; replaced with a literal message.
3. The customer path used `logger.warning`, discarding the traceback. Unlike the panel it records no
   evidence entry, so the log is the only record of the outage: now `logger.exception`, with a comment
   stating why it deliberately diverges from the panel's level.

The full suite was re-run green after these corrections.

**Declared tooling limitations.**
- `ruff` is not installed and this project has no linter, type checker, or formatter (recorded by
  `sdd-init`), so the "lint + typecheck" half of the project's check list cannot be run. Not a
  regression introduced here.
- `openspec` CLI is not installed; the spec deltas were reviewed by diff.
- The Graph Check ran against the main worktree root: `graphify-out/` is gitignored, so this worktree
  has no graph, and the code for this area is identical across the two.

## Progress

| Task | Route | Evidence |
|---|---|---|
| T1 pin the contract | inline (2 files, read to decide) | "Pinned contract (T1)" above |
| T2 RED | delegated writer | 5 failing tests; `git diff -- app/` empty |
| T3 GREEN panel | delegated writer (same session as T2) | commit `feb09698` — 3 files |
| T4 GREEN customer | delegated writer (same session as T2) | commit `d4ad75fe` — 2 files |
| T5 spec deltas | inline | commit `17c859d7` — 2 files |
| T6 verify | inline | 1204 passed / 0 failed, exit 0 |
| T7 record + PR | inline | pending |

Work-unit commits, each verified against `git show --stat` so the message cannot overstate the content:

- `a949995c` — `docs(odd): register the kb-retrieval-failure unit` (1 file)
- `feb09698` — `fix(assistant): degrade an unavailable knowledge base instead of faking a miss` (3 files)
- `d4ad75fe` — `fix(chat): escalate an unavailable knowledge base instead of dropping the reply` (2 files)
- `17c859d7` — `docs(spec): record the knowledge-base-unavailable outcome` (2 files)

## Next step

T7 — push the branch, open the PR against `main` with a single type label, and check CI. The merge
remains the human's decision.
