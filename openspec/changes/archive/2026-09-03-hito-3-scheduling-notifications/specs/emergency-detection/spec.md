# Delta for Emergency Detection

## MODIFIED Requirements

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
