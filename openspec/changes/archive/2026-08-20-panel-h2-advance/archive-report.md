# Archive Report: Panel H2/H4 UI Advance (Inbox + Chat)

**Change**: `2026-08-20-panel-h2-advance`
**Project**: LumatAgent
**Status**: CLOSED
**Date**: 2026-08-20
**Agent**: sdd-archive (`gentle-ai sdd-archive-validate` pass)
**Artifact store**: hybrid (openspec files on disk + engram)

## Executive Summary

Closed the Panel H2/H4 UI Advance change: an additive, Storybook-only delta shipping two new page stories (B1 `InboxThread` for the H2 human inbox, B2 `ChatWithAgent` for the H4 chat-with-agent), a state/assignee/filter upgrade to `ConversationsList`, and a correctness fix to the shipped mock domain (`"open"` → `bot|human|closed`). Implementation is 100% (11/11 SDD tasks), verification PASS (native `sdd-verify-validate` valid:true, verdict pass, 6/6 requirements, 12/12 scenarios, 209 tests passed / 36 files, `npx tsc -b` and `npm run build-storybook` green), both native RDD reviews approved with receipts. Delta specs synced to main specs (`openspec/specs/panel-h2-advance/` created; `R-PRD-PG-14` merged into `openspec/specs/panel-design-system/spec.md`). Change folder moved to `openspec/changes/archive/2026-08-20-panel-h2-advance/`. Delivery via stacked chain: PR #30 (B1→main) and PR #31 (B2→B1), both open, merge in order.

## Final-State Authority

The following facts describe the change AT CLOSE (highest-ranked sources):
- **Native review authority**: `reviewGate` record in structured status confirms both receipts approved (see Review Receipts below).
- **Persisted tasks artifact** (`openspec/changes/2026-08-20-panel-h2-advance/tasks.md`): 11/11 implementation tasks marked `[x]` (T1.1–T1.8 B1 + T2.1–T2.3 B2) plus both lifecycle gates `[x]` (bounded review + graphify archive gate). No stale unchecked implementation tasks.
- **Explicit final-state facts (orchestrator launch prompt)**: R3-001 fix (bubble row alignment) landed in B2 commit be82f08b; cumulative test count 209 (36 files) after the fix; archive graph refresh complete.
- **`verify-report.md`** (intermediate snapshot, valid for verification time): verdict pass, 209 passed, tsc exit 0, build-storybook green.

Per Final-State Authority, no stale `apply-progress`/`verify-report` pending claims are echoed as current facts; the only intermediate claims that mattered (task completion, gate outcomes) are independently confirmed by the persisted tasks artifact and native review receipts.

## Per-Capability Delta Sync

| Capability | Status in main specs | Action | Requirements added |
|------------|----------------------|--------|--------------------|
| `panel-h2-advance` | Did not exist | **Created** `openspec/specs/panel-h2-advance/spec.md` | R-PRD-PG-8 (Inbox List), R-PRD-PG-9 (Inbox Thread Composer & State Controls), R-PRD-PG-10 (24-Hour Reply Window), R-PRD-PG-11 (Chat With Agent Page), R-PRD-PG-12 (Dedicated Chat & Assignee Mock Shapes), R-PRD-PG-13 (Verification Gates & Boundary Guards) |
| `panel-design-system` | Exists | **Updated** — appended R-PRD-PG-14 to `openspec/specs/panel-design-system/spec.md` (added-only, non-destructive) | R-PRD-PG-14 (Conversation State Domain) |

- `panel-h2-advance` main spec copied byte-identical from the delta via shell `cp`→`diff -r`→`mv` (empty diff).
- `R-PRD-PG-14` merged into the main `panel-design-system` spec by appending the full requirement + both scenarios. Verified it appears exactly once (no duplication) and no other requirement was touched. No MODIFIED/REMOVED/RENAMED deltas existed, so no destructive merge — no warning required per `openspec/config.yaml` archive rule.
- Pre-existing requirements in `panel-design-system` (DS-TKN-*, DS-TOKENS-*, DS-STORY-*, DS-VER-*, R-PRD-PG-1..7) preserved unchanged.

## Verification Summary (Final)

- Native validator: `gentle-ai sdd-verify-validate` → `valid: true`, verdict **pass**, `blockers: 0`, `critical_findings: 0`.
- Requirements: **6/6 compliant**; scenarios: **12/12 compliant** (B1 10 + B2 5 scoped; PG-12 "no open state" covered by B1 `conversations.test.ts`).
- Tests: **209 passed (36 files)** — `cd web && npm test` exit 0, hash `sha256:d0747487526a6883f8b619377c9a1c9c4be9041ed6fd475e95f6a974bdabe014`.
- Typecheck: `cd web && npx tsc -b` exit 0.
- Build: `cd web && npm run build-storybook` exit 0, hash `sha256:25fcf91bc2ee26bc9a2541a0b8a2bcd9d8ac248e8467467f773e08e9bbe6daf0`; index includes `ChatWithAgent.stories-D09N_WZe.js` (+ InboxThread, ConversationsList from B1).
- Warnings: pre-existing B1 `users.test.ts:9` redundant tautology (not introduced by B2, informational). No CRITICAL issues; nothing blocks archive.
- R3-001 fix (bubble row alignment) was applied in B2 commit `be82f08b`; the cumulative 209/36 counts above reflect the post-fix final state.

## TDD Compliance (B2)

4/4 RED-GREEN cycles documented and cross-validated by focused re-execution (9/9 B2 tests: 6 unit + 3 RTL); all B2 task files are NEW (no modified-file safety-net exposure). Assertions verified real behavior (shape fidelity, role/status domain, bubble/avatar counts, composer enable/disable). Full change TDD compliant.

## Review Receipts (Native RDD — approved)

| Batch | Receipt | Receipt sha256 | Gate | Result |
|-------|---------|----------------|------|--------|
| B1 Inbox | `review-93bbd5951158648b` | `bfd96de3...` | pre-pr | ALLOW vs main |
| B2 Chat | `review-b900c31714b5ba60` | `11e943f...` | pre-pr | ALLOW vs `origin/feat/panel-h2-advance-b1` (stacked) |

`reviewGate` present with `result: allow` in structured status — a discovered receipt that governs this candidate and validates it. Both receipts match the final candidate tree, paths digest, policy, ledger, fix delta, current independent verification evidence, mode counters, and base relationship. No present non-`allow` value; archive proceeds under receipt-validated policy.

## Delivery State

- **Strategy**: auto-chain, chain strategy = stacked-to-main.
- **B1** = `feat/panel-h2-advance-b1` → PR **#30** (target **main**) — **OPEN**.
- **B2** = `feat/panel-h2-advance-b2` (HEAD `be82f08b`, base B1) → PR **#31** (target B1) — **OPEN**.
- Chain merges in order: merge B1 first, then B2; each slice < 400 changed lines (B1 ~330, B2 ~280), aggregate ~610, medium budget risk as forecast.

## Risks / Notes

1. **Archive destination naming**: change name already carries the ISO date prefix (`2026-08-20-panel-h2-advance`), so the archive folder is `openspec/changes/archive/2026-08-20-panel-h2-advance` (no doubled `YYYY-MM-DD-` prefix). Consistent with repo's existing date-prefixed archive folders.
2. **Backlog (out of scope, unchanged)**: backend `GET /conversations` list-endpoint gap remains tracked separately (flagged at apply; not part of this Storybook-only change).
3. **Assignee is design mock** (R2): no backend `Conversation` field; H2 adds the real field later.
4. **24h window is UI-only today** (S3/template-only): real enforcement lands with H2 backend.
5. **`verify-report.md`** was untracked at archive time and is included in the archived folder byte-identically; orchestrator commits the archive move.
6. **B1 WARNING** `users.test.ts:9` tautology is a pre-existing, non-blocking quality note — not introduced by this change's B2.

## Archive Audit Trail

- Source-of-truth specs synced: `openspec/specs/panel-h2-advance/spec.md` (created), `openspec/specs/panel-design-system/spec.md` (R-PRD-PG-14 appended).
- Change folder moved to archive: `openspec/changes/archive/2026-08-20-panel-h2-advance/`.
- ENGRAM observations read for traceability:
  - `sdd/2026-08-20-panel-h2-advance/apply-progress` (#1711)
  - `sdd/2026-08-20-panel-h2-advance/verify-report` (#1732)

## SDD Cycle Status

Complete. Planned, implemented (11/11 tasks), verified (6 req / 12 scenarios PASS), natively reviewed (both receipts ALLOW), and archived. Ready for the next change.
