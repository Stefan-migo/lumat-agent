# WhatsApp Webhook Specification

## Purpose

Receive and ingest Meta WhatsApp Cloud API webhooks at `POST https://agente.lumat.cl/webhook/whatsapp` with verified authenticity, immediate acknowledgement, lossless persistence, and idempotent processing tolerant of Meta's at-least-once retry delivery.

## Requirements

### Requirement: WH-1 — Verify Handshake

The system MUST respond to `GET /webhook/whatsapp` by validating that `hub.mode=subscribe` and `hub.verify_token` equals the configured token. On success it MUST return `hub.challenge`; otherwise it MUST return HTTP 403.

#### Scenario: Meta subscribes the webhook
- GIVEN Meta calls GET with the correct verify token
- WHEN the request matches `hub.mode=subscribe` and token
- THEN the system returns 200 with the exact `hub.challenge` value

#### Scenario: Token mismatch
- GIVEN Meta calls GET with a wrong or missing token
- WHEN verification fails
- THEN the system returns 403 and logs the failed attempt

### Requirement: WH-2 — Signature Verification

The system MUST verify every POST by recomputing the HMAC-SHA256 of the raw request body using the configured app secret and comparing it with the `X-Hub-Signature-256` header. Requests that fail verification MUST be rejected with HTTP 403 and MUST NOT be persisted or processed.

#### Scenario: Valid signature
- GIVEN Meta posts a message with a correct `X-Hub-Signature-256`
- WHEN the signature is verified against the raw body
- THEN the request is accepted for persistence

#### Scenario: Invalid signature
- GIVEN a POST with a missing, malformed, or incorrect signature
- WHEN verification fails
- THEN the system returns 403 and drops the payload

### Requirement: WH-3 — Immediate 200

The system MUST respond HTTP 200 to every accepted POST before any business processing begins. Processing MUST be decoupled so the response is never blocked by downstream work.

#### Scenario: Slow downstream processing
- GIVEN a valid POST arrives while conversation processing is slow
- WHEN the request is accepted
- THEN the 200 is returned immediately, before processing completes

### Requirement: WH-4 — Persist Before Process

The system MUST persist the raw webhook payload (or a normalized message record) to the database before any business logic (classification, reply, escalation) runs, so no message is lost even if processing fails.

#### Scenario: Crash after 200 but before processing
- GIVEN a valid POST is persisted
- WHEN processing later fails or crashes
- THEN the raw payload remains stored and is not lost

### Requirement: WH-5 — Deduplicate by WAMID

The system MUST deduplicate inbound messages by `wamid` (message ID). Duplicate deliveries MUST NOT be processed more than once. The combination of persist-before-process and dedup MUST tolerate Meta at-least-once retries.

#### Scenario: Meta retries a delivery
- GIVEN the same wamid is delivered twice within a short window
- WHEN the duplicate arrives
- THEN only the first delivery is processed and the duplicate is acknowledged and skipped

### Requirement: WH-6 — Filter Unsupported Events

The system MUST ignore webhook events that are not `messages` events, and MUST ignore messages with error code `131051` (unsupported/undeliverable), without failing or retrying. Such events SHALL be logged at debug level only.

#### Scenario: Unsupported event type
- GIVEN a webhook delivery with a non-message event type
- WHEN it is received
- THEN it is acknowledged, logged at debug level, and never processed

#### Scenario: Error 131051 message
- GIVEN a message object carrying error 131051
- WHEN it is received
- THEN it is skipped without processing or alerting

### Requirement: WH-7 — Retry-Storm Tolerance

The system MUST remain correct and available under bursts of duplicate deliveries (Meta retry storms): no message loss, no duplicate side effects, and no unbounded queue growth.

#### Scenario: Burst of retries
- GIVEN Meta re-delivers a batch of messages several times in quick succession
- WHEN all deliveries are processed through the dedup path
- THEN each wamid yields exactly one processing pass and the service stays responsive

## Requirements Covered
All messages accepted by this spec feed the `conversation-manager` spec for flow processing.

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
