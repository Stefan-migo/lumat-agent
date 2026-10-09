# ODD: realistic-dev-seed

## Objective

Replace the two ad-hoc dev seeders with **one realistic, functional dev seeder** that makes the
whole panel feel like a real operating database (≥10 real-looking clients with conversations,
cases, agenda, equipment, notes and memories), and fix the raw-markdown rendering of
conversation/case `summary` in the Conversaciones and Ficha surfaces.

## Problem

The dev database looks broken and generic:

- `app/panel/seed_demo.py` creates **30 customers literally named `Demo Customer N`**, each with a
  single message `"Demo dashboard inquiry"` and no comuna/address. It exists only to feed the
  Dashboard charts.
- `app/panel/seed_clientes_ficha.py` creates **3 realistic customers** but is undocumented and
  narrow.
- The conversation detail composer appears **permanently locked** because seeded conversations are
  older than 24 h (WhatsApp window closed) and almost all are in `bot` state — see the earlier
  investigation. There is no seeded conversation that exercises the human composer.
- `conversations.summary` / `cases.summary` are rendered as plain text in Conversaciones and Ficha,
  so the assistant-handoff markdown (`**Resumen**`, `- **Cliente:**`, `#`) shows as raw noise.

## Why

- One entry point for dev data, realistic enough to review UI work honestly.
- The composer must be exercisable locally (a fresh inbound + `human` state).
- A realistic dataset must not lie: reserved/fake phone numbers stay, so no accidental real contact.

## Scope

**Authorized (in scope):**

- New `app/panel/seed_dev.py`; delete `app/panel/seed_demo.py` and
  `app/panel/seed_clientes_ficha.py`.
- Rewrite `tests/functional/test_seed_demo.py` as `tests/functional/test_seed_dev.py`.
- Web: a small markdown→plain-text helper under `web/src/components/shared/`, plus its test, and its
  application in `ConversationsList.tsx`, `ConversationThread.tsx`, `ClientFicha.tsx` (and their
  tests). Use the existing `Markdown` component in detail surfaces.

**Out of scope (do not touch):**

- `db/seed.sh` (settings + admin) and `tests/integration/test_seed.py`.
- `Dashboard.tsx`, `AppointmentDetail.tsx`, `TechnicianAgenda.tsx` summary render (same class of
  bug, deliberately left for a follow-up so this unit stays reviewable).
- The handoff flow that *produces* markdown (`app/chat/...`): the source fix is a separate decision.

## Constraints (verified facts)

- **Strict TDD is ON** (`openspec/config.yaml:38`). RED before implementation, GREEN after, never
  invent evidence.
- Python runner: `uv run pytest tests/` (this worktree's test DB is isolated; env from
  `eval "$(infra/test-db.sh env)"`).
- Web runner: `cd web && npm test` (vitest). Static gate: `cd web && npm run build` (`tsc -b`).
  No linter/formatter in the repo.
- UI copy the operator reads is **Spanish**; code, identifiers, comments, tests and docs are
  **English**.
- No `Co-Authored-By`, conventional commits, no squash.
- The seeder keeps its safety envelope: `--yes`/`LUMAT_DEMO_SEED=1` opt-in, `db|localhost|127.0.0.1`
  host allow-list unless `--allow-nonlocal`, and the exact "Target database:" / "Demo rows will be
  replaced." stdout contract used by the functional test.

## Design — `app/panel/seed_dev.py`

**Marker / phones.** Keep a reserved prefix so deletes are safe and no real number is dialled, but
give valid Chilean mobile shape: `MARKER = "5690000000"`, numbers `f"+{MARKER}{i:02d}"`
(`+569000000001`…). Delete every row under `phone_e164 LIKE '+5690000000%'`. Re-export `MARKER`
(the test imports it).

**Realism.** 12 customers with real Chilean names, comunas, streets, optional email, `CustomerState`,
`consent_status`, staggered `created_at`. Real equipment (`calefón`/`caldera`, brands/models/age),
notes and memories for several. WhatsApp conversations with plausible Spanish dialogue
(`inbound`/`outbound`, several turns), realistic cases (`service`, `priority`, `status`, `summary`,
`amount`, `responsible_id`, `escalated_at`, `emergency`, `acknowledged_at`, `closed_at`).

**Every summary is plain text** — no `**`, `- `, `#`, backticks. That is the whole point of the
clean dataset.

**Composer must be exercisable.** At least two conversations: `state=human`, last inbound message
within 24 h (composer unlocked). At least one `state=bot` conversation whose **last message is
inbound** (drives the dashboard's unanswered list and the take-over path). One `closed` conversation.

**Dashboard volume (must satisfy the rewritten functional test).** Spread conversations/cases across
the last 30 days so that, for `window_days` ∈ {7, 14, 30}: `contacts > 0`, `derived > 0`,
`visit_requests > 0`, `motivos` non-empty and the `contacts` trend sums > 0. Ensure within the last
7 days at least one `escalated_at` case and at least one `service == "visita"` case; at least one
open `emergency` case; at least some customers `created_at` within 7 days. `today_projection` must
return non-empty `appointments_today` (one appointment on the current `America/Santiago` local day),
`unanswered_conversations` and `urgent_cases`.

Counts are the new design's, not 30/30/30/1 — the test asserts the new exact counts.

## Design — markdown render fix (web)

- Add `plainMarkdown(text)` (name TBD by writer) that collapses a markdown summary to one readable
  plain line (strip `**`/`__`, `#`, leading list markers, backticks, `[t](u)`→`t`, collapse
  whitespace).
- **Detail surfaces → render real markdown** with the existing `Markdown` component:
  - `ConversationThread.tsx:105` (case summary in the inspector).
  - `ClientFicha.tsx:482` (selected case summary) and `:717` (conversation summary).
  Replace the `<p>` with a block container (`<div className="…"><Markdown …/></div>`) so block
  children are valid; keep the existing class name and adjust CSS only if the selector assumed `p`.
- **Constrained surfaces → plain text** via the helper:
  - `ConversationsList.tsx:89,121` (list row / mobile card; avoid a block element inside the inline
    `span`).
  - `ClientFicha.tsx:453,462` (DataTable cells) and `:724` (`<option>` label — markdown/HTML is
    impossible there, must be plain).

## Tasks

| ID  | Task | Route |
| --- | --- | --- |
| **T1** | Create `seed_dev.py`, delete the two old seeders, rewrite the functional test. RED then GREEN on pytest. | delegated writer |
| **T2** | Add the markdown→plain helper, apply the render fix in Conversaciones/Ficha, add web tests. RED then GREEN on vitest + build. | delegated writer |

## Acceptance criteria

- `uv run pytest tests/` green in the worktree.
- `cd web && npm test` green and `cd web && npm run build` clean.
- Seeded customers ≥ 10, all with real names; no `Demo Customer` string remains.
- At least one seeded conversation is `human` with an open reply window; at least one `bot`
  conversation ends on an inbound message.
- No seeded `conversation.summary` / `case.summary` contains markdown markers.
- The functional test asserts the new counts and still proves 7/14/30-day KPIs, trend, and the three
  `today_projection` lists.
- A rendered markdown summary no longer shows literal `**` in Conversaciones/Ficha detail views;
  list/table/option contexts show clean single-line text.

## Delivery

Actual change (base `d1810cb7` → branch): **372 added / 563 deleted / 935 total changed lines**
across 14 files. The deletions are the two retired seeders (435 lines); the authored surface is
~372 added plus small edits. Either way the review budget (>400) is exceeded, so `ask-on-risk`
triggers a delivery decision before this branch is presented: **one PR with `size:exception`**, or a
chained split (PR1 = seeder, PR2 = web render). Recorded here; the choice is the owner's.

## Checks

- `eval "$(infra/test-db.sh env)" && uv run pytest tests/`
- `cd web && npm test`
- `cd web && npm run build`

## Route and delegation record

- T1: delegated writer (`general`). Trigger: 2+ non-trivial files (new seeder + test rewrite).
- T2: delegated writer (`general`). Trigger: 2+ non-trivial files (helper + component edits + tests).

## Graph

Nodes consulted via the exploration phase: `app/services/dashboard.py` (`compute_kpis`,
`today_projection`, `trend`), `app/panel/api/routes/dashboard.py`, `app/models.py`
(`Conversation`, `Message`, `Case`, `Customer`, `Appointment`, enums), `ConversationsList.tsx`,
`ConversationThread.tsx`, `ClientFicha.tsx`, `Dashboard.tsx`, `shared/Markdown.tsx`,
`tests/functional/test_seed_demo.py`.

## Progress

- [x] **T1** — `8787030b` *feat(dev): unify and make the dev seeder realistic* + `0a6834ce`
      *refactor(dev): vary the seeded summaries and equipment copy*. Unified realistic seeder with 12
      named clients; both old seeders removed; functional test rewritten.
- [x] **T2** — `318ebebe` *fix(web): render conversation summaries as markdown or plain text*.
      `plainSummary` helper + markdown in the two detail surfaces + plain text in list/table/option.

## Verification evidence

Observed, not asserted:

| Check | Command | Result |
| --- | --- | --- |
| T1 focused | `uv run pytest tests/functional/test_seed_dev.py -q` | `1 passed` |
| T1 full backend | `uv run pytest tests/` | `1840 passed in 334.55s` |
| T2 focused | `npx vitest run <4 touched test files>` | focused tests pass |
| T2 build | `cd web && npm run build` | `tsc -b` + Vite build passed |
| T2 full web | `npx vitest run` | 16 failed / 1083 passed — **pre-existing contention flake** |

- The full web-suite failures (AgendaPage, ClientFicha, UserManagement, AgendaPage.stories,
  AppShell) are **not** caused by this unit: every failing file passes in isolation
  (`ClientFicha.test.tsx` 100%, `AgendaPage.test.tsx` 47/47, `UserManagement.test.tsx` 21/21,
  `AgendaPage.stories.test.tsx` 12/12), the failing set differs run to run, and **`main` at the base
  commit reproduces the same failures (19 failed / 1075 passed)**. The repo documents the flake
  (`odd/tasks/conversations-redesign.md:66`, `odd/tasks/conversation-workspace-text-zoom.md:189`).

**Not verified** (stated honestly):

- No browser/visual measurement: `jsdom` has no layout, so the rendered spacing of the markdown
  blocks in the inspector/ficha detail was not measured. Structural only.
- The `Dashboard`, `AppointmentDetail` and `TechnicianAgenda` summaries keep the old plain-text
  render (deliberately out of scope).
