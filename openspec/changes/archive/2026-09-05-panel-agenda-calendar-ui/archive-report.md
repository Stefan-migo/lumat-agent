# Archive Report: panel-agenda-calendar-ui

## Final Status

- **Status:** success with warnings
- **Change:** `panel-agenda-calendar-ui`
- **Archived:** 2026-09-05
- **Delivery:** merged to `main` through stacked PRs #90, #91, #92, and #93; issues #86–#89 closed. This phase created no branch, commit, or PR.
- **Artifact store:** hybrid (OpenSpec plus Engram mirrors)
- **Review gate:** no structured `reviewGate` was present in the supplied archive status. The orchestrator supplied approved review lineage facts for all four delivery slices; archive proceeded under ordinary repository policy.

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `calendar-integration` | Updated | Added CI-3 bounded authenticated agenda range-read contract, validation, ordering, display joins, lifecycle/sync projection, and scenarios. |
| `agenda-calendar-ui` | Created | Copied the approved AG-UI-1..4 capability specification as the new canonical capability spec. |
| `admin-panel` | Updated | Replaced AP-11 with the approved actionable cancellation/retry and independent lifecycle/sync visibility contract; preserved all unrelated requirements. |

No `openspec/config.yaml` change was required; the prior archive convention leaves configuration unchanged.

The AP-11 replacement was flagged before execution as a bounded destructive requirement merge. No large-section deletion occurred, and unrelated requirements were preserved.

## Verification and Completion

- Archived `exploration.md`, `proposal.md`, `design.md`, `specs/`, `tasks.md`, `apply-progress.md`, and `verify-report.md`.
- Archived tasks contain 12/12 checked implementation tasks and no unchecked implementation task rows.
- Final verification: PASS WITH WARNINGS; 6/6 requirements, 10/10 scenarios, 0 blockers, and 0 critical findings.
- Final evidence: backend `uv run pytest tests/ -q` — 578 passed; frontend `cd web && npm test` — 58 files / 387 tests passed; `npx tsc -b` and `npm run build` passed.
- Non-blocking warnings are the documented Slice 4 RED-output reconstruction limitation, pre-existing non-failing React `act(...)` warnings, and unavailable coverage/linter tooling.

## Mechanical Readback

The canonical new capability spec was copied with shell `cp` and verified with `diff -r` before installation. The output was empty.

The complete change folder was snapshotted before the move, moved mechanically with `git mv`, and compared against the pre-move snapshot with `diff -r`.

```text
--- Verbatim canonical spec copy diff -r (empty means identical) ---

--- Verbatim archive move diff -r (empty means identical) ---
```

Both recursive readbacks were empty, proving byte-identity for the mechanical copy and archive move. This report was added after the move and is therefore additive.

## Graph Traceability

Graph report was read first. Query: `panel-agenda-calendar-ui archive sync calendar-integration agenda-calendar-ui admin-panel`.

Nodes consulted: `Panel Agenda / Calendar UI Change`, `Panel Agenda/Calendar UI Proposal`, `AgendaPage.tsx`, `calendar.py`, `scheduling.py`, `Appointment`, `AppointmentCalendarSync`, `appointments.py`, `serializers.py`, `PanelShell.tsx`, `AppShell.tsx`, `api.ts`, `types.ts`, `DataTable`, `PageFrame`, `StateMessage`, `AgendaPage.test.tsx`, and the `Admin Panel Specification`, `Calendar Integration Spec`, and agenda capability nodes.

Edges consulted: appointments route → scheduling service → models; sync status left join → agenda serializer; panel routes → AppShell → AgendaPage → api; shared page/table/feedback primitives → agenda UI.

Graph report freshness warning: report built from commit `681ed2e4`; final delivery was later merged to `main`.

## Engram Traceability

Source artifact observations read:

- `#2496` — `sdd/panel-agenda-calendar-ui/exploration` mirror
- `#2498` — `sdd/panel-agenda-calendar-ui/proposal` mirror
- `#2500` — `sdd/panel-agenda-calendar-ui/spec` mirror
- `#2501` — `sdd/panel-agenda-calendar-ui/design` mirror
- `#2506` — `sdd/panel-agenda-calendar-ui/tasks` mirror
- `#2514` — `sdd/panel-agenda-calendar-ui/verify-report` mirror

No review observation IDs were read because no structured `reviewGate` or review artifact paths were supplied in the archive status.
