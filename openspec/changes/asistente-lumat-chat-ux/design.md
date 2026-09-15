# Design: Asistente Lumat Chat UX

## Technical Approach

Recompose `AgentChat` as one centered, light-theme conversation surface inside the shell. Use shipped primitives and `tokens.css`; add no dependency or token value change. Preserve SSE, approval, recovery, attachments, deep links, tier metadata, and planning APIs. D5, D6, and dark mode are out of scope.

## Architecture Decisions

| Decision | Choice | Rationale / tradeoff |
|---|---|---|
| Composition | `PageFrame` header actions, `Popover` history, closed context drawer, centered ~48rem column; inline `PlanCard`/`EvidenceList`; auto-growing composer. | ChatGPT grammar on Lumat’s light service-workspace language; rewrite zone/tab tests. |
| Existing system | Reuse `Avatar`, `Badge`, `Button`, `Card`, `Dialog`, `Popover`, `Textarea`, `StateMessage`, `EmptyState`; CSS stays token-based. | `web/package.json` has React, React DOM, and approved Radix menu. No markdown package or font; use `pre-wrap` and a fenced-code splitter. |
| Responsive behavior | Retain `COMMAND_CENTER_BREAKPOINTS` and `commandCenterTier`; compact/tablet reflow to one column, desktop centers the readable column. | `AgentChat.tsx:37-39,82` still uses this metadata; critical actions remain reachable. |
| Planning (D3) | Replace `globalThis.prompt` with the native `Dialog`: title/label “Tema de planificación”, required input with initial focus, native focus trap, Escape/cancel without an API call, and `Cancelar`/`Iniciar planificación`. Trim and reject empty input before `openPlanningSession(topic, thread.id)`. Keep the assistant entry point and `Sesiones de planning`; duplication is accepted. `/planning <topic>` and `/planning close` continue converging on `openPlanningSession`/`closePlanningSession`. | Accessible, testable, context-bound entry while preserving both existing lifecycle APIs and the durable planning read surface. |
| Thread identity (D7–D11) | Opening the page does not create a thread; `Nuevo chat` calls the existing creation endpoint. Navigator rows render only generated/renamed title, relative time, and visible active marker—never status. If status appears in the context drawer, translate it using approved Spanish labels. Filter empty owned threads, group `Hoy`/`Últimos 7 días`/`Anteriores`, and order by latest message `created_at, id` descending. | The status has no meaning in this private assistant list; identity and ordering become predictable. |
| Title lifecycle (D8) | Add nullable `title`; generate inline after the first assistant response only when `title IS NULL` and `internal_thread_cost_state` is `normal`, attributing the call to the first assistant message through `record_llm_cost`. | The title source is the earliest `author='admin'` row ordered by `created_at, id`. `title_or_preview` is wrong because it serializes the latest row regardless of author and can expose a long agent answer. Replace it with nullable `title` in the summary shape. Generated titles are one-time and bounded; rename overwrites them. Title exceptions are swallowed and fallback stored. The fallback selects that same opening user message and truncates it in `app/services/agent_chat.py` before persistence (bounded UTF-8 text); non-normal mode, timeout, or failure never charges. |
| Capabilities | Move `AssistantCapabilitiesView` out of `AgentChat` and render it in the admin `web/src/components/pages/Settings.tsx` host, using the existing `/panel/api/assistant/capabilities` contract. | Keeps static tool reference with Configuración, without inventing a settings surface or changing permissions. |

## File Changes

| File | Action | Description |
|---|---|---|
| `web/src/components/pages/AgentChat.tsx`, `web/src/components/primitives/primitives.css` | Modify | Composition, navigator, drawer, composer, inline blocks, Spanish states, D3 dialog. |
| `web/src/components/pages/Settings.tsx` | Modify | Capabilities host. |
| `web/src/api.ts`, `web/src/types.ts` | Modify | Title and CRUD contracts. |
| `app/models.py`, `app/panel/api/serializers.py`, `app/panel/api/routes/chat.py`, `app/services/agent_chat.py` | Modify | Model, summary, ownership/CRUD, filtering/order, D4, title lifecycle, explicit creation. |
| `db/migrations/025_internal_chat_thread_title.sql` | Create | Add nullable `title`. |
| `web/src/components/pages/AgentChat.test.tsx`, `web/playwright/command-center.spec.ts`, backend assistant tests | Modify | RED coverage for UX, lifecycle, cost/fallback, ownership, preserved contracts. |

## Interfaces / Contracts

`PATCH /panel/api/chat/threads/{id}` accepts `{ "title": string }`; `DELETE` and all thread routes enforce existing ownership checks. Summaries replace `title_or_preview` with nullable `title` and expose timestamps for grouping/relative time; status is absent from navigator rows. `PlanCard` and `EvidenceList` remain in `AgentChat.tsx`.

## Testing Strategy

Backend tests cover migration, creation, title gate/cost/fallback, CRUD, filtering/order, ownership, and Spanish failures. Tests cover dialog keyboard behavior, commands, layout/reflow, inline execution, composer/message affordances, streaming, attachments, recovery, deep links, navigator grouping, and Settings capabilities. Run `uv run pytest tests/`, `cd web && npm test`, `npx tsc -b`, and Playwright.

## Threat Matrix

N/A — no shell commands, subprocesses, VCS/PR automation, executable-file classification, or process-integration boundary is introduced; HTTP route ownership and input bounds are covered by the API tests above.

## Migration / Rollout

Apply additive migration `025` before deploying API/UI together. Existing rows receive fallback titles when eligible; code rollback may retain the nullable column. Deployment migration permissions remain an operational prerequisite.

## Open Questions

- [ ] D5 remains out of scope; reproduce separately if it recurs.
- [ ] Confirm deployment database migration permissions before rollout.

## Graph Check

Consulted nodes `AgentChat()`, `Dialog()`, `PanelShell()`, `Settings.tsx`, `PlanningSessions.tsx`, `openPlanningSession()`, `closePlanningSession()`, `listChatThreads()`, `chat.py`, `serializers.py`, `InternalChatThread`, and `record_llm_cost`. Edges: `AgentChat` → `api.ts`/`panelRoutes.ts`; `chat.py` → `api/deps.py`; Cortex lifecycle connects `AgentChat`/`PlanningSessions` to open/close APIs. `BackgroundTasks` is only post-response webhook work (`app/webhook/router.py:46-70`); `get_db` finalizes/closes request sessions, supporting inline generation.
