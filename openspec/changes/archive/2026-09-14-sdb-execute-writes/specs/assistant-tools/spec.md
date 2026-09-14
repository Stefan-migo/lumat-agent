# Delta for assistant-tools

## MODIFIED Requirements

### Requirement: AT-6 — SDB Approved Write Dispatch

SDB MUST dispatch validated allow-listed read or write registry tools through `execute_tool`. Every write MUST receive the exact consumed approval for the frozen task binding; dispatch MUST never bypass `execute_tool` or domain services. Existing AT-1–AT-5 and AT-7 whitelist, typed validation, project decision, and failure boundaries remain unchanged. (Seams: `app/chat/assistant/tools/registry.py:272-308`, `app/services/agent_chat.py:93-109`; unit tests MUST cover approval forwarding and bypass prevention.)

#### Scenario: Approved write dispatch
- GIVEN a validated frozen write task and its consumed exact approval
- WHEN SDB dispatches it
- THEN `execute_tool` validates the whitelist, arguments, approval, cost, and project decision before the domain handler runs

#### Scenario: Missing or altered approval
- GIVEN a write task with absent, expired, replayed, or changed approval
- WHEN dispatch is requested
- THEN no domain mutation occurs

#### Scenario: Gate ordering
- GIVEN a malformed, disallowed, or cost-blocked write
- WHEN dispatch evaluates it
- THEN rejection occurs before the handler and remains auditable

### Requirement: AT-7 — Write Failure Truthfulness

The assistant boundary MUST preserve bounded failure results from write validation, service errors, or transaction failures and MUST NOT reinterpret them as successful evidence. (Seam: `app/chat/assistant/tools/registry.py:316-327`; unit and integration tests MUST assert failed status and no false completion.)

#### Scenario: Mutation handler failure
- GIVEN a typed write handler raises
- WHEN SDB records the outcome
- THEN it returns bounded failure evidence and no successful completion
