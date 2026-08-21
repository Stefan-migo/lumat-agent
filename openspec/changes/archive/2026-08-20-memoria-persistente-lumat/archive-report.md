# Archive Report: Memoria Persistente LumatAgent

**Change**: `memoria-persistente-lumat`
**Project**: LumatAgent
**Status**: CLOSED
**Date**: 2026-08-20
**Agent**: sdd-archive
**Artifact store**: hybrid (openspec files on disk + engram)

## Executive Summary

Closed the `memoria-persistente-lumat` change: added a persistent, domain-aware memory layer over PostgreSQL + pgvector (3 tables + HNSW embedding index, `app/services/memory.py` CRUD + hybrid search, per-turn context injection + persistence, close-time customer memo + typed observations, and panel API + `ClientMemories` UI on the ficha). Implementation is 100% (24/24 SDD tasks, S1–S4), verification PASS WITH WARNINGS (native `gentle-ai sdd-verify-validate` valid:true, 10/10 requirements, 19/19 scenarios, backend 438 passed / web 223 passed / `npm run build` + `build-storybook` exit 0). Delta specs synced to main specs: `openspec/specs/memory/` created (full spec, 6 MEM requirements), `openspec/specs/conversation-manager/spec.md` updated (+CM-7, CM-8, CM-9), `openspec/specs/customer-records/spec.md` updated (+CR-7). Change folder moved to `openspec/changes/archive/2026-08-20-memoria-persistente-lumat/` (preserved, not deleted). Three WARNING-level findings (W1/W2/W3) are documented follow-ups, not blockers. Delivery: not yet pushed — the orchestrator coordinates the stacked PR chain after this archive.

## Final-State Authority

The following facts describe the change AT CLOSE (highest-ranked sources):
- **Native review authority**: `reviewGate` is structurally absent in the archive-status context for this candidate — no RDD receipt was ever started for `memoria-persistente-lumat`. Per the Native Review Receipt Gate, archive proceeds under ordinary repository policy; the post-verify review offer (if any) is an invitation, not a gate, and declining it is not a verb.
- **Persisted tasks artifact** (`openspec/changes/archive/2026-08-20-memoria-persistente-lumat/tasks.md`): 24/24 implementation tasks marked `[x]` (S1 1.1–1.6, S2 2.1–2.5, S3 3.1–3.6 incl. 3.5 sanity APPROVED, S4 4.1–4.7). No stale unchecked implementation tasks. Task Completion Gate passes.
- **Explicit final-state facts (orchestrator launch prompt)** — outrank intermediate snapshots:
  - Code + verify commits on `feat/memoria-persistente-lumat`: `5b0e5408` (S1 schema+ORM), `b7d342b9` (S1 service), `f6dcb954` (S2 pipeline), `5f38758c` (S3 close+memo+obs), `6d21f4c2` (S4 panel API), `df5ee101` (S4 web), `30641d48` (SDD artifacts), `879bf009` (verify report). These match working-tree HEAD (`879bf009`).
  - Final tests: backend **438 passed**, web **223 passed**, `npm run build` + `build-storybook` exit 0.
  - Sanity 3.5 approved by Stefan 2026-08-20 (recurrence window 30d / count 2 + 24h no-reply, both configurable).
  - Warnings W1/W2/W3 are WARNING-level, no blockers, documented in verify-report; NO push / NO PR yet — orchestrator coordinates the PR chain post-archive.
- **`verify-report.md`** `sdd/memoria-persistente-lumat/verify-report` (#1811) and **`apply-progress`** `sdd/memoria-persistente-lumat/apply-progress` (#1787): intermediate snapshots, valid at their write time. Their "pending"/drift claims (e.g. "434" baseline) are NOT echoed as current facts; final counts (438) come from verify-report's final run and the launch prompt.

## Per-Capability Delta Sync

| Capability | Status in main specs | Action | Requirements added |
|------------|----------------------|--------|--------------------|
| `memory` | Did not exist | **Created** `openspec/specs/memory/spec.md` (byte-identical via shell `cp`→`diff -r`→`mv`, empty diff) | MEM-1 (Schema and Migration), MEM-2 (Memory Service CRUD), MEM-3 (Hybrid Search), MEM-4 (Close-Time Customer Memo), MEM-5 (Observations), MEM-6 (Panel Management) |
| `conversation-manager` | Exists | **Updated** — appended CM-7, CM-8, CM-9 requirements + boundary note to `openspec/specs/conversation-manager/spec.md` | CM-7 (Memory Context Pre-Respond), CM-8 (Turn-Time Memory Persistence), CM-9 (Close Trigger Feeds Customer Memo) |
| `customer-records` | Exists | **Updated** — appended CR-7 to `openspec/specs/customer-records/spec.md` | CR-7 (Living Customer Memo on Ficha) |

- All three deltas were **ADDED-only** (no MODIFIED/REMOVED/RENAMED). No destructive merge — no archive warning required per `openspec/config.yaml` archive rule.
- Pre-existing requirements preserved unchanged: conversation-manager CM-1..CM-6 intact; customer-records CR-1..CR-6 intact. Verified each new requirement appears exactly once in its main spec (no duplication).
- `memory` main spec copied byte-identically from the delta (mechanical copy, empty `diff -r`).

## Verification Summary (Final)

- Native validator: `gentle-ai sdd-verify-validate` → `valid: true`, verdict **pass_with_warnings**, `blockers: 0`, `critical_findings: 0`.
- Requirements: **10/10 compliant**; scenarios: **19/19 compliant** (MEM-1..6, CM-7..9, CR-7 — all covering tests passed at runtime).
- Tests (final state): backend **438 passed / 0 failed** (`pytest tests/` exit 0, hash `sha256:1741aa6d...`); web **223 passed (38 files)** (`npm test` exit 0); `npm run build` (tsc -b + vite) exit 0 (hash `sha256:28648180...`); `npm run build-storybook` exit 0 (non-blocking chunk-size warning).
- TDD: 24/24 tasks RED→GREEN covered; TDD compliance 6/6 (per verify-report).
- Coverage: not available (pytest-cov/coverage not installed) — informational, not a failure.

## Open Warnings (Follow-ups, NOT blockers)

All three are WARNING-level per verify-report; none breaks a spec scenario and none is CRITICAL. Each remains an explicit follow-up for a future change, not silently dropped:

- **W1 — Design deviation (signature)**: design `close_conversation(session, *, state, acta_text)` vs implementation `close_conversation(session, conversation, *, acta_text)`. Intentional and documented in the docstring: a panel close has no in-run `ConversationState`, so the persisted `Conversation` is required to derive observations. All callers coherent; no broken references. Action: none required; consider updating the design doc reference on the next related change.
- **W2 — Design deviation (observation sources)**: design detected Riesgo via `state.emergency or emergency_hit` and Oportunidad via `intent in {postventa, valores}`; implementation derives both from persisted data (`case.emergency` for riesgo; `case is None or case.status is None` for oportunidad). Consistent with W1 (persisted-data approach); MEM-5 does not mandate the transient-state source. Action: confirm the persisted-data proxies (`case.emergency` / `case.status`) are the intended product signal with the product owner.
- **W3 — MEM-5 "linked to a memory" clause**: `close_conversation` creates `memory_observations` rows with `memory_id=NULL` (schema allows nullable FK). Detail payload is present and the "Observation persisted" scenario passes, but observations are entity-scoped and not FK-linked to a specific memory row at write. Requirement-prose clause partially unmet by design choice. Action: if the product wants observation→memory linkage, set the FK at write in a follow-up.

Suggestions (non-blocking): S1 — promote `DataTable` + `PageHeader` from `web/src/stories/pages/_shared` to `primitives/` when the panel UI is wired to production (production `ClientMemories.tsx` currently imports them from the storybook `_shared` dir). S2 — refresh the pre-apply baseline "434" to the final **438** backend count. S3 — storybook build chunk-size warning is informational.

## Deferred (explicitly out of scope / YAGNI at archive)

Recorded so a future reader knows they were consciously deferred, not forgotten:
- **ToolNode LangGraph tools** (CORRECTION #3) — deferred until a second agent exists.
- **Cross-project search / Report Agent (D4)** — only `proyecto='default'`; admin cross-project read deferred.
- **Auto conflict-judgment by similarity + decay worker** — schema + `memory_relations` present; `suggest_relations()` has no consumer (YAGNI, Ponytail deferral).
- **Batch compression** (context growth) — deferred; entity-scoped memos keep the hot path safe.
- **S1 suggestion — promote `_shared` helpers to `primitives/`** — see S1 above; schedule with production panel wiring.

## Delivery State

- **Strategy**: auto-chain, chain strategy = **stacked-to-main** (4 slices S1→S4).
- Commits shipped on `feat/memoria-persistente-lumat` (8 total, HEAD `879bf009`):
  `5b0e5408` (S1 schema+ORM) · `b7d342b9` (S1 service) · `f6dcb954` (S2 pipeline) · `5f38758c` (S3 close+memo+obs) · `6d21f4c2` (S4 panel API) · `df5ee101` (S4 web) · `30641d48` (SDD artifacts) · `879bf009` (verify report).
- **NOT pushed, no PR opened yet** — the orchestrator coordinates the stacked PR chain after this archive. No push/PR performed by sdd-archive (per task rules).

## Risks / Notes

1. **S4 slice breadth**: S4 authored ~1204 lines (mostly tests) — exceeds the 400-line single-PR budget as a slice; flagged at apply for possible `size:exception` or sub-splitting at PR time. Within the overall ~1200-line chained design.
2. **Graph refresh**: the apply-time `graphify . --update` produced uncommitted `graphify-out/` changes (currently 2489 nodes / 5348 links committed at `e8b56fe1`). Per precedent `e8b56fe1`, the session-close graph refresh commit is owned by the orchestrator, not sdd-archive. Graph consulted and recorded below; its persistence commit is out of this archive scope.
3. **`verify-report.md`** is committed (`879bf009`) and moved with the folder; still byte-identical in the archive (checked by `diff -r`).
4. **Worktree isolation**: this worktree is `lumat-agent-memoria` (branch `feat/memoria-persistente-lumat`); the parallel agent working in `/home/stefan/repos/lumat-agent` was never touched.

## Archive Audit Trail

- Source-of-truth specs synced: `openspec/specs/memory/spec.md` (created, byte-identical), `openspec/specs/conversation-manager/spec.md` (+CM-7/8/9), `openspec/specs/customer-records/spec.md` (+CR-7).
- Change folder moved to archive: `openspec/changes/archive/2026-08-20-memoria-persistente-lumat/` (git mv rename, `diff -r` empty — byte-identical; folder preserved, not deleted).
- Mechanical Copy Contract: both the memory-spec copy and the folder move passed `diff -r` readback with empty output (byte-identity). The `archive-report.md` is additive-only and excluded from the readback (did not exist in the source snapshot).
- ENGRAM observations read for traceability:
  - `sdd/memoria-persistente-lumat/apply-progress` (#1787)
  - `sdd/memoria-persistente-lumat/verify-report` (#1811)
- ENGRAM observation written: `sdd/memoria-persistente-lumat/archive-report`.

## Graph Check (Graphify) — consulted

- Graph exists at `graphify-out/graph.json` (2489 nodes / 5348 links / 13 hyperedges, committed at `e8b56fe1`).
- **Query**: `graphify query "describe the memory persistence layer, conversation state pipeline, and customer records ficha"` (BFS depth=2, ~900-token budget) — 589 nodes reached. Key nodes surfaced: `Memory` (app/models.py, community 69), `memory.py` (app/services/memory.py, community 50), `state.py` (app/chat/state.py, community 12), `graph.py` (community 12), `models.py` (community 2), `Message`/`Conversation`/`Customer` (community 5), `test_memory_pipeline.py` (community 62), `test_memory_observations.py` (community 31), `test_api_memories.py` (community 20), `api/routes/clients.py` (community 69), `Customer Records` spec node, `CM-8 Turn-Time Memory Persistence`.
- **Path**: `Conversation Manager --references [EXTRACTED]--> Customer Records` (1 hop) — confirms the cross-capability reference used to ground CM-7..9 and CR-7.
- **God nodes** (read from `GRAPH_REPORT.md`): `make_user()` (79), `Message` (77), `Conversation` (60), `Customer` (55), `get_or_create_customer()` (55), `_post()` (46), `record_audit()` (40), `Case` (39), `User` (36), `get_or_create_conversation()` (34).

## SDD Cycle Status

Complete. Planned, implemented (24/24 tasks S1–S4), verified (10 requests / 19 scenarios, PASS WITH WARNINGS), and archived. Three WARNING-level findings (W1/W2/W3) are documented follow-ups, not blockers. Delivery (stacked PR chain) is the orchestrator's next step.

## Releases Notes

- Migration `009_memory.sql`: `memories`, `memory_relations`, `memory_observations` + HNSW `vector_cosine_ops` index; `EXPECTED_TABLES` updated.
- `app/services/memory.py`: `upsert`/`get_by_key`/`list_for_entity`/`delete`/`set_mark` + `hybrid_search` (vector + 0.3×FTS, min_sim 0.55, top_k 5, entity-scoped) + `load_customer_context`/`persist_memory_session`/`close_conversation`.
- Per-turn memory context injection + persistence (S2); close-time customer memo + 4 observation patterns (S3); panel memories API + ficha memo surface (S4).
