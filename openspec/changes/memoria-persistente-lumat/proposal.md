# Proposal: Memoria Persistente LumatAgent

## Intent

Give LumatAgent a persistent, domain-aware memory layer (Engram/Tukulpan style) over PostgreSQL + pgvector. Today it only rebuilds context from DB + static summaries (CM-5) + staff notes (CR-4): no living customer_memo, no typed observations, no cross-session recall. Adds 3 tables, per-turn context + persist, close-time memo, so H2 multi-agent is born with context (D7).

## Scope

### In Scope
- Migration **009**: `memories` + `memory_relations` + `memory_observations` + index on `memories.embedding` vector(384, local); update `EXPECTED_TABLES`.
- `app/services/memory.py`: CRUD via `(proyecto, scope, entity_id, topic_key)` upsert (D6); hybrid search (pgvector cosine + FTS pg_trgm) entity-scoped; reuses `kb.embed_texts()`.
- Pipeline: inject memo+observations+summaries at `from_db` (state.py L150); persist before every `END` in `graph.py`.
- Close: trigger on `set_conversation_state(CLOSED)` writes customer_memo (`scope=customer`) + observations; reuse `summary.py` acta.
- Observations patterns: recurrencia, sin_respuesta, riesgo, oportunidad.
- Panel: `GET/POST /panel/api/clients/{id}/memories` + UI in `web/src/components/domain` (ClientFicha pattern).
- Tests per existing spec/integration/functional marks.

### Out of Scope
- ToolNode LangGraph tools (CORRECTION #3) until a second agent.
- Cross-project search / Report Agent (D4); only `proyecto='default'`.
- Auto conflict-judgment by similarity + decay worker (schema stays, pipeline deferred).
- H2 multi-agent, calendar, automations, reply-from-panel inbox.

## Capabilities

### New Capabilities
- `memory`: schema, per-turn context/persist, close-time memo, hybrid search, observation patterns, panel API + UI.

### Modified Capabilities
- `conversation-manager`: feeds memory context pre-respond; explicit close trigger feeds customer_memo (CM-5 acta unchanged).
- `customer-records`: ficha surfaces living customer_memo (`scope=customer`); `customer_notes` (CR-4) unchanged.

## Approach

Same stack as H1: FastAPI service over existing `Base`/`Session`, LangGraph StateGraph node wiring, vector modeled on KB `vector(384)` (local MiniLM, $0 embeddings). Service-first for recall; ToolNode deferred (YAGNI).

## Affected Areas

`db/migrations/009_memory.sql` (N), `app/models.py` (M), `app/services/memory.py` (N), `app/chat/graph.py` (M), `app/chat/state.py` (M), `app/chat/nodes/` (M), `app/panel/api/routes/clients.py` (M), `web/src/components/domain/` (N), `tests/**` (M).

## Risks

- Scope creep (tools/juicios/decay): High — explicit out-of-scope.
- Context growth: Med — deferred batch compression; entity-scoped memos.
- Migration breaks EXPECTED_TABLES: Med — test updated in-slice.

## Rollback Plan

Drop 009 (reverse DROP + delete `schema_migrations` row). Additive nodes/services remove cleanly; no destructive deltas on existing tables.

## Dependencies

- H1 closed (current batches merged); pgvector + local embedder installed.

## Success Criteria

- [ ] 3 tables migrated, EXPECTED_TABLES updated, tests green.
- [ ] Customer memo in per-turn context; updates on close.
- [ ] Hybrid search scoped; FTS + vector exercised.
- [ ] Panel UI shows/edits client memories; functional tests pass.

## Slices (auto-chain, stacked-to-main)

- S1: migration 009 + models + `memory.py` core + service tests
- S2: per-turn pipeline (context + persist) + chat tests
- S3: close event + customer_memo + observations
- S4: panel API + UI (ClientFicha pattern) + functional tests
