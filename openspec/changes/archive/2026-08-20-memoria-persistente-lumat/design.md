# Design: Memoria Persistente LumatAgent

## Technical Approach

Persistent memory over the existing PG+pgvector stack, reusing the KB local-embedding pattern (`paraphrase-multilingual-MiniLM-L12-v2`, 384d, $0 via `kb.embed_texts()`). `app/services/memory.py` (KB-style: explicit session, caller commits) owns CRUD + hybrid search + close observations. Per-turn context injects into `ConversationState.from_db()` (D2 no-checkpointer already rebuilds per message); persist hooks `run_conversation()` after invoke; close trigger in `set_conversation_state(CLOSED)` writes the memo (reusing `conversation.summary` CM-5 acta verbatim) + observations. Panel via existing thin-wrapper API + primitives pattern.

## Architecture Decisions

| Decision | Choice | Why |
|---|---|---|
| Embeddings | reuse `kb.embed_texts()` | same local 384d model, $0, one embedder (D2) |
| Uniqueness | `UNIQUE(proyecto,scope,entity_id,topic_key)` | upsert without collisions (D6) |
| Search | pgvector cosine + FTS pg_trgm fused | recall is fuzzy both ways, scoped to entity |
| Memo storage | `scope='customer'` row `topic_key='customer_memo'` | lives with notes/summaries (D3), no new column |
| Close handler | hook in `set_conversation_state` | close is a state transition, not a graph branch |
| Relations/juice/decay | schema + `suggest_relations()` only | deferred worker (see Ponytail) |
| Compression | deferred post-close batch | not business-mandated, hot-path safe |

## Concrete Thresholds (fines de detalle fino)

| Constant | Value | Use |
|---|---|---|
| `MEM_MIN_SIM` | **0.55** | fused score gate for hybrid_search |
| `REL_MIN_SIM` | **0.85** | cosine pair gate for `suggest_relations` |
| FTS boost | **0.3** | `score = vector + 0.3*fts` (vector dominates) |
| `OBS_RECUR_WINDOW` / `OBS_RECUR_COUNT` | **30d** / **2** closes per topic_key | create `recurrencia` only then |
| `OBS_NO_REPLY_HOURS` | **24h** | inbound w/o bot reply → `sin_respuesta` |
| Riesgo | `state.emergency or emergency_hit` non-null | reuse EM-1 gate |
| Oportunidad | intent in {postventa, valores} or case w/o ticket | → `oportunidad` |

## Role → Scope Matrix (MEM-3)

| Role | proyecto | scope | entity_id | mutations |
|---|---|---|---|---|
| `admin` | `default` (writable) | `customer` (plus all scopes read, deferred) | any | full |
| `operador` | `default` | `customer` only | ficha's customer_id | full on that ficha |

Cross-project read for admin deferred (D4). Writers reject `proyecto != 'default'` (MEM-2). Panel list scoped to selected client (MEM-6).

## Schema (009_memory.sql)

```sql
CREATE TYPE memory_type AS ENUM ('decision','discovery','pattern','preference','customer_memo','summary','session','prompt');
CREATE TYPE memory_status AS ENUM ('active','needs_review','archived');
CREATE TYPE observation_type AS ENUM ('recurrencia','sin_respuesta','riesgo','oportunidad');
CREATE TABLE memories (
  id BIGSERIAL PRIMARY KEY,
  proyecto VARCHAR(100) NOT NULL DEFAULT 'default',
  scope VARCHAR(100) NOT NULL, entity_id VARCHAR(100) NOT NULL,
  tipo memory_type NOT NULL DEFAULT 'decision',
  titulo VARCHAR(255) NOT NULL, contenido TEXT NOT NULL,
  embedding vector(384) NOT NULL,
  topic_key VARCHAR(255) NOT NULL DEFAULT 'general',
  pin BOOLEAN NOT NULL DEFAULT FALSE,
  review_after TIMESTAMPTZ, status memory_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proyecto, scope, entity_id, topic_key));
CREATE INDEX idx_memories_embedding_hnsw ON memories USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);
CREATE INDEX idx_memories_entity ON memories (scope, entity_id);
CREATE TABLE memory_relations (
  id BIGSERIAL PRIMARY KEY,
  id_a BIGINT NOT NULL REFERENCES memories(id),
  id_b BIGINT NOT NULL REFERENCES memories(id),
  relation VARCHAR(50) NOT NULL,        -- supersedes|conflicts|related|compatible|scoped|not_conflict
  confidence REAL NOT NULL DEFAULT 1.0, reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK (id_a <> id_b));
CREATE TABLE memory_observations (
  id BIGSERIAL PRIMARY KEY, memory_id BIGINT REFERENCES memories(id),
  scope VARCHAR(100) NOT NULL, entity_id VARCHAR(100) NOT NULL,
  tipo observation_type NOT NULL, detalle JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX idx_memory_observations_entity ON memory_observations (scope, entity_id);
GRANT SELECT,INSERT,UPDATE,DELETE ON memories,memory_relations,memory_observations TO app;
GRANT USAGE,SELECT ON SEQUENCE memories_id_seq,memory_relations_id_seq,memory_observations_id_seq TO app;
```
`EXPECTED_TABLES` (+3 rows). Rollback: drop 009 + delete `schema_migrations` row.

## Service `app/services/memory.py`

`upsert(session,*,proyecto,scope,entity_id,topic_key,tipo,titulo,contenido,pin=False)` — embeds via `kb.embed_texts`, rejects `proyecto!='default'`.
`get_by_key(...)` · `list_for_entity(session,*,scope,entity_id,proyecto='default')` · `delete(session,memory_id)` · `set_mark(session,memory_id,*,pin,status)`.
`hybrid_search(session,query,*,scope,entity_id,proyecto='default',min_sim=MEM_MIN_SIM,top_k=5)` — vector + 0.3*fts, filter fused≥min_sim, ordered desc, cap 5.
`load_customer_context(session,customer_id)->str` · `persist_memory_session(session,state)` · `close_conversation(session,*,state,acta_text)` · `suggest_relations(session,memory_id,min_sim=REL_MIN_SIM)`.

## Graph Integration (exact points)

| Where | Change |
|---|---|
| `state.py` `from_db()` (after window/turn, L186-194) | add `memory_context: str=""`; `load_customer_context` on `conversation.customer_id` |
| `graph.py` `run_conversation()` (after `persist_replies`, L192) | `persist_memory_session(session,state)` |
| `nodes/respond.py` `respond()` | append `<memory>{state.memory_context}</memory>` to user prompt (when non-empty), beside `<kb>` |
| `state.py` `set_conversation_state()` (CLOSED branch, L101-102) | after `closed_at`: `close_conversation(session,state,acta_text=conversation.summary)` |

## Panel API + UI

`GET /panel/api/clients/{id}/memories` → `{"memories":[to_memory_dict(m)]}` (scope=customer, 404 unknown client; `require_user_json`).
`POST /panel/api/clients/{id}/memories` body `{tipo,titulo,contenido}` → upsert scope=customer, proyecto=default; audited; 400 empty content.

```json
{"id":1,"scope":"customer","entity_id":"42","tipo":"customer_memo","titulo":"customer_memo",
 "contenido":"...","topic_key":"customer_memo","pin":false,"status":"active","created_at":"…","updated_at":"…"}
```

UI: `web/src/components/domain/ClientMemories.tsx` (Cards + DataTable + Textarea/Button, reusing primitives/PageHeader per `ClientFicha.stories.tsx`), + `web/src/stories/pages/ClientMemories.stories.tsx` + mock in `_shared/mockData`.

## File Changes

| File | Action | Description |
|---|---|---|
| `db/migrations/009_memory.sql` | Create | 3 tables + enums + HNSW + grants |
| `app/models.py` | Modify | 3 enums + `Memory`/`MemoryRelation`/`MemoryObservation` ORM |
| `app/services/memory.py` | Create | CRUD + hybrid search + context + close |
| `app/chat/state.py` | Modify | `memory_context`, from_db, close hook |
| `app/chat/graph.py` | Modify | persist after invoke |
| `app/chat/nodes/respond.py` | Modify | `<memory>` injection |
| `app/panel/api/routes/clients.py` + `serializers.py` | Modify | memories endpoints + `to_memory_dict` |
| `web/src/components/domain/ClientMemories.tsx` + story | Create | ficha panel |
| `tests/**` | Modify/Create | spec/integration/functional |
| `tests/spec/test_memory_spec.py` | Create | MEM-1..MEM-6 |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Spec | MEM-1..MEM-6 | `tests/spec/`, migrate + ORM assertions |
| Integration | upsert/uniqueness, hybrid threshold recall, role isolation, close memo+obs | fake embedder via `kb.get_embedder` seam, pgvector test DB |
| Functional | panel list/edit/delete/mark, unauthorized 401/403 | `tests/functional/` + web |
| RED | threshold, empty-result no-fallback, recurrence count | strict TDD first |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

S1 schema+models+service → S2 pipeline → S3 close+observations → S4 panel. Additive only; drop 009 = rollback. Observations gated to single `default` project. No flag needed.

## Open Questions

- [ ] Operador mutations: full on own ficha vs admin-only for delete/mark (`require_admin_json`).
- [ ] Compression/30d/N=3 values: product sanity check before S3.

## Ponytail: explicit deferrals (YAGNI)

Batch compression worker, decay sweep, auto conflict-judgment → deferred (schema only). Cross-project search and memory ToolNode → out of scope. `memory_relations` trims to `suggest_relations()` until a second consumer.
