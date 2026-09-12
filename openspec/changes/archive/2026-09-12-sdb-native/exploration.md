## Exploration: SDB native

### Current State

The panel assistant is a compiled LangGraph in `app/chat/assistant/graph.py`:

```text
START -> assemble_context -> panel_cost_gate
  -> evidence (blocked) -> END
  -> plan_llm -> guardrails
       -> approval_pending -> END
       -> execute_tool/respond_stream -> evidence -> END
```

`AssistantState` is a `TypedDict` carrying the request/run identity, plan,
approval, tool result, response, evidence, context metadata, guardrails, cost
mode, and compaction state. `plan()` contains an older keyword-based planner,
but production always uses `plan_llm()` and validates `PlannerOutput` (`tool`,
`respond`, or `complex`). The current `complex` value only emits deferred
extension metadata; it does not route to an SDB graph.

Context is assembled from bounded history, attachments, and Tukulpan panel
memories. Pinned memories are loaded first, then panel memories, with a 4,000
token budget. The loader deliberately uses `list_for_entity`; it does not call
`hybrid_search`. Evidence is produced at the terminal node and is attached to
the persisted event stream, including context projection metadata and
compaction degradation.

Tukulpan already provides typed, upserted memories keyed by
`(proyecto, scope, entity_id, topic_key)`. Panel memories use
`scope='panel'`, `entity_id='thread:{id}'`; customer memories use the customer
scope. `record_milestone()` and `record_decision()` are suitable write seams,
but have no production caller. `hybrid_search()` exists and is tested, but has
no production caller and is not registered as an assistant tool. The current
panel projection is therefore exact scoped listing, not semantic retrieval.

The handoff report path supplied for the closed cortex session is not present in
this worktree, so the exploration uses the handoff text, current code, and
Engram observation #1167 as the available source of truth.

### Trigger Design Space

Both trigger classes are required:

1. **Plan classification** — extend the existing structured `PlannerOutput`
   with an SDB classification/intent (or equivalent deterministic field) and
   route only classified SDB work into the subgraph. The only current
   production classification signal is `PlannerOutput.kind == 'complex'`, but
   it is too broad and currently has no runtime route. `assistant_classify.md`
   exists in the declarative registry, but no production caller was found;
   `plan_llm()` is the production planner.
2. **Explicit admin request** — provide an authenticated panel entry point or
   command that requests SDB directly. This must bypass ambiguity in plan
   classification but still enter the same seven-phase state machine and
   approval boundary.

The trigger should be normalized before `SPEC`, persisted with the run, and
must not be inferred from arbitrary tool text. An explicit request should win
over a non-SDB planner classification; malformed or conflicting classification
should fail closed to a normal response or an explicit clarification.

### SDB Subgraph Shape

The smallest faithful insertion is a conditional branch after planning and
guardrails, before ordinary tool execution:

```text
plan_llm -> classify/trigger gate
  -> normal guardrails -> execute/respond -> evidence
  -> SDB CLARIFY -> SPEC -> PLAN -> APPROVE -> EXECUTE -> VERIFY -> DELIVER
```

`APPROVE` should reuse `app/chat/assistant/approval.py`: the existing SHA-256
exact-argument digest, 15-minute expiry, consumed status, and atomic
`approve_plan()`/`claim_execution()` flow. SDB approval payloads should be a
canonical phase/task plan rather than introducing a second token mechanism.

Each task must produce one verifiable output, and evidence must be collected
before declaring a result. `scope-not-found` must remain distinct from
`not-exist`; scope is frozen after `SPEC`; a checkpoint is written after every
task; and `VERIFY` checks outputs against the persisted SPEC.

### Persistence Mapping

The existing `memories` schema can represent the SDB artifacts without a new
artifact table:

| SDB artifact | Tukulpan mapping | Suggested key shape |
|---|---|---|
| SPEC | `tipo=MemoryType.PATTERN` | `sdb:{run_id}:spec` |
| STATE/checkpoint | `tipo=MemoryType.SESSION` | `sdb:{run_id}:state:{checkpoint}` or one stable state key |
| RESULT/evidence | `tipo=MemoryType.DISCOVERY` | `sdb:{run_id}:result:{task_id}` |

All rows should use `scope='panel'` and `entity_id='thread:{thread_id}'`, with
the run ID and phase/task IDs in a bounded JSON payload. This keeps SDB state
thread-visible while `assistant_state` remains the authoritative in-flight
execution record. `record_milestone()` and `record_decision()` can be reused
for checkpoint/decision semantics, but their signatures currently omit
`proyecto`.

The cross-cutting contract is mandatory: `proyecto` must be an explicit,
parameterized argument with default `'default'` at every SDB persistence seam.
It must not be hardcoded to an eventual SDB project namespace. That preserves
an additive future Projects SDD without changing SDB keys or service APIs.
The existing `_guard_writable_project()` currently rejects every value other
than `'default'`; SDB should preserve that safety policy while passing the
parameter through all new calls.

### Resume and Recovery

`InternalChatThread.assistant_state` (JSONB) stores stage, recoverability,
approval, execution status, ordered events, planner/guardrail data, context
metadata, cost mode, and compaction. `current_plan` stores the plan and
`active_run_id` binds the thread to the run. Messages also carry the run ID in
`assistant_metadata`.

`recover_events()` deduplicates `(run_id, sequence, type)`. `claim_execution()`
atomically changes `execution_status=pending` to `running`; `resume_thread()`
then executes the persisted plan exactly once. The thread read route invokes
resume, and the stream route replays persisted events.

SDB should extend this existing JSON state with phase, trigger, frozen scope,
SPEC reference, current task, checkpoint sequence, and verification status.
Each phase transition and checkpoint must be represented both in the durable
state/event stream and, where it is a meaningful artifact, in Tukulpan. Resume
must continue from the last checkpoint, not rerun completed tasks; claims must
remain atomic and scoped by `active_run_id`.

### OWUI Golden Rules Adaptation

Engram #1167 records the OWUI convention: `SPEC=pattern`, `STATE=session`,
`RESULT=discovery`, with `proyecto="sdb"` in OWUI. Native Lumat should retain
the semantic types and evidence-first rules, but use Lumat's panel scope and
parameterized project namespace (default `'default'`) rather than hardcoding
the OWUI project value. The future Projects SDD may supply a non-default
namespace later; that is explicitly out of this change.

### Affected Areas

- `app/chat/assistant/graph.py` — add the conditional SDB branch while keeping normal execution intact.
- `app/chat/assistant/state.py` — add typed SDB trigger/phase/checkpoint fields.
- `app/chat/assistant/nodes.py` — implement the minimal trigger, phase transitions, and evidence/checkpoint seams.
- `app/services/agent_chat.py` — persist/recover SDB state, checkpoints, events, and resume behavior; reuse approval flow.
- `app/chat/assistant/approval.py` — reuse unchanged where possible; canonicalize SDB plan payloads through the existing digest.
- `app/services/tukulpan.py` — parameterize `proyecto` through SDB writes and expose artifact/checkpoint persistence without hardcoded namespaces.
- `app/chat/assistant/tools/registry.py` — only if an explicit SDB/admin command or controlled memory operation requires registration; do not register `hybrid_search` speculatively.
- `app/panel/api/routes/chat.py` — authenticated explicit SDB trigger and existing approval/resume surface, if the API is the chosen entry point.
- `agent/registry.yaml`, `agent/prompts/assistant_plan.md`, and related prompts — declare the classification contract and SDB behavior.
- `db/migrations/009_memory.sql` — current schema is sufficient for artifacts; a migration is only needed if immutable event/checkpoint indexing cannot fit JSONB/memories.
- `tests/integration/` and `tests/spec/` — phase transitions, exact approval, recovery, scope freeze, typed artifacts, and no-scope-fallback scenarios.

### Approaches

1. **Native conditional subgraph in the existing harness** — branch from the
   production planner/trigger gate into seven phase nodes and return through
   the existing evidence/event boundary.
   - Pros: preserves `AssistantState`, `active_run_id`, SSE replay, approval,
     cost gate, audit, and recovery; smallest integration surface.
   - Cons: requires careful phase/checkpoint persistence and a clearer planner
     classification contract.
   - Effort: Medium.

2. **Separate SDB runtime invoked as a tool/service** — make SDB a new tool or
   independent run API with its own state machine.
   - Pros: isolates phase code and could later serve non-chat callers.
   - Cons: duplicates run/recovery/approval/evidence semantics, risks bypassing
     the harness cost and trust boundaries, and expands scope.
   - Effort: High.

### Recommendation

Use the native conditional subgraph. Keep `assistant_state` and the existing
event stream authoritative for resumable execution, persist SPEC/checkpoints/
RESULT artifacts through Tukulpan, and reuse the existing exact-plan approval.
Add the explicit admin trigger alongside a structured planner classification;
do not treat the unused classify prompt or broad `complex` kind as sufficient
without a concrete production signal. Keep semantic memory search out of
implicit context assembly; if SDB needs recall, call `hybrid_search` explicitly
with frozen `scope`, `entity_id`, and parameterized `proyecto`.

### Risks and Open Questions

- The supplied archived cortex-session report is absent from this worktree; its
  handoff text and Engram #1167 were used instead and should be reconciled
  before proposal if the report becomes available.
- `hybrid_search`, `record_milestone`, and `record_decision` have tests but no
  production callers. They are implementation seams, not completed SDB
  behavior. Decide in design whether to wire them directly or add a minimal
  SDB persistence adapter; do not expose broad memory search by default.
- The existing memory service rejects non-default `proyecto`; parameterizing
  the API while preserving that guard requires explicit contract tests.
- JSONB events are replayable but not an immutable append-only event table;
  large SDB runs could exceed practical row size unless checkpoints are bounded.
- `resume_thread()` currently resumes execution-stage work, not arbitrary
  phase nodes. SDB recovery must define phase idempotency and atomic claim
  semantics before implementation.
- The current approval endpoint assumes a tool-shaped plan. SDB must define a
  canonical phase/task payload that remains covered by the same digest and
  cannot be approved for a mutated SPEC.
- Evidence currently has only `tool/status/detail`; SDB verification needs
  bounded task IDs, artifact references, and evidence status without making
  claims outside the frozen scope.
- The graph is stale-but-usable: `graphify-out/GRAPH_REPORT.md` was built from
  commit `c4d13da7`, while this worktree is `267821ee`. It was used read-only;
  no rebuild was run.

### Graph Check Record

- Query: `graphify query "assistant harness graph SDB Tukulpan persistence approval evidence"`.
- Path: `graphify path "assistant/graph.py" "tukulpan.py" --undirected`.
- Consulted nodes: `assistant/graph.py`, `nodes.py`, `tukulpan.py`,
  `agent_chat.py`, `state.py`, `approval.py`, `registry.py`,
  `InternalChatThread`, `record_milestone()`, `record_decision()`,
  `hybrid_search()`, and the assistant harness test communities.
- Consulted edge: `assistant/graph.py --references--> nodes.py
  --references--> tukulpan.py` (EXTRACTED).
- Report context: community 5 (`nodes.py`), community 8 (`registry.py` /
  Tukulpan memory), community 14 (`agent_chat.py`), community 27 (panel chat
  API), community 55 (approval tests), and community 56 (assistant graph).

### Ready for Proposal

Yes. The proposal should commit to the native conditional subgraph, define the
structured classification plus explicit admin trigger, preserve the existing
approval/recovery boundaries, parameterize `proyecto` with default `'default'`,
and keep Projects/UI registry work out of scope.
