# Delta for internal-agent-chat

## MODIFIED Requirements

### Requirement: IAC-2 — Context Boundary

The agent MUST use the separate `AssistantState` graph for panel requests and persist SDB phase, approval, execution, evidence, cost diagnostics, checkpoints, thread state, and artifacts in the existing boundary. SDB writes MUST use `_run_sdb_tasks` as the only durable runner, with approval canonically `consumed`; the graph MUST NOT create a second runner or bypass `execute_tool`. (Seams: `app/chat/assistant/graph.py:69-115`, `app/services/agent_chat.py:79-80,608-610`; unit and integration tests MUST prove canonical routing and no bypass.)

#### Scenario: Canonical approved execution
- GIVEN an approved SDB write plan
- WHEN execution starts
- THEN the consumed approval reaches the canonical runner and every write reaches `execute_tool`

#### Scenario: Recovery state
- GIVEN a run has persisted checkpoints and thread state
- WHEN the thread resumes
- THEN the same frozen plan determines only incomplete work

### Requirement: IAC-8 — Honest SDB Conversation Delivery

Internal agent chat MUST present verified bounded outcomes for writes: success only when every frozen task completed and its durable evidence committed; otherwise it MUST present bounded failure or recovery evidence. It MUST NOT present `not-implemented`. (Seams: `app/services/agent_chat.py:139-148,622-639`, `app/chat/assistant/nodes.py:291-309`; integration tests MUST cover successful mutation, first failure, rollback, and recovery.)

#### Scenario: Successful write conversation
- GIVEN every frozen write task completed and persistence committed
- WHEN delivery occurs
- THEN the conversation presents verified mutation evidence and no `not-implemented` status

#### Scenario: Failed or uncertain write
- GIVEN a task fails, persistence rolls back, or commit outcome is unknown
- WHEN delivery occurs
- THEN the conversation presents truthful bounded failure/recovery evidence and remains recoverable

#### Scenario: No second runner
- GIVEN an SDB write request enters graph or durable API routing
- WHEN execution is dispatched
- THEN only `_run_sdb_tasks` performs execution
