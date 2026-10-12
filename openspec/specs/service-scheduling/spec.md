# Service Scheduling Specification

## Purpose

Provide local, auditable appointment scheduling linked to customers and cases.

## Requirements

### Requirement: SS-1 — Appointment Lifecycle and Time

The system MUST store each appointment with a service, customer, case, technician, fixed duration, canonical timezone, and lifecycle state. It MUST preserve the represented local time across DST transitions and support cancellation and rebooking with history. For chatbot bookings, the system MUST resolve the appointment duration from the case's service using `booking.service_durations`; when the service has no valid configured duration, it MUST use 60 minutes.

#### Scenario: Book and rebook
- GIVEN an available technician and valid local time
- WHEN an authorized user books, cancels, and rebooks a visit
- THEN each state and actor change is retained in history

#### Scenario: Invalid time
- GIVEN a nonexistent or ambiguous DST local time
- WHEN booking is requested
- THEN the system rejects it with a deterministic validation error

#### Scenario: Chatbot duration resolved by service
- GIVEN a case has a service with a valid positive integer duration in `booking.service_durations`
- WHEN the chatbot searches availability and books the appointment
- THEN both operations use the configured duration

#### Scenario: Chatbot duration falls back when unset
- GIVEN the case's service has no valid duration in `booking.service_durations`
- WHEN the chatbot searches availability and books the appointment
- THEN both operations use 60 minutes

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
### Requirement: SS-TECH-1 — Technician-Owned Agenda Read

The scheduling API MUST provide an authenticated technician agenda read covering past, local-day, and future appointments. Results MUST be filtered server-side by `technician_id == current.id` and ordered chronologically. The response MUST use the dedicated privacy-minimal technician serializer.

#### Scenario: Full owned range (pytest)
- GIVEN a tecnico owns past, today, and future appointments
- WHEN the agenda read is requested
- THEN all owned appointments are returned in chronological order

#### Scenario: Other technician excluded (pytest)
- GIVEN another technician owns an appointment in the same range
- WHEN the current technician requests the agenda
- THEN that appointment is absent regardless of request parameters
### Requirement: SS-TECH-2 — Read-Only Privacy Contract

Technician agenda reads MUST be read-only and MUST expose only customer name, address, comuna, phone, appointment service, the appointment's own status, `emergency`, `priority`, and brief `Case.summary`. `emergency` and `priority` are properties of the visit the technician is walking into, not panel workflow state. Operational fields are the panel's workflow state: `responsible_id`, `reminder_count`, `ack_by`, `notified_at`, `bundle`, and `history`. The agenda MUST NOT expose those operational fields, email, consent, conversation/message history, internal notes, or calendar sync.

#### Scenario: Allow-list response (pytest)
- GIVEN an appointment and case with all fields populated
- WHEN the technician endpoint responds
- THEN the serialized key set is exactly the approved allow-list, including `status`, `emergency`, and `priority`

#### Scenario: Anonymous or forbidden read (pytest)
- GIVEN no session or a user without technician ownership
- WHEN the technician agenda is requested
- THEN JSON 401 or 403 is returned and no appointment data is disclosed
