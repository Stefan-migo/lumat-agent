# Delta for human-handoff

## MODIFIED Requirements

### Requirement: HH-5 — Human Response Channel

During `human`, the webhook MUST continue persisting every customer message to the same conversation and MUST suppress bot processing. Authorized panel operators MAY respond through the production outbound command; responses MUST obey OM-1/OM-2 and retain complete history. (Previously: human responded only through WhatsApp application/phone.)

#### Scenario: Human inbound continuity
- GIVEN a conversation in `human` state
- WHEN the customer sends a message
- THEN it is persisted once, updates activity, and produces no bot reply

#### Scenario: Operator response
- GIVEN a human conversation and authorized operator
- WHEN an eligible reply is sent
- THEN it is stored as outbound with actor and delivery state
