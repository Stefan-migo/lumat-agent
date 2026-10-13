# automatizaciones-frontend

## Objective

Redesign the **Automatizaciones** panel section (catalog + installed recipes) to match the
owner's primary reference: a "plantillas" experience with **tabs (Catálogo / Instaladas)**,
**buscador**, **filtro por categoría**, a **row layout with category + channel chips**, and a
**"Configurar" dialog** — all on the existing Lumat panel design system. Add real descriptions to
the code catalog so each row can show one.

## Problem

The current `web/src/components/pages/AutomationRecipesPage.tsx` is a functional but plain page:
an ungrouped `<Card>` list, an inline install form, plain "Activa/Inactiva" text, no dedicated CSS.
Every catalog recipe carries `description=""` (`app/services/recipes.py`), so the page cannot
present the reference's per-row description. The owner supplied the primary reference image.

## Why

Owner request (2026-10-13): continue the automatizaciones thread and redesign the frontend.
Chosen fidelity = **full** (tabs, buscador, filtro, Configurar dialog) **+ real catalog
descriptions**.

## Decisions (closed — do not re-litigate)

1. **Fidelity** = FULL match to the reference: tabs Catálogo/Instaladas, buscador, filtro por
   categoría, filas con chips de categoría y de canal, "Configurar" en `Dialog`.
2. **Descriptions** = add real (factual) descriptions to the 9 recipes in
   `app/services/recipes.py`. Values only — **no reorder, no rename, no id/parameter change**.
3. **Category labels + icons and recipe icons** are resolved in the **frontend** by mapping the
   backend slug (`reservas` / `operacion` / `postventa` / `resumenes`), mirroring the existing
   `web/src/roleLabels.ts` convention.
4. **"Configurar"** opens the deterministic parameter form in a `Dialog` primitive
   (`variant="sheet"` for small screens).
5. **No new endpoints.** There is **no delete/uninstall** endpoint: installed rows offer
   **Activar / Desactivar** and **Editar** (`PATCH /automation-installations/{id}` exists).
6. **Honest UI**: real counts (`recipes.length`, `installations.length`); never fabricate recipes,
   sends or counts; empty/loading/denied/error states must be real.

## Scope

**In:** backend catalog descriptions; frontend redesign (page + CSS + category label/icon map +
Configurar dialog + tabs/search/filter + installed tab + tests + story).

**Out:** new backend behavior/endpoints, pagination, auth changes, other panel sections,
A1 (worker cron), D1 (payments), natural-language input.

## Constraints

- Chat in Rioplatense Spanish; artifacts, code, comments and commits in **English**; UI copy in
  Chilean neutral Spanish. Conventional Commits, no AI attribution.
- **Token-only CSS** (`web/src/tokens/tokens.css`); page-scoped BEM `.automation-recipes__*`;
  never hardcode hex (hex guard). Do not modify shared primitive CSS for page-specific layout.
- Reuse existing primitives: `Tabs`, `SearchInput`, `Select`, `Badge`, `Dialog`, `Button`, `Icon`,
  `Skeleton`, `PageFrame`, `StateMessage`, `EmptyState`. Verify a lucide icon export exists before
  using it.
- Graph Check (`graphify query` / `graphify path`) before touching each module; record the nodes
  and edges consulted.

## Reference (owner, primary)

Header (title + subtitle + "Ver instaladas (N)" action) · info banner when there are no
installations · tabs "Catálogo (N)" / "Instaladas (M)" · toolbar (buscador + "Todas las
categorías") · panel "Plantillas disponibles" whose rows are: leading lucide icon, name,
description, category chip (icon + label), channel chips (Email / WhatsApp), and a
"+ Configurar" button. Footer note: "Configura el mensaje antes de activar la automatización."

The mock shows 7 recipes / 3 categories; the **real** catalog is **9 recipes / 4 categories**
(`reservas` ×4, `operacion` ×1, `postventa` ×2, `resumenes` ×2). Render the real counts.

## Reuse inventory (verified HEAD 89cd1494)

- Backend catalog: `app/services/recipes.py` — `_event_recipe` / `_offset_recipe` /
  `_schedule_recipe` set `description=""`; `RECIPES` = 9 entries in 4 categories.
- API: `app/panel/api/routes/automation_recipes.py` (GET recipes; GET/POST/PATCH installations;
  `/{id}/enable`; `/{id}/disable`). Serializer exposes `description`, `category`, `channel_allowed`,
  `parameters`.
- Frontend: `web/src/components/pages/AutomationRecipesPage.tsx` (+ `.test.tsx`),
  `web/src/stories/pages/AutomationRecipesPage.stories.tsx`, `web/src/api.ts` (l.240-245),
  `web/src/types.ts` (l.75-80), `web/src/components/domain/AppShell.tsx` (l.125),
  `web/src/components/domain/PanelShell.tsx` (l.75).
- Primitives: `Tabs.tsx` (`tabs` = id/label/icon/description; controlled via `activeTab` /
  `onTabChange`), `SearchInput.tsx` (`onSearch`, `delay`), `Dialog.tsx`
  (`open/onClose/title/children/icon/description/size/variant`), `Badge.tsx` (`tone`),
  `Icon.tsx` (lucide), `Select.tsx`, `Button.tsx`, `Skeleton.tsx`.
- Shared: `PageFrame.tsx` (`title/subtitle/meta/actions/state`), `StateMessage.tsx`,
  `EmptyState.tsx`. Dialog precedent: `web/src/components/shared/*Dialog.tsx`.
- Tokens: `web/src/tokens/tokens.css` (forest primary, lime accent, sage surfaces, semantic tones).

## Work units (stable IDs)

### WU1 — Backend: real recipe descriptions

- [x] Add a `description` parameter to `_event_recipe`, `_offset_recipe`, `_schedule_recipe` and
  populate all 9 `RECIPES` entries. Do NOT reorder or rename. Finance wording (Chilean neutral
  Spanish), matching the reference:
  - `appointment_confirmation` → "Envía un mensaje automático al confirmar una reserva."
  - `appointment_cancellation` → "Notifica automáticamente al cancelar una visita."
  - `appointment_rescheduled` → "Informa automáticamente al reprogramar una visita."
  - `appointment_no_show` → "Envía un aviso automático al registrar una inasistencia."
  - `case_new_request` → "Notifica automáticamente al equipo al recibir una nueva solicitud."
  - `appointment_review_request` → "Solicita una evaluación automáticamente después de una visita."
  - `customer_maintenance` → "Envía un recordatorio automático según el intervalo configurado."
  - `admin_daily_summary` → "Envía un resumen diario de la operación al administrador."
  - `admin_weekly_summary` → "Envía un resumen semanal de la operación al administrador."
- [x] Guard test asserting every recipe has a non-empty `description` (strict TDD: observed RED
  first, then GREEN).
- [x] Verify: `uv run pytest tests/integration/test_automation_installations.py
  tests/functional/test_api_automation_recipes.py` green; then full `uv run pytest tests/`.
- Commit `a8767cf4` (feat(automations): add recipe catalog descriptions). Observed: full backend
  suite **1933 passed**.

### WU2 — Frontend: redesigned Automatizaciones page

- [x] `web/src/components/pages/AutomationRecipesPage.tsx` redesigned; new
  `web/src/components/pages/AutomationRecipesPage.css` (imported): namespaced `.automation-recipes__*`,
  token-only.
- [x] Category map (slug → label + lucide icon) and per-recipe icon map (frontend).
- [x] Header: title + subtitle; action button **"Ver instaladas (N)"** → Instaladas tab.
- [x] Banner (`PageFrame` `state`): "Aún no tienes automatizaciones instaladas." only when there
  are none.
- [x] `Tabs`: "Catálogo (N)" / "Instaladas (M)".
- [x] Catálogo: `SearchInput` + category `Select`; panel "Plantillas disponibles"; rows with icon,
  name, description, category chip, channel chips, "+ Configurar" → `Dialog` form (channel/time/
  weekday/number) → create; already-installed recipes show a success `Badge` + "Editar" → PATCH.
- [x] Instaladas: rows with name, parameters summary, `Badge` Activa/Inactiva, Activar/Desactivar
  (+ Editar).
- [x] States: loading (`Skeleton`/`StateMessage`), denied, error (+ Reintentar), filtered-empty,
  empty installed.
- [x] Tests (`AutomationRecipesPage.test.tsx`): catalog render, search filter, category filter,
  configure-dialog create, installed toggle, honest states. Story updated.
- [x] Verify: `cd web && npm run build` + focused `npm test`.
- Commits `2fce30b1` (page redesign) + `33fd2474` (CSS `.btn` fix, from the parent spot check that
  found dead `.button` selectors). Observed: `npm run build` green; serialized `npm test`
  **105 files / 1150 tests** green.

## Review follow-ups (non-blocking — from RDD `review-c281e351db664dee`)

- [ ] **R3-001** (`web/src/components/pages/AutomationRecipesPage.tsx:154`) — when a create/edit save
  fails inside the `Dialog`, `actionError` renders outside the dialog (above the tabs) while the
  sheet stays open, so the failure may not be visible; the form has no inline error. Add inline
  error feedback inside the dialog. Advisory WARNING, non-blocking — does NOT reopen the review.

## Delivery strategy

- Forecast: WU1 tiny; WU2 may approach/exceed ~400 authored lines → `ask-on-risk` (default).
  PR/merge = owner's decision. Single branch `odd/automatizaciones-frontend`.

## TDD resolution

- Backend: `openspec/config.yaml` `testing.strict_tdd: true`, runner `uv run pytest tests/`
  → **TDD ENABLED** (RED → GREEN → REFACTOR with observed evidence) for WU1.
- Frontend: `npm test` (vitest) + `npm run build` (type-check via `tsc -b`). Ordinary checks.

## Verification

- Backend: `bash infra/test-db.sh up` + `eval "$(infra/test-db.sh env)"` && `uv run pytest tests/`.
- Frontend: `cd web && npm run build && npm test -- --maxWorkers=1 --testTimeout=15000`
  (serialize; the parallel run flakes under load).
- Per work unit: Graph Check recorded; conventional commit; observed verification before checking
  off.

## Progress log

- 2026-10-13 — Task doc created. Worktree `../lumat-agent-odd-automatizaciones-frontend`, branch
  `odd/automatizaciones-frontend`, base main `89cd1494`. Graph nodes consulted:
  `AutomationRecipesPage.tsx`, `PageFrame()`, `Badge()`, `Dialog()`, `Tabs()`, `SearchInput()`,
  `Icon()`, `PanelShell.tsx`, `AppShell.tsx`, `panelRoutes.ts`, `types.ts`, `api.ts`.
- 2026-10-13 — WU1 implemented (`a8767cf4`): descriptions for all 9 recipes; guard test added.
  Backend suite **1933 passed**.
- 2026-10-13 — WU2 implemented (`2fce30b1`): redesigned page + CSS (tabs, buscador, filtro, filas
  con chips, Configurar dialog, tab Instaladas). Parent spot check caught dead `.button` selectors
  (Button renders `.btn`) → fixed in `33fd2474`. `npm run build` green; serialized `npm test`
  **105 files / 1150 tests** green.
- 2026-10-13 — RDD review `review-c281e351db664dee` (1 lens review-reliability, medium, 757 lines):
  **approved**, 0 blockers, 1 advisory (R3-001). Authority **burned**.
