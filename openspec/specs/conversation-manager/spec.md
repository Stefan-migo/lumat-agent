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

The system MUST classify the intent of each message and classify the case by service, priority, and status, storing the result for the case record and panel KPIs.

#### Scenario: Inbound message classified
- GIVEN a customer message is received
- WHEN intent classification runs
- THEN intent, service, priority, and status are recorded on the case

### Requirement: CM-4 — Authorized Technical Guidance

The system MUST only provide low-risk, Lumat-approved guidance: safe preliminary checks, requests for photos of screen/manometer/installation, and statements that a visit is needed when information is insufficient. It MUST NOT confirm definitive diagnoses, instruct dangerous interventions, or invent prices/diagnostics/guarantees/availability.

#### Scenario: In-scope guidance
- GIVEN a customer describes a simple symptom within the KB
- WHEN the bot answers from authorized content
- THEN it gives approved safe steps and never a definitive diagnosis

#### Scenario: No reliable answer
- GIVEN the bot lacks an authorized answer
- WHEN the query is out of scope or unknown
- THEN it states it cannot answer reliably, logs the unresolved response, and follows configured escalation rules

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

## Boundary
Emergency flow and human handoff mechanics are specified in `emergency-detection` and `human-handoff`.
