# Delta for internal-agent-chat

## ADDED Requirements

### Requirement: IAC-8 — Honest SDB Conversation Delivery

Internal agent chat MUST present the durable SDB outcome from verification: successful bounded read evidence only after all frozen tasks complete, and bounded failure evidence when any task fails, is unavailable, or remains incomplete. It MUST NOT present `not-implemented` as a terminal result.

#### Scenario: Successful SDB conversation
- GIVEN an approved SDB run with a completed result for every frozen task
- WHEN the conversation receives delivery
- THEN it presents the bounded verified evidence and no `not-implemented` status

#### Scenario: Failed SDB conversation
- GIVEN verification cannot prove every frozen task completed
- WHEN delivery is requested
- THEN the conversation presents an honest bounded failure/error outcome and remains recoverable

#### Scenario: Read-only boundary
- GIVEN an SDB message requests a write tool
- WHEN the plan is validated
- THEN the chat exposes rejection evidence and no side effect occurs

## MODIFIED Requirements

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests, with only declared typed tools and admin authorization. It MUST assemble history-aware turns from the durable thread and persist normal, Cortex, or SDB state, approvals, execution, evidence, cost diagnostics, phase, and checkpoints in the existing thread boundary. SDB execution MUST use the durable canonical runner and MUST NOT create a parallel graph runner. Cortex state MUST be explicitly merged under `assistant_state["cortex_session"]` without clobbering other keys, and MUST NOT couple to WhatsApp state. The deterministic cost gate MUST retain its current behavior before planning.
(Previously: the boundary persisted SDB state but did not require canonical durable execution or real task evidence.)

#### Scenario: History-aware assistant response
- GIVEN an authorized administrator submits a panel request
- WHEN the assistant processes it
- THEN bounded thread context and assistant metadata, usage, and cost are persisted

#### Scenario: Durable SDB context
- GIVEN an authorized administrator starts a valid SDB run
- WHEN a phase transition occurs
- THEN phase, frozen scope reference, current task, and checkpoint sequence persist in the thread

#### Scenario: Durable Cortex context
- GIVEN an authorized administrator turns an active Cortex thread
- WHEN session state changes
- THEN the nested Cortex state persists while unrelated assistant-state keys remain

#### Scenario: Blocked mode
- GIVEN a thread or UTC-day spend reaches its blocking limit
- WHEN an administrator submits a request
- THEN a deterministic reply is persisted, no LLM node is called, and panel access remains available

#### Scenario: Canonical SDB execution
- GIVEN an approved SDB plan
- WHEN execution starts
- THEN the durable runner is authoritative and the approval status is canonically `consumed`

## REMOVED Requirements

### Requirement: `not-implemented` terminal chat response
(Reason: SDB delivery now reports verified evidence or truthful failure.)
(Migration: Replace RED assertions that expect the stub response.)
