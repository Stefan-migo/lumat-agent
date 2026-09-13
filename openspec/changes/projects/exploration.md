## Exploration: Projects (`proyecto` namespace and read-only browse UI)

### Current State

The `sdb-native` change is already archived and provides the additive seam this
change was scheduled to consume. Native SDB persistence writes bounded SPEC,
STATE, and RESULT artifacts through Tukulpan using `scope="panel"`,
`entity_id="thread:{id}"`, run-specific topic keys, and an explicit
`proyecto` argument defaulting to `"default"`. `InternalChatThread.assistant_state`
and `current_plan` remain authoritative for recovery; Tukulpan is the durable
artifact projection. The existing approval boundary uses SHA-256 digests and a
15-minute TTL.

The missing capability is a project registry and project-aware orchestration:
there is no Project model/table/service, no agent project tool contract, and no
production caller that assigns a non-default project. `Memory.proyecto` exists
and is part of the uniqueness key, but `app/services/tukulpan.py` currently
rejects every write except `proyecto="default"`. `hybrid_search()` is explicitly
scoped to one project/scope/entity and is not implicitly called during context
assembly. This protects existing behavior but cannot yet support purpose-based
project discovery or project-scoped SDB writes.

The assistant tool registry is allow-listed and typed. It has read-only memory
listing but no `project.find`, project lifecycle tools, or semantic project
lookup. `agent/registry.yaml` already exposes `kb_scope`/`memoria_scope`, which
is the intended deferred seam for project context; project KB/context is not
needed in this change.

The panel uses a native History API router. `AgentChat` is the existing
`ai-agent-grammar__thread-area` surface, while `ConversationThread` demonstrates
the main/inspector browse pattern. There is no project route, page, API client,
or project navigation item. The current conversation model is unrelated to
projects; WhatsApp conversations must remain outside the project browse view.

### Affected Areas

- `app/models.py`, `db/migrations/` — add the project registry contract if the
  dedicated-table approach is selected; preserve `Memory.proyecto` as the
  namespace key and avoid changing SDB artifact storage.
- `app/services/tukulpan.py` — retain the canonical memory facade, add safe
  project-aware reads/writes through a service boundary, and preserve bounded
  embeddings/search semantics.
- `app/services/agent_chat.py`, `app/chat/assistant/state.py`,
  `app/chat/assistant/graph.py`, `app/chat/assistant/nodes.py` — propagate the
  selected project through the SDB request/state/recovery path without changing
  the seven phases.
- `app/chat/assistant/tools/registry.py`, `agent/registry.yaml`, assistant
  prompts — add typed agent-owned `project.find` and lifecycle operations;
  approval is required for mutating domain actions.
- `app/chat/assistant/approval.py` — reuse exact-plan digest/TTL and include the
  project operation payload in the existing approval contract.
- `app/panel/api/routes/` and serializers — expose read-only project list/detail
  endpoints guarded like the existing admin panel APIs; do not expose CRUD.
- `web/src/api.ts`, `web/src/types.ts`, `web/src/components/domain/{AppShell,PanelShell,panelRoutes}.tsx`,
  `web/src/components/pages/AgentChat.tsx`, and a new Projects page — add
  `/panel/app/projects`, list-to-detail navigation, and a read-only SDB browser
  using the existing thread-area/inspector grammar.
- `openspec/specs/{memory,sdb-native}/spec.md` and new project delta specs —
  clarify that `proyecto` becomes an agent-owned namespace while existing
  default behavior remains compatible.
- `tests/spec/`, `tests/integration/`, and web tests — cover dedup ambiguity,
  approval, rename/merge valves, scope isolation, read-only API/UI behavior,
  and exclusion of WhatsApp conversations.

### Approaches

1. **Dedicated project registry table with embedded purpose** — create a small
   `projects` registry containing slug/name, one-line purpose, status, and
   purpose embedding; keep project SDB artifacts in `memories` keyed by the
   project namespace.
   - Pros: explicit lifecycle/status model; clean list/detail queries; avoids
     treating registry metadata as ordinary memory; supports efficient project
     listing and deterministic slug uniqueness; preserves existing SDB rows.
   - Cons: one migration and model/service surface; purpose embedding must be
     maintained separately from memory embeddings.
   - Effort: Medium.

2. **Memory-row registry** — represent each registry entry as a typed memory
   row, with a reserved registry scope/entity/topic and purpose in `contenido`.
   - Pros: reuses the existing embedding pipeline and hybrid-search machinery;
     no new table; dedup by purpose is naturally close to semantic memory.
   - Cons: registry status/lifecycle becomes convention rather than schema;
     project discovery needs cross-entity/project queries that the current
     `hybrid_search()` contract does not provide; rename/merge and uniqueness
     rules become fragile; ordinary memory cleanup could damage the registry.
   - Effort: Medium initially, High once lifecycle and authorization are made
     reliable.

3. **Project registry plus a separate project-memory table** — model projects
   and project artifacts independently instead of reusing `memories`.
   - Pros: strongest isolation and purpose-built queries.
   - Cons: duplicates typed memory, embedding, bounds, and SDB artifact
     semantics already delivered by `sdb-native`; violates the additive seam and
     creates a second persistence runtime.
   - Effort: High.

### Recommendation

Use **Approach 1**, with the smallest dedicated registry possible and existing
`memories` retained as the SDB artifact store. Let the agent/service own
`list/find/create/rename/archive/merge`; the panel gets only read endpoints.
Anchor dedup on normalized purpose plus scope, with exact slug as the hard
floor, then bounded semantic candidates and explicit agent judgment. When the
agent cannot distinguish reuse from creation, it must create an approval
request and ask the user; never silently reuse or create. Rename and merge are
mandatory domain valves, not optional CRUD extras.

Propagate the selected namespace through the already-parameterized SDB seams,
keeping `scope="panel"`, thread or cross-thread entity identity, and the
`sdb:spec|state|result` topic-key family. Do not rework the seven-phase graph,
introduce project KB context, or place WhatsApp conversations in projects.
The UI should be a read-only `Proyectos` route: project list → project detail →
SDB artifacts, reusing the existing `ai-agent-grammar` thread-area and
inspector patterns.

### Risks

- The current Tukulpan guard rejects non-default project writes. The design
  must replace the single-agent restriction with an agent-owned authorization
  boundary without allowing user CRUD or arbitrary project injection.
- Purpose-based dedup depends on a stable embedding/search contract. Exact slug
  collision, semantic candidate selection, and agent judgment need deterministic
  bounds and tests.
- Rename and merge can invalidate memory namespace references and approval
  digests. They need transactional migration/alias rules and must never leave
  orphaned or duplicated SDB artifacts.
- Existing SDB topic keys in the archived contract are run-specific
  (`sdb:{run_id}:...`), while the input notes also mention
  `sdb:spec|sdb:state|sdb:result`. The proposal must resolve whether those are
  semantic categories or literal keys before implementation.
- The user-facing term “Proyecto” may collide with the domain meaning of a
  client job. Validate the single-word naming with a real user before shipping.
- The graph report metadata says it was built from `c4d13da7`, while this
  worktree is `71798a4c`; queries succeeded and the supplied graph was used
  read-only as required. Do not treat graph-derived freshness as proof until a
  later session-close refresh.

### Open Questions

- Is project identity a stable slug with rename aliases, or does rename mutate
  the namespace and migrate all memory rows transactionally?
- Does `merge` preserve the target project only, retain an audit alias, and
  reject source/target merges across active SDB runs?
- Should project detail show all panel memories or only typed SDB artifacts
  (`sdb:*`), and how are cross-thread entities represented?
- What exact agent/user approval UX is required when purpose candidates are
  ambiguous?
- Must `project.find` be a normal read-only tool, or does semantic ambiguity
  always force an approval-backed response before any namespace is selected?

### Graph Check Record

- Report read: `graphify-out/GRAPH_REPORT.md`; god/community hubs consulted
  included `models.py`, `registry.py`, `agent_chat.py`, `chat/graph.py`,
  `nodes.py`, `Memory`, `ConversationThread`, and `AgentChat`.
- Query: `graphify query "projects namespace proyecto SDB memory service agent chat read-only browse UI"`.
- Paths: `tukulpan.py -> graph.py` (undirected shortest path through
  `models.py`), `registry.py -> AgentChat.tsx` (undirected path through
  `customers.py`, `test_handoff.py`, `ConversationState`, and `api.ts`), and
  `Memory -> ConversationThread` (undirected path through `models.py`, state,
  `api.ts`, and `ConversationThread()`).
- Key edges consulted: `tukulpan.py --imports_from--> models.py`,
  `chat/graph.py --imports_from--> models.py`, `registry.py --imports_from-->
  customers.py`, `AgentChat.tsx --imports--> api.ts`, and
  `ConversationThread() --calls<-- acknowledgeCase`.

### Ready for Proposal

Yes, with the dedicated registry recommendation. The proposal should first
resolve namespace rename/merge semantics and the literal-vs-category topic-key
question, then define the agent authorization/approval boundary and the
read-only project API/UI contract. It must explicitly validate the “Proyecto”
name with a real user before release.
