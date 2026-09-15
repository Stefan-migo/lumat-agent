# Delta for Internal Agent Chat

## ADDED Requirements

### Requirement: IAC-10 — Explicit Threads and Accessible Planning

Opening the assistant MUST NOT create a thread. Thread creation SHALL be explicit through `Nuevo chat`. Planning SHALL open in an accessible in-app dialog, not a browser prompt, and MUST preserve the existing open/close lifecycle.

#### Scenario: Visit without creation
- GIVEN an authenticated user opens the assistant without `thread_id`
- WHEN the page loads
- THEN no thread or audit row is created and `Nuevo chat` remains available

#### Scenario: Planning dialog
- GIVEN an authenticated user chooses planning
- WHEN the control is activated
- THEN an in-app dialog with Spanish label, keyboard focus, Escape, and cancel/confirm actions opens

### Requirement: IAC-11 — Conversation Affordances and Inline Evidence

The conversation MUST render plan approval and tool evidence inline, anchored to the message that produced them. The composer SHALL be one auto-growing bar with inline attachment, Enter-to-send, Shift+Enter newline, and disabled processing state. Messages MUST expose timestamp, copy, retry in place for failures, and a visible streaming cursor.

#### Scenario: Anchored execution output
- GIVEN a message produces a plan or tool evidence
- WHEN the conversation renders
- THEN its approval card or evidence disclosure appears directly in that message's flow, not above the list

#### Scenario: Composer and recovery
- GIVEN the composer contains text or a failed message exists
- WHEN the user presses Enter, Shift+Enter, or `Reintentar`
- THEN Enter sends, Shift+Enter inserts a newline, and retry resubmits in place while preserving content

### Requirement: IAC-12 — Thread Identity and Title Lifecycle

The navigator MUST expose titled, non-empty, owned threads with predictable ordering, active state, grouping, and relative timestamps, plus rename and confirmed delete. A title SHALL be generated once after the first assistant response only when NULL and cost mode is `normal`; generation MUST use `record_llm_cost`. Any failure or non-normal mode MUST use a truncated first-user-message fallback. `Thread #N` MUST NOT be user-visible.

#### Scenario: Title and fallback
- GIVEN the first assistant response is persisted and the title is NULL
- WHEN cost state is checked
- THEN normal mode generates and accounts for one title, while every other mode or failure stores/displays the free truncated first-user fallback

#### Scenario: Navigator actions
- GIVEN the user owns a populated thread
- WHEN the navigator is opened
- THEN the active item, `Hoy`/`Últimos 7 días`/`Anteriores`, relative time, rename, and delete-with-thread-name confirmation are available; empty threads are absent

### Requirement: IAC-13 — Preserved Execution Contracts

The assistant MUST preserve realtime streaming, approval, `active_run_id` recovery, attachments, planning open/close, the `?thread_id=` deep link, and tier behavior.

#### Scenario: Existing interaction contracts
- GIVEN an authorized user streams, approves, recovers, attaches, opens/closes planning, or follows `?thread_id=` at a supported tier
- WHEN the assistant handles the interaction
- THEN event, approval, recovery, attachment, lifecycle, deep-link, and responsive behavior remains functional

## MODIFIED Requirements

### Requirement: IAC-4 — Conversation Surface Presentation

`AgentChat` MUST present persisted messages with direction, identity, empty/loading/error states, recovery, and a composer while preserving approval and tier behavior. Transient streaming MUST NOT replace persisted history.
(Previously: the surface had a labeled composer and did not define the complete chat affordance contract.)

#### Scenario: Persisted and processing states
- GIVEN a thread is empty, loading, or processing
- WHEN `AgentChat` renders
- THEN the Spanish state is visible and the composer is disabled only while processing

#### Scenario: Approval and recovery remain durable
- GIVEN an authorized user receives approval or a recoverable run
- WHEN the stream ends, reconnects, or reloads
- THEN approval remains explicit and persisted recovery state remains authoritative

#### Scenario: Failed message is recoverable
- GIVEN sending fails or returns a failed message
- WHEN the error renders
- THEN a Spanish alert and `Reintentar` affordance appear, submitted content remains recoverable, and persisted messages are not discarded
