# ODD: technician-status

## Objective

Make a cancelled visit unmistakable on the technician agenda. Extend the `TECH-PRIVACY-1`
allow-list so `to_technician_appointment_dict` carries `status`, and render that state on the
card without widening what the technician can see.

## Problem

Carried from `odd/tasks/technician-surface.md` (D5, "Open item") and handoff memory #4335. The
technician surface shipped in PR #244 without fixing this because it needed a spec amendment and
an out-of-scope file.

- **Status is invisible.** `to_technician_appointment_dict` (`app/panel/api/serializers.py:208-225`)
  serializes identity, service, slot, timezone, customer contact and `case_summary` — no `status`.
  A `cancelled` visit and a `booked` visit render identically.
- **`list_for_technician` returns every owned visit**, cancelled included
  (`app/services/scheduling.py`). The header counts them all, so the page said `4 visitas` where two
  were cancelled.
- **Option A was rejected by the user.** Filtering cancelled server-side in `list_for_technician` is
  cheaper, but it deletes the warning exactly when it matters: if dispatch cancels while the
  technician is already en route, the visit would vanish with no explanation.
- **Option B is the decision.** The visit stays visible and is marked as cancelled. The technician
  keeps the history and knows not to travel.

## Scope

**In:**

- `openspec/specs/technician-agenda/spec.md` — amend `TECH-PRIVACY-1`.
- `app/panel/api/serializers.py` — `to_technician_appointment_dict`.
- `tests/functional/test_api_technician.py` — allow-list assertions.
- `web/src/types.ts` — `TechnicianAppointment`.
- `web/src/components/pages/TechnicianAgenda.tsx` and its test.
- `web/src/components/primitives/primitives.css` — one rule for the new status badge's grid slot.
- `web/src/stories/pages/_shared/mockData/technicianAgenda.ts` (and the story test only if the type
  change demands it).
- `odd/tasks/technician-status.md` — this record.

**Out:** `app/services/scheduling.py`, `web/src/components/shared/toneMaps.ts`,
`web/DESIGN_SYSTEM.md`, `openspec/specs/panel-design-system/spec.md`,
`web/src/components/pages/AgendaPage.tsx`, any new dependency.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-technician-status`
- Branch: `odd/technician-status`
- Base: `bc2ee447` (main after PR #246)

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). Backend runner:
  `uv run pytest tests/`. Frontend runner: `cd web && npm run test`. Observe RED before each source
  change; never invent RED evidence.
- UI copy stays neutral Chilean Spanish and reuses the labels already shipped in the panel.
- Token-only styling; status is never communicated by colour alone (`DESIGN_SYSTEM.md`).
- Artifacts in English. Conventional commits, no AI attribution.
- No commits, no push, no PR unless the orchestrator authorizes it.

## Graph check

`graphify query "technician agenda serializer allow-list status"` returned the affected nodes:
`app/panel/api/serializers.py`, `app/panel/api/routes/technician.py`, `app/models.py`,
`web/src/components/pages/TechnicianAgenda.tsx`, `web/src/types.ts`,
`web/src/components/shared/toneMaps.ts`, `web/src/components/primitives/StatusBadge.tsx`,
`web/src/hooks/useAsyncData.ts`, `web/src/components/pages/AgendaPage.tsx`.

`TechnicianAgenda.tsx` still has no graph edge to `primitives.css` or to the token nodes — the same
design-system disconnect recorded in `technician-surface`. This change does not cross it.

## Decisions

- **D1 — Reuse the shared label/tone map, do not create a technician-specific one.**
  `web/src/components/shared/toneMaps.ts` already ships `appointmentStatusLabel` and
  `appointmentStatusTone` with `booked | cancelled | completed | no_show → Reservada | Cancelada |
  Completada | No asistió`. Rendering the same domain state with two different tones on two pages
  would violate `DESIGN_SYSTEM.md` ("the same visual tone must mean the same degree of attention
  across pages"). `cancelled` is already `neutral` while `completed` is `success`, so the
  "do not paint a closed entity green just for being closed" rule is satisfied: cancelled and
  completed are not the same. The label text is the state channel; the tone only reinforces it.
  *Follow-up finding (not fixed here):* the shared map gives `booked` a `success` tone, which
  over-signals routine scheduling as a "confirmed successful outcome" (`DESIGN_SYSTEM.md` domain-state
  hierarchy). Correcting it would change the admin `AgendaPage` too — a separate change, outside this
  worktree's authority.
- **D2 — `status: string`, matching `AgendaAppointment.status`.** The panel's existing appointment
  type uses a plain `string` for the same backend field; a union type here would be a second
  vocabulary for one concept.
- **D3 — Header counter: DECIDED by the user — count only the visits that happen, and name the
  cancelled ones apart.** `N` counts every appointment whose status is not `cancelled`, and when any
  visit was cancelled the meta gains `· M cancelada(s)`. Rationale accepted: the number must never
  read as contradicting the cards below it, and a swallowed cancelled visit is what the whole change
  exists to prevent. A cancelled visit never happened, so it is not a `visita` — unlike a `completed`
  or `no_show` one, which did. The suffix keeps the difference explicit instead of silent.

## Tasks

- [x] **T1** — `TECH-PRIVACY-1` amended: the allow-list now names the appointment's own status,
  with the reason (a cancelled and a booked visit are otherwise indistinguishable and the technician
  travels to a visit that no longer exists), and a new scenario "Cancelled visit stays visible and
  marked". The pre-existing "Sensitive fields absent" scenario is unchanged — none of the fields it
  protects became public.
- [x] **T2** — RED/GREEN backend.
  - RED observed (`uv run pytest tests/functional/test_api_technician.py`):
    `test_technician_cannot_forge_ownership_or_receive_sensitive_fields` → `Extra items in the right
    set: 'status'` (line 46), and `test_cancelled_appointment_stays_visible_and_marked` →
    `KeyError: 'status'` (line 63). Two failures, exactly the two the change predicts.
  - GREEN: `"status": appointment.status.value` added to `to_technician_appointment_dict`;
    `4 passed`.
  - The old line 48 listed `"status"` among the values that must **not** appear in the response —
    a test asserting the defect, in the exact pattern the user asked to watch for. It now asserts the
    opposite (the field is present and holds an approved value) while keeping every genuine privacy
    denial: `private@example.test`, `consent_status`, `history`, `sync`, `notes`.
- [x] **T3** — RED/GREEN type and fixtures. `TechnicianAppointment` gained `status: string` with the
  reason in a comment. RED observed: `npx tsc -b --noEmit` reported 7 errors, every one a fixture
  missing the new required field (`TechnicianAgenda.test.tsx` ×2, `technicianAgenda.ts` ×5). The
  page-test fixture, the `visit()` factory and all story mocks now carry it; `tsc -b --noEmit` exit 0.
  The story roster covers all four states (`completed`, `booked`, `no_show`, `cancelled`) and the long
  roster mixes `cancelled` every fourth row, so the story reviews the new badge instead of hiding it.
- [x] **T4** — RED/GREEN card. Two tests added: every state renders as words (`Reservada`,
  `Cancelada`, `Completada`, `No asistió`) and a cancelled visit is not readable as a booked one on
  the same day. RED: both failed against the unchanged card. GREEN: `Badge` + the shared
  `appointmentStatusLabel` / `appointmentStatusTone`, placed immediately under the slot so the state
  is read before the service. One `primitives.css` rule (`justify-self: start`, the same reason the
  call control has one). `vitest run` for the page + story files: **21 passed**.
- [x] **T5** — Header counter, per D3. RED: one new test failed against the unchanged counter
  (`counts the visits that happen and names the cancelled ones apart`). GREEN: the meta now reads
  `${happening} visita(s)· ${cancelled} cancelada(s) · Actualizado HH:MM`, with the suffix omitted
  when nothing was cancelled and the singular/plural derived for both numbers. Two story assertions
  had to move with it, and they are honest updates rather than accommodation: the `Default` roster now
  reads `3 visitas · 1 cancelada` (was `4 visitas`) and the long roster `9 visitas · 3 canceladas`
  (was `12 visitas`). `vitest run` for the page + story files: **23 passed**.
- [x] **T6** — Verification.
  - Backend functional layer: `uv run pytest tests/functional/ -q` → **186 tests, 100% dots, exit 0**
    (this repo's pytest config prints no summary line). Includes `test_api_technician.py` 4/4.
  - Backend full suite `uv run pytest tests/` → **not completed**: the user aborted the run at ~23% to
    keep moving. Every dot up to the abort was a pass; this is partial evidence, not a pass. Re-run on
    a quiet machine before merging.
  - Frontend: `cd web && npm run test` → **78 files, 589 tests, all passing, exit 0**.
  - `cd web && npx tsc -b --noEmit` → exit 0. `cd web && npm run build` → exit 0.
  - Browser check against the running panel → **pending**: `infra-api-1` mounts the main worktree, so
    this needs the worktree's own API + Vite. Not started without asking.
  - Load average was ~10 during the frontend run. No false red appeared, but the run was not on a quiet
    machine, so a second green on a quiet machine is still the stronger signal.

## Acceptance criteria

1. `GET /panel/api/technician/agenda` returns `status` on every row and still never returns email,
   consent, history, messages, notes or calendar sync.
2. The backend exact-key-set assertion names `status` as approved.
3. A cancelled visit is distinguishable from a booked one on the rendered card **by text**, not by
   colour alone, and the distinction survives a greyscale rendering.
4. `uv run pytest tests/functional/test_api_technician.py` passes, and `cd web && npm run test`,
   `cd web && npx tsc -b --noEmit`, `cd web && npm run build` pass.
5. Only the authorized files change.

## Checks

- `uv run pytest tests/functional/test_api_technician.py`
- `uv run pytest tests/` (breadth, on a quiet machine — the suite is load-sensitive)
- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- Browser check against the running panel with the seeded `tecnico` fixture.

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create technician-status`).
- [x] Graph Check (Step 1) run and recorded above.
- [x] Test database for this worktree provisioned (`infra/test-db.sh up`, isolated project
      `lumat-test-lumat-agent-odd-technician-status`, port 5529). `infra/.env` copied from the main
      worktree (gitignored).
- [x] T1 + T2 complete. Evidence: RED 2 failures → GREEN `4 passed`. Not committed.
- [x] T3 + T4 complete. Evidence: RED `tsc` 7 errors → exit 0; RED 2 vitest failures → GREEN
      `21 passed` (page + story files) plus `tsc -b --noEmit` clean. Not committed.
- [x] T5 complete (D3 decided: count only the visits that happen). Evidence: RED 1 failure → GREEN
      `23 passed`; two story assertions updated to the new intended numbers.
- [x] T6 complete except the browser check. Everything green: backend functional 186/186, frontend
      589/589, `tsc` and `build` exit 0. Full backend suite not completed (user aborted at ~23%, no
      failures seen) — recorded as partial.
- [x] Committed as four work units and opened as **PR #247** (`odd/technician-status` → `main`):
      `7a8bcd7c` backend, `db534347` payload type, `6e3cf3d5` card + counter, `dc7718aa` this record.
      Label `type:feature`, GitGuardian pass, MERGEABLE / CLEAN.
- [x] Base note: the branch was fast-forwarded to main `e9b8191b` ("run the test database in RAM…")
      before committing, and `tests/functional/` was re-run green on that base. That commit is **local
      to main and unpushed** (`origin/main` = `bc2ee447`), so the PR diff currently also carries its
      four files (`app/config.py`, `app/services/users.py`, `infra/docker-compose.yml`,
      `tests/conftest.py`). Pushing main removes them from this PR without a rewrite.
- [ ] Browser verification still pending. Nothing left to implement.

## Size

`e9b8191b..HEAD` is **300 changed lines over 10 files**: 182 lines of ODD record, and 118 of code,
spec and tests — 15 of them deletions. Production is small (`TechnicianAgenda.tsx` 11,
`primitives.css` 5, `serializers.py` 1, `types.ts` 3); the rest is tests, the story fixtures and the
spec. Comfortably inside the 400-line review budget.
