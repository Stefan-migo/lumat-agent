# asistente-workspace-refine

## Objective

Continue the **Asistente Lumat** workspace redesign (parent feature `asistente-workspace-redesign`,
AW-7 owner visual-review passes) with structural refinements toward the references
`refs/Diseño Lumat/AgenteLumat/LumatAgentProjectContextWorkspace.png`,
`LumatAgentNewthreadTools.png`, `LumatMulti-AgentWorkspace.png`.

The references show: global icon rail, a **Proyectos** pane (own collapse control, search, project
tree with `Contexto y archivos` / `Historial de hilos`, and an **Agentes del proyecto N** section with
real statuses), a centre with **closable workspace tabs** (project context / threads + `+`), and a
right **Actividad/Contexto del hilo** panel with its own close control.

## Problem (owner visual review, 2026-10-10)

- The two pane-collapse controls live in the **central thread header**; the reference puts each
  control in the side panel's **own header**.
- `Contexto y archivos` / `Historial de hilos` **navigate to another page** instead of opening in the
  centre; the workspace tabs are not the reference's closable workspace tabs.
- The centre action row (`Contexto` / `Planificar` / `Nuevo chat` in `AgentChat.tsx`) and the section
  tabs row (`AssistantTabs`) are out of place.
- The sidebar **Agentes del proyecto** section is a hard-coded stub; the real roster endpoint is never
  called.
- The composer is full-width and lacks the reference's controls.

## Scope (this document = Slice 1 only)

**Slice 1 (this unit): the sidebar.** S1–S4 below.
Later slices (not here): centre tab model, section-tabs removal, composer, header cleanup.

**Out:** palette/tokens; `PanelShell` global chrome; other panel sections; the centre tab model.

## Constraints

- References control geometry/layout, not palette. Reuse shipped primitives.
- Honest UI only: no fabricated agents, counts, threads, or resources.
- Frontend artefacts/tests/commits in English; UI copy neutral Chilean Spanish.
- Conventional Commits, no AI attribution; ≤5 cohesive files per work-unit commit.

## Backend contract (small, required by S2/S3)

**B1 — threads by project.** `GET /panel/api/chat/threads` does not return `proyecto` and has no
filter, so a per-project history/search is impossible today.

- `app/panel/api/serializers.py` — `to_internal_chat_thread_summary_dict`: add `"proyecto": thread.proyecto`.
- `app/panel/api/routes/chat.py` — `list_chat_threads`: add an optional `proyecto: str | None = Query(default=None, max_length=100)`; when provided, add `InternalChatThread.proyecto == proyecto` to the `where`. Keep the cortex-session exclusion and the `limit` bounds.
- `web/src/types.ts` — `InternalChatThreadSummary` gains `proyecto: string`.
- `web/src/api.ts` — `listChatThreads(limit, proyecto?)` appends `&proyecto=<enc>` when provided.
- Tests (backend strict TDD RED→GREEN): the summary includes `proyecto`; `?proyecto=default` returns
  only that project's threads; without the param behaviour is unchanged.

## Work units (stable IDs)

### S1 — Collapse control in each panel header
- [x] Remove the two `.assistant-workspace__pane-toggle` buttons from the central thread header
      (`AssistantWorkspace.tsx:278-280`).
- [x] **Proyectos** pane: put the collapse control in its own header (next to the title/`+`). Collapsed,
      the pane becomes a narrow rail (~48px) whose header keeps only the expand control, so it can be
      reopened. Preserve `aria-expanded`/`aria-controls`, labels, and the narrow-viewport scrim.
- [x] **Actividad del hilo** pane: give it a header (title + collapse/close control) with the same
      collapsed-rail behaviour.
- [x] No `PanelShell` change.
- [x] Tests: panel visibility toggles from each panel header; existing visibility assertions updated.

### S2 — Proyectos header: default chat
- [x] Add to the Proyectos pane header: a **new default chat** control (create a `default`-namespace
      thread for admin/operator and open it) and a **default history** control (a popover listing the
      `default` project's threads via `listChatThreads(20, "default")`). Honest loading/empty/error states.
- [x] Only for roles that may use `default` (mirror `AgentChat.newChat`); otherwise hide the control.

### S3 — Per-project thread history + search
- [x] Under each expanded project, `Historial de hilos` reveals that project's threads
      (`listChatThreads(20, project.slug)`) in an inline list with a `SearchInput` filtering by title.
- [x] Selecting a thread opens it; honest loading/empty/error states; no fabricated rows.
- [x] Keep `Contexto y archivos` navigation behaviour unchanged for now (the tab model is a later slice).

### S4 — Wire Agentes del proyecto
- [x] Replace the stub (`AssistantWorkspace.tsx:248-251`) with the real roster:
      `listProjectAgents(selectedProject.slug)` (existing API). Render each agent's `name`, `role`,
      `description`, `read_only`, and the project's `latest_run` status (`En curso` / `Listo` / `—`).
- [x] Count = roster length; the `+` stays disabled (no add contract). Honest loading/denied/error/empty
      states. No rows when no project is selected.

## Slice 2 — Sidebar sections + active orchestrators (this pass)

Restructure the workspace sidebar into **three sections** and make the Agentes section a live
indicator of **active orchestrators**. Owner direction 2026-10-10. Full picture (orchestrators live +
sub-agents live) is split: sub-agent live activity needs a new runtime in-progress signal and is a
later slice.

### B2 — owner-scoped active-run listing (backend)

`GET /panel/api/chat/active-runs` (owner-scoped, `require_agent_surface_json`): list this owner's
threads whose run is currently non-terminal so the sidebar can show active agents. Today the only
project/agent read is the per-project static roster + single latest run; no cross-thread active list
exists.

- Select threads where `InternalChatThread.user_id == current.id` and
  `assistant_state -> 'live' ->> 'status' == 'running'` (the only non-terminal status; terminal set is
  `completed/failed/approval_pending/cancelled`, `agent_chat.py:_TERMINAL_RUN_STATUSES`). Exclude cortex
  sessions as the existing list does.
- Ordered by `updated_at` desc; bounded (e.g. `limit` default 50, 1..100).
- Response: `{"active_runs": [{"thread_id", "title", "proyecto", "agent": "orchestrator", "stage", "run_id", "updated_at"}]}`
  where `stage`/`run_id` come from `assistant_state.live`. The `agent` field is `"orchestrator"` today so
  the later sub-agent slice can add rows without a shape change.
- Strict backend TDD RED→GREEN: a running thread appears with its project + stage; a terminal thread does
  not appear; another owner's running thread does not appear.

### S5 — Sidebar three-section layout (frontend)

- [x] Complete the three-section sidebar layout and retain the reopenable collapsed rail.
- **Header section:** title "Asistente Lumat" with the pane collapse/expand toggle on the same row; below,
  two actions **"Nueva conversación"** (create a `default`-namespace thread, admin/operador) and
  **"Historial"** (default-namespace thread history). Reuses the S2 handlers, relocated + relabelled.
  When the pane is collapsed, these render **icon-only** in the rail (label via accessible name only).
- **Proyectos section:** "Proyectos" title with the **"Nuevo proyecto"** action on the same row; the
  existing project tree (search + expandable `Contexto y archivos` / `Historial de hilos`) unchanged.
- **Agentes section:** title only (**no `+` button**); renders the live active-agent list (S6).
- Collapsed rail shows the toggle + the two header actions icon-only; Proyectos/Agentes bodies hide.
- CSS + tests.

### S6 — Active orchestrators indicator (frontend)

- [x] Complete the polled active-orchestrator indicator with honest loading, empty, and error states.
- Poll B2 (`listActiveRuns`) on an interval (e.g. every 5s) while the workspace is mounted; honest
  loading/empty/error states. Render one row per active run: agent label "Orquestador" + the project
  name (or "Conversación rápida" for the `default` namespace) + the live stage label.
- Honest empty state: "No hay agentes activos".
- No fabricated activity: only rows returned by the endpoint. (Sub-agent rows are a later slice.)
- Tests with fake timers / mocked endpoint for the list, empty, and error states.

## Acceptance criteria

1. `npx tsc -b --force --noEmit`, `npx vitest run --no-file-parallelism`, `npm run build` green (from `web/`).
2. Backend `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` green (from the worktree root).
3. No fabricated data; every unbacked region is an honest empty/disabled state.
4. Existing chat/tab/panel behaviour and tests preserved.

## Checks

- Frontend: `npx tsc -b --force --noEmit`; `npx vitest run --no-file-parallelism`; `npm run build`.
- Backend: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`.
- Graph Check per repo AGENTS.md; record nodes consulted.
- Conventional Commits, no AI attribution.

## Env / review

- Worktree `../lumat-agent-odd-asistente-lumat-frontend`, branch `odd/asistente-lumat-frontend`, from
  `main` = `576b07ef`.
- Because B1 changes the backend, the review runs against the **worktree's own API** (isolated compose
  project on `:8001` / db `:5433`), not the primary stack; Vite `:5174` points at `:8001`.

## Progress log

- Slice 1 opened from `main` = `576b07ef`. Graph Check: `AssistantWorkspace()`, `AgentChat()`,
  `AssistantTabs()`, `ProjectsPage()`, `listProjects()`, `listChatThreads()`, `listProjectAgents()`,
  `createChatThread()`, `pathForRoute()`, `to_internal_chat_thread_summary_dict()`, `list_chat_threads()`;
  path `AssistantWorkspace()` → `panelRoutes.ts` via `pathForRoute()`.
- Graphify consulted: `AssistantWorkspace.tsx --imports--> api.ts --contains--> listProjectAgents()`;
  `AssistantWorkspace.tsx --imports--> api.ts --contains--> listChatThreads()`.
- S1 — delivered in `28b8263b` (`feat(assistant): refine project workspace sidebar`); focused suite: 13/13 pass.
- S2 — delivered in `28b8263b`; focused suite: 13/13 pass; default controls covered for admin, operador, and tecnico.
- S3 — delivered in `28b8263b`; focused suite: 13/13 pass; project history search and thread navigation covered.
- S4 — delivered in `28b8263b`; focused suite: 13/13 pass; roster, count, loading, and empty states covered.
- Shared verification: `npx tsc -b --force --noEmit` and `npm run build` passed. `npx vitest run --no-file-parallelism` did not complete within 600 seconds; output included existing test timeouts and three AssistantWorkspace tests exceeding the 5-second per-test limit under the prolonged run. The focused AssistantWorkspace run passed after implementation.
- Test-brittleness follow-up: routed the attachment, persisted-approval, and Cortex-close mocks by URL; Graphify path `AgentChat.test.tsx` → `AgentChat.tsx` → `uploadAssistantAttachment()`. `npx vitest run src/components/pages/AgentChat.test.tsx --no-file-parallelism`: 58/58 passed; `npx vitest run --no-file-parallelism`: 104 files, 1,110 tests passed. Commit `70a927e7`.
- **Native RDD review — approved and acknowledged (authority burned), 2026-10-10.** Immutable transport
  available this session. Lineage `review-602235d86ac6b39e`, tier `medium`, single lens
  `review-reliability`, 0 findings across all 11 changed paths. Owner granted consent via the native
  envelope; `review acknowledge-approved` returned `authority: burned`. Slice delivered on
  `odd/asistente-lumat-frontend`; push/PR/merge are the owner's decision.
- **Review env (owner visual review):** isolated compose project `lumat-asistente-lumat-frontend`
  (API `:8001`, db `:5433`), admin seeded via `db/seed.sh`, plus 3 seeded projects + 4 threads
  (script run in the api container). Vite `:5174` targets `VITE_API_TARGET=http://localhost:8001`.
- **B2 backend — implemented and verified:** `app/panel/api/routes/chat.py` adds the owner-scoped,
  bounded active-run route; `serializers.py` emits the stable orchestrator row shape; integration tests
  cover running/terminal/cortex/other-owner filtering and limit bounds. Strict TDD RED: after tests
  were added, `/panel/api/chat/active-runs` returned 404 (both the listing and limit test); GREEN:
  targeted suite 66 passed. Full backend `uv run pytest tests/`: 1,895 passed, 2 existing warnings
  (unawaited `_publish_all` coroutine; fastembed pooling notice). Commit: `b762edcd`.
- Graphify consulted nodes `list_chat_threads`, `InternalChatThread`, `app/panel/api/routes/chat.py`,
  `app/models.py`, and `api/serializers.py`; focused path queries found no directed route-to-model
  path in this graph snapshot.
- S5/S6 — delivered in `2467301e` (`feat(assistant): show live orchestrators in workspace sidebar`).
  Focused `AssistantWorkspace` suite: 14/14 passed; full frontend suite: 104 files, 1,111/1,111
  passed; `npx tsc -b --force --noEmit` passed; `npm run build` passed (Vite reported only the
  existing >500 kB chunk-size advisory). Companion `AgentChat.test.tsx`: 58/58 passed.
  Graphify consulted `AssistantWorkspace()`, `api.ts`, `types.ts`, and active-conversation route nodes;
  directed `AssistantWorkspace()` → `api.ts`/`types.ts` paths were not present in this graph snapshot.
