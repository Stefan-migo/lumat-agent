# Proposal: Case Closure and Open-Status Projection

## Intent

Amend `AD-HOY-1` so urgent cases are selected by urgency and current open status,
not by whether the historical closure timestamp is null.

## Why now

The case-closure correction makes status the source of truth for whether a case is
open. Classification and emergency handling can reactivate a previously closed
case, so the dashboard contract must describe the same open-case rule used by
case queries.

## Evidence

- `odd/tasks/case-closure-fix.md` records Decision D2: status is the open/closed
  gate and `AD-HOY-1` must be amended accordingly.
- `app/services/cases.py` defines `CLOSING_CASE_STATUSES`, the NULL-safe
  `case_is_open_expr()`, and `_apply_status()` to synchronize status with
  `closed_at`.
- `openspec/specs/advanced-dashboards/spec.md:45` currently defines urgent as
  `escalated_at` set or `emergency` true, with `closed_at` null.

## What changes

- Modify `AD-HOY-1` so urgent still requires an escalation timestamp or emergency
  flag and the case must also remain open: status is NULL or is not `closed`,
  `cerrado`, `finalizado`, or `cancelado`.
- Add one scenario showing that a case reactivated from closed is urgent again.

## What does not change

- No live spec edit; the delta syncs during archive.
- No dashboard implementation, endpoint, serialization, or urgency-source change.
- No status values, timestamp rules, migration, or backfill.

## Approach

Ship one modified requirement and one scenario as an OpenSpec delta alongside the
case-status invariant correction. Keep the live `advanced-dashboards` spec
untouched until archive.

## Rollback

Revert this change directory to restore the prior contract. No runtime behavior
depends on the delta by itself.

## Affected areas

| Area | Impact | Description |
|---|---|---|
| `openspec/changes/case-closure-open-status/proposal.md` | Added | Rationale, evidence, scope, and rollback. |
| `openspec/changes/case-closure-open-status/specs/advanced-dashboards/spec.md` | Added | `AD-HOY-1` delta. |
| `openspec/changes/case-closure-open-status/tasks.md` | Added | Implementation and archive tasks. |
| `openspec/specs/advanced-dashboards/spec.md` | Unchanged until archive | Delta target. |
