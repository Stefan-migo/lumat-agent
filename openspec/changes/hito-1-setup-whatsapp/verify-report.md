```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:79e45e36542eaac05418dc9f1efe11d8843f8e115aaa1bcb40059d59e5e6b7b5
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 3/3
test_command: pytest tests/ ; pytest tests/integration/test_migrations.py -v ; pytest tests/integration/test_db.py -v ; pytest tests/integration/test_infra.py -v
test_exit_code: 0
test_output_hash: sha256:79e45e36542eaac05418dc9f1efe11d8843f8e115aaa1bcb40059d59e5e6b7b5
build_command: .venv/bin/python -c "import app.main" (with test env set)
build_exit_code: 0
build_output_hash: sha256:196c321bf8e43723e10f86032bd62cbafc1155df016ca950341fa8113e633550
```

# Verification Report — hito-1-setup-whatsapp

**Change**: hito-1-setup-whatsapp · **Project**: LumatAgent (lumat) · **Phase**: sdd-verify
**Latest verified slice**: **Batch 1 (PR 2)** — commits `d405dcab..45565e3f` (T1.1, T1.2, T1.3)
**Mode**: **STRICT TDD** (config.yaml `apply.tdd: true`, runner `pytest tests/`)
**Artifact store**: hybrid (this file + Engram `sdd/hito-1-setup-whatsapp/verify-report`)
**Ledger token (verify run)**: `sha256:a989ce4f3c0ad2811e298d6f4b525322bc19b7d0fa2c338d3c2a55f7ad9171f0` (orchestrator settles)
**Cumulative verified**: 6 requirements / 8 scenarios across B0+B1 slices (slice-scoped envelope: B1 = 3/3 reqs, 3/3 scenarios)

---

## Previous Slice — Batch 0 (PR 1) PASS — preserved verbatim

**Verified slice**: commits `f8357e5f..0894f5c7` (scaffold, app factory, webhook verify/signature) · Mode: Standard (B0)

```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:0373751e8d7c944e1a270e25972d54d080ed3d345d405a618733667f7f245d2b
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 5/5
test_command: pytest tests/ ; pytest tests/integration/test_webhook_verify.py -v
test_exit_code: 0
test_output_hash: sha256:0373751e8d7c944e1a270e25972d54d080ed3d345d405a618733667f7f245d2b
build_command: .venv/bin/python -c "import app.main"
build_exit_code: 0
build_output_hash: sha256:29ac96f0f0140d10a79b55231d14e65a2759e0c42f091f7c9d961f4ddf8716b7
```

**B0 summary**: PASS — T0.1–T0.3 complete; 12/12 tests green; WH-1..WH-3 compliant (5/5 scenarios); WH-4..7 deferred to B1/B2 per tasks.md. No CRITICAL/WARNING code findings. Issues carried: SUGGESTION-1 (WH-1 caplog assertion), SUGGESTION-2 (tasks.md "34 tasks" vs 33 rows), SUGGESTION-3 (conftest `setdefault` leak), SUGGESTION-4 (spec markers). Full B0 detailed body preserved in git history (file state at commit d405dcab).

---

# Batch 1 (PR 2) — THIS VERIFY RUN

**Verified slice**: commits `d405dcab..45565e3f` (4 commits: dc9c9078 migration · af741c8a ORM/audit · bde1d4b8 compose/env · 45565e3f tasks [x])
**Runtime harness**: `lumat-pg-test` container UP (localhost:5432, pgvector ext 0.8.6) — integration suites executed against real DB.

### Completeness (B1 slice)

| Metric | Value |
|--------|-------|
| Tasks total (change) | 33 (header says 34 — pre-existing discrepancy, SUGGESTION-1) |
| Tasks complete | 6/33 (B0: 3 + B1: 3) |
| B1 tasks complete | 3/3 — T1.1 [x], T1.2 [x], T1.3 [x] (tasks.md) |
| B1 requirements verified | 3/3 slice-scope: WH-5 (schema mechanism), SH-5 (audit foundation), SH-2 (secrets-in-repo part) |
| B1 scenarios verified | 3/3 slice-scope: WH-5 retry (schema), SH-5 settings-change (service), SH-2 secrets-not-in-repo |
| Deferred (not B1 scope) | SH-5 login → T5.1 · SH-2 read-only fs → T7.1 · WH-5 full delivery path → T2.2 |

Full-spec totals for context: whatsapp-webhook spec = 7 reqs / 10 scenarios; security-hardening spec = 5 reqs / 8 scenarios. Cumulative B0+B1 verified: 6 reqs / 8 scenarios; remaining scenarios land per tasks.md traceability (B2–B7).

### Build & Tests Execution (B1)

**Build-equivalent**: ✅ Passed (exit 0)
```text
.venv/bin/python -c "import app.main; from app.db import Base; from app.models import <10 models>"
-> import OK, 10 mapped tables   (hash sha256:196c321b…e633550)
Bare `import app.main` without env fails with pydantic ValidationError naming missing vars
-> expected T0.2 fail-fast, unchanged from B0
```

**Focused suites** (all live against pgvector container, exit 0):

```text
$ pytest tests/integration/test_migrations.py -v      -> 10 passed in 1.78s
$ pytest tests/integration/test_db.py -v              -> 8 passed in 1.61s
$ pytest tests/integration/test_infra.py -v           -> 8 passed in 0.17s
```

**Full suite**: ✅ **38 passed / 0 failed / 0 skipped** (12 B0 + 26 B1) in 2.89s, exit 0 — matches expected 38.
Output hash: `sha256:79e45e36542eaac05418dc9f1efe11d8843f8e115aaa1bcb40059d59e5e6b7b5`.

**Static checks** (all passed):
```text
git ls-files | grep -i env                          -> only infra/.env.example (SH-2)
docker compose -f infra/docker-compose.yml config    -> valid with required vars injected
   (without infra/.env the :?required interpolation fails fast — intended SH-2 fail-fast, not a defect)
git grep -iE "secret|change-me|sk-|AKIA|ghp_|xoxb-" infra/ db/ app/ (excluding .env.example)
   -> only comments and env-var references; no credential values
```

**Live DB evidence** (docker exec lumat-pg-test):
```text
\dt                          -> 11 tables (10 design + schema_migrations)
schema_migrations            -> [001_init]
app grants on audit_log      -> INSERT=t UPDATE=f DELETE=f SELECT=t   (append-only, SH-5)
db/migrate.sh re-run         -> "skip 001_init (already applied)" / "migrations up to date" (exit 0)
```

**Coverage**: ➖ Not available (config.yaml `verify.coverage_threshold: 0`; no coverage tooling — consistent with B0).

### Spec Compliance Matrix (B1 slice)

| Requirement | Scenario | Covering test (runtime) | Result |
|-------------|----------|-------------------------|--------|
| WH-5 Deduplicate by WAMID | Meta retries a delivery | `test_migrations.py > test_messages_wamid_partial_unique_inbound_only` (dup inbound wamid → UniqueViolation; outbound wamid repeat allowed) + live indexdef | ✅ COMPLIANT (schema mechanism — partial unique index inbound-only proven at runtime; full delivery-path dedup completes in T2.2 per tasks.md `WH-5 → T1.1, T2.2`) |
| SH-5 Audit Log | Settings change audited | `test_db.py > test_audit_record_writes_before_after` (actor/action/entity/before/after persisted) + `test_audit_is_append_only_via_grants` (UPDATE/DELETE denied) + `test_app_role_audit_log_insert_and_select_only` | ✅ COMPLIANT (service + grant mechanism proven; admin-change wiring to settings service completes in T4.1 per tasks.md `SH-5 → T1.2, T4.1…`) |
| SH-2 Container and Secrets Hardening | Secrets not in repo | `test_infra.py > test_env_example_has_no_real_secrets` + `test_gitignore_covers_secrets_and_runtime_data` + `git ls-files` + `git grep` | ✅ COMPLIANT (only `.env.example` tracked; `change-me` placeholders; zero real keys in repo) |
| SH-5 Audit Log | Login audited | — (auth layer does not exist until T5.1) | ⏸️ DEFERRED — T5.1 (tasks.md `SH-5 → T5.1`) |
| SH-2 Container and Secrets Hardening | Read-only agent filesystem | — (prod compose `read_only` lands in T7.1) | ⏸️ DEFERRED — T7.1 (tasks.md `SH-2 → T1.3, T6.4, T7.1`) |

**Compliance summary (B1 slice)**: 3/3 scenarios compliant for the verified scope. 2 scenarios explicitly deferred to T5.1/T7.1 per tasks.md — not failures of this slice.

### Correctness (Static Evidence — B1)

| Design item | Status | Notes |
|-------------|--------|-------|
| 10 tables per design Data Model | ✅ Implemented | `001_init.sql` + `app/models.py`: customers, users, conversations, messages, cases, conversation_events, kb_documents, kb_chunks, settings, audit_log. Tested + live `\dt` (11 incl. schema_migrations) |
| `customers.phone_e164 UNIQUE` (CR-2) | ✅ Implemented | SQL `UNIQUE` + `test_customers_phone_e164_unique` (UniqueViolation raised) |
| Partial unique `messages.wamid` inbound-only (WH-5) | ✅ Implemented | `uq_messages_wamid_inbound ... WHERE direction='inbound' AND wamid IS NOT NULL`; mirrored in ORM `Index(..., postgresql_where=...)`; tested |
| HNSW `kb_chunks.embedding` (vector_cosine_ops, m=16, ef_construction=64) | ✅ Implemented | Exact params in SQL; `test_kb_chunks_embedding_hnsw_index` asserts `USING hnsw`, `vector_cosine_ops`, `m='16'`, `ef_construction='64'` |
| `vector(1536)` | ✅ Implemented | SQL + `Vector(1536)` ORM + `test_kb_chunk_vector_round_trip` (1536-dim round-trip) + `test_kb_chunks_accepts_1536d_vector` |
| App role INSERT+SELECT only on `audit_log` (SH-5 append-only) | ✅ Implemented | Grants + service surface; tested (InsufficientPrivilege on UPDATE/DELETE) + live `has_table_privilege` (I=t U=f D=f S=t) |
| Full CRUD grants on business tables | ✅ Implemented | SQL grants + `test_app_role_full_crud_on_business_tables` |
| `db/migrate.sh` idempotent + `schema_migrations` | ✅ Implemented | Python+psycopg runner, per-migration transaction, version tracking; `test_migrate_applies_cleanly_twice` (2nd run prints `skip 001_init`); live re-run confirmed |
| ORM: 10 models, PG-native enums, JSONB | ✅ Implemented | `pg_enum()` helper with `values_callable` (member values); 7 enums; JSONB on `payload`/`source_meta`/`value`/`before`/`after`; tested |
| Audit service `record(actor, action, entity, before/after)` + admin read | ✅ Implemented | `app/services/audit.py`: `record_audit` + `list_audit_entries` (newest-first); append-only by surface + grants; tested |
| Compose api + pgvector, db/media/backups volumes, healthcheck, migrate-then-serve | ✅ Implemented | `infra/docker-compose.yml`; `docker compose config` valid; `test_infra.py` structural checks; command = `uv sync --frozen && migrate.sh && uvicorn` |
| `.env.example` placeholders committed, secrets never in repo (SH-2) | ✅ Implemented | `change-me-*` placeholders only; `.env` gitignored; `!infra/.env.example` whitelisted; tested + verified via `git ls-files` |

### Coherence (Design — B1)

| Design decision | Followed? | Notes |
|-----------------|-----------|-------|
| Data Model 10 tables / enums / jsonb / vector / audit append-only | ✅ Yes | Matches design Data Model section field-for-field; append-only enforced by grants (design: "app DB role = INSERT+SELECT only") |
| HNSW index params (m=16, ef_construction=64, vector_cosine_ops) | ✅ Yes | Exact match to design KB Pipeline |
| Partial unique wamid inbound-only | ✅ Yes | Matches design Webhook Pipeline Dedup row + WH-5 |
| migrate.sh runner + schema_migrations (alembic deferred to H2) | ✅ Yes | Design: "Numbered SQL migrations + migrate.sh (schema_migrations table; alembic deferred — H2)" |
| Compose topology + volumes (design Deployment step 1) | ✅ Yes | api + postgres pgvector; db/media/backups volumes; healthcheck; migrate in container |
| Deviation 1: `pgvector>=0.3` python dep | ✅ Acceptable | Design mandates Vector via SQLAlchemy types; T0.1 dep list omitted the client package — required for `Vector(1536)` (documented in apply-progress #1372) |
| Deviation 2: migrate.sh python+psycopg (not psql) | ✅ Acceptable | psycopg already a dep; runs in api container without postgresql-client; handles role creation with env password (SH-2) — documented |
| Deviation 3: conftest DATABASE_URL → db `lumat` | ✅ Acceptable | Compose uses db `lumat`; B0 tests never connect — no behavior change — documented |
| Deviation 4: api `.venv` named-volume shadow | ✅ Acceptable (required fix) | Prevents container `uv sync` clobbering host venv (broken symlinks); verified host venv intact — documented |
| Deviation 5/6: extra test files + APP_DB_PASSWORD in .env.example | ✅ Acceptable | Strict TDD (tests ship with unit); migrate.sh needs APP_DB_PASSWORD — documented |
| Rollback boundary | ✅ Yes | B1 = 4 commits dc9c9078..45565e3f; reset to d405dcab removes slice cleanly; nothing outside B1 depends on these files (isolated set verified) |

### Strict TDD Compliance (Step 5a + expanded)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | apply-progress #1372 "TDD Cycle Evidence" table present (3 rows: T1.1, T1.2, T1.3) |
| All tasks have tests | ✅ | 3/3 tasks have test files (test_migrations.py, test_db.py, test_infra.py) |
| RED confirmed (tests exist) | ✅ | 3/3 test files verified on disk (RED = failing before impl per apply-progress: rc=127, ModuleNotFoundError, 7 failed) |
| GREEN confirmed (tests pass) | ✅ | 26/26 B1 tests pass on execution now (10+8+8) — cross-referenced against live runs, not trusted blindly |
| Triangulation adequate | ✅ | T1.1: 10 cases (idempotency, tables, uniqueness, indexdef, grants, enums) · T1.2: 8 cases (CRUD, jsonb, vector, audit ×3) · T1.3: 8 checks — multiple distinct expectations per behavior; no single-case task with multi-scenario spec |
| Safety Net for modified files | ✅ | conftest.py (B0 file) extended: B0 suites 12/12 still green in full run; new files "N/A (new)" correct |
| Assertion quality audit (5f) | ✅ | No tautologies, no ghost loops, no smoke-only, no type-only-alone, no mock-heavy tests (zero mocks — real DB). All assertions verify real behavior |

**TDD Compliance**: 6/6 checks passed.

### Test Layer Distribution (B1)

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 0 | 0 | — |
| Integration | 26 | 3 (+ shared conftest) | real pgvector container + psycopg/SQLAlchemy; no external mocks |
| E2E | 0 | 0 | — |
| **Total** | **26 (B1)** | **3** | suite total 38 (12 B0 + 26 B1) |

### Changed File Coverage

Coverage analysis skipped — no coverage tool detected (config.yaml `verify.coverage_threshold: 0`, no pytest-cov in pyproject). Not a failure (strict-TDD module: informational only).

### Quality Metrics

**Linter**: ➖ Not available (no lint config/runner in repo) · **Type Checker**: ➖ Not available. Informational only — never blocking.

### Issues Found (B1 slice)

**CRITICAL**: None

**WARNING**:
1. **Real `OPENAI_API_KEY` exported in the dev shell** (`~/.bashrc`) — combined with `tests/integration/conftest.py` `os.environ.setdefault(...)`, the real key silently overrides the `sk-test` placeholder in test env (confirmed: pytest runs picked up the real key; pydantic error revealed it in `input_value`). No B1 test calls OpenAI, so zero result impact, and the key is NOT in the repo (`git grep` clean — SH-2 intact). This elevates B0 SUGGESTION-3 to material: fix in T6.1 by forcing values (`os.environ[...] = ...`, no setdefault) and stop exporting the real key in the dev shell (direnv/scoped env file).
2. B0 WARNING-1 (stale graphify) → **RESOLVED**: graph refreshed at 636 nodes/1211 edges/39 communities; B1 file nodes present in queries.

**SUGGESTION**:
1. (Carried, still open) `tasks.md` header claims "34 tasks" vs 33 rows (line 4). Fix on next tasks.md edit.
2. (Carried, still open) WH-1 "Token mismatch" scenario log clause — no `caplog` assertion yet (B1 untouched router.py); close in a later batch or T6.1.
3. (Carried, still open) README curl proof manual — spec-marker count check in T6.1.
4. `test_infra.py::test_db_service_uses_pgvector_image` (lines 61-62) — convoluted double-condition assert for POSTGRES_PASSWORD presence; works, could be simplified to a key-presence assert. Cosmetic.
5. B1 diff size: 1,437 insertions / 5 deletions (~1.4k authored lines) vs B1 forecast ~800+test-files — within chained-PR work-unit contract (review budget guard is a delivery-strategy concern, already resolved as auto-chain; flagging for PR-time awareness only).

### Graphify Context (B1)

- Graph check: `graphify-out/graph.json` present and fresh (orchestrator-refreshed; 636 nodes / 1211 edges / 39 communities; B1 code nodes present — no refresh needed for verify).
- Query `graphify query "db schema migration ORM audit"` (BFS depth=2): 114 nodes; start nodes `Audit Log`, `db/migrations/001_init.sql`, `T1.2 ORM + session + audit service`, `SH-5 Audit Log`; subgraph includes `app/models.py`, `app/services/audit.py`, `pgvector`, `T1.1 Schema + migrations`, `T2.2` — all [EXTRACTED] from code/specs.
- Path `graphify path "T1.1" "WH-5"` → 1 hop: `T1.1 --implements[EXTRACTED]--> WH-5 Deduplicate by WAMID` ✓
- Path `graphify path "SH-5" "T1.2" --undirected` → 1 hop: `T1.2 --implements[EXTRACTED]--> SH-5 Audit Log` ✓ (directed query fails because the edge direction is T1.2→SH-5 — expected)
- Cosmetic: graphify skill 0.6.1 vs package 0.9.40 version-mismatch warning — ignore.

### Runtime Harness Spot-Check (live)
```text
docker exec lumat-pg-test psql -U lumat -d lumat -c "\dt"            -> 11 tables (10 + schema_migrations)
has_table_privilege('app','audit_log', I/U/D/S)                       -> t / f / f / t   (append-only confirmed)
SELECT version FROM schema_migrations                                 -> [001_init]
DATABASE_URL=... APP_DB_PASSWORD=app bash db/migrate.sh               -> "skip 001_init" exit 0 (idempotent)
docker compose -f infra/docker-compose.yml config (vars injected)     -> valid
```

### Verdict (B1 slice)

**PASS** — Batch 1 (T1.1 schema+migrations, T1.2 ORM+audit, T1.3 compose+env) is complete (3/3 tasks [x]), fully tested (26/26 focused, 38/38 full suite, all live against the pgvector container), and matches the design Data Model, WH-5 (schema mechanism), SH-5 (audit foundation), SH-2 (secrets), and task acceptance criteria. Strict TDD evidence validated 6/6. No CRITICAL findings; 1 WARNING (dev-shell secret hygiene, no repo impact). Deferred items (SH-5 login → T5.1, SH-2 read-only fs → T7.1, WH-5 full path → T2.2) remain deferred per tasks.md — not failures of this slice. Recommended next: archive B1 slice (orchestrator) then proceed to Batch 2 apply (T2.2 webhook ingest).
