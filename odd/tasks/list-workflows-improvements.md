# Conversations and Clientes list workflows
Objective: Improve how operators find and resume conversations and identify, open, and manage clients, extending the existing Lumat design system.
Branch: `odd/frontend` · Delivery: ask-on-risk, frontend-only; no push/PR/merge · Verification: Vitest, TypeScript/Vite build, Chromium at representative widths.

## Specs

- S1 — “Rehacer la tarjeta móvil alrededor de la identidad.” On Clientes mobile, name and phone form a broad ficha-opening link; show state and consent underneath and highlight “Archivado” only when applicable. Keep checkbox and action menu as separate controls. Do not change ClientFicha or desktop date column. Validate two clients with the same name by phone and verify opening either does not activate checkbox or menu.
- S2 — “Dar una salida clara cuando un filtro deja cero clientes.” Keep the status tabs; group secondary consent/archive filters and identify active filters. Empty status results offer return to “Todos”; clearing search must not clear consent or archived filters. Preserve distinct loading, error, and genuinely empty states.
- S3 — “Alinear la selección con lo que se va a archivar o restaurar.” Rename selection to “Seleccionar esta página”. Selection count, confirmation, and action target set must match exactly; never broaden bulk operation targets. Validate selecting two clients, searching for one, and confirming that hidden clients are not included and the count matches processing.
- S4 — “Mantener el lugar al volver de una ficha.” Preserve Clientes search, filters, and page on return, but never restore bulk selection. Show the actual visible range, e.g. “11–20 de 34” on page two.
- S5 — “Unificar búsqueda y filtros.” Group Conversations tabs, search, and assignee filter visually on mobile and desktop queue; show applied context (example: “Atención humana · Asignadas a mí”) and allow removing one filter without clearing others. Preserve Emergencias shortcut and current filters.
- S6 — “Distinguir una búsqueda sin coincidencias de una bandeja vacía.” Show filtered-empty feedback and a scoped recovery: clear search for a text query, or remove relevant filters for a narrowed result. Load failures remain errors.
- S7 — “Conservar el contexto al volver del hilo.” Preserve Conversations search, assignee, tab, and page during the mobile list/thread/list route without putting phone searches in the URL. Do not change the approved thread design.
- S8 — “Quitar controles que no hacen nada.” Keep the result range but hide pagination controls when there is one page; retain controls for multiple pages.
- S9 — “la idea aqui es solo trabajr frontend de forma que cuando tengamos que mergear no se haya tocado nada extra”. Do not change backend, API contracts, infrastructure, unrelated pages, PWA, tokens/palette, or the approved thread. Reuse existing primitives and the current design system.

## Tasks

- [x] T1 · S1–S4, S9 · delegated direct (parallel writer) · Clients mobile identity, filtered-empty recovery, safe page selection, list context, page range; commit identity pending.
- [x] T2 · S5–S8, S9 · delegated direct (parallel writer) · Conversation queue filters, empty feedback, return context, pagination visibility; preserve existing uncommitted queue optimization; commit identity pending.
- [x] T3 · S1–S9 · inline · Wire each list's return context in `AppShell` (without restoring bulk selection), update `web/DESIGN_SYSTEM.md`, inspect seam/diff, run final suite/build/browser verification; commit identity pending.

## Log

- L1: “continua con la implementacion de esto” (2026-11-17), referring to the owner’s preceding detailed analysis and acceptance cases for Clientes and Conversaciones.
- L2: Current worktree `odd/frontend`; preserve pre-existing uncommitted Conversations-only changes in `web/DESIGN_SYSTEM.md` and `web/src/components/pages/ConversationsList.{tsx,css,test.tsx}`. No code has been written for this feature yet. Graph consulted: `ClientesList()` / `ConversationsList()` imports into `AppShell.tsx`; both queues share `api.ts`, `SearchInput`, `Pagination`, and `Tabs`. Existing design-system architecture entries prescribe Clientes and Conversaciones composition. Keep code frontend-only and the user’s approved thread unchanged.

- L3: “revisa el trabajo hecho. no quedo tan bien . asegurate de mejorar en base a lo analizado” (2026-11-17). Compared draft against the attached acceptance criteria. In Clientes, clustered mobile actions and secondary filters, expanded the opening and selection targets without nesting controls, removed mobile creation-date noise, kept recoveries independent, guarded filtered-empty feedback on request failure, and constrained range to an available page. In Conversaciones, consolidated the filter surface and removed duplicate active-text summaries; added a direct filtered-empty recovery and let the canonical route control the selected tab. No change to the detail views, backend, or PWA runtime.

- L4: RED reproduced the duplicate-filter summary and the false Clientes empty state on a failed request. Build passed. Full initial integration suite passed (1,435 tests across 121 files); the final targeted suite passed (139 across 4 files) after making fixtures wait for completed results. Chromium verified both drills at 320, 390, 768, 1024 and 1440 px with synthetic loopback data and no mutations; mobile duplicate names are distinguishable, checked targets do not rearm after returning, and the conversation phone query survives return without entering the route URL. Final native review preflight returned read-only filesystem before starting a candidate; no approval or delivery is claimed.

- L5: Risk item 1 independently verified in scratch (52/52 Clientes tests with exact archive/restore IDs and rejection probes; 100/100 broader Clientes/AppShell tests). Functional verification is complete. Changes remain local and uncommitted; no approval, push, PR, or merge claimed.
