# Delta for whatsapp-webhook

## ADDED Requirements

### Requirement: WH-8 — Human-state regression continuity

The existing verified webhook authentication, immediate acknowledgement, WAMID deduplication, and retry tolerance MUST remain unchanged; a valid inbound message for a `human` conversation MUST persist exactly once and MUST NOT invoke bot processing or create an automated outbound message.

#### Scenario: Human webhook regression
- GIVEN a valid signed Meta message for a human-owned conversation
- WHEN the webhook is delivered once or retried
- THEN it is acknowledged, persisted once, and no bot send occurs

#### Scenario: Closed conversation inbound
- GIVEN a valid message for a closed conversation
- WHEN it is ingested
- THEN inbound history remains durable and no unauthorized state reopening occurs
