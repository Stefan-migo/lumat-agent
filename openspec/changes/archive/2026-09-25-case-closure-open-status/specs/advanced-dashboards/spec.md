# Delta for Advanced Dashboards

## MODIFIED Requirements

### Requirement: AD-HOY-1 — Operational HOY Projection

One authenticated endpoint MUST return bounded projections for today’s appointments, active unanswered conversations, and open urgent cases. Unanswered MUST mean at least one inbound message and no outbound message after the latest inbound. Urgent MUST mean `escalated_at` is set or `emergency` is true, AND the case is still open: its status is NULL or is not one of `closed`, `cerrado`, `finalizado`, or `cancelado`.
(Previously: urgent meant `escalated_at` was set or `emergency` was true, with `closed_at` null.)

#### Scenario: A reactivated case is urgent again (pytest)

- GIVEN a case was closed and is reactivated with an open status and `escalated_at` set
- WHEN the HOY endpoint is requested
- THEN the reactivated case appears in the urgent cases projection
