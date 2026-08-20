# Tasks: Memoria Persistente LumatAgent

## Review Workload Forecast

Estimated changed lines: ~1200 (S1 ~430, S2 ~150, S3 ~280, S4 ~340). 400-line budget risk: High. Chained PRs recommended: Yes (4 stacked). Delivery strategy: auto-chain. Chain strategy: stacked-to-main.

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Work Units

| Unit | Goal | Test cmd | Runtime | Rollback |
|------|------|----------|-----------------|----------|
| S1 | Schema+ORM+service | `docker compose -f infra/docker-compose.yml --profile test up -d db-test && .venv/bin/pytest tests/spec/test_memory_spec.py` | `db/migrate.sh` 009 + EXPECTED_TABLES green | drop 009 + delete migration row |
| S2 | Context+persist | `.venv/bin/pytest tests/integration/test_chat_state.py tests/integration/test_chat_capture.py` | wa message→graph: memory_context present + persisted | revert from_db/memory injection + graph persist |
| S3 | Close memo+obs | `.venv/bin/pytest tests/integration/ -k "obs or memo or close"` | close convo + recurring reply → memo+recurrencia | remove close hook |
| S4 | Panel+UI+ficha | `.venv/bin/pytest tests/functional/` + `cd web && npm test` | open ficha → ClientMemories edits; 401 | revert routes + ClientMemories.tsx |

## S1 — Schema, Models, Service

- [x] 1.1 RED `tests/spec/test_memory_spec.py` MEM-1: `memories` absent → fails
- [x] 1.2 `db/migrations/009_memory.sql`: 3 tables + HNSW + grants; update `EXPECTED_TABLES` (`tests/integration/test_migrations.py:31`)
- [x] 1.3 Add `Memory`/`MemoryRelation`/`MemoryObservation` ORM + enums in `app/models.py`
- [x] 1.4 `app/services/memory.py`: `upsert` (rejects `proyecto!='default'`, embeds via `kb.embed_texts()`), `get_by_key`, `list_for_entity`, `delete`, `set_mark`
- [x] 1.5 `hybrid_search` (vector+0.3\*FTS, min_sim 0.55, top_k 5, entity-scoped, no fallback)
- [x] 1.6 RED→green: upsert uniqueness, non-default rejected, threshold recall, role isolation, empty result

## S2 — Per-Turn Pipeline

- [x] 2.1 RED `test_chat_state.py`: `from_db()` lacks `memory_context`
- [x] 2.2 `app/chat/state.py` `from_db()` (L186-194): add `memory_context`; `load_customer_context(session, customer_id)`
- [x] 2.3 `app/chat/graph.py` `run_conversation()` (after `persist_replies` L192): `persist_memory_session(session, state)`
- [x] 2.4 `app/chat/nodes/respond.py`: append `<memory>{state.memory_context}</memory>` when non-empty
- [x] 2.5 Tests: memo injected for returning customer; empty on first contact, reply not blocked (CM-7); persisted next turn (CM-8)

## S3 — Close Event, Memo, Observations

- [x] 3.1 RED: `set_conversation_state(CLOSED)` writes no customer_memo
- [x] 3.2 `app/chat/state.py` close hook (CLOSED, L101-102): `close_conversation(session, state, acta_text=conversation.summary)`
- [x] 3.3 `memory.py`: `close_conversation` upserts customer_memo (`scope=customer`, acta verbatim, CM-5 untouched) + `record_observation`
- [x] 3.4 Patterns: recurrencia (30d/`OBS_RECUR_COUNT` 2), sin_respuesta (24h), riesgo (`case.emergency`/EM-1 flag), oportunidad (case w/o ticket)
- [x] 3.5 Sanity (open question): confirm 30d/2 + 24h values with product pre-merge — APROBADO por Stefan 2026-08-20
- [x] 3.6 Tests: close memo verbatim (MEM-4/CM-9/CM-5); recurrence only at 2 (MEM-5); patterns fire

## S4 — Panel API + UI + Ficha

- [x] 4.1 RED `tests/functional/`: `GET /panel/api/clients/{id}/memories` → 401 anonymous
- [x] 4.2 `to_memory_dict` in `app/panel/api/serializers.py`
- [x] 4.3 `routes/clients.py`: `GET/POST /clients/{id}/memories` scoped (404 unknown, `require_user_json`, 400 empty, audited POST)
- [x] 4.4 Delete/mark via `require_user_json` on own ficha (operador full per matrix; revisit if admin-only)
- [x] 4.5 `web/src/components/domain/ClientMemories.tsx` + `stories/pages/ClientMemories.stories.tsx` + mock in `_shared/mockData`
- [x] 4.6 Surface memo on ficha, distinct from `customer_notes` (CR-7: coexist; empty memo no error)
- [x] 4.7 Tests: list/edit/delete/mark scoped (MEM-6); unauthorized 401/403 (MEM-6); `cd web && npm test`

## Deferred (YAGNI)
`suggest_relations()` — no consumer until relations worker (Ponytail). `memory_relations` schema-only.
