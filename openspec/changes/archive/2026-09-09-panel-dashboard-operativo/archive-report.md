# Archive Report: panel-dashboard-operativo

## Final Status

- **Status:** success with warnings
- **Change:** `panel-dashboard-operativo`
- **Archived:** 2026-09-09
- **Final HEAD:** `0568896b`
- **Artifact store:** hybrid (OpenSpec plus Engram mirrors)
- **Delivery:** three slices merged to `main` through PRs #132, #135, and #136.
- **Review:** gentle-ai approved all slices: `review-0aa5619620ad49e2` (slice 1), `review-ba5233a9ac8f9417` (slice 2, four lenses), and `review-dc0ab8cc185c24b1` (slice 3).

## Executive Summary

The panel now provides the bounded operational dashboard, technician-owned privacy-minimal agenda, and admin-only automation surface. All implementation tasks are checked, and the change is closed after final verification and the post-verify fixture correction.

## Final Verification

- PASS WITH WARNINGS: 21/21 requirements, 45/45 scenarios, 0 blockers, and 0 critical findings.
- Web: 488 tests pass and TypeScript typecheck is clean.
- Backend: 591 passed / 595 total. The remaining baseline failures belong to the parallel assistant change: migration `020_assistant_metadata` expectation and two `h4_chat` tests. They are not defects of this change.
- The dashboard cap-test warning in the earlier verify report was fixed after verification in commit `0568896b` by anchoring the fixture to a fixed local day. Dashboard tests are now stable at 9/9 across three runs.
- The archived verify report remains the historical intermediate snapshot; its earlier dashboard-cap warning is superseded by the post-verify fix above.

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `advanced-dashboards` | Updated | Replaced AD-1/AD-2 with operational seven-day/HOY behavior and added AD-HOY-1/2; existing unrelated content was preserved. |
| `admin-panel` | Updated | Replaced AP-2/AP-8/AP-12 and added AP-DASH-1. |
| `panel-app` | Updated | Replaced PNL-APP-8 and added PNL-APP-24/25/26. |
| `service-scheduling` | Updated | Added SS-TECH-1/2. |
| `automation-rules-panel` | Updated | Replaced ARP-1 and added ARP-4. |
| `technician-agenda` | Created | Installed the complete new TECH-ROLE/TECH-AUTH/TECH-AGENDA/TECH-PRIVACY/TECH-DENY capability. |

## Open Items

Review findings `R3-001` on `Dashboard.tsx:40-43` (slice 1) and `R4-001` on `db/migrations/019_tecnico_role.sql:1` (slice 2) remain informational, non-blocking follow-ups. They do not prevent closure.

## Archive Contents

The complete change folder was moved mechanically to `openspec/changes/archive/2026-09-09-panel-dashboard-operativo/`. It contains proposal, six delta specs, design, checked tasks, and verify report. The active change directory no longer exists.

## Mechanical Readback

```text
--- Verbatim canonical technician spec copy diff -r (empty means identical) ---
```

```text
--- Verbatim archive move diff -r (empty means identical) ---
```

Both recursive readbacks were empty, proving byte-identity for the new canonical spec copy and the complete archive move.

## Graphify Traceability

Graphify was queried before archival for the dashboard, technician, scheduling, automation, and panel-shell areas. Consulted nodes included `Dashboard.tsx`, `TechnicianAgenda.tsx`, `AppShell.tsx`, `PanelShell.tsx`, `panelRoutes.ts`, `services/dashboard.py`, `services/scheduling.py`, `appointments.py`, `serializers.py`, `models.py`, `automation_rules.py`, and focused tests. Consulted edges included `AppShell → PanelShell → panelRoutes`, `routes → services`, and `appointments → serializers`.

The graph was stale at build commit `eb990dcf`; the session-close incremental refresh was attempted after archival but failed closed/timed out while reporting missing-corpus and dependency warnings. `GRAPH_REPORT.md` therefore remains at the prior build and this archive records the degraded refresh explicitly.

## Engram Traceability

Source artifact observations read:

- `#2751` — `sdd/panel-dashboard-operativo/proposal`
- `#2752`, `#2754`, `#2755`, `#2756`, `#2757` — the five delta/full capability specs
- `#2759` — `sdd/panel-dashboard-operativo/design`
- `#2764` — `sdd/panel-dashboard-operativo/tasks` (final checked version)
- `#2814` — `sdd/panel-dashboard-operativo/verify-report`

No structured `reviewGate` artifact topics were found for this candidate; the approved review lineages above were supplied as final delivery facts.
