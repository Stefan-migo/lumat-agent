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

- [ ] **T1** — Pin the mirrored contract. Route: inline (2 files, read to decide). Read and pin:
      `PANEL_GROUNDING_REFUSAL` (`nodes.py:38-41`), the #298 degraded pattern (`:676-690`),
      `collect_evidence` (`:807-826`), and on the customer side the exact `CANNOT_ANSWER_REPLY` copy,
      the escalation/handoff message, and the `kb_miss` block (`respond.py:129-150`). Decide from that
      reading whether the customer outage needs a new string or an existing escalation string is
      already honest.
- [ ] **T2** — RED. Route: delegated writer. Minimum cases: (a) panel `kb.retrieve` raises -> not the
      clarification, evidence `degraded`; (b) `{"content": None}` and `{"content": 5}` -> no raise;
      (c) `retrieve_kb` with `session=None` -> own scope; (d) customer `kb.retrieve` raises ->
      escalation with a reason other than `kb_miss`. Observe RED before writing implementation.
- [ ] **T3** — GREEN, panel (`nodes.py`, `graph.py` routing, `state.py` if needed). Route: delegated
      writer (same writer as T2).
- [ ] **T4** — GREEN, customer chat (`respond.py`). Route: delegated writer (same writer as T2/T3).
- [ ] **T5** — Spec deltas: IAC-14 (`openspec/specs/internal-agent-chat/spec.md:41-53`, a failure
      scenario) and CM-4 (`openspec/specs/conversation-manager/spec.md:47-79`, the KB-unavailable
      escalation).
- [ ] **T6** — Verify. Full suite + the focused tests. See "Verification evidence" below.
- [ ] **T7** — Record committed, branch pushed, PR open against `main` with the single type label.
      **The merge remains the human's decision.**

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

_(filled at close)_

## Verification evidence

_(filled at close)_

## Progress

_(filled task by task, with the work-unit commit identity as evidence)_

## Next step

T1 — pin the mirrored contract by reading both call sites, then T2 RED.
