# Archive Report: Panel Adoption

## Closure

- **Change:** `2026-08-24-panel-adoption`
- **Archived:** `2026-08-25`
- **Mode:** hybrid (OpenSpec + Engram)
- **Status:** CLOSED — authorized with warnings
- **Native verification settlement:** succeeded through the orchestrator; archive authorized.

## Final State

- **Tasks:** 24/24 complete, including corrective S7 tasks 7.1–7.2.
- **Requirements:** 10/10 compliant.
- **Scenarios:** 24/24 compliant.
- **Frontend:** 319 tests passed; TypeScript build passed.
- **Conversation tests:** 7 focused tests passed.
- **Backend:** 499 tests passed.
- **Critical findings:** 0.
- Corrective S7 wires AppShell D7 routing to all six live views and preserves ClientFicha and ConversationThread drill-downs.
- The S6b tone-save test waits for the initial tone display value; the final Settings suite is 25/25.

Historical apply-progress evidence is preserved in the archive. Its pre-S7 pending, placeholder, and psycopg statements are historical snapshots, not current blockers or implementation state.

## Warnings

1. React `act(...)` warnings remain in tests where Dashboard fetch effects run during shell/story renders; assertions pass.
2. No live browser/server SPA proof is configured; frontend API consumption is proven with fetch-backed component tests and the conversation endpoint with TestClient.

These warnings are non-blocking. No CRITICAL findings remain.

## Specs Synced

- `panel-app`: created canonical spec from the complete delta.
- `admin-panel`: added AP-9, preserving all existing requirements.
- `panel-design-system`: modified R-PRD-PG-2 to permit the established `_shared` imports while preserving the helper boundary and zero-CSS constraint.

## Mechanical Readback

The canonical `panel-app` copy and archive move were performed with shell copy/move operations. Both mandatory `diff -r` readbacks were empty (no differences).

## Engram Traceability

OpenSpec artifacts read directly:

- `proposal.md`
- `specs/panel-app/spec.md`
- `specs/admin-panel/spec.md`
- `specs/panel-design-system/spec.md`
- `design.md`
- `tasks.md`
- `apply-progress.md`
- `verify-report.md`

Engram observations read directly:

- `#2040` — `sdd/2026-08-24-panel-adoption/proposal`
- `#2041` — `sdd/2026-08-24-panel-adoption/spec`
- `#2042` — `sdd/2026-08-24-panel-adoption/design`
- `#2102` — `sdd/2026-08-24-panel-adoption/verify-report`

No dedicated persisted Engram `tasks` or `apply-progress` artifact was found; the OpenSpec files are the authoritative persisted task/progress records for those artifacts. No review receipt topics were read because structured status did not expose a `reviewGate` artifact; native verification settlement was authoritative for final verification.

## Next Steps

- Consider adding a live browser/server SPA smoke harness if deployment-level rendering proof becomes a release requirement.
- Optionally wrap shell tests mounting fetching Dashboard in async `act(...)` assertions to remove warning noise.

## Graph Closure Note

The required session-close `graphify . --update` was attempted after archival. It was degraded because all three semantic extraction chunks failed with provider error 402 (insufficient balance); the existing graph was retained and no application source was modified. A future session should rerun the update when semantic extraction is available.
