# Delta for conversation-manager

## MODIFIED Requirements

### Requirement: CM-3 — Intent and Case Classification

The system MUST classify the intent of each message and classify the case by service, priority, and status, storing the result for the case record and panel KPIs. It MUST persist a `classified` activity in the existing `ConversationEvent` model when classification completes.
(Previously: classification was stored for the case record and panel KPIs but produced no required activity history.)

#### Scenario: Inbound message classified
- GIVEN a customer message is received
- WHEN intent classification runs
- THEN intent, service, priority, and status are recorded on the case
- AND one `classified` activity is persisted

## ADDED Requirements

### Requirement: CM-10 — Conversation Activity and Recency

The system MUST persist only the activity vocabulary `classified`, `kb_retrieved`, and `escalation` in the existing `ConversationEvent` model. It MUST update `last_message_at` whenever a customer or outbound panel message is committed, and activity history MUST remain queryable after reconnect.

#### Scenario: Knowledge retrieval activity
- GIVEN classification retrieves knowledge-base content
- WHEN retrieval completes
- THEN one `kb_retrieved` activity is persisted for the conversation

#### Scenario: Message recency
- GIVEN a customer or outbound panel message is committed
- WHEN the conversation is saved
- THEN `last_message_at` is updated to that message time

#### Scenario: Unknown activity rejected
- GIVEN an event outside the three approved activity names
- WHEN persistence is attempted
- THEN it is rejected and no unsupported activity enters history
