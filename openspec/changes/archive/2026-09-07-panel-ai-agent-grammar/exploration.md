# Exploration: Panel AI-Agent Grammar

## Status

ready

## Executive summary

The archived `panel-shell-ai-agent` change delivered the infrastructure seam only: native History routing, production shared-helper promotion, and tokenized shell CSS while explicitly preserving the previous visual behavior. The approved `AiAgentGrammar` story is therefore still a concept surface, not the production shell.

The next visual slice should keep the existing `AppShell` → `PanelShell` seam and evolve it into a reusable agent-app frame: forest rail, brand and role-safe navigation, a clearly separated `Conversaciones activas` region, conversation-oriented header/content/composer rhythm, and an optional operational inspector for conversation detail. It should not add WebSocket, streaming, event activity persistence, or new backend behavior; those belong to the next conversational/realtime change.

The design-system boundary is important: conversation and internal-agent views should adopt the agent-app grammar, while dashboard, customers lists, cases, knowledge base, settings, agenda, automation, and dense sections of the client ficha retain the control-room primitives (tables, KPI cards, badges, dividers, and explicit state treatment).

## Current state

- `PanelShell.tsx` is a 367-line class-based shell with a two-column desktop layout, mobile drawer, keyboard focus management, collapsed sidebar, role-filtered `NAVIGATION`, and a single page header. It has no active-thread region, conversation context, central thread slot, or inspector slot.
- `AppShell.tsx` is a 94-line native History API dispatcher for 11 views plus client/conversation/automation drill-down routes. It always renders one `PanelShell` around one page component and does not pass route context into shell chrome.
- `AiAgentGrammar.stories.tsx` is the approved visual target: 15rem/4rem rail states, navigation plus active threads, forest/lime selection treatment, central message bubbles and activity chips, handoff banner, reply-window composer states, and an 18rem operational inspector. Its styles are story-local and use existing tokens.
- Production `ConversationThread.tsx` still presents messages as a `DataTable`, uses short state-control labels (`Tomar`, `Devolver`, `Cerrar`), and has a basic textarea composer. It already has the real reply-window, mutation, retry, and error behavior that visual work must preserve.
- Production `ConversationsList.tsx` is a control-room `DataTable` with state/responsible filters. Its API response contains conversation state, responsible ID, timestamps, and customer ID, but not a customer display name.
- Production `AgentChat.tsx` has persisted internal-chat behavior and a textarea/button, but no avatars, bubbles, activity treatment, or conversation-oriented layout.
- `ClientFicha.tsx` is a dense operational record: identity card, memory surface, notes, visits, and history tables. It should receive consistent shell/chrome treatment, not be converted into a chat surface; its history tables remain control-room primitives.
- `ChatWithAgent` and `InboxThread` stories already demonstrate the relevant bubble, state-control, reply-window, stale, and processing contracts, but are story-local and explicitly do not wire production.
- The token system already covers the concept grammar: `--primary-800/700/100/200`, `--surface`, `--bg`, `--border`, semantic pairs/tints, spacing, radii, typography, focus, motion, brand lime/cyan/aqua, and `--info`. There are no dedicated rail, bubble, inspector, or activity-chip tokens; add semantic tokens only if repeated consumers prove that existing roles are insufficient.

## Affected areas

- `web/src/components/domain/PanelShell.tsx` — add semantic shell regions and an active-thread chrome contract without breaking drawer, collapse, role filtering, focus, or mobile behavior.
- `web/src/components/domain/AppShell.tsx` — identify conversation routes and pass shell context/optional inspector/thread data; preserve the existing History API route table.
- `web/src/components/domain/panelRoutes.ts` — likely route-context helper only if the visual shell needs a stable conversation-detail predicate; no router dependency.
- `web/src/components/primitives/primitives.css` — move the approved grammar into the existing tokenized stylesheet boundary; preserve the control-room baseline and responsive/reduced-motion rules.
- `web/src/tokens/tokens.css` — likely no new tokens initially; validate existing roles against rail, bubbles, activity chips, handoff, and inspector. Any additions need a real repeated consumer.
- `web/src/components/pages/ConversationThread.tsx` — primary production visual target: table-to-thread presentation, approved labels, activity/handoff slots where data exists, composer rhythm, and explicit reply-window treatment while preserving current API behavior.
- `web/src/components/pages/ConversationsList.tsx` — retain the dense table as the list surface, but align page/header/filter chrome and active-row treatment with the agent-app language.
- `web/src/components/pages/AgentChat.tsx` — restyle as a conversation surface using existing persisted internal-chat behavior; do not add realtime transport.
- `web/src/components/pages/ClientFicha.tsx` — adopt shared shell/page rhythm and inspector-like hierarchy only where useful; retain cards, memories, notes, and history tables.
- `web/src/stories/pages/ChatWithAgent.stories.tsx` and `web/src/stories/pages/InboxThread.stories.tsx` — promote the approved visual contracts from story-local inline styling into production-consumable patterns or wrappers, without changing their data ownership.
- `web/src/stories/concept/AiAgentGrammar.stories.tsx` and its test — remain the visual reference and should become a traceable acceptance/state matrix, not the production implementation.
- `web/src/components/domain/AppShell.test.tsx`, `web/src/stories/domain/AppShell.stories.test.tsx`, page tests, story tests — update shell assertions and add grammar behavior/state coverage.
- `app/panel/api/routes/conversations.py`, `web/src/api.ts`, `web/src/types.ts` — inspect only for compatibility. A future active-thread endpoint/display-name join may be needed; do not expand backend scope in this change.

## Active-conversation rail scope

`Conversaciones activas` cannot be fully data-backed by the current shell contract without additional decisions. `listConversations()` provides state and recency, but not customer names, and the shell currently has no data-fetching boundary. The production endpoint can technically return all conversations, but using it directly in persistent chrome would couple every page to network/loading/error behavior and would still require a customer-name strategy.

Recommended B scope: build the rail as structural chrome with an explicit optional data contract (`activeThreads` plus loading/empty/error states), and render a truthful empty/placeholder state when no data is supplied. Do not fabricate live threads and do not fetch from `PanelShell`. C should decide and wire the live source, customer-name enrichment, unread/freshness semantics, and realtime updates. Open product question: should C add a dedicated active-conversation summary endpoint, or compose existing conversation and customer endpoints?

## Page classification

### Agent-app grammar

- Conversation detail / human inbox: bubbles, direction, owner/status badge, handoff treatment, reply-window banner adjacent to composer, direct state actions, and optional inspector.
- Internal `AgentChat`: bubbles, avatars, agent-processing status, composer, and failure/retry treatment.
- Conversation list: still a dense table, but with agent-app page chrome, explicit active/human leading treatment, freshness, and direct drill-down affordance.
- Shared shell on all routes: forest rail, lime selection geometry, role-safe nav, active-conversation region, compact/expanded behavior, and consistent content rhythm.

### Control-room grammar remains authoritative

- Dashboard KPIs and motives.
- Clients list and the dense history regions of `ClientFicha`.
- Cases, agenda, knowledge base, settings, notifications, and automation rules.
- Tables, KPI cards, badges, filters, and operational state messages everywhere, including inside the inspector when showing structured facts.

This is a hybrid grammar, not a full conversion of every page into a chat layout.

## Approaches

1. **Shell-only chrome with page restyling** — evolve `PanelShell` and apply conversation classes/layouts to existing pages; active threads are optional shell data.
   - Pros: smallest change, preserves route/data contracts, clean boundary for C, matches the archived seam and design-system migration rules.
   - Cons: inspector and thread activity need explicit visual slots; some story-local patterns must be promoted carefully.
   - Effort: Medium

2. **New global three-column shell for every route** — always render rail, main, and inspector regions.
   - Pros: visually uniform desktop frame.
   - Cons: wastes working area on tables/settings, contradicts the design system's no-redundant-chrome rule, creates empty inspector semantics, and increases responsive complexity.
   - Effort: High

3. **Dedicated conversation shell/page fork** — leave `PanelShell` mostly unchanged and introduce a separate shell only for conversation routes.
   - Pros: isolates chat layout.
   - Cons: violates the product decision that the whole panel adopts the agent-app shell language and duplicates nav/drawer/accessibility behavior.
   - Effort: High

## Recommendation

Choose Approach 1. Make the global shell read as an agent application through rail/navigation/active-thread chrome and consistent interaction language, but make the conversation detail region adaptive rather than universal. Use semantic slots or narrow props for active-thread data and an optional inspector; keep route ownership and API behavior in `AppShell`/pages. Restyle `ConversationThread`, `AgentChat`, and the conversation list first, then align `ClientFicha` and other pages through shared page chrome without replacing their dense primitives. Keep WebSocket, streaming truth, activity-event data, unread state, and active-thread backend composition for C.

## Testing needs

- Preserve all existing `AppShell.test.tsx` coverage for native routing, role-safe admin nav, mobile drawer, collapse, focus, deep links, and `aria-current`.
- Extend shell tests for expanded/collapsed active-thread region, selected thread semantics, missing/loading/empty/error rail states, optional inspector presence, responsive class/state behavior, and no injected shell style.
- Add source/CSS contract tests proving grammar styles use existing tokens, no hard-coded colors, accessible labels are retained, and dense page primitives remain present.
- Extend `ConversationThread.test.tsx` for bubble direction, owner/status labels, handoff/reply-window hierarchy, approved action labels, disabled reasons, retry/error behavior, and keyboard composer flow.
- Extend `AgentChat.test.tsx` for bubble/role rendering, processing state, empty state, failed message retry, and composer disabled semantics.
- Extend `ConversationsList` and `ClientFicha` tests only for chrome/selection and unchanged table/state behavior; do not duplicate table contract coverage.
- Keep concept/story tests as the visual state matrix: expanded/compact rail, inspector visible/hidden, emergency/visit, enabled/streaming/window-closed/not-taken composer. Add production story coverage for narrow, medium, desktop, loading, empty, stale, error, and permission states.

## Backend gaps and non-goals

- Current conversation list lacks customer display names and a purpose-built active-thread summary. This is a C/backend follow-up, not a reason to invent a B endpoint.
- Current production conversation payload has no persisted agent activity events for `clasificó`, `buscó KB`, or `derivó`; B may provide visual slots only. C owns real activity/streaming data and WebSocket behavior.
- No new WebSocket, polling loop, streaming indicator backed by fake state, unread counter, event store, serializer redesign, permissions model, or API contract should be implemented here.

## God nodes consulted

Graphify was queried before code inspection. Relevant god/community nodes and edges consulted:

- God/community nodes: `AppShell.tsx` (community hub), `PanelShell.tsx`, `PanelShell()`, `NAVIGATION`, `AiAgentGrammar.stories.tsx`, `activeThreads`, `ConversationsList.tsx`, `ConversationThread.tsx`, `AgentChat.tsx`, `ClientFicha()`, `StatusBadge.tsx`, `tokens`, `DESIGN_SYSTEM.md (taste authority)`, `primitives.css (tokenized shell CSS boundary)`, `api/routes/conversations.py`, `Conversation`, `Message`.
- `AppShell.tsx --imports_from--> ConversationsList.tsx` (direct extracted edge).
- `PanelShell.tsx --imports_from--> Avatar.tsx <--imports_from-- AiAgentGrammar.stories.tsx` (two-hop path connecting current shell and approved concept primitives).
- The graph report identifies the `AppShell.tsx` community as containing the route table, shell, and production page dispatch; the `panel-shell-ai-agent` community contains the archived infrastructure boundary; the `AiAgentGrammar.stories.tsx` community contains the approved visual target; and the `Lumat Panel Design System` community contains the token/primitive contracts.
- `tokens.css` to `primitives.css` had no direct graph path; the source inspection verified the practical relationship through the tokenized stylesheet boundary and `main.tsx` import contract.
- Graph freshness: report built from commit `de6c63f6`; no refresh was run during exploration.

## Risks

- A global three-column implementation could degrade tables and settings by consuming working width; keep inspector and thread-area regions conditional.
- Fetching conversations inside `PanelShell` would create hidden network coupling, duplicate page fetches, and undefined loading/error semantics.
- Reusing raw `bot`/`human` values in new chrome would violate approved user-facing vocabulary; use `StatusBadge` labels and explicit state text.
- Converting the existing message table without preserving delivery/retry/error and reply-window semantics would be a behavioral regression disguised as visual work.
- Story-local inline styles and production `PageFrame` style injection can cause duplicate visual contracts; promote only stable, repeated patterns and keep the stylesheet boundary tokenized.
- The current graph is older than the latest local work; it is suitable for relationship mapping, but exact behavior was verified against source files.

## Next recommended

Create the proposal/design around a conditional agent-app shell: global rail and active-thread slot, conversation-only thread/composer/inspector regions, and unchanged control-room dense primitives. Resolve the single scope question with the product owner before implementation: should B render only structural active-thread chrome, or may it consume a temporary existing conversation list adapter? Default recommendation is structural chrome with no shell-owned fetch.

## Artifacts

- `openspec/changes/panel-ai-agent-grammar/exploration.md` — this exploration.
- Engram observation — topic `sdd/panel-ai-agent-grammar/explore`, type `architecture`, matching this content, prompt capture disabled.

## Skill resolution

- Loaded `/home/stefan/repos/lumat-agent/.opencode/skills/cortex-persona/SKILL.md`.
- Loaded `/home/stefan/.config/opencode/skills/graphify/SKILL.md`.
- Loaded `/home/stefan/repos/lumat-agent/.opencode/skills/design-agent-lead/SKILL.md` because token/design-system mapping is in scope.

## Ready for proposal

Yes. Proceed after recording the active-thread data decision; no backend or realtime design is required for this visual slice.
