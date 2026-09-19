# ODD: technician-surface

## Objective

Bring the technician role surface (`TechnicianShell` + `TechnicianAgenda`) up to the panel's design
contract and make it usable in the field: one page title instead of two, a date-led agenda that marks
today and separates past from upcoming, a phone action that is a real touch target and not a broken
`tel:` link, a refresh path, and the panel's own primitives instead of raw `<button>` elements.

## Problem

Verified against the running panel (`infra-api-1`, main) with a seeded `tecnico` user and four
appointments (past, today, future, cancelled), at 1440×900 and 390×844. Every claim below was
observed, not inferred.

**Functional**

- **Status is invisible.** `to_technician_appointment_dict` (`app/panel/api/serializers.py:208-225`)
  does not serialize `status`, so a `cancelled` and a `booked` appointment render identically. The
  live page reported `4 visitas` where two were cancelled. `DESIGN_SYSTEM.md:419` expects the
  business outcome to decide the tone, which is impossible with no status in the payload.
- **No temporal anchor.** `list_for_technician` (`app/services/scheduling.py:141-149`) orders
  `starts_at` across past, today, and future in one list; the page paints it flat. On 2026-09-19 the
  first card was a 2026-09-15 visit, with no marker for either.
- **No refresh.** `useAsyncData` (`web/src/hooks/useAsyncData.ts:26-46`) fetches once per mount and
  `TechnicianAgenda` passes no `refreshKey`. There is no polling, no refresh control, and no
  pull-to-refresh, so a reassignment never reaches the open page.
- **Broken `tel:` link.** With a null `phone` the component still emits `<a href="tel:">` around
  `Teléfono no registrado`; observed in the accessibility tree as `Teléfono no registrado -> tel:`.

**Visual / design contract**

- **Two `<h1>Agenda técnica`** on one page: `TechnicianShell.tsx:17` and `PageFrame`'s title from
  `TechnicianAgenda.tsx:22`. On desktop they are also misaligned — measured `shellH1.left = 16` vs
  `content.left = 208` — because the shell header spans the full width while the content is centred
  at `64rem`.
- **The phone number renders in the browser default link colour.** Computed `rgb(0, 0, 238)`.
  `primitives.css` contains no bare `a` rule. The primary action of the surface is the only
  untokenized element on it.
- **Card boundary contrast is 1.37:1** (`--border` `#d8dde3` on `--brand-bg`). `DESIGN_SYSTEM.md:463`
  requires at least 3:1 for meaningful UI boundaries; `--border-strong` (`#7e858f`) exists for this.
- **Raw `<button>` elements.** `Cerrar sesión` (`TechnicianShell.tsx:22`) and `Reintentar`
  (`TechnicianAgenda.tsx:15`) bypass the `Button` primitive. The logout inherits the UA font size
  (computed `13.33px`) instead of `--text-md`.
- **Inverted type priority.** The service name is `h2`/24px/700 while the appointment time is plain
  16px body text. On an agenda the time is the scanning anchor.
- **Mobile header consumes 215px of an 844px viewport** (measured `shellHeader.height = 214.8`),
  because the brand logo is `7rem` wide and the duplicated title stacks under it.
- **Phone tap target is 22px tall** — below the 24×24 minimum in WCAG 2.2 SC 2.5.8 — while the
  secondary logout button gets `min-height: 2.75rem` (44px) from a media query. Priority is inverted.
- **`className="technician-agenda"` has no rule anywhere** in `primitives.css` or `tokens.css`.
- **`TechnicianShell` injects a `<style>` string** (`TechnicianShell.tsx:10`). The design contract
  forbids exactly this pattern for the sibling shell: `openspec/specs/panel-design-system/spec.md:669`
  — *"PanelShell MUST NOT inject the former `PANEL_SHELL_STYLES` `<style>` block"* — and
  `primitives.css` now carries 151 `panel-shell` rules from that migration. TechnicianShell was left
  behind.

**Root cause: no design coverage.** `openspec/specs/panel-design-system/spec.md` never mentions the
technician surface; `DESIGN_SYSTEM.md` "Page architecture" documents Panel, Clientes, Conversaciones,
Casos, Base de conocimientos, Configuración, Proyectos, Sesiones de planificación and Login, and has
no technician section. There is no Storybook story (every other page has one) and one thin test that
lives in `components/domain/` while its component lives in `components/pages/`. Graphify confirms the
disconnection: no path exists from `TechnicianAgenda()` to `primitives.css` or to the token nodes.

## Scope

**In:** `web/src/components/domain/TechnicianShell.tsx`, `web/src/components/pages/TechnicianAgenda.tsx`,
the technician test file, a new Storybook story and its test, and (last, see D6) the technician section
of `web/src/components/primitives/primitives.css`.

**Out:** `app/panel/api/serializers.py` and the technician allow-list (an amendment to TECH-PRIVACY-1
is required, and `odd/kb-workspace` holds that file dirty — see D5); `app/services/scheduling.py`;
`tokens.css`; `DESIGN_SYSTEM.md`; `panel-design-system/spec.md`; any new dependency; the PanelShell,
login, and other page surfaces.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-technician-surface`
- Branch: `odd/technician-surface`
- Base: `b38e33bd`
- Files: `odd/tasks/technician-surface.md`, `web/src/components/domain/TechnicianShell.tsx`,
  `web/src/components/pages/TechnicianAgenda.tsx`,
  `web/src/components/pages/TechnicianAgenda.test.tsx` (moved from `components/domain/`),
  `web/src/stories/pages/TechnicianAgenda.stories.tsx`,
  `web/src/stories/pages/TechnicianAgenda.stories.test.tsx`, and — only in T10 —
  `web/src/components/primitives/primitives.css`

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml` (`testing.strict_tdd: true`). The configured
  runner is pytest; for this frontend-only change the applicable runner is Vitest via
  `cd web && npm run test`. Observe RED before each source change; never invent RED evidence.
- Frontend checks: `cd web && npm run test`, `cd web && npm run build`,
  `cd web && npx tsc -b --noEmit`.
- UI copy stays neutral Chilean Spanish (`DESIGN_SYSTEM.md:424`); no new text is introduced beyond
  what these fixes require.
- Token-only styling: no hard-coded colour values anywhere (`DS-GRAMMAR-2`).
- Artifacts in English. Conventional commits, no AI attribution.
- No commits, no push, no PR unless the orchestrator authorizes it.

## Decisions

- **D1 — The page title belongs to `PageFrame`, not to the shell.** The shell is a chrome boundary
  that wraps exactly one page here; rendering the page name in both produced the duplicate `h1`. The
  shell keeps the brand and the session controls, and gains a horizontal gutter that matches the
  centred content instead of spanning the full viewport.
- **D2 — Grouping and today-marking are computed on the client.** `starts_at` and `timezone` are
  already in the payload, so separating past from upcoming and marking today needs no API change and
  no new dependency.
- **D3 — The phone action is a real control, not an inline text link.** On a phone this is the action
  the surface exists for. It becomes a tokenized, full-width, ≥44px control when a number is present,
  and plain muted text when it is absent — never an anchor with an empty `tel:`.
- **D4 — The card leads with the time, then the service.** Matches the scanning order of the work:
  *when*, then *what*, then *where*.
- **D5 — Cancelled-appointment visibility is NOT fixed in this change.** Two blockers, both outside
  this worktree's authority: `status` is absent from the TECH-PRIVACY-1 allow-list, so it needs a spec
  delta; and the only file that can add it, `app/panel/api/serializers.py`, is currently dirty in
  `odd/kb-workspace`. Either exit (exclude cancelled server-side in `scheduling.list_for_technician`,
  or serialize a status) is a product decision, recorded as an open item below rather than decided
  here.
- **D6 — The stylesheet-boundary migration was released mid-flight.** T10 was sequenced last because
  `primitives.css` is where `odd/kb-workspace` intended to land its KB grammar styles. That worktree
  finished during this session: commit `9f153656` added its KB section (+66 lines, appended at the end
  of the file) and its working tree went clean. The technician section is therefore inserted next to
  the panel-shell block (around line 1350), far from that end-of-file append, so the two branches merge
  without overlapping hunks. The shell half of T10 folded into T1, which was already rewriting those
  styles; T10 now covers only the agenda's inline styles and the card boundary token.
- **D7 — No polling.** A refresh control reuses `useAsyncData`'s existing `retry`; an interval would
  add battery and network cost on a field phone for a page that is opened deliberately. If the user
  wants automatic refresh it becomes its own task.

## Tasks

- [x] **T1** — RED/GREEN: exactly one `h1` on the surface, and the shell gutter aligns with the
  centred content on desktop (measured, not eyeballed). Shell keeps brand + session controls.
  Absorbed the shell half of T10: the styles now live in `primitives.css` and the injected `<style>`
  block is gone.
- [x] **T2** — RED/GREEN: a null phone renders as plain text with no anchor; a present phone renders
  an operable control. The control reuses `Button` with `href`, so it is the shared primitive rather
  than a bare anchor.
- [x] **T3** — RED/GREEN: the phone control clears the touch-target minimum. Measured on an emulated
  touch device (`hover: none, pointer: coarse`): 127.3 × 62px against the 44 × 44 target. On a pointer
  device it is 127.3 × 34.3px, which is the primitive's own `min-height: var(--space-8)` (32px).
  The 44px comes from the existing guarded `@media (hover: none)` block in `primitives.css`; no
  bespoke rule was added, because a second such block fails the D7 test in `tokens.test.ts`.
- [x] **T4** — RED/GREEN: each card leads with the appointment slot, not the service name. The slot
  shows the full range (`ends_at` was already in the payload and a technician needs the duration).
  Rendered in 24-hour: `Intl` with `timeStyle: 'short'` produced `03:00 p. m. – 04:00 p. m.`, which
  repeats the meridiem and costs width on a phone. The service name stops being a heading and becomes
  card content, so the outline reads H1 page → H2 section → H3 day.
- [x] **T5** — RED/GREEN: the list splits at today and groups by the appointment's own local day.
  Upcoming renders first, past second; today and tomorrow are named, other days are dated. Today stays
  with the upcoming work — it is still today's round. Verified: `["Hoy", "Martes, 15 de septiembre"]`,
  `["Próximas visitas", "Visitas anteriores"]`, and no past section when every visit is ahead.
- [ ] **T6** — RED/GREEN: a refresh control re-fetches through `useAsyncData.retry` and the
  last-loaded state is visible to the user. No automatic polling.
- [x] **T7** — RED/GREEN: `Cerrar sesión` and `Reintentar` use the `Button` primitive; no raw
  `<button>` remains on the surface (`grep -n "<button"` returns nothing). The shell's bespoke
  `.technician-shell__logout` rule was deleted — `.btn--secondary` plus the guarded
  `@media (hover: none)` block already covered it, and the UA font (13.33px) is gone: both controls
  now measure 34.3px on a pointer device at `--text-sm`. The recovery control gets its own grid so it
  sits under the alert rather than attached to it.
- [x] **T8** — the dead `technician-agenda` class is now a real class, and the agenda's inline styles
  moved to `primitives.css` (T10's first half). No orphan class names remain.
- [ ] **T9** — Storybook story covering ready / long content / null customer / empty / error, and
  Vitest coverage for the new grouping, null-phone, and single-`h1` behaviour. Move the existing test
  next to its component in `pages/`, preserving its assertions verbatim.
- [ ] **T10** — the agenda's inline styles are already at the boundary (done with T2/T3). What remains
  is raising the card boundary from `--border` to `--border-strong` so the card edge meets the 3:1
  requirement. (The shell half moved into T1.)

## Acceptance criteria

1. The surface renders exactly one `h1`, and the shell chrome and the page content share one left
   gutter at 1440px.
2. The appointment time is the first and most prominent datum in each card.
3. Appointments are grouped by day; today is explicitly marked; past and upcoming are distinguishable
   without colour alone.
4. A null phone produces no link; a present phone produces a control of at least 44px height.
5. A refresh control exists and re-fetches; no polling is introduced.
6. No raw `<button>` remains on the surface; `Button` is reused.
7. No hard-coded colour value is introduced; no new dependency is added.
8. Only the authorized files change, and T10 does not run while `odd/kb-workspace` holds
   `primitives.css`.
9. `cd web && npm run test` and `cd web && npm run build` pass.

## Checks

- `cd web && npm run test`
- `cd web && npm run build`
- `cd web && npx tsc -b --noEmit`
- `npx playwright test` for the browser invariants once the dev server points at this worktree
- `git status --short` / `git diff --check`

## Open item

- **Cancelled appointments are still indistinguishable from booked ones after this change** (D5). The
  user must choose between excluding cancelled visits from the technician agenda server-side, or
  amending the TECH-PRIVACY-1 allow-list to carry a status the surface can render. Both need a spec
  delta and both touch files this worktree does not own.

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create technician-surface`); `npm ci` completed in `web/`.
- [x] Graph Check (Step 1): `graphify query` over the technician area and
      `graphify path TechnicianAgenda() primitives.css` / `... tokens`. Both paths return none, which
      is the graph-level confirmation of the design-system disconnect recorded above.
- [x] T1 — commit `bc6db8cf`. RED observed: `expected [ <h1></h1>, <h1></h1> ] to have a length of 1 but
      got 2`. GREEN: 3/3 tests, `tsc -b --noEmit` exit 0. Browser-verified at 1440 and 390: one `h1`,
      and `headerInner.left = content.left = pageH1.left = article.left = 208` at 1440 (16 at 390).
      Shell header height 214.8 → 130.9; first appointment top 356.8 → 272.9 at 1440, and
      ≈610 → 272.9 at 390. No `style` element is emitted by `TechnicianShell` any more.
- [x] T2 + T3 + T8 — commit pending. RED observed for both: the null-phone case still emitted the
      anchor, and the phone anchor had no `.btn` class. GREEN: 5/5 technician tests. Browser-verified:
      `uaBlueLinks: 0` on both pointer and touch (the UA `rgb(0, 0, 238)` is gone), the placeholder is a
      plain `span`, and the call control measures 127.3 × 62px on touch. `app.test.tsx` asserted
      `findAllByText('Agenda técnica')` **toHaveLength(2)** — it blessed the duplicate-heading bug the
      way T4 of `kb-workspace` blessed the KB deadlock; it now asserts one heading.
- [x] Full-suite context: `npm run test` reported 4 files / 7 tests failing, but one of them
      (`app.test.tsx`) was a real regression from T1 and is fixed. The other six (AppShell ×3,
      AgendaPage ×1, AgentChat ×2) are contention artifacts: load average was 180 during the run, and
      the same three files pass 66/66 both on `main` at the base commit and in this worktree in
      isolation. Re-run the full suite when the machine is quiet before trusting a green signal.
- [ ] T6, T9, T10

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-technician-surface`, branch `odd/technician-surface`.
- Dev server for this worktree: `cd web && npm run dev -- --host 127.0.0.1 --port 5174`, with the API
  proxy pointed at the running `infra-api-1` on `:8000`.
- Review fixture (main dev DB, reversible): user `tec-agenda` (role `tecnico`) and appointments
  ids 5-8 owned by it. Delete those five rows to remove the fixture.
- Playwright review scripts used to produce the evidence live in `/tmp/opencode/` (`tec-review.cjs`,
  `tec-probe.cjs`, `tec-mobile.cjs`); screenshots in `/tmp/opencode/shots/`.
- On resume: read this file, reconcile the checkbox state against `git log`, and confirm that T10's
  blocker (`odd/kb-workspace` holding `primitives.css`) is still accurate before starting it.
