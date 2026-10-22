# Handoff — panel-tecnico → WU3 (technician visit detail)

## Where we are

The technician-panel thread opened as a Rapso session (`2026-10-14-panel-tecnico`) and moved to ODD.
Two work units are **merged to `main`** (`79a288ca`):

- **WU2 — privacy contract** (PR **#602**, merged): the technician no longer receives the customer phone; `TECH-PRIVACY-1` + `SS-TECH-2` amended.
- **WU1 — unified shell** (PR **#604**, merged): the technician runs on the shared `PanelShell` with a role-scoped navigation; `TechnicianShell` deleted.

> Note: an intermediate stacked PR **#603** was closed (not merged) when its base branch was deleted for the cleanup. Its content landed via **#604**; ignore #603.

## Ground truth

- Feature doc: `odd/tasks/panel-tecnico.md` (on `main`; Specs S1–S9, Tasks WU1–WU8, Log L1–L7).
- Session record: `.rapsodia-code/sessions/archived/2026-10-14-panel-tecnico/{session.md,report.md}`.
- Engram: `cortex-session/panel-tecnico` (report) + `cortex-session/panel-tecnico/decision/*` (D1–D8); mirrors `#6603/#6605` (task doc) and `#6604/#6606` (WU1/WU2); PR memory `#6608`.
- RDD (native review) is **ON** (global). `gentle-ai review assess` on the branch read **medium risk, review_due false (under_budget)**.

## Next: WU3 — technician visit detail (S2)

Goal: the technician opens a visit from their agenda and reads an allow-listed detail, reusing the SAME `AppointmentDetail` page gated by role — no technician-specific detail component.

What WU3 must build:

1. **Backend read** — `GET /panel/api/technician/appointments/{id}` (technician-only, own appointment only; the existing technician agenda route is the pattern: `app/panel/api/routes/technician.py`). It MUST return an allow-list with **no phone, no `history`, no conversation summary, no email, no consent** (S2/S3; `SS-TECH-2`).
2. **Route wiring** — `panelRoutes` already parses `/panel/app/agenda/<id>` into `{ view: 'agenda', appointmentId }`. Today `AppShell` renders `TechnicianAgenda` for a technician ignoring `appointmentId`; make it render the role-gated detail when an id is present.
3. **Role-gated `AppointmentDetail`** — `web/src/components/pages/AppointmentDetail.tsx` currently fetches the operator endpoint (`getAppointment`). Give it a role-aware data source so a technician fetches the technician endpoint, and hide the operator-only affordances: "Ver ficha del cliente", the conversation summary, and `appointment.history`.
4. **Tests** — backend unit/functional for ownership + allow-list; frontend for the role-gated sections and the drill-down.

Out of scope for WU3: the close action (WU4) and the WhatsApp quick actions (WU5–WU7).

## Environment (this worktree was cleaned; a new one needs it)

```bash
rapso worktree create panel-tecnico-wu3 --yes --root /home/stefan/repos/lumat-agent
cd ../lumat-agent-odd-panel-tecnico-wu3
cp ../lumat-agent/infra/.env infra/.env
infra/test-db.sh up                 # own test DB (derive the port with `infra/test-db.sh port`)
eval "$(infra/test-db.sh env)"      # REQUIRED before pytest — otherwise the admin URL falls back to app:app and migrate fails
npm install --prefix web            # REQUIRED before vitest / build
```

## Gotchas learned this thread

- **Graph**: `graphify-out/` is copied into a fresh worktree but is stale; refresh with `graphify . --update` before editing (Graph Check is blocking).
- **Flaky, pre-existing**: `web/src/components/pages/AgentChat.test.tsx` → "renders new stream content while a previous markdown snapshot is stale" fails only under a full-suite run; passes in isolation. It can flake CI.
- **Engram MCP** returns `multiple active runtime sessions match …` while another runtime works in the same repo → mirror writes via the CLI: `engram save "<title>" "$(cat file)" --type architecture --project lumat-agent`.
- **Peer overlap**: `AppShell.tsx` / `PanelShell.tsx` / `types.ts` are edited by several in-flight threads (#601 landed). The access map is deliberately default-allow for admin/operador so a peer's new destination is never silently hidden; any new admin-only destination must carry `adminOnly: true` in `NAVIGATION`.
- **Merge hygiene**: `odd/panel-tecnico-privacidad` (PR #602) was merged with a **merge commit**; main uses merge commits, not squash.

## Open product questions (still unanswered)

1. Confirm the technician loses Proyectos + Sesiones de planificación (applied in WU1 per D1 — confirm it is intended).
2. Does the office/operator keep its own "Cerrar visita" fallback? (recommended: yes.)
3. Where does the office see the visit-state semaphore? (needed for WU8.)
4. Meta templates `en_route` + `arrived` must be created and approved in WhatsApp Business Manager — external, gates end-to-end testing of WU5–WU7.
