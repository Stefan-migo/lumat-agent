# Archive Report: Design System "Calma Operacional" — Slice-1 Catalog Adaptation

**Change**: `2026-08-24-design-system-calma-operacional`
**Project**: LumatAgent
**Status**: CLOSED
**Date**: 2026-08-24
**Agent**: sdd-archive
**Artifact store**: hybrid (openspec files on disk + engram)

## Executive Summary

Closed the Design System "Calma Operacional" change — Slice-1 of the CortexDesign DC-004 Corporate catalog adaptation for the Lumat panel (`web/`, package `lumat-panel`). Additive, zero-color-change delta: a 17-slot `--corp-*` token-alias layer in `tokens.css` mapping the catalog contract onto frozen Lumat tokens (never raw hex — hex guard extended), re-targeting existing same-name primitives (Button, Badge, Card, Input/Select/Textarea, StatusBadge→Badge, StateMessage→Alert) to consume that contract, plus micro-changes (tabular-nums for data roles; `DESIGN_SYSTEM.md` canvas `--bg` corrected to `#F1F1E8`). Implementation is 100% (16/16 SDD tasks), verification PASS WITH WARNINGS (native `sdd-verify-validate`, verdict pass_with_warnings, 15/15 requirements, 26/26 scenarios, 300/300 tests / 39 files, `build-storybook` exit 0), native RDD review APPROVED (receipt `review-651ea11f6609513b`, 4 advisory non-blocking findings). Delta specs synced to main specs (`openspec/specs/corp-token-aliases/` and `openspec/specs/corp-primitives/` created; panel-design-system delta DS-TKN-10/11/12 ADDED + DS-TKN-1 MODIFIED merged into `openspec/specs/panel-design-system/spec.md`). Change folder moved to `openspec/changes/archive/2026-08-24-design-system-calma-operacional/`.

## Final-State Authority

The following facts describe the change AT CLOSE (highest-ranked sources):
- **Native review authority**: structured status exposes `reviewGate.result: allow` with reason "approved receipt exactly matches authoritative native state and the current repository" — native RDD receipt `review-651ea11f6609513b` (state approved, delivery gate `ALLOW`). 4 advisory findings (all non-blocking): R4-001 WARNING `PanelShell.tsx:665-737`, R4-002 WARNING `PanelShell.tsx:548-552`, R4-003 SUGGESTION `web/.cortex/validate.js:60-66`, R4-004 WARNING `web/.storybook/component-catalog.json:2244-2245`. No correction opened. Disposition informational; carried into Known Follow-ups below.
- **Persisted tasks artifact** (`openspec/changes/2026-08-24-design-system-calma-operacional/tasks.md`): 16/16 implementation tasks marked `[x]` (T1.1–T1.3 B1 · T2.1–T2.5 B2 · T3.1–T3.2 B3 · T4.1–T4.6 B4). No stale unchecked implementation tasks.
- **Explicit final-state facts (orchestrator launch prompt)**: implementation commits `aab6840b` (alias layer + hex guard), `47691eff` (primitives re-target), `0c321e44` (tabular-nums + DESIGN_SYSTEM `--bg` fix), `8a4fa8fc` (tests), `5333c743` (apply-progress), `ed1f43a2` (accounting correction). Verification `cd web && npm test` → 300/300 (39 files); `npm run build-storybook` → exit 0; 26/26 scenarios; verdict PASS WITH WARNINGS.
- **`verify-report.md`** (intermediate snapshot, valid for verification time): verdict pass_with_warnings, 300/300 tests, `build-storybook` exit 0, evidence_revision `sha256:f949049da8e4ab24aa5c62ab9a19c2028c7d5979702f72105211c6b7e1b16a20`.

Per Final-State Authority, no stale `apply-progress`/`verify-report` pending claims are echoed as current facts. The only verification WARNING (pre-existing `npx tsc -b` failure in `AppShell.test.tsx`) is confirmed by the orchestrator handoff as remaining at close, out of scope (uncommitted v1-shell working-tree changes, not in any slice commit), and correctly recorded, not fixed.

## Per-Capability Delta Sync

| Capability | Status in main specs | Action | Requirements added |
|------------|----------------------|--------|--------------------|
| `corp-token-aliases` | Did not exist | **Created** `openspec/specs/corp-token-aliases/spec.md` | CST-ALIAS-1 (Slots Map to Existing Tokens), CST-ALIAS-2 (Additive-Only Alias Evolution), CST-ALIAS-3 (Frozen Alias Principle), CST-ALIAS-4 (Size-Slot Warning Fallback), CST-ALIAS-5 (Tabular Numerals for Data Values) |
| `corp-primitives` | Did not exist | **Created** `openspec/specs/corp-primitives/spec.md` | CST-PRIM-1 (Catalog Contract Consumption), CST-PRIM-2 (WCAG AA Contrast), CST-PRIM-3 (Control Height/Touch Target), CST-PRIM-4 (Complete States First-Class), CST-PRIM-5 (StatusBadge/StateMessage Mapping), CST-PRIM-6 (No Decorative Animation) |
| `panel-design-system` | Exists | **Updated** — DS-TKN-10/11/12 appended (added-only), DS-TKN-1 replaced with the MODIFIED requirement (now covers the `--corp-*` alias layer) | DS-TKN-10 (Aliases Stay Inside the Hex Guard), DS-TKN-11 (Tabular Numerals for Data Values), DS-TKN-12 (Corrected Canvas Background Documentation) |

- `corp-token-aliases` and `corp-primitives` main specs were copied byte-identical from their deltas via shell `cp`→`diff -r`→`mv` (both empty diffs, exit 0). These deltas are full specs (purpose + `## Requirements`, no ADDED/MODIFIED/REMOVED/RENAMED sections) and no main spec existed, so the delta is the canonical spec per OpenSpec archive semantics.
- `panel-design-system` delta merge: **ADDED** DS-TKN-10/11/12 appended in a new dated section (`## Calma Operacional (corp-*) — added 2026-08-24`) per repo's dated-section convention; **MODIFIED** DS-TKN-1 block replaced in place (added the `Alias layer is single-source` scenario, preserved the existing `Components consume tokens` scenario). No REMOVED/RENAMED deltas existed.
- Verified the merged main `panel-design-system` spec: each of DS-TKN-1/10/11/12 appears exactly once (no duplication); all 37 pre-existing requirement headings (DS-TKN-2..9, DS-TOKENS-*, DS-STORY-*, DS-VER-1, R-PRD-PG-*, DS-UI-*) preserved unchanged. No destructive merge, no archive warning required per `openspec/config.yaml` archive rule.

## Verification Summary (Final)

- Native validator: `gentle-ai sdd-verify-validate` → `valid: true`, verdict **PASS WITH WARNINGS**, `blockers: 0`, `critical_findings: 0`.
- Requirements: **15/15 compliant**; scenarios: **26/26 compliant** (CST-ALIAS-* 8, CST-PRIM-* 12, DS-TKN-* 6 in the verify matrix).
- Tests: **300/300 passed (39 files)** — `cd web && npm test` exit 0, hash `sha256:4127082618bbd3bb3e5f7e4a6e7f985db3e868711d18cdca69c1b451b990cc02`.
- Build: `cd web && npm run build-storybook` exit 0, hash `sha256:37bb2935b88042311ae9789a471c7497499cdb816cb09f5585e25b72341cf5d6`.
- Typecheck: `cd web && npx tsc -b` exit 1 — the ONLY 2 errors are pre-existing, provably out-of-scope (uncommitted v1-shell `AppShell.test.tsx`: TS6133:110 + TS2345:118), NOT in any slice commit (`git diff aab6840b~1..ed1f43a2` contains zero v1-shell files). All slice-1 files tsc-clean. Recorded as WARNING, not fixed.
- Warnings at close: the pre-existing `tsc -b` failure above, and a pre-existing Storybook >500kB chunk-size warning (not introduced by slice-1). Zero CRITICAL findings; nothing blocks archive.

## TDD Compliance

Strict TDD documented in apply-progress and cross-validated by re-execution in verify: 16/16 tasks have test coverage (CSS-only tasks 2.1–2.3 carried by the hex-guard walk + explicit B4 scans per the assertion-quality rules); RED confirmed (test-first for alias guard, tabular-nums, StateMessage pairing, touch targets); GREEN confirmed by 300/300 re-execution; triangulation adequate; safety net 287→293→300 shown for every modified file. Assertion-quality audit: all B4/B1 slice assertions verify real behavior — 0 CRITICAL, 0 WARNING introduced by this change.

## Review Outcome (Native RDD — approved)

| Field | Value |
|-------|-------|
| Lineage | `review-651ea11f6609513b` |
| Review | 4R (risk / resilience / readability / reliability) |
| State | **approved** |
| Gate | `reviewGate.result: allow` in structured status ("approved receipt exactly matches authoritative native state and the current repository") |
| Receipt store | Git common-dir review-transactions store |
| Corrections | None opened |

4 advisory findings, all non-blocking (disposition informational):

| ID | Severity | Location | Disposition |
|----|----------|----------|-------------|
| R4-001 | WARNING | `PanelShell.tsx:665-737` | informational, non-blocking |
| R4-002 | WARNING | `PanelShell.tsx:548-552` | informational, non-blocking |
| R4-003 | SUGGESTION | `web/.cortex/validate.js:60-66` | informational, non-blocking |
| R4-004 | WARNING | `web/.storybook/component-catalog.json:2244-2245` | informational, non-blocking |

Carried into Known Follow-ups below (advisory only; none block archive or require a correction cycle).

## Deviations from Design (recorded, non-blocking)

1. **v1-shell workspace substrate (a)**: `--bg #F1F1E8` + 4 `--*-tint` tokens (`--success/danger/warning/info-tint`) entered slice commit `aab6840b` from the uncommitted `2026-08-20-v1-shell-header-and-bg` working-tree substrate. Kept because slice-1 depends on them (StateMessage D5 tint mapping; DS-TKN-12 executable-wins doc alignment). **v1-shell MUST NOT re-add them** once it lands its own work (they are now part of the slice commits).
2. **`.btn--secondary` border (b)**: uses `--border-strong` (no `--corp-*` alias covers that value; mapping to `--corp-border` would change it). Allowed by CST-PRIM-1 ("references a `--corp-*` slot **or existing token**").
3. **Button loading/empty states deferred (c)**: needs new props + spinner markup with no current consumer — documented first-class-deferred by design (D8, tasks T2.3).
4. **StateMessage inline `<style>` BEM refactor deferred (d)**: minimal Alert mapping is the material D5 deliverable; the full BEM refactor is deferred (budget) — inline style retained.

## Known Follow-ups (chained / open)

- Remaining ~30 Corporate catalog components (Table, Tabs, Dialog, Tooltip, Popover, DropdownMenu, Accordion, Pagination, etc.) are indexed via `web/.cortex/catalog-query.js` for chained slices.
- Optional count-up / fade-content decisions deferred (proposal non-goals).
- `v1-shell` (2026-08-20-v1-shell-header-and-bg) must land its own uncommitted work (AppShell / PanelShell / Dashboard stories) as its own change; must NOT re-add the `--bg`/tint tokens already in slice-1 commits.
- Resolve the pre-existing `AppShell.test.tsx` tsc errors (TS6133 + TS2345) when v1-shell is completed.
- Archive-time stale-checkbox reconciliation: none performed — the persisted tasks artifact already showed 16/16 `[x]`, matching native status `taskProgress.allComplete: true`. No exceptional repair needed.

## Rollback Note

**Additive change — `git revert` is safe.** Reverting the slice-1 commits restores: `tokens.css` without the `--corp-*` alias layer (pre-existing declarations unaffected — CST-ALIAS-2 pinned them byte-identical), `primitives.css` to its prior token-only BEM, and removes the micro-changes (tabular-nums rules, `DESIGN_SYSTEM.md` `--bg` doc correction). No schema, backend, or API change. Caveat: `git revert` of `aab6840b` would also remove the carried `--bg #F1F1E8` + `--*-tint` substrate tokens; those are re-added by the v1-shell change when it lands, per deviation (1).

## Archive Audit Trail

- Source-of-truth specs synced: `openspec/specs/corp-token-aliases/spec.md` (created), `openspec/specs/corp-primitives/spec.md` (created), `openspec/specs/panel-design-system/spec.md` (DS-TKN-10/11/12 appended, DS-TKN-1 modified).
- Change folder moved to archive: `openspec/changes/archive/2026-08-24-design-system-calma-operacional/` (name already carries the ISO date prefix — no doubled `YYYY-MM-DD-` prefix; consistent with the repo's existing date-prefixed archive folders).
- Mechanical copy contract: `corp-token-aliases` and `corp-primitives` specs copied via shell `cp`→`diff -r`→`mv` with empty diffs; archive folder move verified via `diff -r` against a pre-move recursive snapshot (empty diff, exit 0). The `archive-report.md` is additive-only and excluded from that readback.
- ENGRAM: `mem_save` persisted `sdd/2026-08-24-design-system-calma-operacional/archive-report` (this report) for cross-session recovery per the hybrid persistence contract.
- Review gate: `reviewGate.result: allow` — a discovered native receipt governs and validates this candidate; no non-`allow` value present, archive proceeds under receipt-validated policy.

## SDD Cycle Status

Complete. Planned, implemented (16/16 tasks, B1–B4), verified (15 req / 26 scenarios PASS WITH WARNINGS, 300/300 tests, build green), natively reviewed (RDD approved, receipt `review-651ea11f6609513b`, 4 advisory findings), and archived. Ready for the next change.
