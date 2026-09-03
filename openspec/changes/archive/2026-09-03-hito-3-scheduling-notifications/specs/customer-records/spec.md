# Delta for Customer Records

## ADDED Requirements

### Requirement: CR-8 — Scheduled Visit History

The system MUST link every appointment, cancellation, rebooking, and calendar status to its customer and case history, without replacing existing conversation or case records.

#### Scenario: Visit appears in history
- GIVEN a customer has a scheduled visit linked to a case
- WHEN an authorized user opens the customer record
- THEN the visit and its lifecycle history are shown chronologically

#### Scenario: Unlinked appointment rejected
- GIVEN an appointment lacks a valid customer or case reference
- WHEN it is saved
- THEN the system rejects it and creates no partial history entry
