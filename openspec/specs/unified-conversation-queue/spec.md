# Unified Conversation Queue Specification

## Purpose

Provide one operational queue for conversations and their linked cases, with a testable read contract and focused operator actions.

## Requirements

### Requirement: UCQ-1 — Queue Read Contract

The panel MUST expose an authenticated conversation list whose rows include conversation data plus nullable selected case context: `case_id`, `emergency`, `acknowledged_at` or equivalent acknowledgement state, `status`, and `priority`. The endpoint MUST accept `q`, `limit`, and `offset`, return total/count data sufficient for live tab counts, and apply the same case selection rule to list and detail payloads.

#### Scenario: Filtered paginated queue (pytest)
- GIVEN authorized conversations with customer names, phone numbers, summaries, and cases
- WHEN the list is requested with `q`, `limit`, and `offset`
- THEN only matching rows and the requested page are returned with embedded case context and count data

#### Scenario: Multiple cases select operationally relevant case (pytest)
- GIVEN one conversation has multiple cases, including an unacknowledged emergency
- WHEN list and detail payloads are requested
- THEN both select the same case, preferring unacknowledged emergency, then open/unacknowledged case, then the newest remaining case

### Requirement: UCQ-2 — Operational Ordering and Tabs

The queue MUST offer tabs `Todas`, `Humanas`, `Emergencias`, `Casos`, and `Cerradas`, with live counts. Default ordering MUST place unacknowledged emergencies first, human-owned conversations next, active bot conversations by recency next, and closed conversations last. Filtering MUST match the selected tab, and closed rows MUST be available through `Cerradas`.

#### Scenario: Priority ordering (vitest)
- GIVEN rows containing an unacknowledged emergency, human-owned, bot-active, and closed conversations
- WHEN `Todas` renders
- THEN rows appear in the specified priority order and tab counts match the returned count contract

#### Scenario: Tab filtering (vitest)
- GIVEN queue data across all supported categories
- WHEN `Emergencias`, `Casos`, or `Cerradas` is selected
- THEN only the matching rows render and the selected tab is accessible

### Requirement: UCQ-3 — Search, Pagination, and Quick Actions

The queue MUST provide an accessible search input for client, phone, or summary, simple limit/offset pagination, and row actions `Tomar` and `Reconocer` when applicable. It MUST NOT render a KPI row, cursor controls, virtualization, or infinite-scroll controls. Returned rows MUST render directly so all rows in the current page remain observable in the DOM.

#### Scenario: Search and page navigation (vitest)
- GIVEN the queue is loaded
- WHEN an operator enters a search term or changes page
- THEN the corresponding `q`/`limit`/`offset` request is made and the page reflects the response

#### Scenario: Emergency acknowledgement (pytest/vitest)
- GIVEN a row has an unacknowledged emergency
- WHEN `Reconocer` is activated
- THEN the existing case acknowledgement mutation is called and the row/counts refresh from authoritative data

### Requirement: UCQ-4 — Flexible Case Data

The workspace queue contract MUST expose `captured_data` as optional arbitrary key/value data. The UI MUST render present keys and values in a collapsible block and MUST render an empty state when absent; it MUST NOT require a fixed schema.

#### Scenario: Arbitrary captured data (vitest)
- GIVEN captured data contains unknown keys and mixed scalar values
- WHEN the block is expanded
- THEN each key/value is visible without schema-specific assumptions
