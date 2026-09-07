# Archive Report: conversation-realtime

## Final Status

- **Status:** success with warnings
- **Change:** `conversation-realtime`
- **Archived:** 2026-09-07
- **Final implementation HEAD:** `8eae542139c15688ba34d33741de31c71aefa5bf`
- **Delivery:** seven slices merged to `main` through PRs #112–#118
- **Artifact store:** hybrid (OpenSpec plus Engram mirrors)
- **Review gate:** approved Gentle AI review was supplied for every slice; no structured `reviewGate` receipt topics were present in the archive status

## Final Verification

- **PASS:** 15/15 requirements, 28/28 scenarios, 14/14 tasks, 0 blockers, and 0 critical findings.
- Backend: `uv run pytest tests/` — 611 passed.
- Frontend: `cd web && npm test` — 66 files / 444 passed.
- Typecheck and production build passed.
- Non-blocking follow-ups: R3-001 at `AppShell.tsx:126`, the backend `_publish_all` unawaited `RuntimeWarning`, and existing frontend React `act(...)` warnings.

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `conversation-manager` | Updated | Modified CM-3 to persist `classified`; added CM-10 activity vocabulary and recency requirements. |
| `human-handoff` | Updated | Modified HH-1 to persist `escalation`; added HH-6 best-effort state publication. |
| `internal-agent-chat` | Updated | Added IAC-6 compatible token streaming while preserving the synchronous POST contract. |
| `panel-app` | Updated | Added PNL-APP-13, PNL-APP-14, and PNL-APP-15 realtime surface contracts. |
| `panel-design-system` | Updated | Added DS-RT-1 and DS-RT-2 realtime state and responsive surface contracts. |
| `conversation-realtime` | Created | Archived the complete CRT-1..5 capability specification as a new canonical capability spec. |

Canonical files updated:

- `openspec/specs/conversation-manager/spec.md`
- `openspec/specs/human-handoff/spec.md`
- `openspec/specs/internal-agent-chat/spec.md`
- `openspec/specs/panel-app/spec.md`
- `openspec/specs/panel-design-system/spec.md`
- `openspec/specs/conversation-realtime/spec.md`

No application code or tests were changed by archive operations. The untracked `openspec/changes/conversation-realtime/.gentle-ai-instance` vestige was preserved outside the archive and was not staged.

## Archive Contents

The change artifacts were moved to `openspec/changes/archive/2026-09-07-conversation-realtime/` with proposal, specs, design, tasks, apply-progress, verify-report, and this report. Archived tasks contain 14/14 checked implementation tasks and no unchecked implementation rows.

## Mechanical Readback

The artifact set was snapshotted before the mechanical move, moved with `git mv` for tracked files and `mv` for the untracked verification artifacts, and compared against the pre-move snapshot with `diff -r`.

```text
--- Verbatim archive move diff -r (empty means identical) ---
```

The empty readback proves byte-identity for the archived artifact set. The preserved `.gentle-ai-instance` file was intentionally excluded from the archive snapshot per instruction. Canonical spec updates were requirement merges; no delta-to-canonical whole-file copy was performed.

## Graph Traceability

`graphify-out/GRAPH_REPORT.md` was consulted, and Graphify queries covered the conversation-realtime OpenSpec area and canonical-spec relationship. Relevant nodes included `Conversation Realtime Spec (CRT-1..5)`, `realtime.ts`, `AppShell.tsx`, `PanelShell.tsx`, `services/realtime.py`, and the archive-report/OpenSpec communities. The report was built at the final HEAD `8eae5421`; optional refresh remains a session-close action.

## Engram Traceability

Source artifact observations read:

- `#2584` — `sdd/conversation-realtime/proposal`
- `#2585` — `sdd/conversation-realtime/spec` (combined delta mirror)
- `#2591` — `sdd/conversation-realtime/design`
- `#2594` — `sdd/conversation-realtime/tasks`
- `#2598` — `sdd/conversation-realtime/apply-progress`
- `#2620` — `sdd/conversation-realtime/verify-report`

No structured review transaction, ledger, receipt, or gate-context observations were read because no `reviewGate` key was present in the supplied archive status. The supplied final-state facts record that every slice received approved Gentle AI review.

## SDD Cycle Status

The `conversation-realtime` change is fully planned, implemented, verified, and archived. The canonical OpenSpec source of truth now includes the delivered realtime behavior.
