# Cortex-session Specification

## Purpose

Provide an explicit, durable planning session attached to one authenticated panel thread, with a conditional, admin-confirmed handoff of a captured action to a verified assistant turn.

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

### Requirement: CS-4 — Conditional SDB handoff offer

On close, when the session captured a concrete action (a `next_step` note), the agent MUST offer to hand that action off to execution and MUST NOT infer the handoff from conversation text. The handoff MUST be triggered only by the authenticated administrator's explicit confirmation, reusing the admin-only `sdb_requested` flag; a non-admin MUST NOT trigger it. The planning session MUST stay read-only for the business: execution runs as a normal assistant turn (the normal loop plus verification) after confirmation, in the same thread.

#### Scenario: Offer with a concrete action
- GIVEN a closed session that captured a next step
- WHEN the report is produced
- THEN the agent offers the handoff and waits for the administrator's explicit confirmation

#### Scenario: No concrete action
- GIVEN a closed session without a captured next step
- WHEN the report is produced
- THEN no handoff is offered and only the report stands

#### Scenario: Explicit administrator confirmation
- GIVEN an offered handoff
- WHEN the administrator confirms it
- THEN a normal assistant turn runs in the same thread carrying the admin-only handoff flag, and verification applies

#### Scenario: Non-admin or free text
- GIVEN a non-admin user, or conversation text that suggests a handoff without an explicit confirmation
- WHEN a handoff would be triggered
- THEN it is refused and no handoff runs

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
