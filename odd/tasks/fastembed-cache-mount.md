# The container re-downloaded a 241MB model on every recreate

Feature id: `fastembed-cache-mount`
Branch: `odd/fastembed-cache-mount`

## Objective

The api container reuses the host's downloaded fastembed ONNX model instead of re-fetching ~241MB
from the HuggingFace Hub inside the first embedding-dependent turn of every fresh container.

## Problem

`fastembed` defaults its cache to `tempfile.gettempdir()/fastembed_cache` and exposes **no env var to
override it** — only the `cache_dir` argument of the constructor (verified in
`fastembed/common/utils.py:53`). Inside the container that resolves to the container's own `/tmp`,
which is not mounted from anywhere and does not survive a recreate.

The `api` service mounted only `..:/app`, `venv`, `media` and `backups`. So every
`docker compose down` / `up --build` produced a container with an empty model cache, and the next
embedding-dependent turn paid the full download. Measured on this host, 2026-09-22
(`docker logs -t infra-api-1`):

```
22:27:29  POST /panel/api/chat/threads/1/messages            201
22:27:29  GET  /panel/api/chat/threads/1/stream?run_id=02a0c… 200
22:27:33  app/services/kb.py:125 — TextEmbedding(model_name=EMBED_MODEL)
22:27:35  Fetching 5 files:   0%
22:33:06  Fetching 5 files: 100% [05:30]      ← 5m30s, at ~100-140 KB/s
22:33:11  run completed (reply persisted)
```

`stream_events_async(..., timeout=300.0)` had already given up at **22:32:29** — 37 s before the
answer existed. The panel treats a stream end as completion, so the operator saw the spinner stop
with no answer. The download was not slow enough to be a hang; it was slow enough to be *silent*.

**This branch removes the cost, not the symptom.** The silent stream deadline is a separate unit
(`odd/stream-deadline-continuity`); loading the model at boot rather than in a turn is another
(`odd/embedder-prewarm`, delivered).

## Scope

### T1 — mount a durable cache into the api container

- `infra/docker-compose.yml`, `api.volumes`:
  `${EMBED_CACHE_DIR:-/tmp/fastembed_cache}:/tmp/fastembed_cache`.
- The mount target is the container path fastembed already resolves by default, so the application is
  untouched: no `cache_dir` plumbing, no config setting, one compose line.
- The host value lives in the gitignored `infra/.env` (host-specific, correctly not versioned).

### T2 — document the variable

- `infra/.env.example` documents `EMBED_CACHE_DIR`. A compose file that reads a variable nobody
  documents is a trap for the next dev.

## Acceptance criteria

1. The container reads the model from the mounted path and downloads nothing.
2. The resolved bind source is correct when the variable is empty, unset, and explicitly overridden.
3. Dev-only: production is unaffected.

## Out of scope (do not expand)

- **`infra/docker-compose.prod.yml`.** Prod has its own service definition; this is a dev convenience.
- **The boot prewarm** (`odd/embedder-prewarm`, PR #308) — it removes the same cost for a *warm* cache.
- **The 300 s stream deadline** (`odd/stream-deadline-continuity`) — the reason the cost was invisible.
- **Plumbing `cache_dir` through settings.** It would put a container path in application code to
  avoid one compose line.
- **Pinning `fastembed` or the model.** The warning about mean pooling is pre-existing and unrelated.

## Tasks

- [x] **T1** — mount the host cache into the api container.
- [x] **T2** — document `EMBED_CACHE_DIR` in `.env.example`.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `infra/docker-compose.yml` — one bind mount on the api service; target is fastembed's own default, so no application change. |
| T2 | done | `infra/.env.example` — `EMBED_CACHE_DIR` documented with its fallback, next to `EMBED_MODEL`/`EMBED_DIMS`. |

### Verification (observed)

Resolution, three ways, via `docker compose -f infra/docker-compose.yml config` (not assumed):

| `EMBED_CACHE_DIR` | Resolved bind source |
| --- | --- |
| empty | `/tmp/fastembed_cache` (fallback applies to empty, not just unset) |
| unset | the `infra/.env` value (`~/.cache/lumat-fastembed`) |
| `/tmp/some-other` | `/tmp/some-other` (override respected) |

Functionally, inside the rebuilt container, against the mounted cache:

- `kb.embed_texts([...])` → **2.98 s**, 384 dims, and no `Fetching` progress bar. Before: **5m30s**.
- `kb.retrieve(...)` → **2.27 s** (0 rows; the dev KB is empty, which is expected).
- Bind mount confirmed in `docker inspect` and in `/proc/mounts`.

Applying the fix to the running dev stack, and re-measuring, is what produced those numbers.

TDD mode: **active** for this repo (`openspec/config.yaml`: `apply.tdd: true`,
`testing.strict_tdd: true`).

**Correction.** This record first asserted that no test applied here — *"the diff is compose
configuration and a documentation line, hence no RED-first cycle to run and no test to write"*. That
is **false**. `tests/integration/test_infra.py` reads this repository's infra files, and
`test_env_example_has_no_real_secrets` rejects every `.env.example` key whose value is empty. The
first version of `EMBED_CACHE_DIR=` had an empty value and **failed that test in CI** (`1 failed,
1274 passed`); the local suite was never run against that commit, which is the process failure, not a
gap in the tests.

The claim is left visible rather than quietly edited, because the mistake is instructive: "this
change has no code" is not the same as "no test covers this file". A repository can test its own
configuration.

Declared consequence: this unit still has **no RED-first cycle**. Its evidence is the configuration
resolution and the observed latency above, plus the full suite re-run after the correction —
**1271 passed, 2 warnings in 132.95 s** — and CI on the final tip.

## Process note, declared

This change was first committed **directly to `main`** (`76bfc2af`), without a branch or a PR — which
is not this repository's flow. It was moved onto this branch and removed from `main` during the same
session. The correction is recorded here rather than left to be discovered from the reflog.

## Graph nodes consulted

Graph: `graphify-out/` (main worktree). Query: "get_embedder fastembed cache_dir kb retrieval" →
48 nodes (truncated at the 2000-token budget, so it is a map, not a proof).

Key nodes: `get_embedder()` `app/services/kb.py:115` (the only model-load seam in the codebase, which
is why mounting the cache is sufficient), `embed_texts()` `app/services/kb.py:129`, `retrieve()`
`app/services/kb.py:322`. `infra/docker-compose.yml` itself is not in the graph.

## Open risks carried forward

- **The mount target contains `tmp`.** `fastembed`'s `decompress_to_cache` calls
  `shutil.rmtree(cache_dir)` when `"tmp" in cache_dir` (`model_management.py:315-316`). This model is
  fetched through the `hf_hub` snapshot path (`snapshots/`, `blobs/`), not the tarball path, so the
  branch is not hit — but a future fastembed model distributed as a `.tar.gz` would delete the
  mounted directory's contents. Upgrading to an explicit `cache_dir` setting removes the hazard.
- **The host directory is a copy, not the original.** `~/.cache/lumat-fastembed` came from the host's
  `/tmp/fastembed_cache`; the host copy is left in place for host-side runs. On this machine `/tmp`
  is cleared on reboot, so the durable copy becomes the only one — which is the intended direction.
- **The default fallback is the host's `/tmp/fastembed_cache`.** A dev who has never downloaded the
  model gets one download, which is the behaviour that existed before this change: no regression, but
  also no pre-seeded cache for a fresh machine.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/fastembed-cache-mount/tasks`, reconcile
against the actual worktree, and resume the first unfinished task.
