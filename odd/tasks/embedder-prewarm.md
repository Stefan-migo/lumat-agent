# The first embedding turn pays the model load

Feature id: `embedder-prewarm`
Branch: `odd/embedder-prewarm`

## Objective

The local embedding model is loaded off the request path at boot, so no operator turn pays the
load — and a cold fastembed cache, which costs ~5m30s of HuggingFace download, can no longer happen
*inside* a turn that the panel's 300 s SSE stream will abandon.

## Problem

Evidence from the dev stack, 2026-09-22 (container `infra-api-1`, `docker logs -t`):

```
22:27:29  POST /panel/api/chat/threads/1/messages            201
22:27:29  GET  /panel/api/chat/threads/1/stream?run_id=02a0c… 200
22:27:33  app/services/kb.py:125 — TextEmbedding(model_name=EMBED_MODEL)   ← lazy load starts HERE
22:27:35  Fetching 5 files:   0%
22:33:06  Fetching 5 files: 100% [05:30]                                   ← 5m30s download
22:33:11  run completed (message 4 persisted, status processed)
```

`stream_events_async(..., timeout=300.0)` (`app/services/agent_chat.py:932`) gave up at **22:32:29**,
37 seconds *before* the answer existed. `AgentChat.tsx:460` treats a stream **end** as normal: it
reloads the thread and calls `setProcessing(false)`. So the operator watched the spinner stop with no
answer, while the reply sat persisted in the database. That is the whole reported symptom — "el agente
no termina de procesar y no responde".

`kb.get_embedder()` (`app/services/kb.py:115`) is the only load seam in the codebase, and it loads
**lazily on first use**. The first caller is `retrieve_kb` (`app/chat/assistant/nodes.py:602`) or a
memory tool. A conversational turn never touches it, which is why message 1 answered in 6 s and
message 3 took 5m42s.

Two independent defects met in that window:

1. **The load is lazy**, so an operator turn pays for it. *This change fixes this.*
2. **The stream cap (300 s) is shorter than a legitimate cold turn.** Out of scope here — see
   "Open risks carried forward".
3. The ephemeral container cache that turned a ~3 s load into a 5m30s download is an *environment*
   defect, already fixed in the main worktree (the fastembed cache is now bind-mounted from the host).

## Scope

### T1 — load the embedder off the boot path

- A helper spawns the load on a **daemon** thread from the lifespan. Startup must never wait for it:
  a cold cache means minutes, and boot must stay fast either way.
- A prewarm that raises is **logged and swallowed**. It must not fail boot, and it must not skip the
  recovery sweeps that follow it (see `startup-sweep-isolation`).

### T2 — one construction under concurrency

- `get_embedder()` constructs exactly once even when the prewarm thread and an operator turn race.
  Without this, a turn arriving during prewarm triggers a *second* concurrent ONNX load (~240 MB more
  in RAM) — which is precisely the cost this change exists to remove.

### T3 — the suite never warms the real model

- A setting disables the prewarm, and the suite conftest disables it. Without this, every lifespan
  start in the tests (integration tests build the app with `TestClient(create_app())`) would spawn a
  thread that loads the **real** embedder: minutes of download in CI, and the module-level `_embedder`
  global poisoned for every test that monkeypatches the deterministic fake.

## Acceptance criteria

1. Boot does not wait for the prewarm, even when the load is slow.
2. A raising prewarm is logged and does not break startup.
3. `get_embedder()` runs the loader exactly once when two threads call it concurrently.
4. With the prewarm disabled, no lifespan start touches fastembed.
5. `pytest tests/unit` green.

## Out of scope (do not expand)

- **The 300 s stream cap and the panel's stream-abandon behaviour.** Real, confirmed, and *not* fixed
  by this change: any turn longer than 300 s still loses its stream silently. It needs its own
  decision (raise the cap, heartbeat, or a terminal event the frontend acts on) because it changes a
  contract with `web/`. Recorded under "Open risks carried forward".
- **Retry/backoff around the model download.** A download that fails today already surfaces as a
  degraded turn; prewarming changes *when* it happens, not what happens when it fails.
- **The dev container's cache mount.** Already fixed in the main worktree, outside this branch.
- **Embedding quality, model choice, or dims.** Untouched.
- **A readiness/health signal for the prewarm.** No consumer asks for it yet.

## Tasks

- [x] **T1** — prewarm helper + lifespan wiring (daemon thread, fail-soft).
- [x] **T2** — single construction in `get_embedder()` under concurrency.
- [x] **T3** — prewarm setting, off in the test suite.
- [x] **T4** — unit tests + suite green.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `app/main.py` — `_prewarm_embedder()` (fail-soft) + `start_embedder_prewarm()` (daemon thread), called from the lifespan *after* the sweeps so a cold download never delays recovery. |
| T2 | done | `app/services/kb.py` — `_embedder_lock` held across the lazy init; five racing threads construct exactly once. Teeth-verified below. |
| T3 | done | `app/config.py` — `embed_prewarm: bool = True`; `tests/conftest.py` forces `EMBED_PREWARM=false` next to the forced test key (not in `TEST_ENV`, which is `setdefault` and a dev-shell export would defeat). |
| T4 | done | `tests/unit/test_embedder_prewarm.py` (4 tests, DB-free); unit suite 375 passed; full suite 1274 passed. |

### Teeth check (observed, not assumed)

Each mutation was applied, the pinned test was run, the file was restored, and the digest confirmed:

- **Mutation A** — the lock removed from `get_embedder()`:
  `test_get_embedder_constructs_once_under_concurrency` **failed** with `assert 5 == 1` —
  five racing threads each built their own model. Restored: `sha256 0f033a4e…` (matches pre-mutation).
  *Re-verified independently by the orchestrator, not just reported by the implementer.*
- **Mutation B** — `_prewarm_embedder()` called inline in the lifespan:
  `test_prewarm_does_not_block_boot_on_a_slow_load` **failed** with
  `AssertionError: lifespan waited for the prewarm`. Restored: `sha256 020a3438…`.
- **Mutation C** — the `try/except` dropped from `_prewarm_embedder`:
  `test_prewarm_failure_is_logged_and_swallowed` **failed** with
  `RuntimeError: model unavailable`. Restored: `sha256 020a3438…`.

### Verification (observed)

- `uv sync --frozen` — ok (shared uv cache warm).
- `uv run pytest tests/unit -q` — **375 passed**.
- `uv run pytest tests/unit -q -k prewarm` — **4 passed**.
- Focused integration, lifespan + embedder seams:
  `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5606/lumat" uv run pytest -o addopts="" -q tests/integration/test_assistant_chat.py tests/integration/test_kb.py`
  → **67 passed in 14.77 s**.
- Full suite:
  `TEST_ADMIN_DB_URL="postgresql://lumat:lumat@localhost:5606/lumat" uv run pytest -o addopts="" -q`
  → **1274 passed, 2 warnings in 171.65 s**. The warnings are the two pre-existing ones
  (`_publish_all` never awaited; the fastembed mean-pooling notice). The dashboard test recorded
  below as a pre-existing failure passed in this run — its failure needs the last local hour of the
  day, which did not hold here.
- Env → settings plumbing, verified directly (the link the conftest change depends on):
  `EMBED_PREWARM=false → False`, `=true → True`, unset → `True` (production default stays ON).
- Test DB for this worktree is derived, not shared: project
  `lumat-test-lumat-agent-odd-embedder-prewarm`, port **5606**
  (`./infra/test-db.sh env`). `infra/.env` is gitignored and was copied from the main worktree.

One suite test loads the **real** embedder (`tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique`,
visible as the fastembed mean-pooling warning). That is pre-existing and unaffected here — but it is
the concrete reason T3 exists: without the forced-off setting, every lifespan start in the suite
would load that same real model on a background thread instead of once, on demand.

## Checks / verification commands

Run from this worktree root. Tests are DB-free here (`tests/unit` must not need credentials):

- `uv sync --frozen` (first run only; the shared uv cache is warm)
- `uv run pytest tests/unit -q`
- Focused: `uv run pytest tests/unit -q -k prewarm`

The derived test DB for this worktree, if the full suite becomes necessary:

- `infra/test-db.sh project` / `infra/test-db.sh port` (needs `infra/.env` copied from the main
  worktree — it is gitignored and not provisioned by `rapso worktree create`)
- Full suite: `TEST_ADMIN_DB_URL="postgresql://lumat:<TEST_POSTGRES_PASSWORD>@localhost:<port>/lumat" uv run pytest -o addopts="" -q`

TDD mode: **active** for this repo. `openspec/config.yaml` sets `apply.tdd: true` and
`testing.strict_tdd: true` (detected `2026-08-12`, runner `pytest`), and the SDD capability cache
(`sdd-init/lumat`) records `strict_tdd: true`.

**Correction.** This record first asserted that TDD was *"not active for this repo (no strict-TDD
capability cache)"*. That is **false**: both the config and the capability cache say the opposite.
The claim was read from both sources on 2026-09-22, while resuming this unit for delivery.

Declared consequence, not hidden: this unit therefore has **no recorded RED-before-implementation**
step. Its behavioral evidence is the mutation-based teeth check above — three mutations applied, each
pinned test observed failing, every file restored with its digest confirmed — which is strong but is
*not* a RED-first cycle. Runner: pytest.

Known pre-existing suite failure, must not be attributed to this change:
`tests/functional/test_api_dashboard.py::test_today_projection_uses_local_bounds_and_operational_predicates`
fails with `IndexError` in the last local hour of the day (`America/Santiago`).

## Graph nodes consulted

Graph: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md` (main worktree).
Query: "get_embedder fastembed cache_dir kb retrieval" → 48 nodes (truncated at the 2000-token
budget, so it is a map, not a proof).

Key nodes: `get_embedder()` `app/services/kb.py:115` (the only load seam), `embed_texts()`
`app/services/kb.py:129`, `retrieve()` `app/services/kb.py:322`, `lifespan()` `app/main.py:31`,
`create_app()` `app/main.py:57`, `stream_events_async()` `app/services/agent_chat.py:932`,
`retrieve_kb()` `app/chat/assistant/nodes.py:602`, `config.py` (`get_settings`).

## Open risks carried forward

- **The stream cap is untouched.** With the prewarm in place the embedder is no longer the reason a
  turn runs long, but any turn that legitimately exceeds 300 s still ends with a silently abandoned
  stream and a reloaded thread — the exact symptom this feature was reported from. Needs its own
  change.
- **Prewarm runs on every `--reload` restart** in dev. With a warm cache that is ~3 s of background
  ONNX init per code save; harmless, but it is real work happening off nobody's request.
- **A failed prewarm is silent to the operator.** It is logged; nothing surfaces it in the panel. The
  next embedding turn simply pays the load again (with the lock, serially).

## Native review (RDD)

- Contract `gentle-ai.review-integration/v2`, lineage `review-b6316afbcda58ca3`, risk **high**
  (6 files / 366 changed lines). Risk reason: `process_boundary` / `shell_process` in
  `tests/conftest.py`.
- Four lenses, all admitted and completed: `review-risk` (order 0), `review-resilience` (1),
  `review-readability` (2), `review-reliability` (3).
- Result: **0 findings across all four lenses.** Admission closed the review as `approved` and the
  exact acknowledgement burned the authority (`gentle-ai.review-acknowledged/v1`,
  `consumed_revision sha256:890d802a17d0c7cb3fc652abb9e72b21185592eeaacb06dbed7f75796017bada`).
- Frozen correction budget: **183 lines — not used.** No correction was required.
- Candidate frozen at `c546df87` (`candidate_tree f5e0b39c9d948aa9cd670da1d372e08aa2181105`), base
  `5ae02c45` (`base_tree d6aa1747c1e1d838d477d00030919a7eb7eff473`).
- Full suite re-run independently when resuming the unit (not the implementer's number replayed):
  `1274 passed, 2 warnings in 231.14s`, exit 0, against this worktree's own test DB (port 5606).
- The review grants no delivery authority: push and PR are separate human decisions.

## Delivery

- Branch `odd/embedder-prewarm` pushed to `origin` after explicit human authorization.
- PR **#308** — https://github.com/Stefan-migo/lumat-agent/pull/308 — base `main`, exactly one label
  (`type:feature`), `MERGEABLE`.
- PR checks: `test` **pass** (1m55s) and GitGuardian Security Checks **pass**.
- Merge is the maintainer's decision and was **not** taken here.
- After the merge: `bash infra/test-db.sh down` **before**
  `rapso worktree cleanup embedder-prewarm --remote`.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/embedder-prewarm/tasks`, reconcile against the
actual worktree, and resume the first unfinished task.
