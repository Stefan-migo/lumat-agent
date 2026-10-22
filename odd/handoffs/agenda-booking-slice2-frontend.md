# HANDOFF — agenda-booking-slice2: continue with the frontend editor (T5)

Date: 2026-10-10. Backend slice (T1–T4) merged to `main`; worktree/branch cleaned.

## Git state

- `main` = `6cd5a72e` (`Merge pull request #558`). Main worktree: `/home/stefan/repos/lumat-agent`.
- No `odd/agenda-booking-slice2` branch or worktree exists — cleaned after the slice.
- Shipped: **backend of `agenda-booking` Slice 2** (per-technician weekly availability). PR **#558**, label `type:feature`
  (branch `odd/agenda-booking-slice2`).
- Task doc (in `main`): `odd/tasks/agenda-booking-slice2.md` — read it first.

## What the feature is (and why H1 is now fixed)

The customer WhatsApp chatbot (`chatbot-intake-redesign`) ended every booking attempt in a human
handoff because `scheduling.open_slots_for_assignment()` found zero slots: `technician_availability`
could only be written by tests, and the panel had only a read route. Slice 2 adds a per-technician
weekly schedule that is **materialized** into rolling `technician_availability` blocks, so the engine
(the same one it already read) now finds real slots.

## What is already DONE (backend, merged)

- Schema `technician_weekly_schedule` + migration `db/migrations/048_technician_weekly_schedule.sql`.
- Service `app/services/technician_schedule.py`: `get_schedule`, `set_schedule` (validated),
  `materialize` (rolling, idempotent), `ensure_horizon`.
- Panel API (operator): `GET` / `PUT /panel/api/technicians/{technician_id}/schedule`.
- Booking wiring: `app/chat/nodes/booking.py` calls `ensure_horizon` before slot search.
- Tests: `tests/integration/test_technician_schedule.py` (+ additions to `test_api_scheduling.py`,
  `test_chat_booking.py`, migration/conftest tables). Full backend suite EXIT 0.

### Backend API contract (for the frontend)

- `GET /panel/api/technicians/{id}/schedule` → `{ "technician_id": int, "schedule": [ {"weekday": 1-7, "opens_at": "HH:MM:SS", "closes_at": "HH:MM:SS"}, ... ] }`
- `PUT /panel/api/technicians/{id}/schedule` body `{ "schedule": [ {"weekday": 1-7, "opens_at": "HH:MM", "closes_at": "HH:MM"}, ... ] }` → same shape on success.
- Invalid input → `400` with `{"code": "invalid_schedule", "message": "..."}` (weekday outside 1–7, duplicate weekday, or `opens_at >= closes_at`).
- Auth: `require_operator_json` (operator).

## What is NEXT (T5 — frontend editor)

Per `odd/tasks/agenda-booking-slice2.md` T5:

1. Web API client + types in `web/src/api.ts` / `web/src/types.ts` for the schedule routes.
2. A per-technician weekly schedule editor, reusing the interaction pattern of `HoursEditor()`
   (`web/src/components/pages/Settings.tsx:96`) and the `DayToggle` primitive.
   - **D7 (owner may relocate):** the editor lives in **`AgendaPage`**, where technicians are already
     listed (operator context). A "Horarios" control per technician opening a dialog is the intended shape.
   - One window per weekday (UniqueConstraint `(technician_id, weekday)`); the `HoursEditor` rule
     "cada día pertenece a un solo horario" applies.
3. Vitest coverage for the editor behavior (valid save, invalid → surfaced, day/time handling).
4. Operator-facing UI copy in **Spanish (es-CL)**, consistent with `AgendaPage`/`Settings`.

## How to resume (new chat)

1. Read `odd/tasks/agenda-booking-slice2.md` (in `main`) + this handoff + the Engram refs below.
2. Create the ODD worktree (owner consent per-feature):
   `rapso worktree create agenda-booking-slice2-frontend --root /home/stefan/repos/lumat-agent --yes`
   → branch `odd/agenda-booking-slice2-frontend`.
3. Fresh worktree setup:
   - `uv sync`
   - `cp ../lumat-agent/infra/.env infra/.env`
   - `bash infra/test-db.sh up` (host port derives from the slug dir name)
   - **`cd web && npm install` — REQUIRED.** After `rapso worktree create`, `web/node_modules` was
     incomplete (missing `vite`, `@vitejs/plugin-react`); vitest failed with `ERR_MODULE_NOT_FOUND`
     until `npm install` was run. Document/verify this before running the web suite.
4. Strict TDD. Runners: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` and
   `cd web && npx vitest run`; type check via `cd web && npm run build` (`tsc -b`).

## RDD (switch ON)

- After each work-unit commit run
  `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <last reviewed boundary> --committed-only --json`
  and run the returned transition only when `review_due` is true. First boundary = branch point.
- **Known gotcha:** `review start`/`review status` may fail with
  `immutable_review_transport_unsupported` (opencode alternately supported/unsupported). Retry the
  **exact** command; the slot is reoffered and it succeeds (it did this session).
- High-risk candidates return the `gentle-ai.review-integration.consent/v3` envelope → relay
  losslessly and wait for the human.

## Decisions closed (do not re-discuss)

- **Option B** (per-technician editor) chosen by the owner over deriving from business hours.
- **D4** — materialize into `technician_availability`; do not change the scheduling engine.
- **D5** — normalized table, one window per `(technician_id, weekday)`.
- **D6** — rolling, idempotent, on-demand materialization (no cron; the worker is DomainEvent-driven).

## Gotchas (verified)

- **Web suite has 26 pre-existing failures on `main`** (AppShell, AgendaPage, ClientFicha,
  UserManagement, AgentChat, AgendaPage stories). CI does **not** run vitest, so they are undetected on
  `main`. They are **unrelated** to this feature — do not attribute T5 failures to the backend merge,
  and do not "fix" them inside this change unless asked. Verify by running the suite and comparing.
- **`rapso worktree cleanup <slug> --remote`** removes the worktree and local/remote branch but leaves
  the test DB. Stop them manually:
  `docker rm -f lumat-test-lumat-agent-odd-<slug>-db-test-1` and
  `docker network rm lumat-test-lumat-agent-odd-<slug>_default`.
- Pre-merge discipline: merge the current `origin/main` into the branch and re-run the full backend
  suite (main moved twice during this slice — #556, #557). Also run `npm install` in `web/` before the
  web suite if the branch touches web.
- `agent/personas/classify.md` must stay byte-identical to `prompts.FALLBACKS` (not touched here).
- Repo has only `.github/workflows/tests.yml` (jobs `test` + `panel`); no issue-first/label enforcement,
  no PR template. Feature PRs use label `type:feature`.

## Declared debt (follow-ups, non-blocking)

- **R3-001 (from the backend RDD review).** `app/services/technician_schedule.py:61-65` — schedule
  replacement deletes matching future `technician_availability` rows by `(technician_id, starts_at)`
  with no provenance marker; could remove a manually authored block at the same start. Harmless while
  no product path creates manual blocks. Revisit with one-off overrides/vacations (deliberate "Out").
- **Comuna-aware assignment** — slots ignore comuna entirely (unchanged from main).
- **VALORES KB content** and the chatbot copy/flow redesign (H2/H3) are separate units.

## Key files

- `odd/tasks/agenda-booking-slice2.md` — task doc (Objective, Decisions, T5 scope).
- `app/services/technician_schedule.py` — schedule service + materializer.
- `app/panel/api/routes/appointments.py` — `GET`/`PUT` schedule routes.
- `app/chat/nodes/booking.py` — `ensure_horizon` wiring.
- `db/migrations/048_technician_weekly_schedule.sql`.
- `web/src/api.ts`, `web/src/types.ts` — web client.
- `web/src/components/pages/AgendaPage.tsx` (+ `.test.tsx`) — editor home (T5).
- `web/src/components/pages/Settings.tsx` — `HoursEditor()` pattern (reference).
- `web/src/primitives/DayToggle.tsx`, `Input`, `Select`, `Button`, `Dialog` — primitives.

## Engram references

- Task doc mirror: `odd/agenda-booking-slice2/tasks`.
- Backend delivery + review: `agenda-booking-slice2 backend (PR1) entregado y revisado` (#6166).
- H1 root cause: `H1 causa raíz: technician_availability...` (#6145).
