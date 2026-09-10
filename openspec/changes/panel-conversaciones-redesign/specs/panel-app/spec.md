# Delta for panel-app

## MODIFIED Requirements

### Requirement: PNL-APP-7 — Unified Production Conversations

`ConversationsListView` MUST consume the unified queue contract, show case context, tab counts, priority ordering, search, limit/offset pagination, and applicable `Tomar`/`Reconocer` actions. Selecting a row MUST open a workspace whose thread retains current messages, delivery states, and existing conversation mutations. (Previously: the view showed a filtered production list and thread without unified case context, queue tabs, search, pagination, or queue actions.)

#### Scenario: Queue and workspace
- GIVEN the conversations endpoint returns serialized conversations with optional case context
- WHEN the view loads and a row is selected
- THEN the queue fields render and the workspace loads chronological messages plus the selected case context

#### Scenario: Command refresh
- GIVEN a queue row or open thread
- WHEN a take, acknowledge, state, or message command completes
- THEN authoritative queue and thread data refresh while actionable loading/error states remain visible

### Requirement: PNL-APP-12 — Conversation Workspace Context

Conversation routes MUST render the thread as the main workspace area and a RIGHT context panel containing a case block, customer block, and collapsible `captured_data` key/value block when data exists. The panel MUST show explicit emergency, acknowledgement, status, and priority state, preserve direction/owner/handoff/reply-window/retry semantics, and MUST NOT reserve an inspector for non-conversation pages. (Previously: conversation routes had only an optional inspector slot and no required case/customer/captured-data workspace.)

#### Scenario: Loaded workspace (vitest)
- GIVEN a selected conversation with case, customer, and captured data
- WHEN its route renders
- THEN the thread is primary, the context panel is on the right, and all three context blocks are accessible

#### Scenario: Missing optional context (vitest)
- GIVEN a conversation without a case or captured data
- WHEN the workspace renders
- THEN the customer/thread remain usable, absent blocks show no fabricated data, and no empty inspector is reserved elsewhere

#### Scenario: List chrome alignment (vitest)
- GIVEN `ConversationsList` renders loading, empty, error, or rows
- WHEN its page chrome is inspected
- THEN queue tabs, search, pagination, and selected-row treatment use the agent-app grammar while state behavior remains actionable

### Requirement: PNL-APP-21 — Unified Cases Compatibility Route

The Conversations destination MUST be the unified operational section; `/panel/app/cases` MUST soft-redirect or resolve to it with the `Casos` tab active. `CasesList` MUST no longer be the rendered owner of that route, while existing case mutation semantics remain available from the unified workspace. (Previously: a `Conversaciones|Casos` segment rendered `CasesList` as a separate surface and the alias preserved that ownership.)

#### Scenario: Bookmarked cases route (vitest)
- GIVEN an authenticated user opens `/panel/app/cases`
- WHEN the SPA parses the path
- THEN the unified conversations view renders with `Casos` selected and no standalone `CasesList` page is mounted
