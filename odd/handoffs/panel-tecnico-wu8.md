# Handoff — panel-tecnico → WU8 (office semaphore: agenda + visit detail)

Written 2026-10-15. Untracked in the main worktree, like every other handoff here.

> **STATUS — CLOSED (2026-10-15).** WU8 landed as PR **#630** (`main = bc36318c`); the WU8 worktree, its branch (local + remote) and its test DB are gone. **The whole panel-tecnico thread is done**: WU1–WU8 merged, only **EXT** remains and it is on the owner's side (the two Meta templates are created and awaiting Meta approval; the send stays mocked until then, and needs no code change). The maker-checker question is closed as "not now" — `scheduling.close` stays terminal. The body below is the pre-WU8 plan; the authoritative evidence is Log L24–L28 in `odd/tasks/panel-tecnico.md`.

## Where we are

**WU1–WU7 are MERGED to `main`.** `main = 3f329cb9` (merge of PR **#627**, WU7).

```
main 3f329cb9
 └── #627  WU7 — technician field quick actions + visit close   (merged)
 └── #626  assistant config-layer T9                            (merged, other thread)
 └── #625  assistant config-layer T8                            (merged, other thread)
```

- Cleanup for WU7 was total: branch `odd/panel-tecnico-wu7` deleted (local + remote), worktree `../lumat-agent-odd-panel-tecnico-wu7` removed, its test-DB container torn down. **No worktree/branch for this thread exists right now.**
- Pre-merge discipline was applied: `origin/main` merged into the branch, then the local integration re-run over the merged tree (backend **2268 passed**, frontend **108 files / 1233 tests**, `npm run build` exit 0).

## Ground truth

- Feature doc: `odd/tasks/panel-tecnico.md` (**on `main`**) — Specs S1–S9, Tasks WU1–WU8 + EXT, Log L1–L23. **WU1–WU7 done**; **WU8 pending**; EXT pending.
- Session record: `.rapsodia-code/sessions/archived/2026-10-14-panel-tecnico/{session.md,report.md}` — decisions D1–D8 in `report.md`.
- Engram: `odd/panel-tecnico/tasks` (task-doc mirror, obs **#6621**), `odd/panel-tecnico/decisions` (S1 confirmation, obs **#6652/#6653**), `infra/meta-waba-lumat`.
- RDD is **ON** (global). WU3–WU7 all assessed `medium`, `review_due:false` (`under_budget`) — **no native review has ever been required for this thread**.
- Test runners: backend `pytest`; frontend `vitest` (+ `tsc -b` only via `npm run build`).

## Two decisions taken by the owner (record them in the doc when WU8 opens)

1. **S1 confirmed**: the technician **loses Proyectos + Sesiones de planificación** (it was flagged "assumption, per D1; owner may veto" — rewrite S1 and append the verbatim Log entry).
2. **S9 location decided: BOTH** — the office semaphore goes in the **agenda list** AND the **visit detail**. The doc's S9 currently says the location "MUST NOT be assumed"; rewrite it.

Do these two doc edits in WU8's first doc commit (they do not warrant their own CI cycle — same lesson as L20).

## WU8 — office semaphore (S9)

**What exists (backend, from WU5/WU6):** migration **`056`** added `technician_state` (`en_route|arrived`, a separate PG type) and `technician_state_at` to `appointments`; the technician sets them through the quick actions. **The technician details payload exposes them (WU7).**

**What is missing:** the office sees **nothing**. Verified — the two office readers do not carry the field:

- Office **agenda list** → `to_agenda_dict` (`app/panel/api/serializers.py`) is what `app/panel/api/routes/appointments.py:70` (`GET /panel/api/appointments`) returns. Its keys: `id, service, customer_id, customer_name, customer_address, customer_comuna, case_id, case_name, technician_id, technician_name, local_start, timezone, starts_at, ends_at, status, sync`. **No `technician_state`.**
- Operator **visit detail** → `to_appointment_dict` (`app/panel/api/serializers.py:218`), wrapped by `to_appointment_detail_dict` (`:241`). **No `technician_state`.**

### Backend

Add `technician_state` (and `technician_state_at`, if we show "hace X min") to **both** serializers.

⚠️ **Blast radius of `to_appointment_dict` — it is NOT detail-only.** It is also returned by the mutation responses (`app/panel/api/routes/appointments.py:121, 150, 163, 184` — reschedule/close/cancel/create) and by `app/services/dashboard.py:237`. The addition is additive, but every test that pins those exact key sets will need updating. Consider whether the dashboard wants it (probably harmless) or whether a narrower serializer is cleaner.

### Frontend

- `web/src/types.ts`: `AgendaAppointment` needs the new optional field(s). (**Good news:** `Appointment` already carries optional `technician_state` / `technician_state_at` and `TechnicianVisitState` exists — added in WU7 — so reuse them, do not redeclare.)
- Office agenda page: `web/src/components/pages/AgendaPage.tsx` — render the badge per visit row.
- Operator detail: `web/src/components/pages/AppointmentDetail.tsx` — reuse the badge it already renders for the technician ("Último aviso enviado").
- ⚠️ **`QUICK_ACTION_LABELS` is module-local inside `AppointmentDetail.tsx`** (WU7). Extract it to a shared module (e.g. `web/src/components/shared/`) so the agenda reuses the same labels instead of duplicating the strings.
- Sub-decision still open: show **only the state**, or **state + "hace X min"** (which is what distinguishes "va en camino hace 2 min" from "dijo que llegó hace 40 min y no cerró nada"). `technician_state_at` is the input.

### Tests to UPDATE (not create)

- `tests/functional/test_api_technician.py::test_operator_detail_payload_carries_no_technician_field_state` — it **pins the absence** of `technician_state` on the operator payload. WU8 inverts it. Do not delete the intent: keep pinning that no *other* PII leaks.
- Any backend test pinning the exact key set of `to_appointment_dict` / `to_agenda_dict` outputs.

### Definition of done for WU8

- RED→GREEN; backend `pytest` exit 0; frontend `vitest run` + `npm run build` (the repo's pre-merge integration).
- RDD `review assess --base-ref <branch point> --committed-only`; independent verification if the Risk line is high.
- Doc updated (WU8 row + log entry, **including the two decisions above**) and mirrored to Engram (`odd/panel-tecnico/tasks`).
- PR from `main`. Before merging: merge `origin/main` into the branch and run the local integration over the merged tree.

## Environment

### Fresh worktree for WU8

```bash
rapso worktree create panel-tecnico-wu8 --yes --root /home/stefan/repos/lumat-agent
cd ../lumat-agent-odd-panel-tecnico-wu8
cp ../lumat-agent/infra/.env infra/.env
uv sync                                    # REQUIRED: rapso does not create .venv
infra/test-db.sh up                        # own test DB; port via `infra/test-db.sh port`
eval "$(infra/test-db.sh env)"             # REQUIRED before every pytest run
npm install --prefix web
```

### The dev stack is ALREADY up (main worktree) — useful for looking at the panel

- API container `infra-api-1` → http://localhost:8000 (holds the **main worktree's** repo bind-mounted, so it serves `main` = WU7).
- Vite dev server → http://localhost:5173/panel/app/ (proxies `/panel/api` → :8000).
- Dev DB container `infra-db-1`.
- **Technician login for manual review: `jperez` / `tecnico-demo`.** ⚠️ That password was **set directly in the local dev DB** to hand the owner a login — it is a local-dev artifact, not a repo change.
- The dev DB had to be migrated by restarting the API container (`docker compose -f infra/docker-compose.yml restart api`) because the container's `db/migrate.sh` only runs at startup and it predated migration `056`.

## Open product questions

1. **The close model — UNRESOLVED, and it is NOT part of WU8.** The owner asked whether, since the *technician* closes the visit, the operator/admin should then **confirm** the close. Answer given (verified in code): today there is **no confirmation step** — `scheduling.close` is terminal and irreversible, and the technician route and the operator route call the **same** function (status → `completed|no_show`, one history row, one audit row, an event published that fires the follow-up, plus a `notify_admins` on `no_show`). S4 calls the operator close a **fallback**, not a confirmation. A maker-checker model would need a new lifecycle state or a new axis, would touch the office board, and forces a decision on when the customer follow-up fires — much bigger than WU8. **Needs an owner decision before any design.**
2. **Semaphore content**: state only, or state + "hace X min"?
3. **EXT**: the Meta templates (`en_route`, `arrived`) are still pending approval → the real WhatsApp send stays mocked end-to-end.

## Explicitly OTHER threads — do not fold into this one

- **Automations / chatbot**: the owner is driving this in another thread (they already have an agent on it). Everything about post-visit customer messaging lives there. Key context if asked: the post-visit customer message is **already modeled** as the recipe `appointment_review_request` ("Pedir evaluación", postventa, customer-facing, default 3 days after `ends_at`, trigger `app/services/time_triggers.py::_review_due`); it does **not deliver** because the automation send is free-form (`create_operation(content=...)`, no template) and a post-visit message is outside Meta's 24 h window, and its template does not exist yet. A *new* recipe is not needed; making the existing one deliver is the fix.
- **Close-confirmation (maker-checker)**: see open question 1 — belongs to its own decision, not to WU8.

## Gotchas learned this thread

- **The dev stack's DB is only migrated when the API container starts.** If `technician_state` is missing, restart `infra-api-1`; don't go hunting code bugs.
- **`infra/docker-compose.yml` mounts the repo root**, so the running container serves whichever worktree launched it (here the main one).
- `git status` in a fresh worktree is dirty-free even with `.venv`, `node_modules`, `infra/.env` present — so `rapso worktree cleanup` is clean.
- **`ripgrep` `-r` is `--replace`, not recursive.** `rg -rn "x"` silently rewrites matches in the output. `rg` recurses by default; never pass `-r` unless replacing.
- **`app` role has INSERT+SELECT only on `audit_log`** — tests can insert an explicit `created_at` (to age the cooldown) but cannot `UPDATE` it.
- **`appointments` has an exclusion constraint** (`appointments_technician_no_overlap`): fixtures that rewrite `starts_at` to now-relative windows must use one appointment per technician, or non-overlapping windows.
- **`addopts` already sets `-q`** in `pyproject.toml`; a second `-q` hides pytest's final `N passed` line.
- **`eval "$(infra/test-db.sh env)"` does not persist across shells** — prefix every `pytest` run.
- **`uv sync` is required** for a fresh worktree.
- **`test-db.sh` derives project+port from the worktree directory name**, so each worktree gets its own container/port.
- **A committed slice is assessed with** `gentle-ai review assess --base-ref <branch point> --committed-only`; without `--base-ref` it reports `unassessable` (which counts as high).
- **RDD assess uses `--base-ref` = the last reviewed boundary**, and after each work-unit commit the boundary advances.
- **Stacked chains: merge as ONE.** Resolve the `origin/main` conflict once on the tip and merge that single PR (L20's lesson).
- **Flaky under a full frontend run** (pre-existing, load-related): `AgentChat.test.tsx`, `AssistantWorkspace.test.tsx`, `ClientesList.test.tsx`. They pass in isolation — re-run before investigating.
- **GitGuardian false positive in `main`**: `tests/functional/test_api_thread_resources.py` `_login(..., password="res-pass")` is flagged as `Generic Password`. Pre-existing, only surfaces in a PR whose range includes merged `main`.

## Definition of done for the whole thread (remaining)

- **WU8** (above) — the last code slice.
- **EXT** — owner: create + approve the Meta templates `en_route` and `arrived` (4 positional params: `{{1}}` customer name, `{{2}}` technician name, `{{3}}` date `dd/mm/YYYY`, `{{4}}` time `HH:MM`; category Utility; language exactly `es`). Until approved, end-to-end sending stays mocked.

`main` has no branch protection, so `gh pr merge` works with a red check — the pre-merge discipline is evidence, not enforcement.
