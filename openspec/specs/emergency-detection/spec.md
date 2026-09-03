# Emergency Detection Specification

## Purpose

Detect safety-critical situations deterministically and immediately: interrupt the commercial flow, deliver Lumat-approved safety instructions, recommend emergency/gas-distributor contact, and notify the owner or technician without delay.

## Requirements

### Requirement: EM-1 — Deterministic Keyword Detection

The system MUST detect, on every inbound message, Spanish expressions for: olor a gas, fuga (de gas), humo, incendio, chispa, explosión, monóxido, intoxicación, riesgo eléctrico, filtración severa. Detection MUST run before LLM classification. The keyword list MUST be configurable through the panel (settings-scope-limits SS-2).

#### Scenario: Emergency keyword detected
- GIVEN a customer writes "huele a gas en el calefont"
- WHEN the deterministic layer scans the message
- THEN an emergency is raised before any commercial flow continues

#### Scenario: Keyword configured
- GIVEN the owner adds or removes a keyword in settings
- WHEN the list changes
- THEN detection uses the updated list immediately

### Requirement: EM-2 — Flow Interrupt

When an emergency is detected, the system MUST interrupt the current commercial flow immediately and route to the emergency protocol.

#### Scenario: Interrupt mid-capture
- GIVEN a customer is mid-data-capture (CM-2)
- WHEN an emergency expression appears in a message
- THEN the capture flow is abandoned and the emergency protocol starts

### Requirement: EM-3 — Safety Instructions

The system MUST deliver Lumat-approved safety instructions, recommend contacting emergency services or the gas distributor, and state that a technician will be notified. It MUST NOT attempt technical resolution or commercial offers during an emergency.

#### Scenario: Safety guidance delivered
- GIVEN the emergency protocol starts
- WHEN the bot responds
- THEN it delivers approved safety steps, emergency contacts, and confirmation of notification

### Requirement: EM-4 — Immediate Owner/Technician Notification

The system MUST notify the configured owner/technician contact immediately with the customer's number, location when known, and detected emergency context. It MUST use the durable delivery/audit primitives where compatible, but MUST NOT wait for scheduling, calendar synchronization, retries, or a bounded sweep before attempting emergency delivery. Notification MUST include an acknowledgement requirement, and the case MUST be flagged as escalated.

(Previously: emergency notification used a narrowly scoped immediate WhatsApp/SMTP path without the H3 durable delivery boundary.)

#### Scenario: Notification sent
- GIVEN an emergency is detected
- WHEN the protocol runs
- THEN an immediate delivery attempt and audit record are created with customer and context
- AND the case is flagged as escalated

#### Scenario: Delivery failure
- GIVEN the immediate emergency delivery attempt fails
- WHEN the failure is recorded
- THEN the safety reply still completes, the failure remains visible/retryable, and acknowledgement state is preserved

#### Scenario: Notification acknowledged
- GIVEN the owner/technician receives the emergency notification
- WHEN they acknowledge it
- THEN the acknowledgement is recorded on the case

### Requirement: EM-5 — Conservative Default

When detection is ambiguous or the message may indicate risk, the system MUST default to escalation rather than resolution: either treat as emergency or escalate to a human, never silently ignore.

#### Scenario: Ambiguous risk
- GIVEN a message contains a borderline risk expression
- WHEN deterministic detection is uncertain
- THEN the conversation is escalated to a human or the emergency protocol is triggered
