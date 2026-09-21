# ODD: versioning-release-process

**Branch**: `odd/versioning-release-process`
**Worktree**: `../lumat-agent-odd-versioning-release-process`
**Base**: `06768699` (scoped at `5c5f4af2`; `main` advanced 33 commits before the branch was cut —
none of them touched a file in the authorized scope, so the plan below is unchanged)
**Seeded from**: `.rapsodia-code/sessions/archived/2026-09-20-versionado-release-trazabilidad/report.md`
**Status**: in progress — T1 next

## Objective

Give the project a release process it actually executes: one version source of truth, a curated
changelog, and a tagged deploy — so that "what is running in production?" is answerable from outside,
and every deploy has a rollback point.

## Problem (verified)

The documented process exists and was never executed:

- `docs/ops.md §2.1` states *"Every deploy is a tagged release; the tag is the rollback point"*, with
  deploy/rollback both expressed as `git checkout <tag>`.
- Before 2026-09-20 the repository had **zero tags**, local and remote. Production was running
  `10165a6d` (deployed 2026-09-08) with no rollback point.
- `app/main.py:75` returns `{"status": "ok", "version": settings.app_version}` and
  `app/config.py:60` is `app_version: str = "0.1.0"` — a **hardcoded constant**. The multi-stage
  `Dockerfile` does not stamp a git SHA. The deployed revision is not verifiable from outside.
- There is **no `.github/`** at all: no CI. The only gate is a human running ~1000 tests (~208s).
- `docs/ops.md §2.9` (the go-live record, self-described as *"the evidence the change is in
  production"*) is empty, and `docs/hardening.md` records every section as `(VM)` — while production
  is live and carries the hardening headers. The runbook is not a trustworthy record.

## Decisions (agreed — do not re-litigate)

| Decision | Value |
|---|---|
| Version scheme | **CalVer `YYYY.MM.N`**, annotated tags |
| Why not SemVer | No compatibility contract exists (deployed product, no external consumers); the bump is mechanical, not a per-release judgment call |
| Revisit SemVer if | A package or external API is ever published |
| Version sources | One. Feeds `pyproject.toml`, `/health`, the tag, and `CHANGELOG.md` |
| Changelog | Curated by hand from the existing Conventional Commits; Keep a Changelog sections |
| Tag timing | **Before** the deploy, on the exact commit being deployed |
| Part status | One `Status:` line inside each existing spec — no parallel artifact |
| Retroactive baseline | `v2026.09.1` on `10165a6d`, **already created and pushed** (2026-09-20) |
| Explicitly skipped | semantic-release, release-please, changesets, release trains, prerelease channels, LTS/release branches, monorepo version tooling, commit-lint hooks, one-release-per-PR, raw `git log` changelog dumps |

## Authorized scope

- `app/config.py` — the single version source / build-stamped values.
- `app/main.py` — `/health` reports the real version and commit instead of the constant.
- `Dockerfile` and `infra/docker-compose.prod.yml` — stamp version and commit at build time.
- `CHANGELOG.md` — new file.
- `docs/ops.md` — state the CalVer rule, the tag-before-deploy step, and the `Status:` convention.
- `.github/workflows/` — CI running the suite.
- `odd/tasks/versioning-release-process.md` — this record.

## Out of scope (do not touch)

- The catch-up deploy of the ~576 commits production is behind. That is a separate operational
  concern with its own risk profile, not a versioning work unit.
- Rebuilding or re-tagging the `v2026.09.1` baseline.
- Any change to application behaviour, the panel, or the bot.
- Coolify or any deployment-model change. Rejected; do not re-open inside this work unit.
- Reconstructing historical releases for the ~120 untagged PRs. Do not manufacture them.

## Implementation contract

1. **One version source.** The version must not exist as two independent constants that can drift.
   Whatever mechanism is chosen (a build arg read from a single file, or the tag at build time), the
   same value must reach `/health`, the image, and the changelog entry. Leaving `pyproject.toml`
   version and `app/config.py` `app_version` as two hand-maintained values is a failure of this
   requirement.
2. **`/health` must report the deployed identity.** At minimum the CalVer version; recommend also the
   short commit SHA, so a revision can be identified even when a tag was misapplied. Shape:
   `{"status": "ok", "version": "2026.09.2", "commit": "5c5f4af2"}`.
3. **Build-time stamping, not runtime guessing.** The container does not have `.git`, so the commit
   and version must be stamped as build args. Do not attempt to shell out to git at runtime.
4. **`CHANGELOG.md` in Keep a Changelog format** with an `## [Unreleased]` section at the top, plus a
   curated entry for the `v2026.09.1` baseline that states it was tagged retroactively.
5. **CI must run the real suite.** The suite requires PostgreSQL with the `pgvector` extension, so the
   job needs a service container. A CI that cannot run the suite is worse than no CI, because it
   reports green while proving nothing.
6. No new runtime dependency for the version plumbing.

## Tasks

- [x] **T1 — Version source of truth + `/health`.** Make one value flow from a single source into the
      image and out through `/health`, including the commit. Update `app/config.py`, `app/main.py`,
      `Dockerfile`, `infra/docker-compose.prod.yml`. Tests assert `/health` reports the injected
      version rather than a constant. — **done, see the T1 record below.**
- [ ] **T2 — `CHANGELOG.md`.** Create it in Keep a Changelog format; add the curated `v2026.09.1`
      baseline entry, explicitly marked retroactive.
- [ ] **T3 — `docs/ops.md` release section.** State the CalVer rule, the tag-before-deploy step, and
      the `Status:` line convention; correct the §2.9 go-live record guidance so it matches a process
      someone will actually follow.
- [ ] **T4 — CI running the suite.** Add the workflow with a `pgvector` service container. **If this
      grows beyond a single focused workflow it should split into its own work unit** — do not let it
      derail T1–T3.
- [ ] **T5 — Verify.** Focused tests, then the full suite; counts measured and reported.

## Acceptance criteria

1. `/health` reports the injected version and commit; no hardcoded version constant remains reachable
   from the health path.
2. Changing the single version source changes `/health` after a rebuild — proven by a test, not by
   assertion.
3. `CHANGELOG.md` exists, is in Keep a Changelog format, and its baseline entry states it is
   retroactive.
4. CI runs the full suite (including the DB-backed tests) and fails on a deliberately broken branch —
   verified, not assumed.
5. `docs/ops.md` describes the process actually in use, with no step that cannot be executed (the
   existing "tagged release" language becomes true rather than aspirational).
6. The full suite is green; the baseline at this base is measured before changing anything.

## Checks

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(infra/test-db.sh env)"
uv run pytest tests/
```

`pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`. No linter, type checker, or
formatter exists; the tests are the verification.

## Progress

- [x] Worktree created and provisioned; `.opencode/tools/package-lock.json` removed.
- [x] Graph Check before editing — the graph at `graphify-out/` was rebuilt at `06768699`, the
      branch base, so it is fresh (the "stale at `26b463a2`" note below no longer applies).
- [x] Baseline measured before touching anything: `uv run pytest tests/` → **1042 passed, 2 warnings,
      exit 0, 112.68s** (Python 3.14, test DB `pgvector/pgvector:pg16` on port 6364).
- [ ] T2–T5.

### T1 — done (delivered, reviewed, approved)

**Single source:** `pyproject.toml [project] version`, now `2026.09.2` (CalVer `YYYY.MM.N`, the release
after the retroactive baseline `v2026.09.1`). `app/config.py` resolves it through a module-level
`PYPROJECT_PATH` and a `default_factory`, so the value is read per instantiation and no second
constant exists. The image carries `pyproject.toml` and reads the same file, because
`uv sync --no-install-project` leaves no importable project metadata. Only the commit SHA travels as a
build ARG — the build genuinely cannot know it (`.dockerignore` excludes `.git/`). `uv.lock` was
regenerated: the root package version line is the only change in it (`2026.9.2`, PEP 440 normalising
the leading zero; the `/health` value stays the tag form `2026.09.2` because the file is read as text).

**Design decision taken with the human (2026-09-21):** `pyproject.toml` as the single source, chosen
over a root `VERSION` file. Rationale: it needs no new file, no `dynamic` version, no hatchling
configuration, and above all no manual `export APP_VERSION=$(cat VERSION)` step in the deploy — the
class of documented-but-never-executed step this work unit exists to remove. The cost accepted is that
the runtime parses the build file at import.

**Verification (measured, not asserted):**
- Baseline before any change: `1042 passed, 2 warnings, exit 0, 112.68s`.
- Focused: `uv run pytest tests/integration/test_health.py tests/integration/test_infra.py` →
  **13 passed** (re-run independently by the orchestrator: 13 passed in 0.95s).
- Full suite after the change: **1044 passed, 2 warnings, exit 0** (+2 = the two new tests).
- `uv run python -c "...get_settings()..."` → `2026.09.2 unknown`.
- Deploy wiring exercised, not assumed: `docker compose ... config` **fails loudly** without
  `GIT_SHA` (`required variable GIT_SHA is missing a value: export GIT_SHA=$(git rev-parse --short
  HEAD) before building`) and parses cleanly with it exported.
- **Not proven:** an actual Docker image rebuild. The acceptance criterion "changing the source
  changes `/health` after a rebuild" is proven by the source-redirection test, which exercises the
  same read path, not by building the image.

**Review:** native RAR, lineage `review-0fc5cb08461445de`, risk **high**, canonical 4R
(`review-risk`, `review-resilience`, `review-readability`, `review-reliability`), all four admitted.
Result: **approved, 0 findings** across all four lenses. Authority burned
(`gentle-ai.review-acknowledged/v1`, `authority: burned`). Delivery remains a separate human decision.

**Graph nodes consulted (Graph Check step 2):** `get_settings`, `CalVer Release Process`,
`fastapi_app`, `docker_compose_infra`, `test_infra.py`, plus the `version` / `config` /
`health_counts()` symbols from a scoped query. No directed path exists between the config/main
community and the Dockerfile/compose community — expected, the coupling is textual (build args and
file paths), not call-graph.

**Accepted correction noted for T3:** the deploy flow in `docs/ops.md` must now export `GIT_SHA`
before `up -d --build`, and the release-prep step must bump the CalVer in `pyproject.toml` before
tagging. Until T3 lands, the documented deploy command fails fast — which is the intended behaviour
while the doc catches up.

### Pre-flight findings (verified on the branch base, 2026-09-21)

Constraints found by reading the code that the plan did not record. They do not change the
decisions; they change the shape of T1 and T4.

1. **The image cannot read `pyproject.toml` at runtime.** `Dockerfile` installs with
   `uv sync --frozen --no-dev --no-install-project` and the runtime stage never copies
   `pyproject.toml`, so `importlib.metadata.version("lumatagent")` is unavailable in the container.
   The version must be stamped in at build time (build ARG → ENV or a stamped file).
2. **The commit SHA cannot be read inside the build.** `.dockerignore` excludes `.git/` and
   `infra/*`, so no build step can resolve `HEAD`; the SHA must arrive as a build ARG.
3. **`docker compose up -d --build` cannot compute the SHA.** The deploy step must export it
   (`GIT_SHA`, and the version alongside it) before invoking compose, and compose must forward it via
   `args: ${...}`. This adds a step to the §2.1 deploy flow in `docs/ops.md` (T3).
4. **One test encodes the old constant:** `tests/integration/test_health.py:18` asserts
   `body["version"] == "0.1.0"`. It is the only consumer of the `/health` body shape: the nginx
   healthcheck only checks status 200, `infra/monitor.sh` never reads the version, and the SPA does
   not display it. Historical smoke records (`docs/ops.md` §2.1.1, `docs/hardening.md:226`) stay as
   they are — they are evidence of what the endpoint returned at the time, not live documentation.
5. **CalVer vs PEP 440:** `2026.09.2` normalises to `2026.9.2`. Decide whether `/health` reports the
   tag form or the normalised one, so the report and the tag read the same to a human.
6. **T4 cannot reuse `infra/test-db.sh`:** it requires `infra/.env`, which is gitignored and absent in
   CI. The workflow must set `TEST_DB_PORT=5432`, `TEST_POSTGRES_PASSWORD` and `TEST_DB_PROJECT`, and
   let `tests/_testdb.py` derive the rest. Without an explicit `TEST_DB_PORT` the port is derived
   from the checkout directory name by hash, so CI would get an arbitrary port.
7. **`web/` has its own test stack** (vitest + playwright, node 22.22.2) that the plan does not
   mention. "The suite" in this document means the pytest suite. Running the web tests in CI is new
   scope and is not assumed.
8. **T2 may be the most expensive task in wall-clock terms:** curating the `v2026.09.1` baseline entry
   by hand means summarising ~576 commits / ~120 PRs. Agree the granularity before starting — one
   baseline entry stating what the deployed system is, not 120 bullets.

## Notes for the executor

- The knowledge graph at `graphify-out/` is built at `06768699`, the branch base — **fresh**, no
  rebuild needed. (This note previously warned about `26b463a2`; `main` moved again and the graph was
  rebuilt at the new tip before the branch was cut.)
- `main` moved from `26b463a2` to `5c5f4af2` to `06768699` while this work unit sat scoped. It was
  re-checked before branching: the 33 commits added since `5c5f4af2` touch no file in the authorized
  scope, so the tasks below survived the drift intact. Re-check again before opening the PR.
- The retroactive baseline tag `v2026.09.1` already exists on the remote. Do not recreate it.
