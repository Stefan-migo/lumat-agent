# panel-tecnico — technician gets a restricted view of the general panel + WhatsApp field quick-actions

Branch: chained slices off `main`; current slice `odd/panel-tecnico-wu7` (worktree `../lumat-agent-odd-panel-tecnico-wu7`), base `main` (`6a44b631`).
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
| WU5 | Visit-state axis: migration `054` (`technician_state`, `technician_state_at`) + `en_route`/`arrived` transitions with window guards + audit | S5, S6 | inline | done | `36ee6986`, `7d906ae1`, `def40875` |
| WU6 | WhatsApp send + cooldown: template send per state, cooldown guard, technician-only routes | S7, S8 | inline | done | `61cc4b07`, `72d47e04` |
| WU7 | Frontend actions: visit-detail close + quick actions with cooldown countdown | S2, S4, S5, S7 | inline | done | `eef007ee`, `d53457cc`, `cbbf0c22`, `e862c719` |
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

L12 (2026-10-14, delivery) — WU3 pushed as PR **#607** (base `main`; CI green). WU4 as the stacked PR **#615** (base `odd/panel-tecnico-wu3`; its branch contains #607's commits, so the shown diff is only WU4). `main` uses merge commits, so once #607 merges GitHub retargets #615 to `main` with no extra work. The `odd/panel-tecnico-wu3` ref is untouched at its pushed head (`04f49dda`).

L13 (2026-10-14, WU5 done, S5/S6) — Evidence: RED observed (the test module could not import `app.services.visit_state`), then GREEN; the migration guard `test_schema_migrations_records_version` failed once (its expected list) and was updated with `054`.
- Backend: migration `054` adds `technician_state` (`en_route|arrived`, a new PG type `technician_visit_state`) and `technician_state_at` to `appointments`, both nullable — the `appointment_status` enum is untouched, so the axes stay orthogonal. `app/services/visit_state.py` owns the axis: `en_route` from T-60 min, `arrived` from T-15 min, both closing at `ends_at` or earlier when the visit is no longer `booked`. Transitions are forward-only; re-marking the current state is allowed (a resend — the 5-minute cooldown is the caller's, WU6). Each transition writes one append-only `audit_log` entry and never touches `appointment_history`.
- Routes and the WhatsApp send are out of scope here (WU6).
- Suites: backend `pytest` 2192 collected, exit 0.
- Commits: `36ee6986` (schema), `7d906ae1` (service), `def40875` (boundary tests). Route: inline. **Risk item 1** (migration + new persisted columns) → independent verification.

L14 (2026-10-14, WU5 verification) — Independent verifier (Risk item 1): **no blockers**. S5 pass, S6 pass. Migration safety confirmed: applying `054` to a `053` database succeeds, both columns exist and are nullable, the `technician_visit_state` type has exactly `en_route`/`arrived`, the `appointment_status` enum is byte-unchanged, and a pre-existing appointment row survives with both columns NULL. Exact boundaries reproduced (`en_route` at T-60min ±1s, `arrived` at T-15min ±1s, both closing at exactly `ends_at`, closed for `completed`/`no_show`/`cancelled`); forward-only, skip and same-state resend verified in-session and after a DB reload. **Rejected-command invariant PASS** (state, timestamp, audit count and history count unchanged after a backwards or window-closed rejection). A successful transition writes exactly one `audit_log` row and zero `appointment_history` rows. Advisories (non-blocking): the writer's `arrived` negative boundary used T-16min — tightened to the exact T-15min-1s in `def40875`; and WU5 exposes no HTTP route by design (WU6).

L15 (2026-10-14, delivery) — WU5 pushed as the stacked PR **#619** (base `odd/panel-tecnico-wu4` = #615; its branch contains #607's and #615's commits, so the shown diff is only WU5, 309 lines). Chain so far: `#607 → #615 → #619`, each retargeted automatically as its base merges (merge commits). The `odd/panel-tecnico-wu4` ref is back at its pushed head (`949515b5`).

L16 (2026-10-15, WU6 done, S7/S8) — Evidence: RED observed (11 new functional tests: both routes absent → 404, and the two template-name settings unregistered), then GREEN.
- Backend: new `app/services/visit_actions.py`. `notify_customer()` owns cooldown + transition + send as one transaction. The 5-minute cooldown per (appointment, action) is read from the last matching `audit_log` event (`appointment.en_route` / `appointment.arrived`) — no new table, no new column. The send reuses `NotificationOperation` with `idempotency_key = appointment:<id>:visit_state:<state>:<cooldown bucket>` (a 5-minute bucket, so any resend the cooldown allows lands in a later bucket and a replayed send is a no-op) and `process_operation(deliver=notify.send_template(...))`; the recipient is `customer.phone_e164`, resolved server-side. A failed delivery rolls the whole action back, so the technician can retry immediately.
- Routes `POST /panel/api/technician/appointments/{id}/en_route` and `.../arrived` (`app/panel/api/routes/technician.py`): `require_tecnico`, own appointment only; id / foreign → byte-identical 404; window closed or backwards → 409 `visit_state_unavailable`; cooldown → 429 `resend_cooldown` (+ `retry_after_seconds` and a `Retry-After` header); unreachable customer → 502 `notification_failed`. The route takes the appointment row `FOR UPDATE`, so two rapid clicks serialize on the cooldown read. The response is `{ok, technician_state, resend_available_at}` and never the phone. The agenda/detail/close routes were refactored onto one `_owned_appointment` helper with identical semantics.
- Template contract (EXT): body params `{{1}}` customer name, `{{2}}` visit date, `{{3}}` visit time — the `appointment_followup` shape. Names are editable settings `notify.en_route_template_name` / `notify.arrived_template_name` (defaults `en_route` / `arrived`) so the owner can point at the approved Meta name without a deploy.
- Suites: backend `pytest` 2211 collected, exit 0 (was 2203; +8 verification probes). Commits `61cc4b07` (service + routes + tests), `72d47e04` (probes). Route: inline. **Risk item 2** (new role-scoped write routes + PII/phone handling on an outbound send) → independent verification.

L17 (2026-10-15, WU6 verification) — Independent verifier (Risk item 2): **no blockers**. S7 pass, S8 pass, scope pass. Confirmed with its own adversarial probes: exact cooldown boundary (299 s → 429, 300 s → 200); cooldown per action and per appointment, read from the audit row and not `technician_state_at`; the Meta payload is a template to `customer.phone_e164` with the state's name and 3 body params and no free-form text; missing == foreign == byte-identical 404 on both routes; route-level window boundaries (en_route T-60 ±1 s, arrived T-15 ±1 s, `ends_at` and a closed visit → 409); **rejected-command invariant PASS** (state, `technician_state_at`, per-action audit count, total audit count and notification-operation count identical after 404/401/403/409/429/502); no PII in any body; a genuine resend actually sends twice and audits twice (no silent idempotency suppression). Advisories (non-blocking): an unreachable customer is 502 with nothing written (spec silent on it); a visit both outside its window and inside cooldown returns 429 (precedence unstated); the cooldown compares an app-clock `now` against the DB `created_at`.
- RDD: `review assess` over `79a288ca..HEAD` (`--committed-only`) read **medium risk, `review_due: false` (`under_budget`)**, so no native review for this candidate — same as WU3/WU4/WU5.

L18 (2026-10-15, delivery) — WU6 pushed as the stacked PR **#620** (base `odd/panel-tecnico-wu5` = #619; the branch contains #607's, #615's and #619's commits, so the shown diff is only WU6: 632 lines — 260 production/doc + 372 tests). Chain so far: `#607 → #615 → #619 → #620`, each retargeted automatically as its base merges (merge commits). Remaining: WU7 (frontend actions + countdown), WU8 (office semaphore), EXT (Meta template approval, gates end-to-end sending).

L19 (2026-10-15, WU6 refinement, S8) — Verbatim owner request: "si agregemos el nombre del tecnico como variable." The `en_route`/`arrived` Meta template body takes **4** positional parameters, not 3 (supersedes the contract recorded in L16): `{{1}}` customer name, `{{2}}` **technician name**, `{{3}}` visit date `dd/mm/YYYY`, `{{4}}` visit time `HH:MM`. The parameter count is decided before the Meta template is submitted, because changing it after approval forces a new review cycle. The technician name is `User.name`, falling back to `username` when the display name is empty; a missing technician row fails the send exactly like a missing customer phone. Code: `app/services/visit_actions.py` (`_send_state_template`).
- Evidence: RED observed (`assert 3 == 4`), then GREEN. Backend `pytest` 2212 passed, exit 0. The two Meta templates are still pending creation/approval (EXT) and must be created with 4 variables: `Hola {{1}}, tu técnico {{2}} va en camino para tu visita del {{3}} a las {{4}}. Te avisamos cuando llegue.` and `Hola {{1}}, tu técnico {{2}} llegó y te espera afuera para tu visita del {{3}} a las {{4}}. Ante cualquier duda, respóndenos por acá.`
- Verification: this is a small refinement of the already independently verified WU6 send path, delivered by the same writer, and it is pinned by a new contract test; per the verification-timing rule it is covered by the feature-end verifier instead of a new one per delivery.

L20 (2026-10-15, landed) — **WU1–WU6 merged to `main`.** The stacked chain was landed as ONE merge: the tip branch (WU6) was retargeted to `main`, `origin/main` was merged into it once (resolving the shared-file conflicts there instead of four times), and PR **#620** merged; **#624** followed to align the `056` migration header with its filename. GitHub auto-marked **#607** merged (its commits reached `main`); **#615** and **#619** were closed as superseded with a comment pointing at #620. Cleanup was total: the four `odd/panel-tecnico-wu*` branches (local + remote) were deleted, `../lumat-agent-odd-panel-tecnico-wu3` was removed, and its test-DB container was torn down. `origin/main` is byte-identical to the locally verified tree; `main = 6a44b631`. **Known gap, now closed by this entry**: the merge had no "landed" log line (the doc lives in `main` and a PR for one line was not worth a CI cycle). Lesson: **a stacked chain merges as one PR at the tip** — resolving the `origin/main` conflict once, not four times.

L21 (2026-10-15, WU7 done, S2/S4/S5/S7) — Evidence: RED observed (backend `KeyError: 'technician_state'` / `'quick_actions'`; frontend assertions failing before the UI existed), then GREEN.
- **Backend gap closed (the blocker recorded in the handoff).** `to_technician_appointment_detail_dict` (`app/panel/api/serializers.py`) now carries `appointment.technician_state`, `appointment.technician_state_at` and `quick_actions.{en_route,arrived}.resend_available_at`. The route computes the cooldowns through a new `visit_actions.resend_available_at` (same audit-row read as the guard, so the countdown is not re-derived on the client). **No new PII**: the phone stays server-side and the allow-list is unchanged otherwise. Per the plan, **S6 window availability stays client-derived** from `starts_at`/`ends_at` + `status` + `technician_state`, because only the cooldown needs the audit log; the backend re-validates every send anyway.
- **Frontend** (`web/src/components/pages/AppointmentDetail.tsx`): the technician now gets the close action (through `closeTechnicianAppointment`, not the operator route — S4) and an "Avisar al cliente" card with the two quick actions ("Voy en camino" / "Llegué / estoy afuera"), each opening on its own lead, hidden once the axis has passed it (forward-only), and showing a `Reenviar en m:ss` countdown (disabled) while cooling down. The page gained a `now` prop so the field clock is deterministic in stories/tests; live ticking only runs for a technician. New client fns (`closeTechnicianAppointment`, `sendTechnicianQuickAction`) and types; minimal CSS reuses the free `history` grid cell.
- Suites: backend `pytest` 2261 passed, exit 0 (43 in the technician file); frontend `vitest run` 108 files / 1233 tests pass; `npm run build` (`tsc -b` + vite) exit 0. Two existing tests were updated for S4 (a technician now *does* see "Cerrar visita"): `AppointmentDetail.test.tsx` and `AppShell.test.tsx`.
- Commits: `eef007ee` (backend payload + cooldown helper + tests), `d53457cc` (client + types), `cbbf0c22` (page + tests + CSS), `e862c719` (verifier regression tests). Route: inline. **Risk item 2** (the role-scoped PII allow-list serializer changes and the technician UI wires an irreversible close) → independent verification.
- Graph check (project gate): `graphify query "technician visit state quick actions"`; `AppointmentDetail.tsx` and `api.ts`/`types.ts` share a community, confirming the page is shared code touched by both roles.

L22 (2026-10-15, WU7 verification) — Independent verifier (Risk item 2): **no blockers**. S2 pass, S4 pass, S5 pass, S6 pass, S7 pass, S8 pass, scope pass. Confirmed with its own probes in a scratch copy: the technician payload is **byte-clean** with real PII and a real history row present (only `appointment`/`customer`/`case`/`quick_actions`; no phone, email, consent, history or conversation summary); authorization is unchanged on all four technician routes (missing == foreign == byte-identical 404; operador/admin 403; unauthenticated 401) and a technician is still 403 on both operator routes; the surfaced cooldown follows the **audit row**, not `technician_state_at` (a state column with no audit event yields `resend_available_at: null`); the **rejected-command invariant HOLDS** (status, `technician_state`, `technician_state_at`, per-action audit, total audit, `appointment_history` and `notification_operation` counts all unchanged after 404/403/409/422/429); S6 boundaries exact (`en_route` T-60min, `arrived` T-15min, both 409 at/past `ends_at`); S8 sends a template with 4 params and no phone in the body; and the operator detail + close output is **shape-identical** at `6a44b631` vs HEAD. Frontend gating reproduced (technician: close + both quick actions, no ficha/summary/history/Reprogramar; operator: ficha/Reprogramar/Cerrar, no quick actions; countdown and forward-only behaviour from `resend_available_at`). Two of the verifier's probes were kept as regression tests (`e862c719`). Advisories (non-blocking, all pre-existing): window/cooldown precedence returns 429 before 409; the shared page still mounts the closed reschedule dialog with operator copy for a technician; out-of-bigint ids → 500 project-wide.
- RDD: `review assess` over `6a44b631..HEAD` (`--committed-only`) read **medium risk, `review_due: false` (`under_budget`)**, so no native review for this candidate — same as WU3–WU6.

L23 (2026-10-15, delivery) — WU7 pushed as PR **#627** (base `main`). The whole thread now starts from `main`, not from a stack. Before merging, `origin/main` was merged into the branch (main had advanced to `9eaaceba` with #625 and #626 — the assistant global-skills/roles threads, **zero shared files** with WU7) and the local integration was re-run over the merged tree: backend `pytest` **2268 passed** (exit 0), frontend `vitest run` **108 files / 1233 tests pass**, `npm run build` (`tsc -b` + vite) exit 0. That is the repo's pre-merge discipline: the branch must contain the current head of the base and the local integration runs over the merged tree, because `mergeable: CLEAN` says nothing about semantics. Remaining thread work: WU8 (office semaphore) and EXT (Meta templates).

