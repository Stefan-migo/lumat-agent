# Handoff — panel-tecnico → WU6 (WhatsApp send + cooldown + technician routes)

## Where we are

The technician-panel thread runs as a **chain of stacked PRs** off `main` (`main` uses merge commits, not squash). Five work units are done; three slices are open, stacked on each other:

```
main
 └── #607  odd/panel-tecnico-wu3  (04f49dda)   WU3  visit-detail read      — open, CI green
      └── #615  odd/panel-tecnico-wu4  (949515b5)   WU4  close route       — open
           └── #619  odd/panel-tecnico-wu5  (debcbcbf)   WU5  visit-state axis  — open  ← stack tip
```

- Already merged: **#602** (privacy contract) and **#604** (unified shell).
- Each PR's base is the previous slice, so each shows only its own diff. Merge in order; GitHub retargets each to `main` automatically.
- WU1–WU5 done. Next is **WU6**.

## Ground truth

- Feature doc: `odd/tasks/panel-tecnico.md` (Specs S1–S9, Tasks WU1–WU8, Log L1–L15). **WU1–WU5 done**; WU6–WU8 + EXT pending.
- Session record: `.rapsodia-code/sessions/archived/2026-10-14-panel-tecnico/{session.md,report.md}` — **in the MAIN repo**, not in a worktree. The state-machine design and decisions D1–D8 live in `report.md`.
- Engram: topic `odd/panel-tecnico/tasks` (task-doc mirror, #6621) and `odd/panel-tecnico/wu3` (#6622).
- RDD (native review) is **ON** (global). Every slice assessed `medium`, `review_due:false` (under_budget) — no native review has been required yet.

## Next: WU6 — WhatsApp send + cooldown + technician routes (S7, S8)

Goal: each `en_route`/`arrived` transition sends a Meta-approved business-initiated template to the customer, guarded by a 5-minute resend cooldown; the customer phone is resolved **server-side** and must NEVER reach the frontend.

What WU6 must build:

1. **Technician routes** — `POST /panel/api/technician/appointments/{id}/en_route` and `.../arrived` (technician-only, own appointment). Pattern file: `app/panel/api/routes/technician.py`. Ownership miss → **404** (identical to WU3/WU4); window closed → **409**; cooldown active → **409/429** with a machine code.
2. **Transition + send** — reuse `app/services/visit_state.py` (`mark` already enforces S5/S6) and then send the template. Send infra to study: `app/services/send.py` (free-form — legal only inside the 24h window, so NOT what you want), `app/services/notify.py` (`send_template`, business-initiated), `app/services/templates.py` (named templates; `app/settings.py` ~174–176 lists the current ones: `emergency_alert`, `appointment_reminder_24h`, `appointment_followup`, `appointment_followup_no_show`).
3. **Cooldown (S7)** — 5 min per (appointment, action), read from the **last matching `audit_log` event**; NO new table, no extra column. Concurrency: the session risk table says to reuse `NotificationOperation.idempotency_key` semantics so two rapid clicks cannot both pass.
4. **Phone stays server-side (S8)** — resolve `customer.phone_e164` in the backend; the number must not appear in any response the frontend receives. No free-form text.
5. **Tests** — backend: ownership, window, cooldown (a second click inside 5 min is rejected), the send is called with the right template + recipient, and the response body carries no phone. **Mock the Meta send** (never hit the network).

Out of scope for WU6: the frontend buttons + cooldown countdown (WU7), the office semaphore (WU8).

## External gate (EXT)

Templates `en_route` + `arrived` must be created and approved in WhatsApp Business Manager. Until then, end-to-end sending cannot be tested — build behind the template names and mock the send in tests.

## Environment

The env is **already set up** in the existing worktree `/home/stefan/repos/lumat-agent-odd-panel-tecnico-wu3` (`.venv` via `uv sync`, test DB on port **5687**, `web/node_modules`). Its directory name says "wu3" but it currently holds branch `odd/panel-tecnico-wu5` — cosmetic only.

Recommended: reuse it and branch the new slice from the stack tip:

```bash
cd /home/stefan/repos/lumat-agent-odd-panel-tecnico-wu3
git switch -c odd/panel-tecnico-wu6            # from odd/panel-tecnico-wu5 (the stack tip)
```

If you prefer a fresh worktree (e.g. the stack was already merged and you base on `main`):

```bash
rapso worktree create panel-tecnico-wu6 --yes --root /home/stefan/repos/lumat-agent
cd ../lumat-agent-odd-panel-tecnico-wu6
cp ../lumat-agent/infra/.env infra/.env
uv sync                          # REQUIRED: rapso does not create .venv
infra/test-db.sh up              # own test DB; derive the port with `infra/test-db.sh port`
eval "$(infra/test-db.sh env)"   # REQUIRED before pytest
npm install --prefix web
```

## Gotchas learned this thread

- **`eval "$(infra/test-db.sh env)"` does NOT persist across shells.** Prefix EVERY `pytest` run with it, or the admin URL falls back to `app:app` and migrate fails.
- **`uv sync` is required** for a fresh worktree; `rapso worktree create` does not create `.venv`.
- **Adding a migration breaks** `tests/integration/test_migrations.py::test_schema_migrations_records_version` (it asserts the exact applied list). Append the new version there, and add a `_scratch_migration_db` guard test for the new schema.
- **Flaky under a full-suite run** (all pass in isolation; pre-existing, load-related): `AgentChat.test.tsx`, `AssistantWorkspace.test.tsx`, `ClientesList.test.tsx`. They can flake CI — re-run before investigating.
- **Graph**: `graphify-out/` is copied into a worktree but stale; `graphify . --update` before relying on it.
- **Peer overlap**: `AppShell.tsx` / `PanelShell.tsx` / `types.ts` are touched by several threads; any new admin-only destination must carry `adminOnly: true`.
- **Delivery**: branch naming `odd/panel-tecnico-wu<N>`; `main` uses merge commits; stacked PRs retarget automatically.
- **Engram MCP** fails with `multiple active runtime sessions match …`. Mirror the task doc via the CLI: `engram save "<title>" "$(cat odd/tasks/panel-tecnico.md)" --type architecture --project lumat-agent --topic odd/panel-tecnico/tasks`.

## Open product questions (still unanswered)

1. Confirm the technician loses Proyectos + Sesiones de planificación (applied in WU1 per D1).
2. Does the office/operator keep its own "Cerrar visita" fallback? (recommended: yes — already implemented; the operator route is unchanged.)
3. Where does the office see the visit-state semaphore? (needed for WU8.)
4. Meta templates `en_route` + `arrived`: create and approve in WhatsApp Business Manager (external; gates end-to-end testing of WU6–WU7).

## Definition of done for WU6

- RED→GREEN backend tests; full `pytest` exit 0.
- RDD `review assess` over the slice; an independent verifier when the Risk line is high (the send touches auth → item 2).
- Feature doc `odd/tasks/panel-tecnico.md` updated (WU6 row + a log entry with evidence), mirrored to Engram.
- Committed on `odd/panel-tecnico-wu6`; stacked PR with base `odd/panel-tecnico-wu5`.
