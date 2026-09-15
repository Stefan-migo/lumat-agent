# Exploration: UI Command Center v1

## Executive summary

The ui-base change materially changed the starting point: the React shell now has a real Storybook harness, production-owned interaction primitives, responsive navigation, and a working assistant API with SSE and WebSocket updates. The Command Center should therefore be a desktop-first, three-zone assistant workspace built on `AgentChat` and `ConversationThread`, with one narrow reusable shell extension for focus mode; it should not become a second global shell or an offline PWA.

The cortex report's phantom-catalog finding is confirmed in part and needs a precise update: the catalog contains 90 entries, of which 39 point to the nonexistent `src/components/Corporate/` tree, while the current production primitive directory contains 16 component implementations (34 files including tests and CSS). The story-ownership finding is also current: only the two explicitly allowlisted compatibility tests import story helpers; quarantined `ChatWithAgent` and `InboxThread` are not production owners.

## Current State

### Product and shell

The intended information architecture is three zones: threads on the left, the active conversation in the center, and execution context on the right. `AppShell` currently routes `chat` to `AgentChat`, and always wraps the selected page in `PanelShell`. `PanelShell` already owns role-filtered navigation, desktop collapse, a mobile drawer, a mobile footer, notifications, breadcrumbs, focus return, and an optional `inspector` aside. It does not yet expose a named focus-mode contract: collapse is a generic shell toggle and the inspector is only an optional desktop column.

`AgentChat` is functional but single-page and vertically composed. It creates or loads one internal chat thread, renders messages, plans, approval, evidence, attachments, Cortex planning state, and assistant capabilities, and consumes both SSE token events and the shared WebSocket client. `ConversationThread` is a separate production surface for customer conversations; its interactive mode supports take/return/close, human reply-window rules, failed delivery retry, emergency acknowledgment, persisted activity, and WebSocket refresh. These are complementary domains, not interchangeable inbox implementations.

### Existing primitives after ui-base

The production primitive set now includes Button, Input, Textarea, Select, SearchInput, FieldShell, Card, Badge, StatusBadge, Avatar, Tabs, Dialog, Popover, Tooltip, Menu, Combobox, and Skeleton. Native/platform mechanics cover popover, tooltip, dialog, and combobox; Radix is limited to the dropdown menu. The CSS file is globally loaded by Storybook and token-backed.

The remaining Command Center-specific gaps are not generic styling primitives:

- A resizable or responsive split-pane primitive is absent; ui-base explicitly deferred it.
- A command-menu/search-palette primitive with keyboard navigation and thread actions is absent. `Menu` is not a searchable command surface.
- There is no reusable focus-mode shell state or panel visibility contract.
- There is no assistant-specific event timeline/run-status presentation primitive; the current component renders raw plan/evidence/status blocks.
- A scroll-area primitive is not present, although ordinary overflow CSS can cover the first slice.

Do not complete the entire phantom catalog as a prerequisite. Add only primitives justified by the selected zones and their tested states.

### Story ownership and catalog verification

The current story inventory has production-backed page and primitive stories. `ConversationThread.stories.tsx` imports the production `ConversationThread`, but its `BubbleVariant` remains a local markup variant and should not become a Command Center implementation. `ChatWithAgent` and `InboxThread` are under `.storybook/quarantine`, excluded from discovery and Vitest.

The boundary scan found exactly two production-directory imports from stories, both intentional compatibility tests: `web/src/components/shared/closure.test.tsx` and `helpers.test.tsx`. No non-test production component imports from `stories/`. This confirms the corrected cortex claim, not the historical claim that production currently has two story inversions.

The catalog is version `1.2.0` with 90 entries. 39 entries reference `../src/components/Corporate/`; there is no `web/src/components/Corporate/` directory. Thus the catalog is still phantom for that Corporate subset, while the current primitives are real and independently owned. The catalog must not be treated as an implementation manifest for this change.

### Data and API surface

Available assistant endpoints cover:

- create/read internal chat threads;
- send messages and upload attachments;
- SSE run streaming and approval/rejection;
- read-only assistant capabilities;
- open/list/read/close/reopen planning sessions.

The shared WebSocket covers conversation snapshots, activity, message, token, and status updates. Customer conversation endpoints cover queue listing with counts and filters, thread reads, state mutation, replies, retries, and emergency acknowledgment.

The main missing surface for a true left thread zone is a list of internal assistant chat threads with stable title/preview, updated time, status, unread/run state, and pagination or a bounded recent list. `listPlanningSessions` is not a substitute: it lists Cortex sessions, not every assistant conversation. The right zone can initially consume the existing capabilities plus current thread state, plan, approval, evidence, Cortex session, attachment metadata, and connection/run status. A separate agent-configuration endpoint is not justified unless the product requires fields beyond the existing capabilities response.

## Affected Areas

- `web/src/components/domain/AppShell.tsx` — keeps the `chat` route stable and may pass explicit Command Center context; avoid a broad routing rewrite.
- `web/src/components/domain/PanelShell.tsx` — owns the reusable focus-mode contract and responsive panel visibility if that contract is approved.
- `web/src/components/domain/panelRoutes.ts` — only changes if selected thread/deep-link state needs a durable route shape.
- `web/src/components/pages/AgentChat.tsx` — becomes the production composition root for the three zones, preserving existing SSE, approval, attachment, and planning behavior.
- `web/src/components/pages/ConversationThread.tsx` — remains the customer/human-inbox implementation and supplies reusable read-only versus interactive conversation semantics; it should not be duplicated as `InboxThread`.
- `web/src/components/primitives/` — likely adds only split-pane/focus or command-menu behavior if the zone design proves those contracts necessary.
- `web/src/api.ts` and `web/src/types.ts` — need the internal-thread list contract and any explicit context/run serializer fields before the left/right zones are wired.
- `app/panel/api/routes/chat.py` — likely adds the missing owned-thread list endpoint; no inferred write or permission expansion.
- `web/src/stories/pages/` and `web/.storybook/quarantine/pages/` — stories must render production Command Center components; quarantined prototypes are references, not owners.
- `web/.storybook/component-catalog.json` — evidence only; do not expand its 39 phantom Corporate entries as scope.
- `web/DESIGN_SYSTEM.md` — governs calm service-control-room hierarchy, breakpoints, state completeness, Spanish UI copy, and no dark mode/PWA assumptions.

## Open decisions and trade-offs

### 1. Mobile and PWA scope

| Option | Pros | Cons | Effort |
|---|---|---|---|
| Desktop-only, no mobile behavior | Smallest visual scope | Contradicts the already-shipped mobile drawer/footer and leaves operators without a usable narrow route | Low |
| **Responsive mobile web in v1; no installable/offline PWA** | Reuses existing shell behavior, keeps emergency/read-only access available, avoids cache and reconnect correctness risk | Three zones must collapse into an ordered single-column or drawer presentation | Medium |
| Full responsive PWA with offline queue/cache | Strong field resilience | Requires service-worker policy, offline mutation semantics, conflict recovery, and a second verification surface; outside this UI change | High |

**Resolution:** include responsive mobile web behavior in v1 at the existing `<640px`, `640–1023px`, and `>=1024px` tiers. Explicitly exclude installability, offline assistant execution, and offline writes. The mobile presentation should select one active zone at a time rather than squeeze three panels horizontally.

### 2. Global shell versus section-only change

| Option | Pros | Cons | Effort |
|---|---|---|---|
| Section-only composition inside current `PanelShell` | Lowest regression risk; preserves all existing routes | Cannot provide a reusable focus-mode contract and may duplicate collapse behavior | Medium |
| **Small reusable `PanelShell` focus-mode extension plus Command Center section** | Makes the known focus-mode requirement explicit and reusable; keeps navigation authority global | Touches shell CSS/state and requires tests for route restoration, keyboard access, and mobile behavior | Medium |
| Redesign `AppShell`/`PanelShell` globally around the Command Center | Consistent new chrome everywhere | High blast radius, unrelated page regressions, and violates ui-base's deferred shell-redesign boundary | High |

**Resolution:** choose the second option. The global change is limited to a reusable focus-mode/region-visibility contract. `AppShell` remains the route and ownership boundary; the Command Center owns its zones and does not replace global navigation.

### 3. Playwright timing

| Option | Pros | Cons | Effort |
|---|---|---|---|
| Defer all browser automation | No browser dependency or CI setup | jsdom cannot prove split-pane geometry, overflow, breakpoints, focus mode, or resolved CSS tokens | Low |
| **Add a narrow Playwright smoke/geometry suite in v1** | Verifies the declarable visual contract where the primary risk lives; avoids circular screenshot baselines | Adds browser installation and an execution path that currently has no CI | Medium |
| Add full screenshot visual regression now | Strong change detection | Baselines encode implementation unless human-approved, are costly to maintain, and do not judge design quality | High |

**Resolution:** include narrow Playwright verification for panel presence/order, minimum widths/overflow, focus-mode visibility, mobile zone switching, keyboard focus, and resolved token/breakpoint behavior. Defer screenshot baselines and CI integration if infrastructure is not ready; document manual execution rather than claiming jsdom coverage.

### 4. InboxThread disposition

| Option | Pros | Cons | Effort |
|---|---|---|---|
| Promote the quarantined page | Preserves its explicit inbox states and controls | Creates a second owner beside `ConversationThread`; its local clock helper and mock-only state diverge from the production API | High |
| **Delete the quarantined page after preserving useful assertions in production tests** | One contract, no stale copy, and production already has the interactive reply-window/state behavior | Loses a convenient visual reference unless its scenarios are re-expressed as production-backed stories | Low/Medium |
| Keep it indefinitely as reference | Retains design intent | Permanent dead code and ambiguous ownership; it can be mistaken for a supported surface | Low now, high maintenance |

**Resolution:** delete it from the active change after extracting any genuinely missing scenarios into `ConversationThread` stories/tests. Do not promote `InboxThread`; the current production API already supplies `reply_window_open`, state, delivery, and mutation semantics.

## Panel zones and behavior boundary

### Left: thread navigator

Recent internal assistant threads, selected state, last activity, run/approval indicator, and a create-thread action. It should be bounded and scannable, not a second inbox. It requires a new list serializer/endpoint or a deliberate v1 rule of one current thread plus discreet planning-session history.

### Center: assistant conversation

Persisted messages are the durable source of truth. Streaming tokens are transient presentation attached to the active run and must settle into the persisted message when the stream closes. Plan, approval, tool evidence, errors, retry, attachment upload, and Cortex planning handoff remain visible in sequence. Reconnect must reload the thread before presenting the stream as authoritative.

### Right: execution context

Read-only by default: current run stage, plan and approval status, tool evidence, active Cortex session, attachment metadata, connection status, and the validated assistant capability/configuration view. It must never expose a write control merely because a tool is writable; approval remains the explicit action boundary in the center.

### Focus mode

Focus mode hides or minimizes global navigation and secondary context while preserving an escape path, current route, accessible name, keyboard operation, and restoration of the prior shell state. On mobile it should not hide emergency, send, approval, or retry actions; it should switch zones rather than rely on hover or tiny controls.

## Read-only versus streaming rules

The center may stream assistant output; the context panel may update from the same event sequence but remains read-only. Historical messages and evidence are immutable in the UI. Approval, rejection, sending, attachment upload, planning close/reopen, and customer conversation mutations are explicit commands with busy, failure, and recovery states. A disconnected WebSocket must not erase persisted history, and an incomplete SSE run must be represented as recoverable rather than silently successful.

## Graph check consulted

The authoritative `graphify-out/graph.json` was queried before source inspection. Relevant nodes and edges consulted:

- `domain/AppShell.tsx --imports_from--> domain/PanelShell.tsx` (directed edge, 1 hop).
- `AgentChat.tsx` / `AgentChat()` --contains--> `AgentChat()` and `AgentChat.tsx --imports--> `Button()` (undirected path, 2 hops).
- Query results mapped `AppShell`, `PanelShell`, `AgentChat.tsx`, `pages/ConversationThread.tsx`, `panelRoutes.ts`, `api.ts`, `types.ts`, `chat.py`, `ConversationsList.tsx`, `useAsyncData`, `realtime`, `PlanningSessions`, `PageFrame`, and the `AppShell.tsx`, `domain/PanelShell.tsx`, `InboxThread.stories.tsx`, and `ChatWithAgent.stories.tsx` communities.
- Graph report god/community context included `AppShell.tsx`, `domain/PanelShell.tsx`, `AgentChat.tsx`, `Conversation`, `Message`, `chat.py`, `apiFetch`, `types.ts`, and the Cortex planning loop hyperedge.

The report header is one generation behind the supplied graph JSON (it names commit `68a4226a` while the worktree is `040ce318`); the supplied current graph JSON and direct source evidence were used for this exploration.

## Approaches

1. **Production composition with bounded shell extension (recommended)** — Refactor `AgentChat` into three production-owned regions, add only the missing internal-thread list contract and any proven split/focus primitive, and retain current API/event seams.
   - Pros: preserves working behavior, gives one ownership path, makes focus mode reusable, and keeps the change centered on the actual assistant workflow.
   - Cons: requires a small backend read contract and browser-level geometry verification.
   - Effort: Medium

2. **New standalone Command Center page with duplicated state and mock data** — Build a visual shell around the quarantined prototypes, then wire it later.
   - Pros: fast initial screenshot iteration.
   - Cons: repeats the exact Storybook-copy failure, risks divergent streaming/approval semantics, and creates a second owner for inbox-like behavior.
   - Effort: Medium initially, High to reconcile

3. **Global shell redesign plus full component/catalog completion** — Finish the 39 phantom Corporate entries and redesign all panel routes around the new layout.
   - Pros: broad visual consistency.
   - Cons: unrelated scope, high regression surface, contradicts ui-base deferrals, and solves catalog inventory rather than the Command Center job.
   - Effort: High

## Recommendation

Proceed with Approach 1. Define v1 as a responsive mobile-web Command Center with desktop three-zone geometry, a reusable PanelShell focus-mode contract, production-owned `AgentChat` composition, read-only execution context, and streamed center content backed by persisted state. Add the missing internal-thread list API before promising a real left navigator; do not infer it from planning sessions. Use Playwright narrowly for geometry and interaction invariants, while keeping screenshot regression and PWA/offline behavior out of scope. Delete `InboxThread` rather than promote it, and convert any retained scenarios into production-backed `ConversationThread` coverage.

## Risks

- The left-zone requirement is blocked by the absence of an internal chat-thread list endpoint; shipping a fake list would recreate prototype drift.
- Three-zone layouts can become unusable below 1024px; mobile must switch zones and preserve critical actions, not merely shrink columns.
- Focus mode can accidentally hide navigation, approval, retry, or emergency actions; the shell contract needs explicit escape and restoration tests.
- SSE and WebSocket updates have different durability guarantees; transient tokens must never replace persisted messages or imply completion on disconnect.
- The 39 phantom catalog entries can tempt scope expansion; they are evidence of catalog drift, not a Command Center dependency.
- Playwright without CI can become a locally green-only gate; report execution commands and distinguish automated, manual, and unverified evidence.
- Agent capabilities expose writable tools; the right panel must remain informational and preserve approval as the only execution boundary.

## Ready for Proposal

Yes. The proposal should state the four resolutions explicitly: responsive mobile web but no PWA/offline, a narrow reusable focus-mode extension in `PanelShell` but no global shell redesign, narrow Playwright geometry verification but no screenshot baseline/CI commitment, and deletion of `InboxThread` in favor of production-backed `ConversationThread`. It should also include the internal assistant-thread list API as a prerequisite for the left zone and keep catalog completion, broad primitive adoption, and unrelated page redesign out of scope.
