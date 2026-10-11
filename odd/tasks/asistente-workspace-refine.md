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

## Slice 3 — Open-tab model + agents = open tabs (this pass)

Owner model (2026-10-10): **"active" = the thread tab is open in the workspace**, not "the run is
executing". An open tab *means* the agent is active. Today the tab bar shows *recent* threads and the
tab's close button *deletes* the thread. Both are wrong for this model.

Decisions (owner-confirmed):
- **Close tab = remove from the open set** (session state); it never deletes the thread and never
  cancels a run. `deleteChatThread` stays only as the explicit header "…" menu action.
- **Closing a tab deactivates the agent** even if its run keeps running in the background (the run is
  not cancelled).
- Session tabs (in-memory), consistent with the earlier choice; a reload clears the open set.
- No backend change: the Agentes section lists the open tabs and enriches each row with the live stage
  from the existing `GET /panel/api/chat/active-runs` (B2) matched by `thread_id`.

### S7 — Open-thread tab model (frontend)

- [x] Add session state `openThreadIds: number[]` (ordered). The tab bar renders the **open threads**, not
  the recent list.
- [x] Opening a thread (create, pick from `Historial`, pick from a project's thread list, or a `thread_id`
  already in the URL on mount/popstate) adds it to the open set and makes it active.
- [x] **Tab close** removes the id from the open set only. If the closed tab was active, activate the last
  remaining open tab, or clear the URL so the empty "Asistente Lumat" state shows. NO delete, NO cancel.
- [x] Keep resolving tab titles/project from the loaded thread summaries (the recent list remains a
  title/history source); a thread opened directly by URL with unknown title shows an honest placeholder
  until resolved.
- [x] The header "…" menu keeps **Renombrar** / **Eliminar**; delete also removes the id from the open set.

### S8 — Agentes section = open tabs (frontend)

- [x] Render one row per **open thread**: agent label "Orquestador" + the project name (resolve `proyecto`;
  `"default"` → "Conversación rápida").
- [x] Status per row: the live stage label when that thread has an active run (from the polled
  `active-runs`, matched by `thread_id`), otherwise a neutral **"Activo"** (open = active). Unknown
  stage → "En curso".
- [x] Honest empty state when no tab is open: **"No hay agentes activos"**.
- [x] Keep the 5s poll of `active-runs` (only for the stage enrichment). No fabricated rows.

## Slice 4 — Composer-first central panel (this pass)

Owner direction 2026-10-10 (visual review of the current central panel): **delete the redundant chrome
above the conversation and make the composer the centre of gravity.** Owner-confirmed model: **hybrid
composer** — additive actions inside a `+` popover, and stateful tool toggles as **visible inline chips**
(so their on/off state is never hidden).

References: `LumatAgentNewthreadTools.png` (Lumat `+` popover) and the ChatGPT composer (separate bottom
row). Neither is copied verbatim; the owner said the Lumat reference is "not quite right". Do **not** add
a "Plugins" row — Lumat has no plugins.

**In:** the central panel only — `AgentChat.tsx`/`.css`, the `AssistantWorkspace.tsx` centre column
(`__thread-header`, `__thread-tabs`)/`.css`, `primitives.css` composer rules, and their tests.
**Out (Slice 5):** removing `AssistantTabs` and rehoming the Projects/Planning doors. The section tabs are
today the **only** door to the global `planning-sessions` admin view and the `projects` list (confirmed:
`PanelShell` `NAVIGATION` excludes both; `AppShell` reaches them only via `sectionTabs`), so they cannot
be removed before the new doors exist.

### S9 — Composer-first central panel

- [x] **Remove the redundant header chrome.**
  - `AssistantWorkspace.tsx`: delete the `__thread-header` block (`<h1>` title + `<p>Proyecto: …</p>` + the
    thread `Menu`). Relocate the thread `Menu` (Renombrar/Eliminar) into the `__thread-tabs` bar, right of
    the tab list and next to the `+`. Preserve behaviour: rename; delete also drops the id from the open set.
  - `AgentChat.tsx`: stop rendering the `PageFrame` `actions` row (`Detener ejecución`, `Herramientas`,
    `Historial`, `Contexto`, `Planificar`, `Nuevo chat`). Hide the `PageFrame` titlebar
    (`.assistant-chat .page-frame__titlebar { display: none }`) so the "Asistente Lumat" title/meta no
    longer render. Keep the `state` banner (loading/error) and keep rendering `{sectionTabs}` for now.
- [x] **Relocate the removed controls — no capability loss.**
  - `Detener ejecución`: render above the composer (in `__composer-wrap`) only while a run is active, with
    the existing title/copy.
  - `Herramientas`: replaced by the visible tool chips (below). Remove the popover.
  - `Historial`: the sidebar already lists default + per-project history; remove the header popover.
  - `Contexto`: remove the header button **and** the inline `assistant-chat__context` aside — the right
    `Actividad del hilo` pane already shows project/capabilities/files/artifacts.
  - `Nuevo chat`: preserved by the sidebar `Nueva conversación` and the tab-bar `+`.
  - `Planificar`: becomes a composer control (below).
- [x] **Composer (hybrid).** Keep the attachment list and the `Textarea`.
  - `+` popover ("Agregar al hilo"): **"Adjuntar archivo"** (existing upload) + **"Elegir del proyecto"**
    (disabled, honest "Próximamente" — project resource selection is not available yet).
  - **Visible tool chips:** one toggle chip per `toolPolicy.available` tool, showing its label + on/off
    state; toggling calls the existing `updateThreadToolPolicy`. Disabled while a run is active / while
    saving. Honest loading + error states — never hide the tool state.
  - **Planificar:** a subtle toggle/button opening the existing planning dialog (disabled without a thread).
  - **`@Agente`** chip, disabled ("Próximamente").
  - **Project chip:** shows the current `thread.proyecto` name (relocating the deleted "Proyecto:" line);
    informational only (no picker). `"default"` → "Conversación rápida".
  - Send unchanged. Keep the status footer (Conexión/estado) but compact.
- [x] **Narrow + centre.** Revert the full-width override so the conversation column is
  `width: min(100%, 48rem)` and centred. Keep the existing responsive tiers.
- [x] **Centre when empty.** When there is no thread or no messages and nothing is processing, centre the
  composer vertically (ChatGPT behaviour); with messages, keep the composer docked at the bottom.
- [x] Tests updated for every removed/relocated control; no fabricated data.

## Slice 5 — Rehome the section-tab doors, remove AssistantTabs (this pass)

Owner direction 2026-10-11: remove the section tabs `Chat | Proyectos | Sesiones de planificación` and give
each destination a proper home. Rationale (verified): `AssistantTabs` is the **only** door to the global
`planning-sessions` admin view and the `projects` list (`PanelShell` `NAVIGATION` excludes both), so the new
doors must exist before the row is removed. Chat becomes the only view.

- **Proyectos page** → the sidebar **Proyectos** section header gets a `...` (kebab) `Menu` holding
  **"Nuevo proyecto"** and **"Administrar proyectos"** (opens `/panel/app/projects`). **No standalone `+`** —
  everything lives in the kebab (owner decision).
- **Sesiones de planificación** → an item inside each project folder (next to "Contexto y archivos" /
  "Historial de hilos"), **rendered only when that project has ≥1 session**, opening the planning-sessions
  page scoped to that project.
- **Per-project start-chat** → each project row gets a button that starts a new chat bound to that project
  immediately. Reuse `navigateToProject(project, "threads")` → `?proyecto=<slug>`: `AgentChat`'s mount
  effect already auto-creates a thread for that project (no new code path). Owner request.
- **Chat** becomes the only view; the tab row disappears.

### B3 — project scope for planning sessions (backend)
`GET /panel/api/planning/sessions` lists **all** of the owner's sessions with no project filter, and the
payload omits `proyecto` (`app/panel/api/routes/chat.py:296-299`, `to_cortex_session_dict`), so a
per-project tree item is impossible today.
- `app/panel/api/serializers.py` — `to_cortex_session_dict`: add `"proyecto": thread.proyecto`.
- `app/panel/api/routes/chat.py` — `list_planning_sessions`: add optional
  `proyecto: str | None = Query(default=None, max_length=100)`; when provided, filter
  `InternalChatThread.proyecto == proyecto`. Keep the cortex-session filter, owner scope, and order.
- `web/src/types.ts` — `PlanningSession` gains `proyecto: string`.
- `web/src/api.ts` — `listPlanningSessions(proyecto?)` appends `?proyecto=<enc>` when provided.
- Strict backend TDD RED→GREEN: the summary includes `proyecto`; `?proyecto=X` returns only that project's
  sessions; without the param behaviour is unchanged.

### S10 — Remove AssistantTabs and rehome its doors (frontend)
- [x] Sidebar **Proyectos** header: replace the standalone "Nuevo proyecto" button with a `...` kebab `Menu`
      whose items are "Nuevo proyecto" and "Administrar proyectos" (navigates to `{ view: "projects" }`).
- [x] Each project row: add a start-chat control (icon) that calls `navigateToProject(project, "threads")`.
- [x] Each expanded project: add a "Sesiones de planificación" item, rendered **only when the project has
      ≥1 session** (fetch `listPlanningSessions(project.slug)` lazily on expand); navigates to
      `{ view: "planning-sessions", projectSlug }`.
- [x] `AppShell.tsx`: remove `AssistantTabs` + `sectionTabs` wiring; drop `assistantView`.
- [x] `TechnicianShell.tsx`: remove `AssistantTabs` + `sectionTabs` (its footer nav already covers
      projects/planning).
- [x] `AgentChat.tsx`, `ProjectsPage.tsx`, `PlanningSessions.tsx`: remove the `sectionTabs` prop and render.
- [x] `PlanningSessions.tsx`: accept a `projectSlug` prop; when present, list that project's sessions
      (`listPlanningSessions(projectSlug)`) and show the project in the header.
- [x] `panelRoutes.ts`: support `{ view: "planning-sessions", projectSlug }` →
      `/panel/app/planning-sessions?proyecto=<slug>`; parse it back.
- [x] Delete `AssistantTabs.tsx` + `AssistantTabs.test.tsx` and its CSS.
- [x] Tests updated for every removed/relocated control; no fabricated data.

**Out:** palette/tokens; the composer; `PanelShell` global chrome (leave the shell treatment of
projects/planning-sessions as-is unless it looks wrong in the visual review).

## Slice 6 — Chat file/project controls (backend)

Owner direction 2026-10-11 (visual review): the composer must let the user (a) **choose which project the
chat belongs to** and (b) **attach files that already live in the project** to the thread. Neither exists
today: a thread's `proyecto` is set only at creation, and thread attachments are created only by multipart
upload. Owner confirmed **both**.

### B4 — move a chat thread to another project
`PATCH /chat/threads/{thread_id}` today only renames (required `title`).
- Extend the body to accept optional `title` **and** optional `proyecto`; require at least one (422 otherwise).
- Validate `proyecto` exactly like `create_thread` (`app/services/agent_chat.py:264`): resolve via
  `projects.agent_context(session, proyecto, owner_id=user.id)`; `default` requires a business-memory role.
- Reject with **409** while a run is active (mirror the tool-policy guard).
- Update `thread.proyecto`, audit (`internal_chat.thread_project_changed`), return the thread summary.
- `web/src/api.ts` — `setChatThreadProject(id, proyecto)` → `PATCH` with `{ proyecto }`.

### B5 — attach an existing project file to a thread
New route `POST /chat/threads/{thread_id}/attachments/from-project`, body `{ project_file_id: int }`.
- The file must belong to the thread's project (`ProjectFile.project_id` == the thread's resolved project);
  404 otherwise. `default` threads have no project → 400.
- Respect `assistant_attachment_max_count` and the expiry cleanup, like `upload_attachment`.
- Read the file bytes and create the `AssistantAttachment` via the same `store_attachment` path. NOTE:
  `allowed_attachment` (assistant) accepts only pdf/csv/txt/images, while project files also allow
  md/docx/xlsx — an unsupported project file must return **400** with a clear message (the frontend shows
  it honestly; it must NOT offer to fabricate support).
- Audit (`internal_chat.attachment_attached_from_project`), return the attachment dict.
- `web/src/api.ts` — `attachProjectFileToThread(threadId, projectFileId)`; `web/src/types.ts` unchanged
  (`AssistantAttachment` already exists).

Strict backend TDD RED→GREEN for both: project change (valid/invalid slug/role guard/active-run 409);
from-project attach (owned file ok, foreign file 404, unsupported type 400, count limit).

## Slice 7 — Composer + empty state (frontend)

Owner visual review 2026-10-11.
- **Empty state (no chat open):** Momentum-style greeting — **time-based salutation + the user's saved
  name (`SelfProfile.name`, fallback to `username`)** — and a single **"Iniciar conversación"** button.
  Remove the thread-tabs bar (with its `+`) and the disabled composer while no chat is open.
  Name plumbing: the `User` type must carry `name`; `/me` already returns it, but the login path does not —
  refresh it so the greeting is correct right after login.
- **Composer (chat open):**
  - The **send button becomes a stop button** while a run is active; remove the separate "Detener ejecución"
    block above the composer.
  - **All tool toggles move inside the `+`** popover, with real Lumat design (today they are unstyled).
  - **Fix the `+` button** (not centred).
  - **Drag & drop** a file onto the chat → same `attach` path as the picker.
  - **Bottom row below the composer** (quick access, outside the `+`): **project selector** (B4 → change the
    thread's project) + **project files picker** (B5 → attach a file already in the project).
  - Badge "Conversación rápida" → **"General"**.
  - Remove the **"Conexión: … | Listo"** footer from the composer (the WS status is noise for this view).

## Slice 8 — Composer to match the final reference (this pass)

Owner direction 2026-10-11 (visual review): the composer must look like the **final references** — a wider
composer, a **bottom bar of three items** (`Proyecto ▾` · `Archivos N` · `Herramientas N`) like ChatGPT's,
active tool/attachment chips above the input, and a `+` popover that groups the tools. Owner: "el diseño
tiene que verse así como en estas 3 imágenes".

**Target structure (chat with a thread):**
- Empty-thread hero (thread exists, no messages): title **"¿En qué trabajamos hoy?"** + subtitle
  **"Consulta, planifica o trabaja en tus proyectos con el asistente Lumat."** (replaces
  "¿En qué podemos ayudarte?" / "Describe una tarea o consulta para comenzar.").
- Composer **wider**: `width: min(100%, 56rem)` (~900px like the reference), rounded + elevated.
- **Above the input:** active **tool chips** (`Buscar en la web ×`) and **attachment chips**
  (`Manual de atención.pdf · PDF · Listo ×`).
- Input (textarea).
- **Controls row:** `+` · **Planificar** (pill, highlighted when active) · **@ Agente · Próximamente** ·
  spacer · **send `↑`**.
- **Bottom bar** (a bordered row inside the composer card, below the controls): three items:
  - **Proyecto** — `📁 <name> ▾` → dropdown: search `Buscar proyecto…`, then **"General / Sin proyecto"**
    first (selected when `default`), then the projects; footer **"El proyecto define el contexto de este hilo."**
    Selecting one calls `setChatThreadProject`.
  - **Archivos** — `📎 Archivos N` (N = thread attachment count) → popover **"Archivos de este hilo"**:
    search `Buscar archivo…`, the thread attachments (filename + kind + "Adjuntado" + remove), and a footer
    with **`+ Adjuntar archivo`** (disk picker) **and** **`Agregar del proyecto`** (project files via
    `attachProjectFileToThread`, only for a real project).
  - **Herramientas** — `🛠 Herramientas N` (N = enabled tool count) → popover with the tool toggles.
- **`+` popover ("Agregar al hilo"):** **"Adjuntar archivo — Sube un documento o una imagen"**, then the
  tool toggles **grouped**: **"Consultar información"** and **"Acciones del asistente"**, each row with a
  switch; footer **"ⓘ Herramientas disponibles para este hilo."**
- **Tool labels** — a frontend map from raw tool name → `{ label, description, group }`; unknown tools fall
  back to the raw name (no fabricated descriptions):
  `web.search` → "Buscar en la web" / "Consulta información actualizada" / "Consultar información";
  `web.fetch` → "Consultar una URL" / "Lee el contenido de un enlace" / "Consultar información";
  `automation.create_rule` → "Crear automatización" / "Automatiza tareas recurrentes" / "Acciones del asistente";
  `project.create` → "Crear proyecto" / "Organiza tu trabajo en un nuevo proyecto" / "Acciones del asistente";
  `project.rename` → "Renombrar proyecto" / "Cambia el nombre de un proyecto" / "Acciones del asistente";
  `project.archive` → "Archivar proyecto" / "Archiva un proyecto" / "Acciones del asistente";
  `project.merge` → "Fusionar proyectos" / "Combina dos proyectos" / "Acciones del asistente".

**In:** `web/src/components/pages/AgentChat.tsx` + `.css`, a small tool-label map (new file or inline), and
their tests. **Out:** backend (B4/B5 already exist); `PanelShell`.

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
- **Slice 2 RDD assessment (2026-10-10):** `review assess --base-ref 08581eff --committed-only` →
  `risk: medium` (executable change in `app/panel/api/routes/chat.py`), 10 paths, 328 lines,
  `review_due: false` (`under_budget`). No review opened; the reviewed boundary stays at `08581eff` and
  accumulates with the next slice. Slice 2 is up for owner visual review against the isolated env
  (Vite `:5174` → API `:8001`).
- Graph Check for Slice 3: consulted `AssistantWorkspace()` and `listActiveRuns`/active-run listing nodes;
  graph path query did not find a directed path between the workspace and polling API symbols.
- S7/S8 — delivered in `28e71da4` (`feat(assistant): model workspace tabs as open threads`). Focused
  suite: 14/14 passed; `npx tsc -b --force --noEmit` passed; full frontend suite: 104 files,
  1,111/1,111 passed; `npm run build` passed (existing >500 kB chunk-size advisory). Tab close only
  removes session state and clearing the active tab resets the chat URL. Rollback boundary: the
  `AssistantWorkspace.tsx` and `.test.tsx` changes in `28e71da4`.
- **Slice 2+3 RDD review — approved and acknowledged (authority burned), 2026-10-10.** Lineage
  `review-989c693ae0dc93dc`, tier `medium`, lens `review-reliability`; owner granted consent via the
  native envelope; `review acknowledge-approved` returned `authority: burned`. One non-blocking advisory
  (follow-up, do NOT re-review this candidate): **R3-001 WARNING** — when the active-run poll fails the
  `error` state is recorded but not rendered (`AssistantWorkspace.tsx:88-91`), so open-tab rows keep
  showing "Activo" and a failed poll is indistinguishable from a successful empty result. Fold into a
  later slice (honest error indicator in the Agentes section).

- **Slice 4 (S9) opened 2026-10-11.** Owner direction (visual review of the current central panel):
  make it composer-first; owner confirmed the **hybrid composer** model (additive actions in a `+`
  popover; stateful tool toggles as visible inline chips so their state is never hidden). Graph Check:
  graph present in the worktree; consulted `AssistantWorkspace()`, `AgentChat()`, `Menu()`,
  `PageFrame()`, `toolPolicy`, `listChatThreads()`, `api.ts`; no directed path between
  `AssistantWorkspace()` and `AgentChat()` in this snapshot.
- S9 — delivered in `d8ef52e1` (`refactor(assistant): remove redundant thread header chrome`) and
  `f8b2fa3f` (`feat(assistant): build a hybrid composer with visible tool chips`), 6 files, net −372
  lines. Removed the thread header (title + "Proyecto: X" + menu), the `PageFrame` titlebar/actions row,
  and the inline context panel; relocated the thread menu to the tab bar, `Detener ejecución` above the
  composer, tools to visible chips, `Planificar` to the composer, and the project label to a composer
  chip. Composer narrowed (`min(100%, 48rem)`, centred) and centred-when-empty. Section tabs
  (`AssistantTabs`) intentionally kept: they remain the only door to the global `planning-sessions` admin
  view and the `projects` list — rehoming them is Slice 5.
- Verification (S9): `npx tsc -b --force --noEmit` pass; focused `AgentChat` + `AssistantWorkspace`
  suite 68/68; full `vitest` 104 files / 1,107 tests; `npm run build` pass (existing >500 kB advisory).
- **Slice 4 RDD review — approved and acknowledged (authority burned), 2026-10-11.** Lineage
  `review-9e58f874c2a8fd68`, tier `medium`, lens `review-reliability`; owner granted consent via the
  native envelope; `review acknowledge-approved` returned `authority: burned`. One non-blocking advisory
  (follow-up, do NOT re-review this candidate): **R3-001 WARNING** — the rehomed inline tool chips
  dropped the old popover's explicit "Bloqueadas durante la ejecución" status, so while a run is active
  the checkboxes are disabled without the reason being shown (`AgentChat.tsx:1065-1081`). Fold into a
  later slice together with the earlier active-run poll error indicator.

- **Slice 5 opened 2026-10-11.** Owner direction: remove the section tabs and rehome the two doors —
  Proyectos via a sidebar kebab, Sesiones de planificación inside each project folder (only when it has
  sessions); plus a per-project "start chat" button. Owner decision: everything in the kebab, no
  standalone `+`. Graph Check: graph present; consulted `list_planning_sessions()`,
  `to_cortex_session_dict()`, `AssistantWorkspace()`, `Menu()`, `AppShell()`, `TechnicianShell()`,
  `pathForRoute()`, `parsePanelPath()`.
- B3 — delivered in `f7903838` (`feat(assistant): scope planning sessions by project`). Strict TDD RED
  (`KeyError: 'proyecto'`) → GREEN. `to_cortex_session_dict` adds `proyecto`; `list_planning_sessions`
  accepts `?proyecto=`. Targeted 10 tests pass; full backend suite passes (two known warnings).
- S10 — delivered in `f8d9f99b`, `fd26b1ad`, `a115cf50`, `f460b09f`. `AssistantTabs` deleted (+test);
  `AppShell`/`TechnicianShell`/`AgentChat`/`ProjectsPage`/`PlanningSessions` stripped of `sectionTabs`;
  `PlanningSessions` scoped by project; `panelRoutes`/`api`/`types` updated. Verification: tsc pass;
  focused suite 83 tests; full frontend suite 103 files / 1,105 tests; build pass.
  (Slice 5 checkboxes were left unchecked in the doc; marked done 2026-10-11 after confirming
  `AssistantTabs.tsx` no longer exists and the delivery log matches the commits.)
- Follow-up fix: `assistant-workspace__project-chat:hover` used an undefined token `--surface-muted`;
  switched to the established `--surface`.
- **Slice 5 RDD assessment (2026-10-11):** `review assess --base-ref f8b2fa3f --committed-only` →
  `risk: medium` (executable change in `app/panel/api/routes/chat.py`), 21 paths, 321 lines,
  `review_due: false` (`under_budget`). No review opened; the reviewed boundary stays at `f8b2fa3f` and
  accumulates with the next slice. Slice 5 is up for owner visual review against the isolated env
  (Vite `:5174` → API `:8001`).

- **Slice 6 (backend) + Slice 7 (frontend) opened 2026-10-11.** Owner visual review: (a) empty state =
  Momentum-style greeting by the **saved name** + "Iniciar conversación"; (b) composer = send↔stop, tools
  inside `+`, `+` centred, drag & drop, bottom row (project selector + project files), badge "General", no
  "Conexión"; (c) two new backend endpoints (owner confirmed **both**). Graph Check consulted
  `rename_chat_thread()`, `ProjectFile`, `store_attachment()`, `AgentChat()`, `AssistantWorkspace()`,
  `AppShell()`.
- B4/B5 — delivered in `a0919d16` (`feat(assistant): move threads and attach project files`). Strict TDD
  RED→GREEN. `PATCH /chat/threads/{id}` accepts optional `{title?, proyecto?}` (409 while a run is active;
  `default` needs a business-memory role). New `POST /chat/threads/{id}/attachments/from-project` (project
  scope + type + count validation; unsupported types → honest 400). Backend full suite + 25 focused tests pass.
- Slice 7 — delivered in `c16ed1ef`, `31d02f93`, `1381346f`. Empty state greeting (saved `name` via `/me`,
  fallback username) + "Iniciar conversación"; thread-tabs hidden with no open tab; composer send↔stop;
  tools moved into the `+` popover (styled); `+` centred; drag & drop; bottom row with the project selector
  (B4) and project-file picker (B5); badge "General"; "Conexión" footer removed. Verification: tsc pass;
  focused 69 tests; full 103 files / 1,107 tests; build pass.
- **Slice 6+7 RDD review — approved and acknowledged (authority burned), 2026-10-11.** Lineage
  `review-8e1822a6a3a1b5c8`, tier `medium`, lens `review-reliability`, 26 paths / 862 lines. Two
  non-blocking advisories (follow-ups, do NOT re-review this candidate): **R3-001** — the login→`fetchMe`
  name refresh (`web/src/app.tsx:46-47`) can resolve after logout and re-set the authenticated shell; guard
  it with a cancellation / current-state check. **R3-002** — `attach_project_file` reads the stored path
  (`app/panel/api/routes/chat.py:632-634`) without handling a missing/unreadable file → uncaught filesystem
  error instead of a controlled response; wrap the read and answer honestly.
- Known follow-ups to fold into a later slice: R3-001 and R3-002 above, plus the earlier tool-chip
  "bloqueadas durante la ejecución" reason and the active-run poll error indicator.

- **Slice 8 opened 2026-10-11.** Owner gave the FINAL references: a wider composer, a bottom bar
  (`Proyecto ▾` · `Archivos N` · `Herramientas N`), chips above the input, a `+` popover with grouped
  tools, and the empty-thread hero "¿En qué trabajamos hoy?". Graph Check consulted `AgentChat()`,
  `Popover()`, `ChatThreadToolPolicyBody`.
- S8 — delivered in `320c74f3` (`feat(assistant): label composer tools`) and `ec460c9b`
  (`feat(assistant): match final composer reference`). Composer widened to `min(100%, 56rem)`; active tool
  + attachment chips above the input; empty-thread hero title/subtitle; controls row (`+`, Planificar pill
  highlighted while planning, `@ Agente · Próximamente`, send `↑`); bottom bar with the Proyecto dropdown,
  Archivos popover and Herramientas popover; `+` popover with "Adjuntar archivo" + grouped tool rows +
  footer; new `assistantToolLabels.ts` map. The `+` circle styling was scoped to
  `.assistant-chat__add-popover` so the bottom-bar popovers render as text triggers. Verification: tsc
  pass; focused 57 tests; full 104 files / 1,110 tests; build pass.
- Slice 8 RDD assessment: `review assess --base-ref 1381346f --committed-only` → medium, 6 paths, 322
  lines, `review_due: false` (`under_budget`). No review opened; the boundary stays at `1381346f` and
  accumulates. Note: the popover-display fix `ba05f577` sits after the S6+S7 receipt (a post-review byte
  change) and is folded into this accumulating range.

## Slice 9 — Composer tray and tool controls

Owner direction: refine the Slice 8 composer into a layered composer card + protruding tray, move tool
state out of visible chips and into the `+` popover, and keep the bottom-row Herramientas affordance
read-only. The tool count means opt-in tools available for activation (`toolPolicy.available.length`),
not currently enabled tools.

- Wrap the main composer and a narrower back tray in `.assistant-chat__composer-stack`; move the project
  and attachment controls into the tray, preserving empty-state centring and attachment chips.
- Replace emoji triggers with Lumat-style Lucide icons and `Badge` counts; remove the Herramientas popover.
- Make the `+` trigger round and organize its popover into attachment, grouped tool switches, and a master
  toggle, preserving reset, active-run status, and footer behavior.
- Remove active tool chips from above the textarea while retaining attachment chips.
- Extend `Popover` with an optional `trigger: ReactNode`, keeping `triggerLabel` as the accessible name
  and preserving string-trigger compatibility.
- Update focused tests for the new trigger semantics, switches, count source, and chip removal.

Graph Check: queried `chat composer bottom bar tools popover project files`; consulted `AgentChat.tsx`,
`Popover()`, `ProjectListFilesArgs`, `Composer-First Central Panel`, and `filesystem`. Path query
`AgentChat()` → `Popover()` returned no directed path (source match ambiguous); no edge is claimed.
`graphify-out/GRAPH_REPORT.md` read: hubs include `api.ts`, `Conversation`, `AssistantWorkspace.tsx`, and
`Lumat Panel Design System`; relevant composer/popover relationships were checked via the query results.

Delivered in `010bf1e5` (`feat(ui): render icon triggers in the popover primitive`) and `242f6fc3`
(`feat(assistant): rebuild the composer as a layered tray`). Verification: `npx tsc -b --force --noEmit`
passed; focused `AgentChat` + `Popover` suite 59/59; `npm run build` passed (existing >500 kB chunk-size
advisory). Full `vitest` is pre-existing flaky: a clean-base run of the same suite also failed (6 tests
across different, unrelated files — `AgendaPage`/`ClientFicha`/`UserManagement`), while the candidate's own
files pass in isolation (149/149 for `AgentChat`+`ClientesList`+`ClientFicha`), so Slice 9 does not
introduce the failures.

RDD assessment `review assess --base-ref 1381346f --committed-only` → risk `medium` (executable
`AgentChat.css`), 8 paths, 427 lines, `review_due: true` (`slice_budget_reached`). Native review opened and
**approved/acknowledged (authority burned)**, 2026-10-11, lineage `review-bd24abaf0dc7ff21`, lens
`review-reliability`. One non-blocking advisory (follow-up, do NOT re-review this candidate): **R3-001
WARNING** — the Herramientas badge shows `toolPolicy.available.length` (available tools) rather than the
enabled count, so disabling a tool does not lower the number. This is the **owner-decided semantics** (the
bar shows the activatable opt-in tools, defaults excluded), so it is by design, not a defect.

## Slice 10 — Composer visual-review corrections

Owner direction: apply visual-review corrections to the Slice 9 layered composer, scope the composer popovers upward without changing the global primitive behavior, and correct tool-count semantics and copy.

- Give the tray vertical breathing room and distribute General left, Archivos centre, Herramientas right.
- Consolidate composer wrapper/composer/textarea styling in `AgentChat.css`; keep a single outer card with a lighter surface and a darker protruding tray. Preserve wrapper focus ring and hidden label.
- Increase control spacing; render Planificar as a tinted Workflow pill while preserving its active state.
- Scope composer popovers to open upward with bounded height/viewport width; add project/file row icons and clearer menu structure. Map file types to Lucide icons with focused tests.
- Count enabled tools in Herramientas; relabel the policy reset action to “Usar la selección del proyecto” without changing behavior.
- Update `AgentChat` assertions for enabled count changes, reset label, slug-free project labels, and preserve existing behavior coverage.

Graph Check: `graphify query "assistant chat composer textarea popover project file icon"` surfaced `AgentChat.tsx`, `Popover()`, `Textarea()`, `Icon()`, `Composer-First Central Panel`, and project/filesystem nodes. A narrower query surfaced `AgentChat()`, `Popover()`, `AgentChat.tsx`, `services/project_files.py`, and `Project`. `graphify path "AgentChat()" "Popover()"` did not find a directed path (ambiguous source match); the undirected retry also found no path. `graphify-out/GRAPH_REPORT.md` consulted: hubs include `api.ts`, `Conversation`, `AssistantWorkspace.tsx`, and `Lumat Panel Design System`; relevant AgentChat and Popover nodes were checked through query results.

Implementation: the outer wrapper is the sole composer card; its inner composer has no visible box. Tray spacing/distribution, scoped upward popovers, icon-led menu rows, the Workflow planning pill, enabled-tool counting, and reset copy are in place. File-type icon mapping is covered by focused unit tests. Project selection continues to use the existing thread-project endpoint.

Verification from `web/`: `npx tsc -b --force --noEmit` passed; `npx vitest run src/components/pages/AgentChat.test.tsx src/components/pages/assistantFileIcon.test.ts src/components/primitives/Popover.test.tsx` passed (3 files, 67 tests; existing React `act(...)` warnings); `npm run build` passed (Vite reported the existing >500 kB chunk-size advisory).

Ponytail: the new type-to-icon helper is the minimum reusable mapping needed by two row types and a unit test; native `:has()` and CSS anchor positioning are already-supported platform features used for the wrapper focus ring and upward popovers. No shortcut with a known ceiling was introduced. Commits: `e85f51cd` (layered composer styling), `f6cb23d6` (popover menus, icons, enabled count, copy, and tests).

## Slice 11 — Active-conversation composer

Owner direction: when `messages.length > 0`, dock the composer at the bottom of the conversation, remove the project/files/tools tray from rendering, and compact the composer to a single-row baseline that grows with wrapped input. Preserve the existing empty-state centered card and tray unchanged.

- Derive `activeConversation` from `messages.length > 0`; apply an active modifier to the composer stack and do not render the tray in that state.
- In active mode remove the reserved tray padding, compact the wrapper while retaining the `+`, Planificar, `@ Agente`, and send controls, and keep the composer width at `min(100%, 56rem)`.
- Confirm the grid composer row is bottom-docked; retain the existing textarea input auto-resize and set its baseline to one line.
- Add focused tests that verify the active modifier and absent tray with messages, and the tray remains with no messages.

Graph Check (before source edits): `graphify query "assistant chat composer active conversation messages layout bottom"` consulted `AgentChat()`, `AssistantWorkspace()`, `messages`, `Composer tray (layered composer card)`, and `ODD: conversation-inspector-layout`. `graphify path "AgentChat()" "AssistantWorkspace()"` returned no directed path (ambiguous source/target matches). Read `graphify-out/GRAPH_REPORT.md`; relevant hubs include `AssistantWorkspace.tsx`, `Conversation`, and `Lumat Panel Design System`. The graph report freshness is `f460b09f`, while this worktree starts at `485132f8`.

Implementation: `AgentChat` derives active state directly from `messages.length`, applies
`assistant-chat__composer-stack--active`, and omits the tray subtree in active conversations (so its
controls leave the accessibility tree). The existing conversation grid's `minmax(0, 1fr) auto` rows
already dock the composer at the bottom; active mode removes tray reservation, reduces wrapper padding,
and sets a one-line textarea minimum while preserving the existing input auto-resize (capped at 160px).
The 56rem width and empty-state card/tray remain unchanged. Focused tests cover both active and empty states.

Verification from `web/`: `npx tsc -b --force --noEmit` passed (no output); `npx vitest run
src/components/pages/AgentChat.test.tsx` passed (1 file, 59 tests; existing React `act(...)` warnings);
`npm run build` passed (Vite reported the existing >500 kB chunk-size advisory).

Ponytail: the existing `resize` handler already supports multi-line growth, so no second resizing
mechanism was added. CSS grid's existing auto-sized composer row provides bottom docking without layout
restructuring. No shortcut with a known ceiling was introduced.

Implementation and tests: `c3796641` (`feat(assistant): dock composer for active conversations`).

## Slice 12 — Composer popover direction and density

Owner direction: empty-state composer popovers open downward, while the active-state `+` popover opens
upward at chatbox width. Compact the tool, project, and files dialogs; tighten and rebalance the tray.

- Keep accessible naming while visually hiding the `+` dialog title; render compact icon/name/toggle tool
  rows with consistent toggle alignment and no per-tool descriptions.
- Give every tool a Lucide icon with a neutral fallback; preserve grouped headers, master toggle, file
  attachment, reset, active-run status, and footer.
- Default empty-state `+`, project, and files popovers downward; scope upward positioning only to the
  active-state `+` popover. Bound panel height and viewport width; match `+` width to the chatbox.
- Compact project/files dialogs and vertically center tray controls, grouping General and Archivos on
  the left while pushing Herramientas to the right.
- Update focused tests for title accessibility, icon metadata/rendering, row descriptions, and tray layout.

Graph Check (before source edits): `graphify query "assistant chat popover direction tray density tool rows"`
consulted `AgentChat.tsx`, `Popover()`, `AssistantToolLabel`, and `Layered Composer Card + Tray` (community
20/421); related nodes surfaced include `AgentChat()` and `Composer tray`. `graphify path "AgentChat()"
"Popover()" --undirected` found no path (ambiguous source match). Read `graphify-out/GRAPH_REPORT.md`;
god nodes include `make_user()`, `User`, `Customer`, `Conversation`, and `Message`; relevant UI hubs include
`api.ts`, `AssistantWorkspace.tsx`, and `Lumat Panel Design System`. The report originally identified
freshness `f460b09f`; an incremental graph update ran before editing and refreshed the queried graph.

Implementation: `Popover` now supports `hideTitle` while retaining its labelled heading; the `+` menu uses
it and renders icon/name/toggle rows without subtitles. Tool metadata maps Lucide glyphs with `Wrench` as
the unknown-tool fallback. The assistant-chat-wide upward override was removed; empty-state popovers use
the primitive's downward anchor placement and only active `+` is positioned upward. Popovers are
viewport-bounded, `+` tracks the 56rem chatbox maximum, project/files menus and rows are tighter, and the
tray now vertically centres its controls, groups General/Archivos at the left, and pushes Herramientas to
the right with muted text.

Verification from `web/`:
- `npx tsc -b --force --noEmit` — passed (no output).
- `npx vitest run src/components/pages/AgentChat.test.tsx src/components/pages/assistantToolLabels.test.ts src/components/primitives/Popover.test.tsx` — passed (3 files, 66 tests); existing React `act(...)` warnings remain in the AgentChat suite.
- `npm run build` — passed; Vite emitted the existing advisory that the 848.80 kB JS chunk exceeds 500 kB.

Ponytail: the existing native Popover/anchor positioning and Lucide dependency cover the behavior without
new dependencies or custom positioning logic. Tool rows use a single three-column CSS grid for consistent
toggle alignment; the master row overrides to flex because it has no leading icon. No further equivalent
reduction found, no shortcut with a known ceiling was added, and no authorized behavior was deferred.

Commits: `8da47ce7` (`feat(ui): allow visually hidden popover titles`), `87bfc07a`
(`feat(assistant): map tool labels to Lucide icons`), and `4d593b59`
(`feat(assistant): refine composer popovers and tray`).

## Slice 13 — Popover anchoring and composer details

Owner direction: make every popover anchor to its own trigger; keep empty-state composer popovers below
their triggers with a visible gap, and place the active-conversation `+` popover entirely above the
composer card. Remove tray count badge decoration, make the `+` trigger square/circular, and restore
left/top textarea padding in active mode.

- Give each `Popover` instance a sanitized unique anchor name through a root custom property; bind only
  popover triggers/panels to it, leaving tooltip behavior unchanged. Cover two-instance uniqueness and
  trigger/panel association in `Popover.test.tsx`.
- Verify empty composer panels open downward without covering their triggers; in active mode, position the
  `+` panel above the composer card edge rather than merely above its own trigger. Retain bounded panel
  height and scrolling.
- Render bare numeric counts for tray Archivos/Herramientas; force the `+` trigger to a fixed square with
  no minimum width or padding; add active textarea left and top padding.
- Update focused `AgentChat` tests for tray counts and composer classes/placement wiring.

Graph Check before source edits: ran `graphify query "popover anchor positioning primitive trigger panel"` and
`graphify path "Popover()" "AgentChat()"`; the query consulted `Popover()`, `Popover.tsx`,
`Popover.test.tsx`, `AgentChat.tsx`, and `AgentChat()`. The path query found no directed path (ambiguous
matches). Read `graphify-out/GRAPH_REPORT.md`; relevant UI nodes include `Popover()`, `AgentChat.tsx`,
`Popover.test.tsx`, and `web/src/components/primitives/primitives.css`. The report initially lagged HEAD
(`f460b09f` vs `bdbc6da0`), so its graph was incrementally refreshed before source edits.

Implementation: `Popover` sanitizes React's `useId()` into a per-instance `--pop-anchor-*` value on its
root; only popover triggers/panels consume that property, while tooltip anchoring remains on its previous
shared name. This prevents each popover panel from resolving against another instance's trigger. Empty-state
composer panels retain the downward primitive placement and gap. In active mode only the `+` panel anchors
to the composer card and opens above its top edge. Panel height/scroll bounds remain intact. Tray counts are
plain numbers; the `+` trigger now overrides the base minimum height to stay square; active textarea padding
includes horizontal and top space. Tests cover instance uniqueness/association, plain counts, and active/
empty composer markup; the browser positioning check covers the placement geometry.

Verification from `web/`:
- `npx tsc -b --force --noEmit` — passed (no output).
- `npx vitest run src/components/pages/AgentChat.test.tsx src/components/primitives/Popover.test.tsx` — passed (2 files, 64 tests); existing React `act(...)` warnings remain. The “confirms a copy with a transient label” test passed in this batch.
- `npm run build` — passed; Vite emitted its existing advisory that the 848.89 kB JS chunk exceeds 500 kB.
- Browser positioning check using a minimal reproduction of the implemented anchor declarations in installed Google Chrome `151.0.7922.137` via Playwright — CSS anchor positioning supported; empty panel bounds were top 69 / bottom 179 against trigger bottom 61 (8px gap); active panel bottom 333 against composer card top 341 (8px gap). No overlap in either tested placement.

Ponytail: useId and native CSS anchor positioning are the minimum existing React/platform mechanisms; no
new dependency, custom positioning runtime, or duplicate layout system was added. The fixed named composer
card anchor is scoped only to the single active composer, while instance-specific anchors remain necessary
for all popover triggers. The only shortcut is native CSS anchor-position support; the existing
`@supports` guard preserves the non-anchor fallback when unsupported, so no known ceiling requires a
`ponytail:` code comment and no authorized behavior was deferred.

Commits: `f4ebc506` (`fix(ui): isolate popover anchor names`) and `077c717a`
(`fix(assistant): refine composer popover placement`).

**Slices 10–13 RDD review — approved and acknowledged (authority burned), 2026-10-11.** Lineage
`review-da4e2aa15d1b6708`, tier `medium`, lens `review-reliability`, 11 paths / 457 lines
(`slice_budget_reached`). The reviewer inspected all 11 paths and returned **no findings**. No correction
was opened; the reviewed boundary advances past this range.

## Slice 14 — Composer tools dialog and nested project files

Owner visual review: redesign the `+` tools dialog as a single vertical, chatbox-width panel with a visible
header/title, enabled/available badge, native close button, attachment row, master toggle, grouped tool
rows, project-selection reset row, and footer note. Keep loading/error/empty states and active-run lock
copy/semantics. Open the nested “Archivos del proyecto” panel beside its trigger with bounded scrolling
and viewport-safe placement.

- Extend `Popover` with optional dismissible native-popover close control and title accessory while
  preserving hidden-title behavior and accessible label wiring.
- Update `AgentChat` layout/copy and tests for title, count, reset row, master toggle, and vertical stacking;
  preserve the existing file picker and tool-policy behavior.
- Position the nested project-file popover to the side with a maximum height and vertical scrolling.

Graph Check (before source edits): `graphify query "composer add popover tools dialog layout nested files popover"`
consulted `Popover()`, `AgentChat.tsx`, `Popover.tsx`, `Popover.test.tsx`, and
`web/src/components/primitives/primitives.css`. `graphify path "Popover.tsx" "AgentChat.tsx" --undirected`
found `Popover.tsx <--imports_from-- AgentChat.tsx`; the `AgentChat.tsx` → `primitives.css` path query found
no path. The directed Popover-to-AgentChat query was ambiguous and returned no path. Read
`graphify-out/GRAPH_REPORT.md`; relevant hubs include `AgentChat.tsx`, `Popover.tsx`,
`web/src/components/primitives/primitives.css`, and `Lumat Panel Design System`. Graph report built from
`bdbc6da0`, behind starting HEAD `3b910a8e`.

Implementation: the composer `+` panel now shows “Herramientas del hilo”, an enabled/available count,
and a native Popover API close button; tool controls stack vertically, the attachment/master/reset rows
include the requested supporting copy, and the thread selection note is retained. Existing tool policy
states, lock copy, and reset action remain in place. The nested project-file panel uses side anchor
placement with inline flip fallback and bounded vertical scrolling. `Popover` keeps `hideTitle` and
`aria-labelledby` behavior for other callers.

Verification from `web/`:
- `npx tsc -b --force --noEmit` — passed (no output).
- `npx vitest run src/components/pages/AgentChat.test.tsx src/components/primitives/Popover.test.tsx` — passed (2 files, 65 tests); existing React `act(...)` warnings appeared in AgentChat tests.
- `npm run build` — passed; Vite emitted the existing advisory that the 849.87 kB JS chunk exceeds 500 kB.

Ponytail: native Popover API target-action and CSS anchor positioning provide dismissal/placement without
custom JavaScript. One-column CSS grid is simpler and more reliable than the former wrapping flex layout;
the inline-flip fallback handles constrained viewport width. No shorter equivalent preserves the requested
layout and controls; no intentional shortcut with a known ceiling or deferred authorized behavior.

Commit: `94a470bd` (`feat(ui): add native close controls to popovers`) — Popover accessory and native
dismiss control, with primitive tests.

Composer layout commit: `650bbfb1` (`feat(assistant): refine thread tools popovers`) — single-column tools
dialog and side-opening, scroll-bounded project-file popover with updated composer tests and Slice 14
verification results.

## Slice 15 — Simplify tool controls and align the dialog to the composer

Owner direction: replace per-tool controls in the `+` dialog with only the master toggle and one web
search toggle (controlling both `web.search` and `web.fetch`); keep attachment, policy reset, run-lock
status, tool loading/error/empty states, and the thread-selection footer. Remove the header count while
retaining the visible “Herramientas del hilo” title and dismiss button. Match the `+` panel exactly to the
composer-card width; open below the card in the empty state and above it in active conversations, with
bounded scrolling retained.

Graph Check before source edits: `graphify query "composer add popover tools toggle width anchor chatbox"`
consulted `AgentChat.tsx`, `Popover.tsx`, `Popover.test.tsx`, `assistantToolLabels.ts`, and the
`AgentChat.tsx` community. `graphify query "assistant composer wrap anchor popover tool labels"` surfaced
`AgentChat()`, `Popover()`, `AgentChat.tsx`, `assistantToolLabels.ts`, and `assistantToolLabel`. The path
`AgentChat.tsx` → `Popover.tsx` was one extracted `imports_from` edge. Read `graphify-out/GRAPH_REPORT.md`;
its UI community includes `AgentChat.tsx` and `Popover.tsx`, with `AgentChat.tsx` a community hub. The graph
was built from starting HEAD `5b8bfbd4`.

Implementation: the dialog now has only the master and combined web-search switches; the latter requires
both web capabilities to be available, checks only when both are enabled, and sets/clears both together.
The title and close button remain; the count accessory and unused tool-label map were removed. The composer
card has the same named anchor in both states; the `+` panel uses anchor width and bottom/above-card placement
in the empty/active states, with viewport-bounded width fallback, max-height, and scrolling retained.

Verification from `web/`:
- `npx tsc -b --force --noEmit` — passed (no output).
- `npx vitest run src/components/pages/AgentChat.test.tsx src/components/primitives/Popover.test.tsx` — passed (2 files, 65 tests); existing React `act(...)` warnings appeared in AgentChat tests.
- `npm run build` — passed; Vite emitted the existing advisory that the 848.29 kB JS chunk exceeds 500 kB.

Ponytail: native CSS anchor positioning and the existing Popover primitive cover positioning and dismissal
without custom JavaScript. Removing the no-longer-consumed tool-label map avoids retaining dead UI metadata.
The viewport clamp is intentionally retained as the fallback ceiling when anchor positioning is unsupported
or the full card width cannot fit; no authorized behavior was deferred. An optional Playwright geometry probe
could not launch because the installed Playwright browser executable is absent; no browser package download
was attempted.

Commits: `1ba689bd` (`feat(assistant): simplify thread tool controls`) covers the tool UI, composer
anchoring, tests, and this Slice 15 record; `9aa55c01` (`refactor(ui): remove unused popover accessory`)
removes `Popover.titleAccessory` and its accessory-specific test; the final cleanup commit removes the
now-unused tool-label map and its unit test (`1de4f8e8`, `refactor(assistant): remove unused tool labels`).

## Slice 16 — Compact, viewport-safe composer dialogs

Owner final visual feedback: hide the visible “Herramientas del hilo” heading from the `+` dialog while
retaining its accessible name and close button; compact composer popover rows; bound every composer dialog
to a viewport-safe height with internal vertical scrolling and block-axis flip fallbacks; and keep file names
on one ellipsized line with the full filename available on hover.

- Apply `Popover.hideTitle` only to the `+` dialog; keep the `h2` as its accessible label and preserve the
  native close control and all dialog content.
- Use a smaller height cap than the existing `min(70vh, 32rem)` where needed so panels anchored low in the
  viewport can flip and remain wholly visible while scrolling internally. Preserve the empty-state `+`
  preference to open below the chatbox and the nested project-files panel's inline flip.
- Compact row padding/line-height in all composer popovers and ellipsize long attachment/project filenames
  without removing file-type/subtitle information.
- Add/update focused tests for the accessible title and long filename presentation; verify bounded scrolling
  and anchor fallback with a browser geometry probe.

Graph Check before source edits: ran the required
`graphify query "assistant composer popover panel max-height scroll overflow truncate file row"`, which
surfaced `AgentChat.tsx`, `Popover()`, `Popover.tsx`, `Popover.test.tsx`, and the composer-first central panel.
`graphify path "AgentChat.tsx" "Popover.tsx"` found the extracted import edge
`AgentChat.tsx --imports_from--> Popover.tsx`; the reverse directed path from Popover to AgentChat tests was
absent. Read `graphify-out/GRAPH_REPORT.md`; its UI hub/community includes `AgentChat.tsx` and `Popover.tsx`.
The report initially lagged starting HEAD `5c25b0ed` (graph built at `5b8bfbd4`), so Graphify was updated
and the report regenerated before editing. `cluster-only` reported 757 communities; HTML visualization was
skipped because the graph exceeds its 5,000-node visualization limit.

Implementation: the `+` popover now sets `hideTitle`, retaining its labelled `h2` and close button without
showing the title. Composer popovers share a `min(45vh, 20rem)` border-box cap, internal vertical scrolling,
and block-axis flip fallback; the nested project-files panel keeps its inline flip and adds block flip. The
empty-state `+` still declares below-chatbox placement first. Tool, project, and file rows use tighter vertical
spacing/line height. Both file-row variants render a titled, single-line ellipsis filename while preserving
their type/status subtitle. Focused tests cover the accessible title, close button, and thread attachment
filename metadata.

Verification from `web/`:
- `npx tsc -b --force --noEmit` — passed (no output).
- `npx vitest run src/components/pages/AgentChat.test.tsx src/components/primitives/Popover.test.tsx` — passed (2 files, 66 tests); existing React `act(...)` warnings remain in AgentChat tests.
- `npm run build` — passed; Vite emitted the existing advisory that the 848.46 kB JS chunk exceeds 500 kB.
- Chrome 151 headless / Playwright viewport probe (1200×600; trigger at y=550; 40-row popover): `top=272`, `bottom=542`, `height=270`, `maxHeight=270px`, `overflowY=auto`, `scrollHeight=2016`, `clientHeight=268`, `positionTry=flip-block`. Panel stayed inside the viewport, flipped above the low trigger, and remained internally scrollable.

Ponytail: the native Popover/anchor-positioning platform handles internal scrolling and directional fallback;
the existing `hideTitle` API avoids primitive changes. Duplicate `+` panel sizing/scroll declarations were
removed in favor of the shared panel rule. No intentional shortcut with a known ceiling or authorized behavior
was deferred.

Commit: `2df854b3` (`fix(assistant): bound composer popovers and filenames`).

## Slice 17 — Attachment delete + inline content (backend)

Owner visual review 2026-10-11: a thread attachment cannot be removed from anywhere (neither the
composer nor the "Archivos de este hilo" popover), and an attached image cannot be opened/previewed.
Both need backend support: today only upload (`chat.py:565`) and attach-from-project (`chat.py:599`)
exist, the thread response lists attachments (`chat.py:370-381`), and a `FileResponse` exists only for
artifacts (`chat.py:445-453`).

### B6 — delete a thread attachment
`DELETE /chat/threads/{thread_id}/attachments/{attachment_id}` (owner-scoped, `require_agent_surface_json`).
- `get_thread(session, thread_id, current.id)` → 404; then load the attachment where
  `id == attachment_id`, `thread_id == thread_id`, `deleted_at.is_(None)` → 404 otherwise.
- Mirror the existing active-run guard (`_require_no_active_run`) used by the tool-policy routes.
- Unlink the stored file (`Path(row.stored_path).unlink(missing_ok=True)`) and set `deleted_at` (the
  same soft-delete shape as `cleanup_attachments`, `attachments.py:84-93`).
- Audit `internal_chat.attachment_deleted`; commit; `204`.
- `web/src/api.ts` — `deleteThreadAttachment(threadId, attachmentId)`.

### B7 — serve attachment bytes for preview
`GET /chat/threads/{thread_id}/attachments/{attachment_id}/content` (owner-scoped).
- Same ownership/not-deleted resolution; a missing file on disk → 404 (never an uncaught `OSError`,
  per the R3-002 lesson).
- `FileResponse(row.stored_path, filename=row.filename, media_type=row.content_type,
  content_disposition_type="inline")` so images render in the browser.
- `web/src/api.ts` — `threadAttachmentContentUrl(threadId, attachmentId)` (same-origin path for `<img src>`).

Strict backend TDD RED→GREEN: delete removes it from `GET /chat/threads/{id}` and unlinks the file;
double-delete → 404; another owner's / another thread's attachment → 404; content returns bytes with the
stored content type; content of a deleted attachment → 404; missing file → 404.

Implementation: `app/panel/api/routes/chat.py:648-693` (owner-scoped delete with the active-run guard and a
204, plus the inline `FileResponse` content route with a 404 for a missing file); `web/src/api.ts`
(`deleteThreadAttachment`, `threadAttachmentContentUrl`, and 204 handling in `apiFetch`). Tests:
`tests/integration/test_assistant_attachments.py:147-227` (delete unlinks + hides, double-delete 404,
thread/owner scope, active-run 409, inline image content, missing-file 404) and `web/src/api.test.ts`.

Verification: focused `uv run pytest tests/integration/test_assistant_attachments.py -q` → 19 passed;
full backend `uv run pytest tests/ -q` → 1,898 collected, two pre-existing warnings; `npx tsc -b --force
--noEmit` → passed. Commits: `5738ae70` (`feat(chat): delete and preview thread attachments`),
`9f7fe4ad` (`docs(odd): plan attachment delete, preview, and drop slices`).

**Slices 14–17 RDD review — approved and acknowledged (authority burned), 2026-10-11.** Lineage
`review-35f4696e4b49e90b`, tier `medium`, lens `review-reliability`, 13 paths / 603 lines
(`slice_budget_reached`). The reviewer inspected all 13 paths and returned **no findings**; no correction
was opened and the reviewed boundary advances past `9f7fe4ad`.

## Slice 18 — Composer attachment tray, delete, and image preview (frontend)

Owner visual review 2026-10-11: attachments must show more orderly (a dedicated tray above the
composer, attachment-only), with a reduced (ellipsized) filename and an `x` to remove each one — from
both the tray and the "Archivos de este hilo" popover — and attached images should be clickable to
preview.

- Move the composer attachment list out of the composer card into a dedicated top tray
  (`.assistant-chat__attachment-tray`) rendered above the composer card while attachments exist; keep
  the active-conversation state compact.
- Each tray item: file-type icon + a single-line ellipsized filename (`title` = full name) + `x` →
  `deleteThreadAttachment`, then drop the id from local `attachments`.
- "Archivos de este hilo" popover rows: add a remove `x` per row (same handler); image rows become
  clickable to preview.
- Image preview: `kind === "image"` opens the existing `Dialog` primitive with an
  `<img src={threadAttachmentContentUrl(...)}>`; non-images are not clickable. Honest error state if the
  image fails to load.
- Remove the old in-composer `.assistant-chat__attachment-list` markup.
- Tests: delete calls the API and removes the row from both the tray and the popover; the tray renders
  only with attachments; an image row opens the preview while a non-image does not; the filename carries
  the full name via `title`.

Implementation: `AgentChat.tsx` (attachment tray above the composer card, a shared delete handler with a
visible error, image-only preview through the `Dialog` primitive, and an image-load error state),
`AgentChat.css` (tray, ellipsized filename, remove controls, preview sizing), and tests in
`AgentChat.test.tsx`. Verification from `web/`: `npx tsc -b --force --noEmit` passed;
`npx vitest run src/components/pages/AgentChat.test.tsx` → 63 passed (existing React `act(...)`
warnings); `npm run build` passed (existing >500 kB advisory). Commit: `8f811c34`.

## Slice 19 — `+` dialog close placement and full-area drop (frontend)

Owner visual review 2026-10-11: in the open `+` dialog the close `×` sits on its own line above the
first row and the dialog can be tighter; drag & drop only works over the composer stack
(`AgentChat.tsx:1054`) and takes a single file.

- `Popover`: when `hideTitle` + `dismissible`, place the close `×` at the height of the first content row
  instead of a standalone header line; keep the visible-title behavior unchanged for other callers.
- Compact the `+` dialog further to match the owner's reference.
- Drag & drop: attach the drop handlers to the whole chat area (conversation + composer), not only the
  composer stack, and accept **multiple** dropped files (loop over `dataTransfer.files` into `attach`).
  Preserve the existing picker path.
- Tests: `×` renders aligned with the first row (no standalone header row when `hideTitle`); dropping N
  files attaches N; the drop zone covers the conversation area.

Implementation: `AgentChat.tsx:888-896, 1079` (drop handlers on the whole chat area, multiple files through
the existing `attach` path, non-file drags ignored, active-run/upload guards kept), `AgentChat.css:50-55`
(hidden-title close aligned alongside the first row, compacter `+` dialog), `Popover.tsx:38` (a modifier
rendered only for the hidden-title dismissible case), and tests in `AgentChat.test.tsx` /
`Popover.test.tsx`. Verification from `web/`: `npx tsc -b --force --noEmit` passed;
`npx vitest run src/components/pages/AgentChat.test.tsx src/components/primitives/Popover.test.tsx` → 71
passed (existing React `act(...)` warnings); `npm run build` passed (existing >500 kB advisory). Commit:
`3ba006f7`.

## Slice 20 — Remove the `+` dialog close control (frontend)

Owner visual review 2026-10-11: the `+` dialog's `×` cannot sit at the first row's height, and the dialog
already closes by clicking outside or the trigger — so the close control is unnecessary. Remove it.

- `AgentChat.tsx`: drop `dismissible` from the `+` `Popover` (keep `hideTitle`).
- `Popover.tsx`: remove the now-unused `dismissible` prop, the `.popover__header` wrapper and the
  `.popover__close` button (revert to the plain labelled `h2`); `dismissible` has no other caller.
- `primitives.css`: remove `.popover__header`, `.popover__header .popover__title`, and `.popover__close`.
- `AgentChat.css`: remove the hidden-title dismissible alignment rules.
- Tests: drop the `Popover.test.tsx` close-control tests and the `AgentChat.test.tsx` assertions on the
  "Cerrar" button; keep the hidden-title accessible-name assertion and every other passing case.

Implementation: `Popover.tsx` (removed `dismissible`, the `.popover__header` wrapper and the
`.popover__close` button, reverting to the labelled `h2`), `primitives.css`, `AgentChat.css`, `AgentChat.tsx`
(the `+` popover keeps only `hideTitle`), and both test files. Verification from `web/`:
`npx tsc -b --force --noEmit` passed (an unused `fireEvent` import was cleaned up);
`npx vitest run src/components/pages/AgentChat.test.tsx src/components/primitives/Popover.test.tsx` → 69
passed; `npm run build` passed (existing >500 kB advisory). Commit: `8d06113a`.

## Slice 21 — Workspace tabs look like tabs, with a per-tab `⋮` menu (frontend)

Owner visual review 2026-10-11 (reference: the panel's tab row): the current thread tabs do not read as
tabs — the separator line sits far below them, every tab has a bottom border, and the active tab is not
visually joined to the content. Each tab needs a small **vertical `⋮`** opening a menu to close or rename
it.

- `AssistantWorkspace.css`: the separator must sit at the tabs' baseline — remove the tab bar's
  `padding-bottom` gap so `border-bottom` runs along the tabs' bottom edge; strip each tab's bottom border
  (top/left/right only, rounded top); make the active tab join the content below (background matches the
  content surface and it covers the separator at its own bottom). Match the reference geometry.
- `AssistantWorkspace.tsx`: replace the per-tab `×` (`__thread-close`) with a small vertical-`⋮` `Menu`
  per tab whose items are **Renombrar**, **Cerrar pestaña** (close the tab — remove it from the open set
  only, no delete) and **Eliminar hilo** (the existing permanent delete). The third item is kept so the
  documented delete capability is not silently lost and its dialog/handler do not become dead code; ask
  the owner whether they want only Cerrar/Renombrar. Clicking the tab label still activates the tab. Remove
  the single active-thread `Menu` beside the `+` now that each tab owns its actions; keep the `+` (new
  thread).
- Tests: each open tab renders its own `⋮` menu and its items act on that tab; the standalone actions menu
  is gone; existing tab-navigation assertions preserved.

Implementation: `AssistantWorkspace.css` (the bar separator moves to the tabs' baseline; tabs lose the
bottom border; the active tab joins the content), `AssistantWorkspace.tsx` (per-tab vertical-`⋮` `Menu`
with Renombrar / Cerrar pestaña / Eliminar hilo acting on that tab; the standalone active-thread menu
removed; the `+` kept), and `AssistantWorkspace.test.tsx`. Verification from `web/`:
`npx tsc -b --force --noEmit` passed; `npx vitest run src/components/pages/AssistantWorkspace.test.tsx` →
15 passed; `npm run build` passed (existing >500 kB advisory). Commit: `c1221058`.

## Slice 22 — Empty-state greeting with a second line (frontend)

Owner visual review 2026-10-11: with no chat open the state is minimal but needs a second sentence after
the greeting (e.g. "¿Con qué trabajamos hoy?"), the CTA lower, all centred with line spacing.

- `AgentChat.tsx`: under the time-based greeting (`Buenas tardes, admin`) add a second, muted sentence, and
  keep the "Iniciar conversación" `Button` as the CTA clearly below it.
- `primitives.css` `.assistant-chat__hero`: increase the vertical gap so the greeting, the second line and
  the CTA read as separate centred lines (CTA lower), preserving the other hero (thread with no messages).
- Tests: the no-chat empty state renders the second sentence and the CTA; existing assertions preserved.

Implementation: `AgentChat.tsx:898-901` (a second muted line, `¿Con qué trabajamos hoy?`, between the
greeting and the CTA) and `primitives.css:2699-2700` (welcome-only spacing so the greeting, the second line
and the CTA read as separated centred lines; the thread-empty hero is unchanged). Tests in
`AgentChat.test.tsx`. Verification: the same focused run → 69 passed; `npm run build` passed. Commit:
`6fee9929`.
