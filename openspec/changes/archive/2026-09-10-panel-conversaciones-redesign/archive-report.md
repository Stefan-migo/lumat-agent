# Archive Report: panel-conversaciones-redesign

## Final Status

- **Status:** success with warnings
- **Change:** `panel-conversaciones-redesign`
- **Archived:** 2026-09-10
- **Final implementation HEAD:** `f98fd588` (`main`)
- **Artifact store:** hybrid (OpenSpec plus Engram mirrors)
- **Delivery:** fully implemented and merged through PRs #150, #148, #151, and #152.
- **Verification:** PASS WITH WARNINGS; 8/8 requirements and 16/16 scenarios.

## Executive Summary

The conversations redesign is complete. Slice A delivered the case-aware backend read model, search, pagination, counts, and realtime parity; Slice B delivered the unified queue tabs, ordering, search, pagination, and `Tomar`/`Reconocer` actions; Slice C delivered the thread workspace, right-side case/customer context, flexible `captured_data`, coalesced refresh, `/cases` compatibility routing, and removal of `CasesList` as a rendered route owner.

## Final Verification

- Backend full suite on merged `main`: exit 0, all tests passed.
- Frontend: `70 files / 513 tests` passed.
- TypeScript: `npx tsc -b` passed.
- Dedicated test database `lumat_conversaciones` is required through `TEST_ADMIN_DB_URL`/`DATABASE_URL`; the environment-aware fixture correction shipped in PR #150.
- Critical findings: 0. Blockers: 0.
- Non-blocking warnings: richer runtime `RealtimeSnapshot` fields than the declared TypeScript type, existing Vitest React `act()`/jsdom warnings, and full-suite wall-clock cost.

The earlier `apply-progress.md` and `verify-report.md` snapshots recorded timeout and fixture-isolation problems at their write times. Those claims are historical, not final state: the test-infrastructure fix was merged in #150 and the final merged-main verification passed.

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `unified-conversation-queue` | Created | Added UCQ-1 through UCQ-4 as the canonical queue capability specification. |
| `panel-app` | Updated | Replaced the old PNL-APP-7, PNL-APP-12, and PNL-APP-21 behavior with the unified queue/workspace and `/cases` compatibility contracts; all other requirements were preserved. |
| `conversation-realtime` | Updated | Replaced CRT-3 with the case-aware queue snapshot contract and added CRT-6 for bounded queue refresh. |

Canonical files updated:

- `openspec/specs/unified-conversation-queue/spec.md`
- `openspec/specs/panel-app/spec.md`
- `openspec/specs/conversation-realtime/spec.md`

No application source code or tests were changed by archive operations.

## Archive Contents

The complete change tree was moved mechanically to `openspec/changes/archive/2026-09-10-panel-conversaciones-redesign/`. It contains proposal, exploration, three delta specs, design, checked tasks, apply progress, and verify report. The active change directory no longer exists. Persisted tasks contain 8/8 checked implementation tasks and no unchecked implementation rows.

## Mechanical Readback

```text
--- Verbatim canonical spec copy diff -r (empty means identical) ---
--- End canonical spec copy diff -r ---
--- Verbatim archive move diff -r (empty means identical) ---
--- End archive move diff -r ---
```

Both recursive readbacks were empty. The canonical capability was copied mechanically, and the archived change tree is byte-identical to the pre-move snapshot. This report was added after the move and is therefore additive.

## Graph Traceability

`graphify-out/GRAPH_REPORT.md` was read. Queries covered the OpenSpec archive/canonical-spec area and the panel conversation redesign relationship. Consulted nodes included `Conversation`, `Customer`, `Case`, `serializers.py`, `routes/conversations.py`, `routes/realtime.py`, `ConversationsList.tsx`, `ConversationThread.tsx`, `realtime.ts`, `AppShell.tsx`, `panelRoutes.ts`, `CasesList.tsx`, and the canonical `panel-app`/`conversation-realtime` specifications. Consulted edges included REST serializer/query relationships, realtime-to-conversation relationships, queue API/UI dependencies, and AppShell-to-route ownership.

The required session-close `graphify . --update` completed successfully, refreshing the graph to 4,339 nodes, 9,762 edges, and 312 communities. Graphify emitted non-blocking extraction warnings for unsupported SQL parsing, sensitive `tokens.css`, zero-node JSON profiles, and dropped out-of-scope semantic attributions; these do not block archival.

## Engram Traceability

Source artifact observations read:

- `#2850` — `sdd/panel-conversaciones-redesign/proposal`
- `#2855`, `#2856`, `#2857` — queue, panel-app, and conversation-realtime specifications
- `#2859` — `sdd/panel-conversaciones-redesign/design`
- `#2860` — `sdd/panel-conversaciones-redesign/tasks`
- `#2862` — `sdd/panel-conversaciones-redesign/apply-progress`
- `#2885` — `sdd/panel-conversaciones-redesign/verify-report`

No structured `reviewGate` artifact topics were read because the supplied status had no `reviewGate` key; archive proceeded under ordinary repository policy.

## Risks and Follow-ups

- Align the declared `RealtimeSnapshot` TypeScript type with the runtime queue envelope (`items`, counts, total, offset, and limit).
- Clean up existing React `act()` and unrelated jsdom warning output when addressed globally.
- Keep the dedicated test database environment in the worktree test instructions.

## SDD Cycle

The `panel-conversaciones-redesign` change is fully planned, implemented, verified, and archived. Canonical OpenSpec specifications now reflect the delivered unified conversation queue, workspace, and realtime behavior.
