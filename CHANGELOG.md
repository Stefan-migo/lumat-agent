# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses CalVer in the `YYYY.MM.N` format.

## [Unreleased]

## [2026.09.1] - 2026-09-08

This is a retroactive release tag: `v2026.09.1` was created on 2026-09-20 for
the production deploy that began on 2026-09-08 and was not tagged at the time.

### Added

- Production WhatsApp webhook ingestion with verification, signed requests, and durable message handling.
- Conversational agent workflows for intake, intent routing, knowledge-based responses, emergency detection, and human handoff.
- Customer records, conversation history, cases, and operator controls in the authenticated administration panel.
- Knowledge-base ingestion and retrieval for customer-facing answers and operator management.
- Appointment scheduling with technician availability, conflict prevention, cancellation, rebooking, and calendar export.
- Durable notification delivery with retries, emergency fallbacks, and versioned channel templates.
- Realtime conversation updates and internal agent chat for authorized panel users.
- Event outbox processing, deterministic automation rules, notification center, and browser push fallback flows.
- Operational dashboards with configurable summaries, trends, and metric drill-downs.
- Installable React panel shell with service-worker caching for the static application shell.
- Production operations and security controls covering deployment, hardening, backups, monitoring, and audit logging.
