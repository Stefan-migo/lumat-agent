# Archive Report — Panel Design System — Foundation (LumatAgent)

> Change: `panel-design-system` · Project: LumatAgent (client: Lumat, gasfitería, Chile)
> Phase: sdd-archive · Date: 2026-08-19 · Status: **ARCHIVED** — complete
> Artifact store: openspec (file-based). This report is the terminal record of the SDD cycle for this change.

## Summary

The `panel-design-system` foundation slice is fully implemented, verified, and archived. This slice delivered the design-system **token foundation**, a **Tokens reference page** in Storybook, and **doc-level story upgrades** for all 10 existing story files — completing the "FUNDACIÓN PRIMERO" objective for the Lumat agent-facing admin panel (`web/`, package `lumat-panel`). Domain patterns, dark mode, dynamic theming, new components, component code changes, and the backend were explicit non-goals and remain out of scope.

The spec delta `panel-design-system` (DS-TKN-1..9, DS-TOKENS-1..2, DS-STORY-1..7, DS-VER-1) was synced as a new capability into the source-of-truth spec store. The entire change folder was moved to the archive per the OpenSpec archive convention.

## Deliverables (final state — what shipped)

Delivered as two chained PRs, stacked to main, per the auto-chain strategy:

| Batch | PR | Commit | Content |
|---|---|---|---|
| B9 | #17 | `c1854fdf` | Token foundation: 25 new tokens in `tokens.css` (type scale `xs/base/xl/3xl`, `--leading-*`, `--weight-*`, focus-ring set, motion scale, breakpoints, `--shadow-3`); drift-guard extension in `tokens.test.ts`; Storybook autodocs (`tags: ['autodocs']`) + `--bp-*` viewport presets in `preview.ts` (diff +97/−0, web-only) |
| B10 | #18 | `29c7fc63` | Tokens page (`Tokens.stories.tsx` parsing `tokens.css?raw`), shared `Matrix` helper (`helpers/matrix.tsx`), and doc-level upgrades for all 10 story files (13 web files, +628/−10 authored) |
| Post-verify fix | (PR #19, pending merge on branch `fix/panel-design-system-tokens-grouping`) | `02e38599` | Corrected the semantic-token grouping regex to `^--(?:danger|success|warning)(?:$|-)` so the bare tokens `--danger`/`--success`/`--warning` group to **Color (semantic)** instead of "Other" |

Mid-cycle commits baked into the merged main state: `51d767f9` (lifecycle gates + verify report), `1f2da975` (graphify refresh — knowledge graph re-balanced for the web/ area, 2126 nodes).

## Verification Outcome

**Final state: PASS.** The verify report (`verify-report.md`, verdict `pass_with_warnings`, `critical_findings: 0`, `blockers: 0`) recorded at HEAD `567464f5`:

- **19/19 requirements**, **28/28 scenarios** passed.
- `cd web && npm test` → **14 files / 48 tests passed** — token drift-guard (pinned palette, `tokens.ts` mirror equality, no-hard-coded-hex walk, new-group spot-checks), 3 Tokens-page grouping specs, all component tests.
- `cd web && npx tsc --noEmit -p tsconfig.json` → **clean (exit 0)**.
- `cd web && npm run build-storybook` → **green (10.82s)**, 33 story + 11 docs entries; Tokens page present with token values inlined in the static bundle (DS-TOKENS-2).
- Diff review: web/-only implementation plus openspec artifacts; no `app/`, `db/`, `infra/`, `src/components/**`, `tokens.ts`, or `main.ts` changes.

The verify report carried **2 WARNINGs**. Per the Final-State Authority hierarchy, their resolution at close is:

1. **WARNING #1 — Tokens-page grouping vs design D8 (ledger mismatch)** → **RESOLVED post-verify.** The fix landed in commit `02e38599` (branch `fix/panel-design-system-tokens-grouping`, PR #19 pending merge at archive time). The regex `^--(?:danger|success|warning)(?:$|-)` now routes the bare semantic tokens to "Color (semantic)" while still rejecting lookalikes (`--dangerous`, `--successor`, `--border-radius` → "Other"). Tests updated; `npm test` 48/48 and `tsc` clean re-confirmed on the fix branch. tasks.md now documents this in its **Post-Verify Fix** section, so the ledger is factually accurate (Color (semantic) 9, Other 0, 67 tokens total).
2. **WARNING #2 — tracked graphify cache file in B10 diff** → **INFO tooling noise, accepted.** `graphify-out/cache/stat-index.json` (gitignored dir, previously tracked) changed by 1 mtime line in commit `29c7fc63`. Not code; the graphify refresh (`1f2da975`) is complete. Recommend untracking `graphify-out/cache/` at the next meta cleanup but nothing blocks this archive.

Additionally, the verify report's **PR-boundary note** (B10's 628-line authored diff shipped as one PR rather than the conditional 2a/2b split) is a process observation — scope is correct and all gates were green; accepted as-is.

## Post-Verify Fix Detail (final state)

- **Location**: `web/src/stories/tokens/Tokens.stories.tsx` (rule line) + `web/src/stories/tokens/Tokens.stories.test.ts` (assertions) + tasks.md ledger note (Post-Verify Fix section).
- **Fix**: rule changed from `^--(?:danger|success|warning)-` (trailing hyphen required) to `^--(?:danger|success|warning)(?:$|-)` (anchored to end-of-name or hyphen), so bare semantic tokens group correctly while lookalike tokens still fall to "Other" (preserving the R3-001 review-correction intent).
- **Evidence**: `node` parse of `tokens.css` with the shipped rule list → Color (semantic) 9, Other 0, total 67 (matches the ledger). `npm test` 48/48; `npx tsc --noEmit` clean.
- **Status**: ledger factually accurate; no remaining WARNING-1-type drift.

## Graphify Refresh

Lifecycle gate **G3** (archive-mandated `graphify . --update`) is satisfied. Commit `1f2da975` persisted the refreshed knowledge graph (2126 nodes), re-balancing the previously backend-dominated web/ area into proper web communities (43, 47, 54, 59, 60, 62, 63, 65, 66, 71, 72, 99). B10 edges (`*.stories.tsx --imports_from--> helpers/matrix`, `Tokens.stories.tsx --imports_from--> tokens.css?raw`) are materialized. Known graph gap persists: CSS import AST nodes are not extracted (preview→tokens.css edge not materialized). No further graphify run needed at archive — the graph is current at HEAD.

## Task Completion

All implementation and lifecycle tasks were checked `- [x]` before archive:

- **Implementation (8/8)**: T9.1, T9.2, T9.3, T10.1, T10.2, T10.3, T10.4, T10.5
- **Parent lifecycle gates (3/3)**: bounded review B9 (PR #17), bounded review B10 (PR #18), archive graphify update

Grep of the persisted `tasks.md` for unchecked `- [ ]` lines returned **0 matches**. No stale unchecked tasks — the audit trail reflects the final state. This is output of the Task Completion Gate: no archival of completed work with stale checkbox state occurred.

## Spec Sync

The delta spec `openspec/changes/panel-design-system/specs/panel-design-system/spec.md` (new capability `panel-design-system`, RFC 2119 wording preserved: DS-TKN-1..9, DS-TOKENS-1..2, DS-STORY-1..7, DS-VER-1) was synced as the **new main capability spec** at `openspec/specs/panel-design-system/spec.md` via a **mechanical byte-identical copy** (no model Read/Write passthrough). The `openspec/specs/` store had no prior `panel-design-system` capability, so the delta is the full spec (there was nothing to merge). Verbatim `diff -r` between the change-folder delta and the live spec is empty (byte-identical).

## Archive Move

- **From**: `openspec/changes/panel-design-system/`
- **To**: `openspec/changes/archive/2026-08-19-panel-design-system/` (ISO date prefix per the OpenSpec archive convention, matching e.g. `2026-07-20-lumat-propuesta-final`)
- **Method**: mechanical `git mv` (files were git-tracked); pre-move recursive snapshot taken, then verified with `diff -r` — **empty (byte-identical)**. The active `openspec/changes/` directory no longer contains this change.
- **Preserved artifacts**: proposal.md, design.md, specs/panel-design-system/spec.md, tasks.md, apply-progress.md, verify-report.md + this additive archive-report.md.

## Action Context / Config

- `actionContext.mode: repo-local`, `allowedEditRoots: ["/home/stefan/repos/lumat-agent"]` — all operations stayed inside the allowed root.
- `openspec/config.yaml` does **not** track active changes (schema `spec-driven`; no active-changes key; `rules.archive` only says "Warn before merging destructive deltas" — this sync was a non-destructive new-capability add, no destructive delta warning applicable). No config.yaml edit required.

## Intentional-With-Warnings Declaration

This archive is **not** a partial archive and requires no stale-checkbox reconciliation. It is recorded as a **complete archive** with two accepted non-blocking verify WARNINGs that were resolved (WARNING #1 fixed post-verify on an approved lineage branch; WARNING #2 accepted INFO tooling noise). No intentional-with-warnings partial-archive override applies.

## Learned

- The pre-verify `/^--(?:danger|success|warning)-/` regex required a trailing hyphen, which silently mis-routed the bare semantic tokens (`--danger`/`--success`/`--warning`) to the "Other" group — a real token can be invisibly swallowed by an over-strict grouping rule unless the bare-name case is handled. The fix `(?:$|-)` anchor is the correct general form.
- The verify report was written at HEAD `567464f5`; the final main state additionally includes `51d767f9` (gates) and `1f2da975` (graphify), and the post-verify fix on branch `fix/panel-design-system-tokens-grouping` (PR #19 pending). Anyone reading the verify snapshot must cross-reference these later commits for the true close state.
