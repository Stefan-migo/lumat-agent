# Delta for Conversation Manager

## ADDED Requirements

### Requirement: CM-7 — Memory Context Pre-Respond

The system MUST inject the customer's persistent memory context (customer_memo, observations, and summarized history) into the graph state before responding to an inbound message. The context MUST be loaded when the state is rebuilt from the DB via `ConversationState.from_db()` and MUST be scoped to the customer's `entity_id`. If no memory exists, the system MUST proceed with an empty memory context and not block the reply.

#### Scenario: Context injected
- GIVEN a returning customer with an existing customer_memo
- WHEN the graph rebuilds state for an inbound message
- THEN the memo and observations are present in the state before the respond node runs

#### Scenario: No memory yet
- GIVEN a first-contact customer with no stored memory
- WHEN the graph rebuilds state
- THEN the memory context is empty
- AND the reply flow continues normally

### Requirement: CM-8 — Turn-Time Memory Persistence

The system MUST persist per-turn memory before each `END` transition of the graph. Any memory or observation written during the turn MUST be flushed so a subsequent turn sees it without data loss.

#### Scenario: Persist before END
- GIVEN a graph run that produced replies and memory updates
- WHEN the run reaches `END`
- THEN the memory changes are committed and retrievable on the next turn

### Requirement: CM-9 — Close Trigger Feeds Customer Memo

When a conversation transitions to CLOSED via `set_conversation_state(CLOSED)`, the system MUST fire a close handler that upserts the customer_memo (`scope=customer`) and persists typed observations, reusing the existing CM-5 acta content unchanged. The close handler MUST NOT alter the acta summary itself.

#### Scenario: Close triggers memo
- GIVEN a conversation completes and is closed
- WHEN `set_conversation_state(CLOSED)` runs
- THEN the customer_memo is upserted under the customer
- AND the CM-5 acta remains the source of the memo content

## Boundaries

The acta summary (CM-5) is unchanged; the close handler consumes it, it does not rewrite it. ToolNode memory tools are out of scope until a second agent exists.
