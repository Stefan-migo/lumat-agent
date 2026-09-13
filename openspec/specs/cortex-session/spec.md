# Cortex-session Specification

## Purpose

Provide an explicit, durable planning session attached to one authenticated panel thread, with an honest approved-plan handoff to SDB.

## Requirements

### Requirement: CS-1 — Explicit lifecycle and fail-closed gate

The system MUST persist a thread-level Cortex flag and validate it on every turn. Missing or invalid state MUST fail closed. Sessions MUST be opened and closed only by the UI controls or literal `/planning <topic>` and `/planning close`; free text MUST NOT infer lifecycle. One session MUST exist per thread, and reopening MUST reactivate the thread.

#### Scenario: Open and reopen
- GIVEN an authorized administrator and a thread without an active session
- WHEN they use the planning button or `/planning budget review`
- THEN one Cortex session is opened for a new thread and its active indicator is visible

#### Scenario: Invalid state or free text
- GIVEN missing/invalid Cortex state or ordinary text containing planning language
- WHEN a turn is submitted
- THEN the turn does not activate or bypass the lifecycle gate

### Requirement: CS-2 — Visible turn loop

An active session MUST classify each turn as `question`, `research`, `decision`, `continue`, or `close`. Question and research turns are valid without a decision. The active UI MUST show a visible Cortex indicator.

#### Scenario: Valve permits clarification
- GIVEN an active session
- WHEN the agent classifies a turn as question or research
- THEN it responds or performs bounded read-only research without requiring a decision artifact

#### Scenario: Close command
- GIVEN an active session
- WHEN the administrator uses the close button or `/planning close`
- THEN the session produces its closing report and becomes closed

### Requirement: CS-3 — Durable artifacts and merged state

Each decision MUST persist to Tukulpan as `cortex-session/{slug}:decision:{n}`, type `DECISION`, scope `panel`, entity `thread:{id}`. Closing MUST persist `cortex-session/{slug}:report`, type `SUMMARY`, and status `closed`. State under `assistant_state["cortex_session"]` MUST be explicitly merged without clobbering existing keys.

#### Scenario: Multiple decisions survive reload
- GIVEN two accepted decisions in one session
- WHEN the thread is reloaded
- THEN both uniquely keyed decision artifacts and merged session state remain available

#### Scenario: Existing state is preserved
- GIVEN assistant state contains unrelated keys
- WHEN Cortex state is persisted
- THEN unrelated keys remain unchanged

### Requirement: CS-4 — SDB handoff approval boundary

On close, the agent MUST propose the session as an SDB `SPEC`; an administrator MUST approve it before SDB proceeds to `APPROVE`. Delivery MUST be labeled as an approved plan and MUST NOT claim execution.

#### Scenario: Approved handoff
- GIVEN a closed session and its report
- WHEN the administrator approves the proposed SDB handoff
- THEN SDB delivers an approved plan

#### Scenario: No approval
- GIVEN a proposed handoff that has not been approved
- WHEN execution is requested
- THEN no execution is claimed or performed

### Requirement: CS-5 — Authenticated browse and reopen

The panel MUST provide authenticated read-only list and detail navigation under “Sesiones de planning”, including reopening a session by opening its thread and reactivating it.

#### Scenario: Browse session
- GIVEN an authorized administrator
- WHEN they open the planning navigation and select a session
- THEN list and detail data show its thread, decisions, report, and status

#### Scenario: Unauthorized read
- GIVEN an unauthorized user
- WHEN they request planning-session data
- THEN the API rejects the request and exposes no session data
