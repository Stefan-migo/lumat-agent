# Handoff — panel-tecnico → WU7 (frontend actions + cooldown countdown)

## Where we are

The whole thread **WU1–WU6 is MERGED to `main`**. `main` = `6a44b631`.

```
main
 └── #602  privacy contract                 (merged)
      └── #604  unified shell               (merged)
           └── #620  WU3 + WU4 + WU5 + WU6  (merged — the whole stack)
                └── #624  migration header fix (merged)
```

- **#620 landed the whole stack in one merge.** Its branch contained every slice, so it was retargeted to `main` (after merging `origin/main` into it, resolving the conflicts) and merged. `origin/main` is byte-identical to the locally verified tree.
- The stacked PRs were cleaned up: **#607 was auto-marked MERGED** by GitHub (its commits reached `main`); **#615 and #619 were closed as superseded** with a comment explaining that their content is in `main` via #620.
- **No branch, worktree or container is left**: the four `odd/panel-tecnico-wu*` branches were deleted (local + remote), the worktree `../lumat-agent-odd-panel-tecnico-wu3` was removed, and its test-DB container was torn down.
- ⚠️ **Known gap**: the feature doc on `main` records L16–L19 but has **no "landed" log entry**. That was deliberate (the doc lives in `main` and a PR for one log line was not worth a CI cycle). Add it in WU7's first doc commit.

## Ground truth

- Feature doc: `odd/tasks/panel-tecnico.md` (**in `main` now**) — Specs S1–S9, Tasks WU1–WU8 + EXT, Log L1–L19. **WU1–WU6 done**; WU7, WU8 and EXT pending.
- Session record: `.rapsodia-code/sessions/archived/2026-10-14-panel-tecnico/{session.md,report.md}` — **in the MAIN repo**. Decisions D1–D8 live in `report.md`.
- Engram: `odd/panel-tecnico/tasks` (task-doc mirror), `odd/panel-tecnico/wu6`, `infra/meta-waba-lumat`.
- RDD (native review) is **ON** (global). Every slice assessed `medium`, `review_due:false` (`under_budget`) — no native review has ever been required for this thread.

## What landed (WU3–WU6)

| Slice | What | Where |
| --- | --- | --- |
| WU3 | `GET /panel/api/technician/appointments/{id}` — allow-listed detail, 404 for foreign/missing | `app/panel/api/routes/technician.py`, `serializers.py` |
| WU4 | `POST .../close` (`completed`\|`no_show`) | same route file |
| WU5 | Visit-state axis: migration **`056`**, windows, forward-only transitions | `app/services/visit_state.py` |
| WU6 | `POST .../en_route` and `.../arrived` — WhatsApp template send + 5-min audited cooldown | `app/services/visit_actions.py` |

**The migration was renumbered `054` → `056`.** The branch was created when `053` was the highest, but `main` had meanwhile taken `054_project_files_kb_document` and `055_project_folders`. Two migrations shared the number `054`, so ours was renumbered to `056` and the expected-list plus the `_scratch_migration_db` guard in `tests/integration/test_migrations.py` were updated. **Always re-check the migration number against `origin/main` right before merging a branch that has been open a while.**

## Next: WU7 — frontend actions + cooldown countdown (S2, S4, S5, S7)

**A backend gap blocks it.** The technician detail payload does **not** expose `technician_state` / `technician_state_at` (zero hits in `app/panel/api/serializers.py`) and nothing exposes the cooldown. WU7 first has to extend the payload with:

- `technician_state` and `technician_state_at`;
- when a resend becomes available (the route returns `resend_available_at` on a successful action, but nothing exposes it on a read);
- enough to decide window availability — the payload already carries `starts_at` / `ends_at`, so the UI can compute T-60 / T-15 itself.

Then the UI: the close action plus the two quick actions on `AppointmentDetail`, role-gated (S2/D3 — same page for operator and technician) with the cooldown countdown.

## EXT — Meta templates

- The owner created **`en_route`** and **`arrived`** on 2026-10-15; both **pending Meta approval** (usually < 24 h).
- Production WABA = **`1062988939969174`** (Messaging account "Lumat"). The test WABA is `819245577928607` — **a template created there is invisible to the production number**.
- Contract: category **Utility**, language exactly **`es`** (not `es_CL`), **4 positional params**: `{{1}}` customer name, `{{2}}` technician name, `{{3}}` date `dd/mm/YYYY`, `{{4}}` time `HH:MM`. Bodies are recorded in the feature doc L19.
- Names are editable settings: `notify.en_route_template_name` / `notify.arrived_template_name` (defaults `en_route` / `arrived`).
- These two do **not** need a `NotificationTemplateVersion` registry row (unlike the appointment reminder/follow-up).
- **Local-only drift**: `infra/.env` has `META_PHONE_NUMBER_ID=1265841639944235`, but Meta reports `1372549195931756` for the Lumat number. Production is fine; align the local value before trying to test template sends locally.
- Still open elsewhere: is `emergency_alert` approved? If it does not exist, emergency notifications have been silently falling back to email. And the three appointment templates (`appointment_reminder_24h`, `appointment_followup`, `appointment_followup_no_show`) are still not created — contract in `docs/meta-templates.md`.

## Explicitly OTHER threads — do not fold into this one

- **Chatbot**: what happens when a customer replies to a template (the bot answers; `closed` opens a new conversation), and whether the agent should *know* it just sent a template or *suppress* a pure-ack turn. Findings and the proposed design are in Engram `#6635` and `#6636`, including the key gap: **template sends are not persisted as conversation messages**, so neither the bot's context window nor the panel sees them. Owner said this belongs to the chatbot thread.
- **Automations**: every automation WhatsApp send is **free-form** (`send_text`, no template), so anything firing outside the 24 h customer-service window is rejected by Meta. 5 customer recipes and 4 team recipes are affected. Engram `#6633`.

## Gotchas learned this thread

- **`app` role has INSERT+SELECT only on `audit_log`** — tests can *insert* an explicit `created_at` (to age the cooldown) but cannot `UPDATE` it.
- **`appointments` has an exclusion constraint** (`appointments_technician_no_overlap`): test fixtures that rewrite `starts_at` to now-relative windows must use one appointment per technician, or non-overlapping windows.
- **`addopts` already sets `-q`** in `pyproject.toml`; adding another `-q` hides pytest's final `N passed` line.
- **`eval "$(infra/test-db.sh env)"` does not persist across shells** — prefix every `pytest` run, or the admin URL falls back to `app:app` and migrate fails.
- **`uv sync` is required** for a fresh worktree; `rapso worktree create` does not create `.venv`.
- **Renaming an applied migration in a worktree** requires recreating that worktree's test DB (`docker exec <container> psql -U lumat -d postgres -c "DROP DATABASE lumat WITH (FORCE);"` then `CREATE DATABASE lumat OWNER lumat;`). The superuser is `lumat`, **not** `postgres`.
- **GitGuardian false positive lives in `main`**: `tests/functional/test_api_thread_resources.py` `_login(..., password="res-pass")` is flagged as a `Generic Password`. Pre-existing, not ours; it only surfaces in a PR whose range includes the merged `main`. Fix or ignore it at the GitGuardian level.
- **Stacked chains: merge as ONE.** Resolving the `origin/main` conflict once on the stack tip and merging that single PR avoids resolving the same conflict four times — and the previous thread (`odd/panel-visual-alignment`) already paid for that lesson.
- **Flaky under a full frontend run** (pre-existing, load-related): `AgentChat.test.tsx`, `AssistantWorkspace.test.tsx`, `ClientesList.test.tsx`. They pass in isolation — re-run before investigating.

## Open product questions (still unanswered)

1. Confirm the technician loses Proyectos + Sesiones de planificación (applied in WU1 per D1).
2. Does the office/operator keep its own "Cerrar visita" fallback? (recommended: yes — already implemented.)
3. **Where does the office see the visit-state semaphore?** Needed for WU8, and it is still an open question — do not assume.
4. Meta templates: approval pending; without them the send stays mocked.

## Definition of done for WU7

- RED→GREEN; backend `pytest` exit 0; frontend `vitest run` + `npm run build` (the repo's pre-merge integration).
- RDD `review assess` over the slice; independent verification if the Risk line is high.
- Feature doc updated (WU7 row + log entry, **including the missing "landed" entry**) and mirrored to Engram.
- Chained PR from `main`; the whole thread now starts from `main`, not from a stack.

## Environment (fresh worktree)

```bash
rapso worktree create panel-tecnico-wu7 --yes --root /home/stefan/repos/lumat-agent
cd ../lumat-agent-odd-panel-tecnico-wu7
cp ../lumat-agent/infra/.env infra/.env
uv sync                                    # REQUIRED: rapso does not create .venv
infra/test-db.sh up                        # own test DB; port via `infra/test-db.sh port`
eval "$(infra/test-db.sh env)"             # REQUIRED before pytest
npm install --prefix web
```

`main` has no branch protection, so `gh pr merge` works with a red check — the pre-merge discipline is evidence, not enforcement. Before merging anything, bring `origin/main` into the branch and run the local integration (backend suite + frontend suite + `npm run build`).
