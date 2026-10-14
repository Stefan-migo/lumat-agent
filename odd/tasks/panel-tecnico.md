# panel-tecnico — technician gets a restricted view of the general panel + WhatsApp field quick-actions

Branch: chained slices off `main`; current slice `odd/panel-tecnico-wu3` (worktree `../lumat-agent-odd-panel-tecnico-wu3`), base `main`.
Delivery: chained PRs (feature exceeds the ~400-authored-line heuristic).
Test runners: backend `pytest`; frontend `vitest` (+ `tsc -b` only via `npm run build`).

## Specs

S1 — Unified role-gated navigation.
The technician signs in and lands on the SAME panel shell as every other role (`PanelShell`), with the navigation filtered by role. The navigation MUST show only: Agenda, visit detail, Asistente, Notificaciones, Perfil. The separate `TechnicianShell` (`web/src/components/domain/TechnicianShell.tsx`) MUST be removed. The technician loses Proyectos and Sesiones de planificación (assumption, per D1; owner may veto).

S2 — One visit-detail page, role-gated.
The visit detail is the SAME page (`web/src/components/pages/AppointmentDetail.tsx`) for operator and technician, with actions, sections and payload gated by role. For the technician it MUST NOT render: the "Ver ficha del cliente" link, the conversation summary, `appointment.history`, email, or consent.

S3 — Customer phone never exposed to the technician.
Verbatim owner rule: "la gente de lumat no quiere facilitar el numero de telefono del cliente al tecnico". The technician serializer MUST NOT include `customer.phone` / `phone_e164` (`app/panel/api/serializers.py:268`). This amends `TECH-PRIVACY-1` (`openspec/specs/technician-agenda/spec.md`) and `SS-TECH-2` (`openspec/specs/service-scheduling/spec.md`), both of which currently include `phone` in the allow-list.

S4 — Technician closes the visit.
The technician closes an owned visit as `completed` or `no_show` from their panel. The office/operator retains its own "Cerrar visita" fallback. Requires a technician-scoped close route (own appointment only) — today every appointment route is `require_operator_json`.

S5 — Two field quick-action states.
Owner words: "decir llegue o estoy afuera o algo asi". Two states: `en_route` (label "Voy en camino") and `arrived` (label "Llegué / estoy afuera"). They are an axis orthogonal to `AppointmentStatus` and MUST NOT be added to that enum. Transitions are forward-only; skipping `en_route` is allowed.

S6 — Per-state availability windows.
`en_route` is available from T-60 min; `arrived` from T-15 min. Both close when the visit closes (`completed`/`no_show`) or at `ends_at`, whichever is first.

S7 — Resend cooldown.
Owner words: "que 5 minutos mas tarde pueda volver a enviar el mensaje". A 5-minute cooldown per (appointment, action). No new table: the cooldown is read from the last matching `audit_log` event.

S8 — WhatsApp send, phone resolved server-side.
Each state transition sends a Meta-approved business-initiated template for that state. The backend resolves `customer.phone_e164`; the number MUST NOT reach the frontend. Contains no free-form text (free-form is only legal inside the 24h window).

S9 — Office semaphore.
The office can see the visit's technician-state. Location is an open question (agenda list vs appointment detail) — MUST NOT be assumed.

## Tasks

| ID | Task | Specs | Route | Status | Commit |
|----|------|-------|-------|--------|--------|
| WU1 | Frontend unification: explicit role→view map; route the technician through `PanelShell`; role-gate nav and routes; remove `TechnicianShell` | S1 | inline | done | `92735a0a`, `3fa1de8e`, `fa5b0688`, `1a1f6921` |
| WU2 | Privacy: remove `phone` from the technician serializer; amend `TECH-PRIVACY-1` + `SS-TECH-2`; update failing tests | S3 | inline | done | `a7b512b0`, `7274f8e0` |
| WU3 | Technician visit-detail read: allow-listed payload enabling `AppointmentDetail` reuse | S2 | inline | done | `f58a6720`, `649a5d33`, `9c4593b4` |
| WU4 | Technician close route (own appointment, `completed`/`no_show`) + audit | S4 | inline | done | `20b0fe66` |
| WU5 | Visit-state axis: migration `054` (`technician_state`, `technician_state_at`) + `en_route`/`arrived` transitions with window guards + audit | S5, S6 | inline | pending | — |
| WU6 | WhatsApp send + cooldown: template send per state, cooldown guard, technician-only routes | S7, S8 | inline | pending | — |
| WU7 | Frontend actions: visit-detail close + quick actions with cooldown countdown | S2, S4, S5, S7 | inline | pending | — |
| WU8 | Office semaphore UX | S9 | inline | pending | — |
| EXT | Create and approve Meta templates `en_route` + `arrived` | S8 | external | pending | — |

## Log

L1 (2026-10-14, verbatim):
"Hey chat necesito que inicies un rapso sesion. vamos a trabajar en una seccion que no hemos trabajado y esta abandonada.

necesito que trabajemos en el hilo del Panel del Tecnico.

actualmente tiene un frontend muy basico. la idea es dar acceso al panel general. pero con acceso limitado, restringido para el rol del tecnico.

puedes analizar el codigo y decirme que tenemos reespecto a esto. yo lo unico que se que al entrar con un rol tecnico entro a un frontend penoso. esto es lo que existe hoy. es triste.

necesito que analicemos que es lo que recibe el tecnico. que necesita el tecnico realmente.

pero reutilizaremos el frontend que ya tenemos construido para no crear un panel nuevo solo para el tecnico.

luego hay cosas especificas que me gustaria hacer.

como agregar botones de acciones rapdias para cuando el agente llegue a la visita y pueda avisar por whatsapp que esta afuera. o sea que el tecnico apriete un boton y llegue un mensaje directo a whatsapp del cliente para avisa.

la gente de lumat no quiere facilitar el numero de telefono del cliente al tecnico. no por la plataforma al menos. por eso lo de los botones. para eso habria que construir un sistema de envio de mensajes y los permitidoss. me refiero a que el boton este disponible para decir llegue o estoy afuera o algo asi. y que 5 minutos mas tarde pueda volver a enviar el mensaje. 

o algo asi. no lo tengo claro. necesito que me ayudes a ampliar todo este hilo del panel del tecnico."

L2 — Source: Rapso session `.rapsodia-code/sessions/archived/2026-10-14-panel-tecnico/` (was `ready-for-odd/`). Full decisions D1–D8 and the state-machine design live in its `report.md`/`session.md`. Key reversals recorded there: supersedes design decisions #13 (tecnico read-only) and #17 (phone visible) of `.rapsodia-code/sessions/archived/2026-09-09-dashboard-data-design/session.md`.

L3 — Open questions carried: (a) Proyectos/Sesiones removal assumption; (b) operator close fallback kept; (c) office semaphore location; (d) Meta template approval is external and gates end-to-end testing.

L4 — Start: worktree `../lumat-agent-odd-panel-tecnico` created from `main` (repo moved to `1719cc43`; another runtime is active in the main checkout, so isolation is required).

L5 (WU2 done, S3) — Evidence: RED observed (`assert {'address','comuna','name','phone'} == {'address','comuna','name'}` → `Extra items: 'phone'`), then GREEN. Removed `phone` from `to_technician_appointment_dict` (`app/panel/api/serializers.py`), from the `TechnicianCustomer` type, and the `tel:` render in `TechnicianAgenda.tsx`; amended `TECH-PRIVACY-1` + `SS-TECH-2`. Suites: backend `uv run pytest -q` 100% pass; frontend `vitest run` 105 files / 1186 tests pass; `npm run build` (`tsc -b`) exit 0. Commits `a7b512b0` (frontend), `7274f8e0` (backend + specs).
- Environment note: this worktree needs `cp ../lumat-agent/infra/.env infra/.env`, `infra/test-db.sh up` (port 6030), `eval "$(infra/test-db.sh env)"` before `pytest`, and `npm install` under `web/` before `vitest`/`build`.

L6 (WU1 done, S1) — Evidence: new `web/src/components/domain/panelAccess.ts` (role→view map) + tests; `PanelShell` sidebar and mobile tabs now filter by `canOpen`; `AppShell` routes every role through the one shell and canonicalizes disallowed views to the role's landing view; `app.tsx` no longer branches to a technician shell; `TechnicianShell.tsx` + its test deleted. Net −144 lines.
- Behaviour changes accepted: the technician lands on `/panel/app/agenda` (not the dashboard); the mobile tabs for a technician are Agenda/Asistente/Avisos/Perfil; a non-admin opening a direct `users/<id>` URL is now canonicalized to their landing view (the data is still never requested) instead of rendering an in-page permission alert.
- Suites: frontend `vitest run` 104/105 files pass — the one failure is `AgentChat.test.tsx` "renders new stream content while a previous markdown snapshot is stale", which passes in isolation and touches nothing in this diff (load-related flakiness, pre-existing); `npm run build` (`tsc -b`) exit 0. Commits `92735a0a` (access map), `3fa1de8e` (shell + router), `fa5b0688` (delete the private shell).

L7 (WU1 fix, S1) — **Semantic merge caught before merge.** `origin/odd/chatbot-metrics-panel` (#601) also edits `AppShell.tsx`, `PanelShell.tsx`, `AppShell.test.tsx` and `types.ts`, and adds a `chatbot-metrics` view marked `adminOnly`. The first `panelAccess` version kept a hardcoded ALL_VIEWS / ADMIN_ONLY list, so `canOpen('admin','chatbot-metrics')` was false and `canOpen('operador','chatbot-metrics')` was true — the peer's view would have been hidden from admin and leaked to operador. Fix: `panelAccess` owns ONLY the technician restriction; the admin-only set is read from the navigation's own flag via a new `isAdminOnlyView` export, so default-allow applies to admin/operador and a peer's new view cannot be silently hidden. Commit `1a1f6921`.
- Merge-tree integration (repo pre-merge discipline): merged #601 into the branch locally (`--no-commit`, resolved the textual `AppShell.tsx` arm conflict), then ran frontend `vitest run` (**106 files / 1189 tests pass**), `npm run build` (exit 0) and backend `pytest` (exit 0). Merge aborted afterwards; the branch is not polluted by #601.
- ⚠️ Textual conflict expected when #601 lands after this: both add a `page` arm in `AppShell.tsx`. Keep both arms (chatbot-metrics + the technician agenda guard).

L8 (2026-10-14, WU3 done, S2) — Evidence: RED observed (backend 3 new tests failing because the route did not exist; frontend 2 failing because `role` was ignored), then GREEN.
- Backend: new `GET /panel/api/technician/appointments/{id}` (`app/panel/api/routes/technician.py`) behind `require_tecnico`, own appointment only. A missing id and another technician's visit are both **404**, so the route cannot enumerate ids. New `to_technician_appointment_detail_dict` (`app/panel/api/serializers.py`) returns the allow-list `{appointment, customer, case}` with **no** `history`, no `conversation_summary`, no phone, no email, no consent.
- Frontend: `AppointmentDetail` takes a `role` prop; a technician fetches through `getTechnicianAppointment` (normalized to the shared type with `history: []`) and loses the "Ver ficha del cliente" link, the conversation summary, the history, and the operator actions (Reprogramar/Cerrar belong to WU4). `AppShell` renders the role-gated detail for any role when an appointment id is present; `TechnicianAgenda` links each service to `/panel/app/agenda/<id>`.
- Suites: backend `pytest` 2170 collected, exit 0; frontend `vitest run` 106 files / 1194 tests pass; `npm run build` (`tsc -b` + vite) exit 0.
- Flaky (pre-existing, load-related): a full-suite run flaked `AssistantWorkspace.test.tsx` and `ClientesList.test.tsx` (both pass in isolation), on top of the recorded `AgentChat.test.tsx` one. Not caused by this diff (verified in isolation).
- Commits: `f58a6720` (backend), `649a5d33` (role-gated detail), `9c4593b4` (route wiring + agenda link).
- Route: inline (per plan); **Risk item 2** (authorization/ownership + PII allow-list on a new role-scoped read route) → independent verification.

L9 (2026-10-14, WU3 verification) — Independent verifier (Risk item 2): **no blockers**. S2 pass, S3 pass, operator regression pass. Byte-clean allow-list confirmed with a real history row and seeded PII present; missing / foreign / `0` / `-1` / int64-max ids all return the identical `404 {"detail":"appointment not found"}`; operator and admin → 403, unauthenticated → 401; frontend gating reproduced by an SSR render (a technician hides the ficha link, the summary, the history and both operator action buttons; an operator keeps them). One advisory: the always-mounted closure/reschedule `<dialog>`s keep operator copy in the DOM for a technician, but they are inert (`dialog:not([open])`), unreachable, and the backend double-gates close/reschedule to operators — a pre-existing page pattern, not introduced here. Added `1e3460cf` (technician blocked from the operator detail endpoint).
- RDD: `review assess` over `79a288ca..HEAD` read **medium risk, `review_due: false` (under_budget)**, so no native review for this candidate.

L10 (2026-10-14, WU4 done, S4) — Evidence: RED observed (7 new backend tests failing because the route did not exist), then GREEN.
- Backend: `POST /panel/api/technician/appointments/{id}/close` behind `require_tecnico`, own appointment only, `outcome ∈ {completed, no_show}`. A missing id and another technician's visit are both `404` (no enumeration); an unknown outcome → `422`; a non-booked visit → `409 invalid_lifecycle`. The audit is `scheduling.close`: an appointment-history entry plus an append-only `audit_log` row. The response is `{"ok": true}` with no payload, so no history or conversation data can leak back. The operator close route is unchanged — S4 keeps the operator "Cerrar visita" fallback.
- Frontend is out of scope here: the technician's close button is WU7.
- Suites: backend `pytest` 2178 collected, exit 0.
- Commit: `20b0fe66`. Route: inline. **Risk items 1 + 2** (irreversible status change + authorization/ownership on a new write path) → independent verification.

L11 (2026-10-14, WU4 verification) — Independent verifier (Risk items 1 + 2): **no blockers**. S4 pass. Confirmed: own booked visit closes as `completed`/`no_show`; foreign and missing ids are byte-identical `404`; operador and admin → `403`; unauthenticated → `401`; unknown outcome → `422`; non-booked and double-close → `409`; exactly one history entry and one audit row per successful close; the success body is `{"ok": true}` with no history/conversation/PII; the operator close route is byte-identical across the slice and still works. **Rejected-command invariant PASS**: status, history-row count and audit-row count are unchanged after every `404`/`403`/`409`/`422`. One advisory: an out-of-bigint id (`2**63`) returns `500` on the new route — and identically on the unchanged operator route — a pre-existing project-wide `session.get` pattern, not introduced here. Added `e46db0e3` (double-close and body-field ownership-forgery tests).
