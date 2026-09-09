# Delta for service-scheduling

## ADDED Requirements

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

Technician agenda reads MUST be read-only and MUST expose only customer name, address, comuna, phone, appointment service, and brief `Case.summary`. They MUST NOT expose email, consent, conversation/message history, internal notes, calendar sync, or operational fields.

#### Scenario: Allow-list response (pytest)
- GIVEN an appointment and case with all fields populated
- WHEN the technician endpoint responds
- THEN the serialized key set is exactly the approved allow-list

#### Scenario: Anonymous or forbidden read (pytest)
- GIVEN no session or a user without technician ownership
- WHEN the technician agenda is requested
- THEN JSON 401 or 403 is returned and no appointment data is disclosed
