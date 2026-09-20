# ODD: appointment-status-tone

## Objective

Stop the shared appointment tone map from painting a routine booking as a confirmed successful
outcome, and give the appointment domain the entry it never had in the design system's status-badge
table.

## Problem

Verified against `main` at `481f9cd9`.

- `web/src/components/shared/toneMaps.ts:10` maps `booked: "success"`. `APPOINTMENT_STATUS_TONES`
  is `{ booked: "success", cancelled: "neutral", completed: "success", no_show: "danger" }`, so a
  visit that has not happened yet renders in the same green as one that already completed.
- `web/DESIGN_SYSTEM.md:416` reserves the Positive level for a **confirmed successful outcome**, and
  `:420` states that the business outcome decides the tone. A booking is not an outcome.
- The map has exactly two consumers and both are real surfaces:
  `web/src/components/pages/AgendaPage.tsx:45` (admin agenda table) and
  `web/src/components/pages/TechnicianAgenda.tsx:105` (technician card). Fixing it in the shared map
  is what keeps the two pages meaning the same degree of attention, per `DESIGN_SYSTEM.md:410`.
- **The tone is unguarded.** `web/src/stories/pages/_shared/toneMaps.test.ts` is where this repository
  tests tone maps, and it covers `caseStatusTone` and `customerStateTone` only — never the appointment
  tones. The surfaces assert the *label* (`AgendaPage.test.tsx:101,119` use
  `appointmentStatusLabel('booked')`), never the tone, so nothing contradicted `booked: "success"`.
  (That test imports through `web/src/stories/pages/_shared/toneMaps.ts`, a one-line `export *`
  compatibility wrapper, so `components/shared/toneMaps.ts` remains the single source of truth.)
- `web/DESIGN_SYSTEM.md:370-376` lists approved status-badge labels per domain — Conversation,
  Customer, Case, KB document, Reply window. **Appointments are absent**, which is the doc-level
  reason nothing contradicted `booked: "success"`.

**A vocabulary gap was found and deliberately left open.** `DESIGN_SYSTEM.md:412-418` defines five
semantic levels, including *Informational*, but `BadgeTone` (`Badge.tsx:4`) can only express four:
`neutral | success | warning | danger`. The `--info` / `--info-tint` tokens exist (`tokens.css:145,68`)
and `StateMessage` accepts `tone="info"`, but `Badge` has no informational tone. Closing that gap
means touching a shared primitive and is a design-system change of its own; it is recorded here as a
follow-up rather than smuggled into this one.

## Scope

**In:** `web/src/components/shared/toneMaps.ts` (the one value),
`web/src/stories/pages/_shared/toneMaps.test.ts` (extend the existing tone-map test),
`web/DESIGN_SYSTEM.md` (the missing Appointments row), `odd/tasks/appointment-status-tone.md` (this
record).

**Out:** the `Badge` primitive and its tone union; `tokens.css`; `primitives.css`; any page component;
the label map (`APPOINTMENT_STATUS_LABELS`); any new dependency. The `cancelled` / `completed` /
`no_show` tones are not touched — only `booked` is wrong.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-appointment-status-tone`
- Branch: `odd/appointment-status-tone`
- Base: `481f9cd9`
- Files: `odd/tasks/appointment-status-tone.md`, `web/src/components/shared/toneMaps.ts`,
  `web/src/stories/pages/_shared/toneMaps.test.ts`, `web/DESIGN_SYSTEM.md`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). Frontend-only, so the
  applicable runner is Vitest: `cd web && npm run test`. Observe RED before the source change.
- Token-only styling; `DESIGN_SYSTEM.md` edits are prose, not styling.
- Artifacts in English. Conventional commits, no AI attribution.
- No commits, no push, no PR unless the orchestrator authorizes it.

## Decisions

- **D1 — `booked` becomes `neutral`.** The level that fits a scheduled visit is `DESIGN_SYSTEM.md:414`
  Neutral, "Routine information". Green returns to meaning *confirmed successful outcome*, which is
  what `completed` legitimately is, and danger stays with `no_show`.
  - **`warning` was rejected.** `DESIGN_SYSTEM.md:417` defines it as "Human attention soon/now"
    (human handoff, approaching spend limit, reply-window risk). A routine booking is not a risk, so
    this would over-signal in the opposite direction.
  - **Adding an `info` Badge tone was rejected for this change.** It is the honest way to close the
    five-levels/four-tones gap, but it touches a shared primitive and deserves its own design-system
    change. The user chose the minimal option deliberately.
  - **The cost of `neutral` is accepted and named:** `booked` and `cancelled` now share the neutral
    badge. The visible label is the state channel — `Reservada` vs `Cancelada` — which is exactly what
    D5 of `odd/tasks/technician-status.md` required ("by text, not by colour alone"). Colour only
    reinforces.
- **D2 — Guard the map, not just the one value, and guard it where the repository already guards tone
  maps.** The assertions go into the existing `web/src/stories/pages/_shared/toneMaps.test.ts`, not a
  new file: that is the established home for this contract, and a second location would split it. The
  test asserts the whole appointment map, so a future edit that re-introduces a success tone for an
  unstarted state fails loudly. The absence of this guard is the reason the defect survived
  undetected across two merged units.
- **D3 — Document the domain in the design system.** The Appointments row goes into the existing
  `Status badge` table, with the guidance that a booking is not an outcome. Without it the next reader
  has no approved contract to check against — the same gap that let this through.

## Tasks

- [x] **T1** — RED: extend `web/src/stories/pages/_shared/toneMaps.test.ts` with the appointment tones.
  Watch it fail on `booked`. Follow the file's existing shape (one `describe` per tone function, plus
  the valid-tone and no-collision coverage it already applies to `caseStatusTone` and
  `customerStateTone`).
- [x] **T2** — GREEN: `booked: "neutral"`. T1 passes; no other value changes.
- [x] **T3** — `DESIGN_SYSTEM.md`: add the Appointments row to the `Status badge` table with the
  approved labels and the guidance.
- [x] **T4** — verification: Vitest suite, `tsc -b --noEmit`, `build`.

## Acceptance criteria

1. `appointmentStatusTone('booked')` is no longer `success`.
2. `completed` stays `success`, `no_show` stays `danger`, `cancelled` stays `neutral`, and the labels
   are unchanged.
3. A test guards the map, so the tone cannot drift back unnoticed.
4. `DESIGN_SYSTEM.md` lists the appointment domain in the status-badge table with the rule that a
   booking is not an outcome.
5. `cd web && npm run test`, `npx tsc -b --noEmit` and `npm run build` pass.
6. Only the authorized files change.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create appointment-status-tone`); `npm ci` completed in `web/`.
- [x] Graph Check (Step 1): `graphify query "appointment status tone map booked success design system
  domain state"` returned `appointmentStatusTone()` (`toneMaps.ts:32`) in the `TechnicianAgenda.tsx`
  community and `APPOINTMENT_STATUS_TONES` (`toneMaps.ts:10`) in the `shared/toneMaps.ts` community —
  the cross-page contract this record is about. **It also corrected a wrong assumption:** the graph
  carries a `toneMaps.test.ts` node at `web/src/stories/pages/_shared/toneMaps.test.ts`, a file this
  record had missed because it had only searched `components/shared/`. `graphify path toneMaps.ts
  AgendaPage.tsx` returns no directed path (the consumer edge runs the other way).
- [x] **T1** — RED observed with `npx vitest run src/stories/pages/_shared/toneMaps.test.ts`:
      **3 failed / 31 passed**, and the three failures are exactly the ones that must fail while
      `booked` carries `success` — `maps booked to neutral`, `reserves success for an outcome that
      actually happened`, and `lets booked and cancelled share a tone while their labels stay
      distinct`, the last one reporting `expected 'success' to be 'neutral'`.
- [x] **T2** — GREEN: `APPOINTMENT_STATUS_TONES` is now
      `{ booked: "neutral", cancelled: "neutral", completed: "success", no_show: "danger" }`. The
      focused file passes **34/34**. No other value, label or consumer changed.
- [x] **T3** — `web/DESIGN_SYSTEM.md` gains the Appointment row in the `Status badge` table, placed
      after Case, with the approved labels and the guidance that a booking has not happened yet.
- [x] **T4** — Verification on `web/`: `npm run test` → **79 files, 599 tests, exit 0**; `npx tsc -b
      --noEmit` → exit 0; `npm run build` → exit 0 (the pre-existing 500 kB chunk warning is
      unchanged in kind).

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-appointment-status-tone`, branch
  `odd/appointment-status-tone`.
- On resume: read this file and reconcile the checkbox state against `git log`.
