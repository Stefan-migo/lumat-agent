# Conversation Manager Specification

## Purpose

Drive the customer-facing WhatsApp conversation through a single-agent LangGraph flow: greet, show the 8-category menu, progressively capture structured data, classify intent and case, provide in-scope technical guidance, generate summaries, and log unresolved responses.

## Requirements

### Requirement: CM-1 — Single-Agent Flow with Menu

The system MUST run one LangGraph graph per conversation with persistent per-conversation state. On first contact it MUST greet as Lumat's virtual assistant and present the 8-category menu: Calefont, Caldera, Calefacción, Solicitar visita, Valores, Postventa/Garantía, Emergencia, Hablar con una persona.

#### Scenario: First contact
- GIVEN a new customer sends the first message
- WHEN the conversation starts
- THEN the bot greets, identifies itself, and presents the 8-category menu

#### Scenario: Repeat contact on same conversation
- GIVEN a customer continues an existing conversation
- WHEN a new message arrives
- THEN the flow resumes from the stored conversation state, not from scratch

### Requirement: CM-2 — Progressive Structured Data Capture

The system MUST collect, in a progressive question flow, the fields defined in LumatRequest §1.5: identification (name, phone, email), location (comuna, address), equipment (type, brand, model, approximate age), failure (description, error code, when it occurs, frequency), evidence (photos, videos, audio when applicable), availability (preferred days/times), and consent to store data.

#### Scenario: Complete capture
- GIVEN a customer chose "Calefont"
- WHEN the bot asks the fields in order and the customer answers
- THEN each answer is validated and stored against the conversation and customer record

#### Scenario: Customer skips a field
- GIVEN the customer refuses or cannot answer a field
- WHEN the bot asks for it
- THEN the field is marked unknown and the flow continues without blocking

### Requirement: CM-3 — Intent and Case Classification

The system MUST classify the intent of each message and classify the case by service, priority, and status, storing the result for the case record and panel KPIs. It MUST persist a `classified` activity in the existing `ConversationEvent` model when classification completes.

#### Scenario: Inbound message classified
- GIVEN a customer message is received
- WHEN intent classification runs
- THEN intent, service, priority, and status are recorded on the case
- AND one `classified` activity is persisted

### Requirement: CM-4 — Authorized Technical Guidance

The system MUST only provide low-risk, Lumat-approved guidance: safe preliminary checks, requests for photos of screen/manometer/installation, and statements that a visit is needed when information is insufficient. It MUST NOT confirm definitive diagnoses, instruct dangerous interventions, or invent prices/diagnostics/guarantees/availability.

The "no reliable answer" refusal is a **defensive guard**. No intent the classifier is allowed to emit routes to it: every declared intent is dispatched elsewhere — capture, research triage, or handoff (CM-3, AO-3). The guard exists so that an intent outside the declared vocabulary still refuses rather than answering from an empty knowledge base.

#### Scenario: In-scope guidance
- GIVEN a customer describes a simple symptom within the KB
- WHEN the bot answers from authorized content
- THEN it gives approved safe steps and never a definitive diagnosis

#### Scenario: No reliable answer (guard — undeclared intent only)
- GIVEN a query whose classified intent falls outside the classifier's declared vocabulary
- WHEN retrieval returns no chunk above the threshold
- THEN it states it cannot answer reliably, logs the unresolved response, and escalates to a human
- AND it MUST NOT answer from an empty knowledge base

#### Scenario: A KB intent that misses escalates through handoff
- GIVEN a retrieval intent (`valores`, `postventa`, `consulta`) whose scoped retrieval misses
- WHEN the bounded retry is exhausted
- THEN the turn escalates to a human with the handoff message, and the unresolved response is logged
- AND the canned refusal is NOT emitted, because the refusal guards the linear path and that path is not taken
- AND the turn MUST NOT loop (AO-8)

### Requirement: CM-5 — Conversation Summary

The system MUST generate a concise summary of each conversation (customer, issue, captured data, classification, outcome) available for the case record, handoff bundle, and panel.

#### Scenario: Summary after flow
- GIVEN a conversation completes or is escalated
- WHEN the summary is generated
- THEN it is attached to the case with customer, issue, and next steps

### Requirement: CM-6 — Unresolved Response Logging

The system MUST record every response the bot could not resolve reliably, with the customer question, context, and timestamp, so the KB can be improved (LumatRequest §1.12).

#### Scenario: Unresolved question logged
- GIVEN the bot cannot answer reliably
- WHEN the exchange ends
- THEN the question and context are stored for KB improvement review

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

## Boundary
Emergency flow and human handoff mechanics are specified in `emergency-detection` and `human-handoff`. The acta summary (CM-5) is unchanged; the close handler (CM-9) consumes it, it does not rewrite it. ToolNode memory tools are out of scope until a second agent exists.
