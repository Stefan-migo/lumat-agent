# Design: Agent-Owned Projects Namespace

## Technical Approach

Use a small `projects` registry alongside `memories`; SDB remains a projection in `Memory`, isolated by `proyecto`. Add an agent-only service facade, pass the selected slug through the existing assistant state, and expose only authenticated read APIs/UI. The seven LangGraph phases and recovery remain unchanged.

## Architecture Decisions

| Decision | Choice | Alternative rejected | Rationale |
|---|---|---|---|
| Registry | `Project` table with `slug`, display `name`, one-line `purpose`, `status`, `purpose_embedding vector(384)`, timestamps | Memory-row or second artifact table | Lifecycle/uniqueness are schema-enforced while existing SDB embedding/storage contracts stay intact. |
| Service boundary | New `app/services/projects.py`; extend Tukulpan only for authorized project-aware memory calls | Put registry lifecycle in `tukulpan.py` | Tukulpan remains the canonical artifact facade; registry transactions, dedup, aliases, and active-run valves deserve one domain boundary. |
| Identity | Stable slug; rename changes presentation/name and records alias, never rewrites namespace | Mutate slug and bulk-rewrite memories | Existing `Memory.proyecto` keys and `UNIQUE(proyecto,scope,entity_id,topic_key)` remain stable and rollback-safe. |
| Authorization | Only trusted assistant execution context may mutate/select non-default projects; panel is read-only; reject caller-supplied arbitrary injection | User CRUD or unrestricted `proyecto` argument | The planner/tool allow-list plus exact approval is the existing trust boundary. |

## Data Flow

```text
assistant request → project service (exact slug / bounded embedding candidates)
  → state.sdb_scope.project → unchanged 7 phases → agent_chat.persist_sdb_state
  → Tukulpan → memories(proyecto, panel, thread:{id}, sdb:{run_id}:{kind})
panel GET → projects service → Project + filtered Memory(topic_key LIKE 'sdb:%') → serializer/UI
```

`state.py` gains a validated `proyecto`/project reference; `agent_chat.py`, `graph.py`, and `nodes.py` carry it into SDB persistence and recovery, without adding phases. Run artifacts preserve `sdb:{run_id}:spec|state:{sequence}|result:{task_id}`; optional project artifacts use `sdb:project:{kind}` and a project entity. No WhatsApp scope is queried.

## Schema, Transactions, and Contracts

Create `db/migrations/024_projects.sql` (next migration): `projects(id BIGSERIAL, slug VARCHAR(100) UNIQUE, name VARCHAR(200), purpose VARCHAR(500), status VARCHAR/enum active|archived, purpose_embedding vector(384) NOT NULL, created_at, updated_at)`; add `project_aliases(project_id, alias UNIQUE, created_at)` and `project_audit` (actor/action/before/after). Normalize slug/name for exact uniqueness; aliases cannot collide with live slugs. Add `Project` and alias/audit mappings in `app/models.py`, preserving `Memory.proyecto` and its existing unique constraint. Purpose embedding calls `kb.embed_texts()` (same `EMBED_DIMS=384` and local model); `hybrid_search` receives the authorized project and never crosses it. Semantic find returns bounded candidates, never auto-creates on ambiguity.

Rename locks the project, rejects any `InternalChatThread.active_run_id` or recoverable SDB state for the namespace, updates name/alias/audit atomically. Merge locks both rows in deterministic id order, rejects active runs on either, moves each source memory to target only after conflict validation (same composite key must be byte-equivalent or abort), records source alias/audit, archives source, and commits once; therefore no orphan or duplicate. Default is seeded and cannot be merged away.

## Interfaces and Files

`projects.py`: typed `list/find/create/rename/archive/merge`; only handlers receive an `agent_context` capability. `registry.py` adds Pydantic typed `project.list`, `project.find`, `project.create`, `project.rename`, `project.archive`, and `project.merge`; `agent/registry.yaml` allow-lists them, with mutators non-read-only. `approval.py` includes canonical project operation payload in the existing SHA-256 digest and 15-minute TTL. Ambiguous semantic find and all mutators pause in APPROVE; consumed approval is required before execution.

Add `/panel/api/projects` and `/panel/api/projects/{slug}` in `app/panel/api/routes/projects.py`, registered in `app/panel/api/__init__.py`, guarded by `require_operator_json` (or the established admin policy chosen in tasks), returning serializers for registry fields plus SDB-only typed artifact summaries grouped by `entity_id`; no POST/PATCH/DELETE. Add `to_project_dict` serializers. Web changes: `api.ts`, `types.ts`, `panelRoutes.ts`, `PanelShell.tsx`, `AppShell.tsx`, and new `ProjectsPage.tsx`; add `/panel/app/projects`, list→detail navigation, and read-only `ai-agent-grammar__thread-area` plus inspector presentation patterned after `ConversationThread`.

## Testing Strategy

Spec/integration tests cover migration, 384d vectors, uniqueness, scope isolation, exact-vs-semantic dedup ambiguity, approval digest/expiry, agent-only authorization, propagation/recovery, rename/merge active-run rejection and atomic conflict valves, and SDB-only API output. Functional web tests cover route/list/detail/read-only controls and WhatsApp exclusion; unit tests cover serializers and route parsing.

## Threat Matrix

| Boundary | Applicability | Response / RED test |
|---|---|---|
| Documentation-like paths | N/A — no executable-file classification | None |
| Git repository selection | N/A — no VCS automation | None |
| Commit state | N/A — no commit automation | None |
| Push state | N/A — no push automation | None |
| PR commands | N/A — no PR automation | None |

## Migration / Rollout

Run migration, seed `default`, deploy service/tools disabled for non-default, then enable agent selection. Rollback disables selection and hides the route; preserve default and archived SDB rows before reverting registry code/schema.

## Open Questions

- [ ] Tasks must settle the exact panel role (`operator` versus `admin`) and semantic similarity threshold.
- [ ] Validate “Proyecto” with a real user before release.
