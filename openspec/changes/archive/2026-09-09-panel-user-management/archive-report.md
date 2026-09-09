# Archive Report: panel-user-management

## Final Status

- **Status:** success with warnings
- **Change:** `panel-user-management`
- **Archived:** 2026-09-09
- **Artifact store:** hybrid (OpenSpec plus Engram mirrors)
- **Delivery:** Slice A backend through PR #144; Slice B frontend through PR #145.
- **Final verification:** PASS WITH WARNINGS; 10/10 requirements and 18/18 scenarios.

## Executive Summary

The panel user-management change is complete and archived. It delivers admin-only user listing, creation, activation toggling, password resets, safe serialization, audit coverage, and the corresponding admin-only SPA view with role-safe navigation and Técnico labeling.

## Final Verification

- In-scope backend: focused user-management pytest passed 6/6.
- In-scope frontend: 59 Vitest tests passed; TypeScript compilation passed.
- Tasks: 4/4 implementation tasks checked in the persisted OpenSpec task artifact.
- Requirements and scenarios: 10/10 and 18/18.
- Critical findings: 0. Blockers: 0.
- Non-blocking warnings: existing React `act(...)` warnings in focused frontend tests.
- The four full-suite failures are external to this change: assistant-chat behavior and stale migration expectations for migrations 020/022, tracked in issue #143. The migration-stale correction is in separate PR #146 and is not included here.

## Specs Synced

| Domain | Action | Details |
|---|---|---|
| `admin-panel` | Updated | Appended USR-API-1 through USR-API-5 for safe listing, creation, active toggling, password reset, and admin JSON authorization. Existing requirements were preserved. |
| `panel-app` | Updated | Appended USR-UI-1 through USR-UI-5 for admin navigation, presentation, creation, mutations, self-protection, and state handling. Existing requirements were preserved. |

Canonical files updated:

- `openspec/specs/admin-panel/spec.md`
- `openspec/specs/panel-app/spec.md`

No application code or tests were changed by archive operations.

## Archive Contents

The complete change artifact set was moved mechanically to `openspec/changes/archive/2026-09-09-panel-user-management/`. It contains proposal, two delta specs, design, checked tasks, apply progress, verify report, and this archive report. The active change directory no longer exists.

## Mechanical Readback

```text
--- Verbatim archive move diff -r (empty means identical) ---
--- End archive move diff -r ---
```

The empty recursive readback proves byte-identity for the complete pre-move change tree. This archive report is additive and was created after the pre-move snapshot.

## Graphify Traceability

Graphify was refreshed and queried before archival. Consulted nodes included `Panel User Management Admin Panel Spec`, `Panel User Management Apply Progress`, `UserManagement.tsx`, `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, `routes/users.py`, `serializers.py`, `services/users.py`, `test_api_users.py`, and the canonical `admin-panel` and `panel-app` specs. Consulted edges included `AppShell → PanelShell → panelRoutes → UserManagement` and the route → authorization/service/serializer/audit seams.

The refresh reported extraction warnings and a one-node shrink guard during cluster-only relabeling; the existing `GRAPH_REPORT.md` remained available and was consulted. These are degraded traceability warnings only and do not block archive.

## Engram Traceability

Source artifact observations read:

- `#2819` — `sdd/panel-user-management/proposal`
- `#2821`, `#2822` — `sdd/panel-user-management/spec/admin-panel` and `sdd/panel-user-management/spec/panel-app`
- `#2824` — `sdd/panel-user-management/design`
- `#2828` — `sdd/panel-user-management/tasks` (superseded snapshot; filesystem task artifact is authoritative and checked)
- `#2839` — `sdd/panel-user-management/apply-progress`
- `#2846` — `sdd/panel-user-management/verify-report` (superseded snapshot; canonical final report is authoritative at 18/18)

No structured `reviewGate` artifact topics were found for this candidate.

## Risks and Follow-ups

- Track issue #143 and separate PR #146 for unrelated full-suite assistant/migration failures.
- Clean up existing React `act(...)` warning output separately.

## SDD Cycle

The `panel-user-management` change is fully planned, implemented, verified, and archived. The canonical OpenSpec specifications now include the delivered user-management behavior.
