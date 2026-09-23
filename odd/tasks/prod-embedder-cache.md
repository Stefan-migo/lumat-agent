# The prod api container cannot write the embedder cache

Feature id: `prod-embedder-cache`
Branch: `odd/prod-embedder-cache`

## Objective

The production api container can load the local embedding model: it gets a writable,
durable cache path, because prod runs with `read_only: true` and currently has none.

## Problem

Evidence from production, 2026-09-23 (VPS `179.199.148.175`, container `lumat-api-1`,
after the first real inbound WhatsApp message was persisted):

```
POST /webhook/whatsapp 200 OK                      <- Meta delivery + signature: fine
messages: id=3 "Hola mundo" status=failed

ERROR xet_runtime logging: Error logging to file
  "/home/appuser/.cache/huggingface/xet/logs/xet_...log" (Read-only file system (os error 30))
ERROR fastembed.common.model_management: Could not download model from HuggingFace:
  I/O error: I/O error: Read-only file system (os error 30). Falling back to other sources.
ERROR fastembed ... Could not download model from either source, sleeping for 3.0 seconds
memory embedding failed after 3 attempts: Previous task error: I/O error: Read-only file system
processing failed for message 3; marking failed
```

Two facts combine:

1. `infra/docker-compose.prod.yml` declares `volumes: !override` with only `media:/app/media`.
   `!override` **replaces** the base list, so the api service has no writable cache path at all:
   the image filesystem is read-only (SH-2) and `media/` is the only writable mount.
2. `hf_hub`'s download path (used by `fastembed` 0.8.0 via `snapshot_download(cache_dir=...)`)
   also writes to `HF_HOME` (`~/.cache/huggingface`) for its xet transport. That path is inside
   the read-only image filesystem, and the failure aborts the model download.

The dev compose mounts a host cache into the container (`odd/fastembed-cache-mount`), which is
exactly why this only shows in production. That unit declared prod explicitly out of scope:

> **Out of scope (do not expand): `infra/docker-compose.prod.yml`.** Prod has its own service
> definition; this is a dev convenience.

This unit closes that deferral. The gap was invisible until Meta could actually deliver a message,
which required the phone number to be registered — done the same day.

## Scope

### T1 — a writable, durable embedder cache in the prod api container

- `infra/docker-compose.prod.yml`: add a named volume mounted at `/home/appuser/.cache`
  (covers `HF_HOME` and any other HuggingFace cache path) and point the two cache
  locations at it explicitly:
  - `HF_HOME=/home/appuser/.cache/huggingface`
  - `FASTEMBED_CACHE_PATH=/home/appuser/.cache/fastembed`
    (`fastembed/common/utils.py:54` reads this env var; the previous unit's claim that
    "no env var to override it" exists is **wrong for 0.8.0** — corrected here.)
- The path deliberately does **not** contain `tmp`: `decompress_to_cache` calls
  `shutil.rmtree(cache_dir)` when `"tmp" in cache_dir` (`model_management.py:315-316`).

### T2 — the volume must be appuser-writable on first mount

- `Dockerfile`: pre-create and `chown` `/home/appuser/.cache`, exactly the pattern already
  used for `media/`. Without it Docker seeds a fresh named volume as root and the appuser
  cannot write, which is the same failure one layer down.

### T3 — a regression test, so it cannot silently vanish again

- `tests/integration/test_infra.py`: assert the prod api service declares the cache mount and
  that `read_only: true` and the no-host-ports shape are preserved.

## Acceptance criteria

1. `docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml config`
   resolves the embedder cache to a writable, non-image path, and the api service still
   publishes no host ports and stays `read_only: true`.
2. The new test fails when the mount is removed (teeth), and the existing suite stays green.
3. In production, a real inbound message reaches `status: processed` (not `failed`) — the
   observable outcome, verified after deploy.

## Out of scope (do not expand)

- **The dev compose mount** (`odd/fastembed-cache-mount`, delivered) — untouched.
- **The boot prewarm** (`odd/embedder-prewarm`, delivered) — it stays as-is; a cold volume now
  warms off the request path instead of failing forever.
- **Baking the model into the image.** `EMBED_MODEL` is a runtime setting; baking one model
  couples the image to a value that lives in `infra/.env`.
- **`DEEPSEEK_API_KEY`, invalid at the same time.** Separate credential, separate owner, and
  it would fail the turn with a 401 even with the cache fixed. Not this unit's concern.
- **The 300 s stream deadline** (`odd/stream-deadline-continuity`).
- **Plumbing `cache_dir` through app settings.** The env var makes it unnecessary.

## Tasks

- [x] **T1** — prod compose: named cache volume + `HF_HOME` / `FASTEMBED_CACHE_PATH`.
- [x] **T2** — Dockerfile: pre-create + chown `/home/appuser/.cache`.
- [x] **T3** — regression test in `tests/integration/test_infra.py`.
- [ ] **T4** — deploy to the VPS + verify a real message reaches `processed`.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `infra/docker-compose.prod.yml` — `embed-cache:/home/appuser/.cache` added under `volumes: !override`, plus `HF_HOME` / `FASTEMBED_CACHE_PATH`, and the `embed-cache` volume declared. |
| T2 | done | `Dockerfile` — `RUN mkdir -p /app/media /home/appuser/.cache && chown -R appuser:appuser /app /home/appuser`. |
| T3 | done | `tests/integration/test_infra.py::test_prod_api_service_has_a_writable_embedder_cache` — see teeth check below. |
| T4 | pending | Deploy + a real inbound message reaching `processed`. |

### Verification (observed)

Resolved compose (not assumed) — `GIT_SHA=$(git rev-parse --short HEAD) docker compose
-f infra/docker-compose.yml -f infra/docker-compose.prod.yml config`:

```
api.read_only: True
api.ports:     None
api.volumes:   [media:/app/media, embed-cache:/home/appuser/.cache]
HF_HOME:               /home/appuser/.cache/huggingface
FASTEMBED_CACHE_PATH:  /home/appuser/.cache/fastembed
volumes:               certbot-certs, certbot-webroot, db, embed-cache, media
```

The hardening shape is preserved: still read-only, still no host ports.

Focused suite: `tests/integration/test_infra.py` → **11 passed**.

Teeth check (observed, not assumed) — the mount line deleted, the pinned test run, the file
restored from `sed`'s backup:

- mount removed → **FAILED**
  `AssertionError: prod api must mount a writable embedder cache, got: ['media:/app/media']`
- restored → **passed**

Suite preconditions in this worktree: `uv sync --frozen` and `infra/test-db.sh up` (test DB on
port 5707); without the worktree `.venv`, `migrated_db` fails with `migrate.sh` exit 127 and every
integration test errors at setup.

## Graph nodes consulted

Graph: `graphify-out/graph.json` (main worktree). Query
"embedder fastembed cache_dir HF_HOME prod compose read_only volume" → 135 nodes.

Key nodes: `Production compose override` (`infra/docker-compose.prod.yml`),
`ODD: fastembed-cache-mount` (`odd/tasks/fastembed-cache-mount.md` — the dev-only precedent),
`ODD: embedder-prewarm` (`odd/tasks/embedder-prewarm.md`),
`test_compose_declares_db_media_backups_volumes()` (`tests/integration/test_infra.py:91`),
`uvicorn api Service` (`infra/docker-compose.yml`), `get_embedder()` (`app/services/kb.py`).

## Delivery

- Branch `odd/prod-embedder-cache` pushed to `origin` after explicit human authorization.
- PR **#317** — https://github.com/Stefan-migo/lumat-agent/pull/317 — base `main`, exactly one
  label (`type:bug`), `MERGEABLE`. No `Closes #N`: this repository has no PR-validation workflow
  (`.github/workflows/` holds only `tests.yml`) and no open issues, which is the same note the
  previous three PRs carry.
- Merge and deploy are the maintainer's decisions. **T4 remains open.**

### Not verified here (declared)

- **No native RDD review.** `gentle-ai review mode status` → `off (decided by clone_local)`, a
  pre-existing explicit decision, so no receipt covers these bytes. `review assess
  --committed-only` reports `risk: high` (`process_boundary` / `shell_process` on the compose
  file), which is why an independent read-only verifier was used instead. Its single WARNING —
  the first version of the test could pass for a read-only or foreign mount — is answered by
  `b72c2674`.
- **The production outcome is unobservable here.** Only after deploy can a real inbound message
  be seen reaching `processed` instead of `failed`.
- **`DEEPSEEK_API_KEY` remains invalid**, and it is still a blocker after this fix: the turn
  would fail with a 401 during classification. Separate credential, separate owner.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/prod-embedder-cache/tasks`, reconcile
against the actual worktree, and resume the first unfinished task.
