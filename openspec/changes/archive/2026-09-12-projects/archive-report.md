# Archive Report: projects

## Status

**SUCCESS WITH WARNINGS**

The `projects` change is complete and archived on 2026-09-12. All 21 implementation
tasks across WU-1 through WU-5 are complete. Verification passed with warnings:
0 blockers, 0 critical findings, 12/12 requirements, and 27/27 scenarios.

## Final-State Evidence

- Backend focused verification: **100 passed**.
- Web verification: **515 passed**.
- Production build: `npm run build` **succeeded**.
- The full backend `pytest tests/` suite was not run because it exceeds 300 seconds.
- `tests/unit/test_assistant_extensions.py::test_all_inventoried_lumat_sdb_consumers_use_guardrails_terminology`
  remains a **pre-existing failure on main**, introduced by the `sdb-native` archive
  commit and unrelated to this change.
- Web tests retain non-failing React `act(...)` and jsdom warnings.

The final implementation includes the recorded mid-flight corrections: WU-1
approval bypass removal, semantic deduplication, and flaky-test stabilization;
the WU-4 approved-namespace-selection gap; and the panel-app navigation contract
correction to ten destinations, including `Usuarios` and `Proyectos`.

## Delta Sync

| Domain | Action | Details |
|---|---|---|
| `projects` | Created | Installed the complete project registry, lifecycle, and approval-safe namespace specification. |
| `memory` | Updated | Applied MODIFIED MEM-2 and MEM-8 requirements for authorized project propagation while preserving default compatibility. |
| `sdb-native` | Updated | Added SDB-5 project propagation through the existing seven-phase and recovery seam. |
| `assistant-tools` | Updated | Added AT-4 typed project tools and AT-5 approval boundary requirements. |
| `panel-app` | Updated | Applied corrected PNL-APP-1 with exactly ten destinations, including `Usuarios` and `Proyectos`; added PNL-APP-27 read-only project browse. |

Unrelated requirements were preserved in all existing main specifications.

## Archive Contents

- `proposal.md`
- `design.md`
- `exploration.md`
- `tasks.md` — 21/21 implementation tasks checked
- `apply-progress.md`
- `verify-report.md`
- `specs/projects/spec.md`
- `specs/memory/spec.md`
- `specs/sdb-native/spec.md`
- `specs/assistant-tools/spec.md`
- `specs/panel-app/spec.md`

## Release Gate

Before release, validate the user-facing **“Proyecto”** naming with a real user.

## Mechanical Readback

The delta-to-main full-spec copy and the pre-move archive snapshot both passed
`diff -r` with empty output. The active `openspec/changes/projects/` directory no
longer exists.

## Graph Check

Consulted `graphify-out/GRAPH_REPORT.md` and the project-area graph query. Relevant
nodes included `services/projects.py`, `Memory`, `registry.py`, `agent_chat.py`,
`PanelShell.tsx`, `ProjectsPage.tsx`, `panelRoutes.ts`, and the five delta specs;
relevant edges included project service to `Project`/`Memory`, assistant registry
to project tools, and `PanelShell`/`AppShell`/`panelRoutes` navigation coupling.
