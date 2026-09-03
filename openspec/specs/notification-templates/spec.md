# Notification Templates Specification

## Purpose

Manage versioned, policy-compliant notification content.

## Requirements

### Requirement: NTP-1 — Versioned Templates

The system MUST store immutable template versions with event, channel, locale, approval/policy status, and required variables. Rendering MUST identify the selected version.

#### Scenario: Render approved version
- GIVEN an approved template with all required variables
- WHEN a notification is rendered
- THEN output is produced and records the template version

#### Scenario: Missing variable
- GIVEN a required variable is absent
- WHEN rendering is requested
- THEN rendering fails without creating a sendable operation

### Requirement: NTP-2 — Channel Policy

The system MUST reject a template/channel combination that violates configured WhatsApp approval or SMTP policy, and MUST preserve prior versions when a new version is published.

#### Scenario: Unapproved WhatsApp template
- GIVEN a business-initiated WhatsApp message uses an unapproved template
- WHEN policy validation runs
- THEN delivery is rejected and the rejection is audited
