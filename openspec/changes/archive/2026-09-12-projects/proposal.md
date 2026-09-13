# Proposal: Agent-Owned Projects Namespace

## Intent

Make `proyecto` an agent-owned namespace so native SDB can organize work beyond
`default`, with a read-only project/SDB browse surface. Consume archived seams.

## Scope

### In Scope
- Small `projects` registry: slug/name, one-line purpose, status, purpose embedding.
- Agent/service `list`, `find`, `create`, `rename`, `archive`, and `merge` operations.
- SDB project propagation and read-only panel list/detail for typed `sdb:*` artifacts.

### Out of Scope
- User CRUD/injection, project KB/context (`kb_scope`), SDB phase rework, WhatsApp conversations, Cortex-session mode, or UI command center.

## Capabilities

### New Capabilities
- `projects`: Registry, namespace selection, lifecycle, and read-only browse.

### Modified Capabilities
- `memory`: Authorized non-default namespaces; `memories` remains artifact storage.
- `sdb-native`: Project propagation without phase or recovery changes.
- `assistant-tools`: Typed project tools and approval boundary.
- `panel-app`: Read-only project navigation and SDB browsing.

## Approach

Lock **Approach 1**: a dedicated registry table with purpose embedding; retain
SDB artifacts in `memories`, keyed by namespace. Reject a memory-row registry
because lifecycle/uniqueness become fragile conventions. Reject a separate
project-memory table because it duplicates typed memory/embedding semantics.

Defaults for design: `sdb:spec|state|result` are semantic categories, not literal
replacements. Preserve archived run keys as `sdb:{run_id}:{kind}`; project-level
artifacts, if needed, use `sdb:project:{kind}` and project entities. Rename keeps
a stable slug plus alias with atomic migration: no orphaned or duplicated
artifacts. Merge preserves the target, records an audit alias, and rejects
source/target merges with active SDB runs. Detail shows only typed SDB artifacts,
grouping cross-thread entities. Exact slug lookup is a normal read; semantic
ambiguity requires SHA-256/15-minute approval and SDB APPROVE before selection.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `app/models.py`, `db/migrations/` | New | Registry. |
| `app/services/tukulpan.py`, assistant graph/state/tools | Modified | Propagation. |
| `app/panel/api/routes/`, `web/src/` | New/Modified | Read-only browse. |
| `openspec/specs/`, tests | Modified | Contracts and coverage. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Ambiguous dedup/injection | Med | Exact slug, bounded candidates, approval. |
| Rename/merge corruption | Med | Atomic rules, aliases, active-run rejection. |
| “Proyecto” misnames concept | Med | Real-user validation is a release gate. |

## Rollback Plan

Disable non-default selection and hide the route; revert registry/API/UI
migrations after preserving default rows. Keep archived SDB behavior intact.

## Success Criteria

- [ ] Namespaces persist; SDB artifacts remain isolated and recoverable.
- [ ] Ambiguity never silently selects or creates a project.
- [ ] Browse is read-only, SDB-only, and excludes WhatsApp conversations.
- [ ] “Proyecto” is validated with a real user before release.

## Open Decisions Deferred to Design

Specify transaction boundaries, alias schema, thresholds, cross-thread presentation,
authorization, and exact API/UI payloads without changing these defaults.
