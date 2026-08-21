# Customer Records Specification

## Purpose

Maintain a single, deduplicated customer record (ficha) per person: auto-created on first contact, recognized by phone number, with lifecycle states, internal notes, captured data, and full history linkage.

## Requirements

### Requirement: CR-1 — Auto-Ficha on First Contact

The system MUST create a customer record automatically when a contact is received from a phone number with no existing record, registering date, time, channel, and responsible entity.

#### Scenario: First contact creates ficha
- GIVEN a message arrives from an unknown phone number
- WHEN the message is processed
- THEN a customer record is created automatically with the inbound phone number

### Requirement: CR-2 — Phone-Based Deduplication

The system MUST identify existing customers by phone number and reuse the existing record. It MUST NOT create duplicate records for the same number, including when normalized formats differ (e.g., `+56 9...` vs `9...`).

#### Scenario: Known customer returns
- GIVEN a message arrives from a previously registered phone number
- WHEN the message is processed
- THEN the existing ficha is reused and no duplicate is created

#### Scenario: Different formatting
- GIVEN the same number arrives in a different phone format
- WHEN normalized comparison runs
- THEN the record is still recognized as the same customer

### Requirement: CR-3 — Lifecycle States

The system MUST track each customer through the states: nuevo, contactado, pendiente, agendado, en evaluación, finalizado, cancelado, postventa. Every state change MUST record who changed it and when, and MUST be reflected in the panel.

#### Scenario: State progression
- GIVEN a customer record exists
- WHEN its case advances (e.g., from pendiente to agendado)
- THEN the state updates with actor and timestamp, and the change is auditable

#### Scenario: Invalid transition rejected
- GIVEN a state change is requested that violates the defined lifecycle (e.g., from nuevo directly to postventa)
- WHEN the change is submitted
- THEN the system rejects or requires justification per configured rules

### Requirement: CR-4 — Internal Notes

Authorized panel users MUST be able to add internal notes to a customer record, visible only to staff (admin/operador), never to the customer.

#### Scenario: Staff adds note
- GIVEN an authorized user opens a ficha in the panel
- WHEN they save an internal note
- THEN the note is stored with author and timestamp and shown to staff only

### Requirement: CR-5 — History Linkage

The system MUST link every conversation, message, case, and file of a customer to the customer record, forming a complete history viewable in the panel.

#### Scenario: History complete
- GIVEN a customer has multiple conversations and cases
- WHEN a staff member opens the ficha
- THEN all linked conversations, cases, and files are listed in chronological order

### Requirement: CR-6 — Data and Consent Recording

The system MUST store the personal data, contact data, and consent acceptance captured during conversation (CM-2) on the customer record, including consent for data storage and use for service purposes.

#### Scenario: Captured data persisted
- GIVEN the conversation flow captured identification, location, equipment, and consent
- WHEN the data is stored
- THEN the ficha contains the captured fields and consent status

### Requirement: CR-7 — Living Customer Memo on Ficha

The customer record (ficha) MUST surface the living customer_memo stored in the memory layer (`scope=customer`). The memo MUST be visible to authorized panel users when opening a ficha and MUST reflect the latest version written at conversation close (MEM-4). Internal staff notes (`customer_notes`, CR-4) MUST remain separate and unchanged.

#### Scenario: Ficha shows memo
- GIVEN a customer whose conversations have closed and produced a memo
- WHEN an authorized user opens the ficha
- THEN the latest customer_memo content is displayed on the ficha

#### Scenario: Memo and notes coexist
- GIVEN a customer has both a customer_memo and staff notes
- WHEN the ficha is opened
- THEN the auto-generated memo and the staff-authored notes are shown as distinct, both retained

#### Scenario: No memo yet
- GIVEN a customer with no closed conversation producing a memo
- WHEN the ficha is opened
- THEN the memo surface is empty
- AND no error is raised
