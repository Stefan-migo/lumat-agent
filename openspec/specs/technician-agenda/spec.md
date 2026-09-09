# Technician Agenda Specification

## Purpose

Provide technicians with a strictly owned, privacy-minimal appointment agenda.

## Requirements

### Requirement: TECH-ROLE-1 — Technician Role Migration

The system MUST add `tecnico` to the application role enum through a new numbered SQL migration after the current highest migration. It MUST NOT edit `001_init.sql`, and migration acceptance tests MUST assert the supported role set.

#### Scenario: Additive migration (pytest)
- GIVEN migrations are applied to a clean database
- WHEN the role enum is inspected
- THEN `admin`, `operador`, and `tecnico` are present and `001_init.sql` is unchanged

### Requirement: TECH-AUTH-1 — Technician Login

The existing panel login MUST accept valid tecnico credentials and return the role. Invalid credentials MUST retain the established generic authentication behavior.

#### Scenario: Technician login (pytest)
- GIVEN an active tecnico with valid credentials
- WHEN login is submitted
- THEN the response is 200 with role `tecnico` and a session cookie

### Requirement: TECH-AGENDA-1 — Owned Agenda Endpoint

An authenticated tecnico MUST receive only appointments whose `technician_id` equals the current user id, ordered across past, today, and future appointments. Server-side ownership MUST NOT rely on a client-supplied technician id.

#### Scenario: Owned ordering (pytest)
- GIVEN appointments owned by the technician and appointments owned by another user
- WHEN the technician agenda is requested
- THEN only owned appointments are returned in chronological order across all dates

#### Scenario: Forged ownership (pytest)
- GIVEN a technician supplies another technician id or appointment id
- WHEN the agenda is requested
- THEN no unowned appointment is returned

### Requirement: TECH-PRIVACY-1 — Exact Allow-List Serialization

The dedicated technician serializer MUST contain exactly customer name, address, comuna, phone, appointment service, and `Case.summary` as a brief note. Email, consent, conversations, messages, internal notes, calendar sync, and operational fields MUST never be serialized.

#### Scenario: Exact fields (pytest)
- GIVEN an owned appointment with every related field populated
- WHEN it is serialized for tecnico
- THEN the key set contains only the approved allow-list

#### Scenario: Sensitive fields absent (pytest)
- GIVEN an owned appointment with email, consent, history, notes, sync, and operational data
- WHEN the response is inspected
- THEN none of those fields or values are present

### Requirement: TECH-DENY-1 — Restricted Surfaces

Technico requests to admin, internal chat, and realtime routes MUST return JSON 403 and MUST NOT disclose route data.

#### Scenario: Restricted route denial (pytest)
- GIVEN an authenticated tecnico
- WHEN admin, chat, or realtime is requested
- THEN JSON 403 is returned without a redirect or payload
