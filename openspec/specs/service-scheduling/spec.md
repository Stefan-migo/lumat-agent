# Service Scheduling Specification

## Purpose

Provide local, auditable appointment scheduling linked to customers and cases.

## Requirements

### Requirement: SS-1 — Appointment Lifecycle and Time

The system MUST store each appointment with a service, customer, case, technician, fixed duration, canonical timezone, and lifecycle state. It MUST preserve the represented local time across DST transitions and support cancellation and rebooking with history.

#### Scenario: Book and rebook
- GIVEN an available technician and valid local time
- WHEN an authorized user books, cancels, and rebooks a visit
- THEN each state and actor change is retained in history

#### Scenario: Invalid time
- GIVEN a nonexistent or ambiguous DST local time
- WHEN booking is requested
- THEN the system rejects it with a deterministic validation error

### Requirement: SS-2 — Availability and Conflicts

The system MUST expose technician availability and blocks, and MUST reject overlapping active appointments for the same technician or customer atomically.

#### Scenario: Conflict rejected
- GIVEN an active appointment occupies the requested interval
- WHEN another booking overlaps it
- THEN no second appointment is created

#### Scenario: Cancellation frees slot
- GIVEN an appointment is cancelled
- WHEN the same interval is requested
- THEN the new booking is accepted if all other rules pass
