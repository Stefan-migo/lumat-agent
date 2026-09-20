# ODD: versioning-release-process

**Branch**: `odd/versioning-release-process`
**Worktree**: `../lumat-agent-odd-versioning-release-process`
**Base**: `5c5f4af2`
**Seeded from**: `.rapsodia-code/sessions/ready-for-odd/2026-09-20-versionado-release-trazabilidad/report.md`
**Status**: scoped — not started

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

- [ ] **T1 — Version source of truth + `/health`.** Make one value flow from a single source into the
      image and out through `/health`, including the commit. Update `app/config.py`, `app/main.py`,
      `Dockerfile`, `infra/docker-compose.prod.yml`. Tests assert `/health` reports the injected
      version rather than a constant.
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

- [ ] Worktree created and provisioned; `.opencode/tools/package-lock.json` removed.
- [ ] Graph Check before editing.
- [ ] T1–T5.

## Notes for the executor

- The knowledge graph was built at `26b463a2` and is **stale** relative to this base (`5c5f4af2`).
  Refresh or rebuild it before Step 1 of the Graph Check.
- `main` moves in parallel: it advanced from `26b463a2` to `5c5f4af2` while this session ran. Pinning
  the base at scope time does not pin it at implementation time — re-check before branching.
- The retroactive baseline tag `v2026.09.1` already exists on the remote. Do not recreate it.
