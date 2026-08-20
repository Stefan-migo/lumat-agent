# Archive Report: Storybook Redesign — Full Design-System Adoption

**Change**: `2026-08-20-storybook-redesign`
**Project**: LumatAgent
**Status**: CLOSED
**Date**: 2026-08-20
**Agent**: sdd-archive (`gentle-ai sdd-archive-validate` pass)
**Artifact store**: hybrid (openspec files on disk + engram)

## Executive Summary

Closed the Storybook Redesign change: full design-system adoption across all Storybook surfaces. The `primitives.css` focus/motion token swaps landed in production primitives (S1), the shared PageFrame + StateMessage frame and Spanish label maps were promoted into `_shared/` (S2), and all 9 old page stories (ClientesList, CasesList, ConversationsList, InboxThread, ConversationThread, ClientFicha, ChatWithAgent, Login, KbList, Settings) were restyled onto the shared frame with a complete domain-state matrix and neutral Chilean Spanish copy (S3–S6). Dashboard remained the regression sentinel. Implementation is 100% (16/16 SDD tasks), verification PASS (verdict pass, blockers 0, critical_findings 0, requirements 10/10, scenarios 12/12, 277/277 tests / 38 files, `npx tsc --noEmit` exit 0, `npm run build-storybook` exit 0). Delta specs synced to the main spec (`openspec/specs/panel-design-system/spec.md`): 10 ADDED requirements (DS-UI-LABELS → DS-UI-STORY) appended, all 27 pre-existing requirement IDs preserved. Change folder moved to `openspec/changes/archive/2026-08-20-storybook-redesign/`. Delivered as a 6-slice stacked-to-main chain: PRs #32–#37 all OPEN against main (merge remains user-driven). All non-goals respected: no AppShell wiring, no helper promotion to `src/components`, no new deps, no dark mode, no Jinja/backend changes.

## Final-State Authority

The following facts describe the change AT CLOSE (highest-ranked sources):
- **Persisted tasks artifact** (`openspec/changes/.../tasks.md`): 16/16 implementation tasks (1.1–7.2) marked `[x]` — no stale unchecked implementation tasks. Verified on disk and confirmed by the launch prompt.
- **Explicit final-state facts (orchestrator launch prompt)**: verify RE-RAN after corrective work and PASSED — verdict `pass`, `blockers: 0`, `critical_findings: 0`, `requirements: 10/10`, `scenarios: 12/12`, `test_command: cd web && npm test`, `test_exit_code: 0`, `evidence_revision: sha256:a36f76c2…`. Two corrective commits landed after the last `apply-progress`/`verify-report` snapshot: `6d2e69df` (`fix(web): replace voseo copy in KB disable confirmation`) and `e5489c0e` (`fix(web): neutralize residual voseo in KB and settings banners`), both on branch `feat/storybook-redesign-s6`.
- **Native review authority**: `reviewGate` is structurally ABSENT — no review receipt artifacts exist for this candidate (`state.yaml` absent, no `review/` topic, no receipt in git history). Per the Native Review Receipt Gate, absence is not a defect: archive proceeds under ordinary repository policy; no present non-`allow` value blocks.
- **`verify-report.md`** (intermediate snapshot, valid for verification time after re-verification): verdict pass, 277/277 passed, tsc exit 0, build-storybook exit 0, requirements 10/10, scenarios 12/12. The prior CRITICAL (4 residual voseo strings in KbList/Settings banners) is resolved by commit `e5489c0e`. WARNINGs (manual viewport verification DS-UI-STORY; cross-slice StateBadge sequencing note) and SUGGESTIONs remain as non-blocking findings.
- **`apply-progress.md`** (intermediate snapshots per slice S1–S6): cumulative 209 → 241 → 248 → 257 → 266 → 277 tests across the chain. These are history; the final 277/277 is confirmed by verify-report + the launch prompt.
- **PR chain (repo evidence)**: PRs #32 (S1) → #37 (S6) all OPEN against `main`; head branch `feat/storybook-redesign-s6`.

Per Final-State Authority, no stale `apply-progress` / `verify-report` pending claims are echoed as current facts; the final-state facts above are independently confirmed by the persisted tasks artifact, the launch prompt, the re-run verify-report, and git history.

## Per-Capability Delta Sync

| Capability | Status in main specs | Action | Requirements added |
|------------|----------------------|--------|--------------------|
| `panel-design-system` | Exists | **Updated** — appended 10 ADDED requirements (DS-UI-LABELS → DS-UI-STORY) to `openspec/specs/panel-design-system/spec.md` | DS-UI-LABELS, DS-UI-LINK, DS-UI-FRAME, DS-UI-STATES, DS-UI-PRIMS, DS-UI-LOGIN, DS-UI-TABLES, DS-UI-TONEFIX, DS-UI-COPY, DS-UI-STORY (10 requirements, 12 scenarios) |

- The delta spec `openspec/changes/.../specs/panel-design-system/spec.md` is **pure-ADDED** (no MODIFIED/REMOVED/RENAMED sections → no destructive merge; no warning required per `openspec/config.yaml` archive rule).
- All 27 pre-existing requirement IDs in `panel-design-system` (DS-TKN-*, DS-TOKENS-*, DS-STORY-*, DS-VER-*, R-PRD-PG-1..14) preserved unchanged; verified each appears exactly once (except the pre-existing R-PRD-PG-1 duplication already in the base).
- Verified the 10 new requirement blocks each appear exactly twice in the repo (once in the archived delta, once in the main spec) and all 12 new scenarios present. Main spec: 27 requirements baseline → 37 total; 45 scenarios baseline → 57 total.

## Verification Summary (Final)

- Verdict: **pass**; `blockers: 0`; `critical_findings: 0`.
- Requirements: **10/10 compliant**; scenarios: **12/12 compliant** (DS-UI-COPY now COMPLIANT after corrective work; DS-UI-STORY remains PARTIAL with non-blocking, non-spec-failing viewport evidence per verify-report).
- Tests: **277 passed (38 files)** — `cd web && npm test` exit 0, `test_output_hash sha256:77fe81f1…`.
- Typecheck: `cd web && npx tsc --noEmit` exit 0.
- Build: `cd web && npm run build-storybook` exit 0 (`build_output_hash sha256:8b882789…`).
- Evidence revision: `sha256:a36f76c20ad8246766ad9e402bc442a77482c0720c7d0c77bac5604b64212729`.
- Corrective commits after the last intermediate snapshot: `6d2e69df` + `e5489c0e` (residual voseo in KB/Settings banners neutralized). No CRITICAL issues at close — archive-ready.

## TDD Compliance

Strict TDD end-to-end per `verify-report.md`: 16/16 TDD checks passed. Every non-assert-nothing task has RED/GREEN evidence in the per-slice apply-progress tables; triangulation exercised real values across states (activo+bloqueado, escalado+abierto, activo+deshabilitado, bot/human/closed); safety nets held per slice (209/209 baseline → 38/38 touched files; Dashboard sentinel 9/9). Banned CSS-class assertions replaced with semantic label/tone/role asserts (S4 rewrote the `style.background` human-row assertion to an approved-label warning-badge assert). Coverage tool not detected → not measured (not a failure).

## Deliverables

- Main spec synced: `openspec/specs/panel-design-system/spec.md` (+10 requirements DS-UI-LABELS..DS-UI-STORY).
- Change archived: `openspec/changes/archive/2026-08-20-storybook-redesign/` (proposal, specs, design, tasks, apply-progress, exploration, verify-report, archive-report).
- Engram archive report saved: `sdd/2026-08-20-storybook-redesign/archive-report` (project `lumat-agent`, type `architecture`).

## Delivery State

- **Strategy**: auto-chain, chain strategy = stacked-to-main (each PR targets `main`).
- PRs #32 → #37 (S1 → S6) all **OPEN** against `main`; head branch `feat/storybook-redesign-s6`. The change state is recorded at close; merging the chain remains user-driven (merge in order #32 → #37).
- Commit(s) for archive/spec-sync on branch `feat/storybook-redesign-s6`.

## Risks / Notes

1. **DS-UI-STORY viewport verification is not automated** (WARNING at verify): 390/640/768/1024/1280 verified via rendered Storybook build, not an automated viewport assertion. Shared PageFrame grid makes clipping unlikely; a machine-enforced viewport gate is a follow-up.
2. **Cross-slice sequencing dependency** (WARNING, informational): S2's StatusBadge label change immediately invalidated ConversationsList badge assertions; the apply phase patched them. A future re-order of StatusBadge work would break the gate.
3. **SUGGESTIONs carried forward**: (a) add an automated voseo/English guard scan so DS-UI-COPY becomes machine-enforced; (b) `tabularNum` signature deviates (standalone `tabularNum(cell)`) — functionally equivalent, documented; (c) `StatusBadge` (production primitives) imports `conversationLabel` from the story app layer — an inversion a future move of `toneMaps` to `web/src/` would resolve.
4. **Spec compliance nuance in verify**: DS-UI-STORY rendered PARTIAL (not PASS/FAIL) for viewport evidence — non-blocking and non-spec-failing; overall verdict remains PASS.
5. **`reviewGate` structurally absent**: no RDD receipt exists for this candidate; archive proceeded under ordinary repository policy (no present non-`allow` value).

## Next Steps

- Merge the PR chain #32 → #37 in order to `main` (user-driven).
- Backlog (out of scope, unchanged): AppShell real-page wiring (production still renders placeholders); helper promotion to `web/src/components/`; dark mode; backend/API changes; Jinja template migration.
- Optional follow-up: automated viewport + voseo guard scans to machine-enforce DS-UI-STORY / DS-UI-COPY.

## Archive Audit Trail

- Source-of-truth spec synced: `openspec/specs/panel-design-system/spec.md` (10 ADDED requirements appended).
- Change folder moved to archive: `openspec/changes/archive/2026-08-20-storybook-redesign/` (verbatim `diff -r` readback = empty; archive-report.md is additive-only and excluded).
- ENGRAM observations read for traceability:
  - `sdd/2026-08-20-storybook-redesign/explore` (#1754)
  - `sdd/2026-08-20-storybook-redesign/proposal` (#1758)
  - `sdd/2026-08-20-storybook-redesign/spec` (#1760)
  - `sdd/2026-08-20-storybook-redesign/tasks` (#1765)
  - `sdd/2026-08-20-storybook-redesign/apply-progress` (#1772)
  - `sdd/2026-08-20-storybook-redesign/verify-report` (#1792)

## SDD Cycle Status

Complete. Planned, designed, speced, implemented (16/16 tasks across 6 slices), verified (10 req / 12 scenarios PASS, 277/277 tests, tsc 0, build-storybook 0), and archived. Ready for the next change.
