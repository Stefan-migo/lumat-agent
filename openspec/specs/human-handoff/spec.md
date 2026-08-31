# Human Handoff Specification

## Purpose

Escalate a conversation from the bot to a human with the full history and a summary so the customer never repeats information, track per-conversation state (bot/human/closed), and make the case visible in the panel. H1 scope: deriva + history + summary + case visibility. Reply-from-panel is NOT part of H1 (H2 deliverable).

## Requirements

### Requirement: HH-1 — Per-Conversation State Model

The system MUST track each conversation's state as `bot`, `human`, or `closed` in the database. Transitions MUST be recorded with timestamp and cause (escalation trigger, human takeover, closure).

#### Scenario: Bot to human
- GIVEN an escalation trigger fires
- WHEN the handoff is initiated
- THEN the conversation state changes to `human` and the transition is recorded

#### Scenario: Close conversation
- GIVEN a case is resolved
- WHEN the owner/operador closes it
- THEN the state becomes `closed` and the closure is recorded

### Requirement: HH-2 — Deriva with History and Summary

The system MUST bundle, for every handoff, the full conversation history and the generated summary (CM-5) so the human can take over without the customer repeating information. A case record MUST be created for the handoff.

#### Scenario: Handoff bundle complete
- GIVEN a conversation is escalated
- WHEN the case is created
- THEN the case contains full history, summary, customer data, and captured fields

### Requirement: HH-3 — Escalation Triggers

The system MUST escalate to a human when any of these conditions occur (LumatRequest §1.9): customer asks to talk to a person; bot fails to understand after two attempts; emergency or risk to people/property; complaint, warranty, or upset customer; personalized quote needed; insufficient or contradictory technical info; evidence (photos/videos) requiring technical review.

#### Scenario: Customer requests a person
- GIVEN a customer chooses "Hablar con una persona"
- WHEN the option is selected
- THEN the conversation is escalated with history and summary

#### Scenario: Two failed comprehension attempts
- GIVEN the bot cannot understand the customer's intent twice
- WHEN the second failure occurs
- THEN the conversation is escalated to a human

### Requirement: HH-4 — Case Visibility in Panel

Escalated cases MUST appear in the panel (pending/escalated view) with customer, summary, and status, and MUST support state changes and responsible assignment by authorized users (LumatRequest §1.11).

#### Scenario: Case appears in panel
- GIVEN a conversation is escalated
- WHEN the operador opens the cases view
- THEN the case is listed with customer, summary, and state

### Requirement: HH-5 — Human Response Channel

During `human`, the webhook MUST continue persisting every customer message to the same conversation and MUST suppress bot processing. Authorized panel operators MAY respond through the production outbound command; responses MUST obey OM-1/OM-2 and retain complete history. (Previously: human responded only through WhatsApp application/phone.)

#### Scenario: Human inbound continuity
- GIVEN a conversation is in `human` state
- WHEN the customer sends further messages
- THEN they are persisted to the same conversation history

#### Scenario: Operator response

- GIVEN a human conversation and authorized operator
- WHEN an eligible reply is sent
- THEN it is stored as outbound with actor and delivery state

## Boundary
The `bot`/`human`/`closed` states are defined here; emergency escalation mechanics live in `emergency-detection`.
