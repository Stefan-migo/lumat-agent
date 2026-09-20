# ODD: ds-stylesheet-boundary

## Objective

Finish the stylesheet-boundary migration the panel started for `PanelShell`, and close the inherited
contrast gap the technician surface left open. Concretely: remove the four remaining component-owned
`<style>` blocks, move their rules into the tokenized stylesheet boundary, widen the spec rule that today
covers only `PanelShell` so the pattern cannot regrow, and write the `contrast-verification.md` that
`DS-CC-5` asks for on the `--border-strong` / `--brand-bg` pair.

## Problem

Every claim below was verified this session against `main` at `a57b353e`, not inherited from a prior report.

**Four components still inject their own stylesheet.**

| Component | Constant | Lines | Rendered at | CSS lines |
|---|---|---:|---|---:|
| `web/src/components/shared/StateMessage.tsx` | `STATE_STYLES` | 11–38 | :52 | 26 |
| `web/src/components/shared/PageFrame.tsx` | `PAGE_FRAME_STYLES` | 4–25 | :40 | 20 |
| `web/src/components/pages/Dashboard.tsx` | `STYLES` | 11–106 | :232 | 94 |
| `web/src/components/pages/AgendaPage.tsx` | `PAGE_STYLES` | 23–26 | :116 | 2 |

These are the last four; `PanelShell` was migrated by `e6d805cc` + `a7093fed` + `6bf75cf6` and
`web/src/components/domain/PanelShell.tsx` no longer injects anything.

**Two of them also land in invalid or semantically wrong places.** `<style>` is metadata content, so a
`<style>` element in the document body is invalid HTML. `StateMessage` renders its block inside the
`role="status"` / `role="alert"` element, which makes the live region's `textContent` begin with CSS text.
`Dashboard` and `AgendaPage` render theirs as a child of `PageFrame`, so it lands inside
`<main class="page-frame">`.

**The spec forbids this only for `PanelShell`.** `DS-SHELL-3`
(`openspec/specs/panel-design-system/spec.md:667-675`) names the former `PANEL_SHELL_STYLES` block, and
`DS-GRAMMAR-2` (`:749-756`) ends with `` `PanelShell` MUST NOT inject shell-owned `<style>` content ``.
Neither rule is general, so removing four instances without a spec delta fixes the instance and not the
class.

**An inherited token pair is unrecorded.** `--border-strong` does not clear 3:1 on `--brand-bg`.
Recomputed independently this session: `--border-strong` `#7E858F` has `L=0.23204`; `--brand-bg`
`#DDE2D6F5` composites on `--bg` (`#F1F1E8`) to `#DEE3D7`, `L=0.75376`; the ratio is
`(0.75376 + 0.05) / (0.23204 + 0.05) = 2.85:1`, under the 3:1 that `web/DESIGN_SYSTEM.md:463` requires of a
meaningful UI boundary. It passes on `--surface` (3.72) and `--brand-bg-elevated` (3.18), which is what
`web/src/tokens/tokens.test.ts:185-198` guards. `DS-CC-5` (`spec.md:850-869`) already mandates recording
such a pair with its computed ratio rather than tolerating it silently, and its scenario names
`contrast-verification.md` as the place.

**Cascade risk (the real hazard of the migration).** `web/src/components/primitives/primitives.css:597`
already defines `.page-frame` and `:637` `.page-frame__content`, so this is not a clean move into an empty
file. An injected `<style>` sits in the document at the component's position while `primitives.css` is
loaded from the document head, so today the injected rules win specificity ties. Moving them into the
shared stylesheet inverts that order. Static pre-check of every overlapping pair, done here:

- `.page-frame`: injected `display`/`gap`/`font-family`; shared `width`/`max-width`/`margin` — no shared property.
- `.page-frame__content`: `min-width: 0` appears in both, with the same value.
- `.page-frame__titlebar`, `.page-frame__banner`, `.dashboard-state*`, `.agenda-page*`: absent from `primitives.css`.
- `.dashboard .kpi-grid` (injected) is more specific than the shared `.kpi-grid`, so order cannot flip it.

No conflicting declaration was found, so the expected computed-style outcome is "no change". That is a
prediction from static analysis, not evidence, and the browser check below is what turns it into evidence.

## Scope

**In:** the four components above, `web/src/components/primitives/primitives.css`,
`openspec/specs/panel-design-system/spec.md` (`DS-GRAMMAR-2`), a new source-walk guard test,
`openspec/specs/panel-design-system/contrast-verification.md`, and the two open items of
`odd/tasks/technician-surface.md`.

**Out:** `tokens.css` values (a token change is a design-system decision, not this slice's);
`web/DESIGN_SYSTEM.md`; renaming the `.dashboard-state*` classes (the mis-namespacing is real — the
component lives in `shared/` while its classes say `dashboard-state` — but renaming is a separate concern
with its own blast radius, and mixing it in would make the cascade verification ambiguous); any other
page's behaviour; any new dependency.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-ds-stylesheet-boundary`
- Branch: `odd/ds-stylesheet-boundary`
- Base: `a57b353e`
- Files: `odd/tasks/ds-stylesheet-boundary.md`, `odd/tasks/technician-surface.md`,
  `web/src/components/shared/StateMessage.tsx`, `web/src/components/shared/PageFrame.tsx`,
  `web/src/components/pages/Dashboard.tsx`, `web/src/components/pages/AgendaPage.tsx`,
  `web/src/components/primitives/primitives.css`, `web/src/components/style-boundary.test.ts`,
  `openspec/specs/panel-design-system/spec.md`,
  `openspec/specs/panel-design-system/contrast-verification.md`

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml` (`testing.strict_tdd: true`). The configured runner is
  pytest for the backend; this slice is frontend-only, so the applicable runner is Vitest via
  `cd web && npm run test`. Observe RED before the source change; never invent RED evidence. The natural
  cycle here is: write the guard test, watch it fail on the four live injections, then remove them.
- Frontend checks: `cd web && npm run test`, `cd web && npm run build`, `cd web && npx tsc -b --noEmit`.
- Token-only styling: the migrated rules keep their existing `var(--*)` values and add no hard-coded
  colour (`DS-GRAMMAR-2`).
- Migrated declarations stay byte-identical; only their container and indentation change. Do not
  "improve" a value while moving it — that would make the cascade verification unable to attribute a
  difference.
- Artifacts in English. Conventional commits, no AI attribution.
- No commits, no push, no PR unless the orchestrator authorizes it.

## Decisions

- **D1 — Migrate verbatim; do not rename.** `.dashboard-state*` is the wrong namespace for a component in
  `shared/`, but renaming it changes selectors, tests and every consumer at once, and it would sit on top
  of a cascade reorder. Two risks in one diff is how attribution dies. Recorded here as a follow-up.
- **D2 — Placement.** `PageFrame`'s four rules join the existing `Page composition` section beside the
  `.page-frame` rules that already live there, so a selector's rules are not split across the file.
  `StateMessage`, `Dashboard` and `AgendaPage` get their own commented sections appended at the end of
  `primitives.css`, matching how the technician, grammar, assistant and KB sections were added.
- **D3 — The gap is recorded, not asserted.** `tokens.test.ts` gets no new assertion for this pair. A test
  asserting the failing ratio would be a test that approves the defect, exactly the anti-pattern the user
  banned as process policy; a test asserting `toBeLessThan(3)` would bless it just as plainly. The
  spec-mandated response is the written record with the computed ratio.
- **D4 — The record is design-system-level, not change-level.** `DS-CC-5`'s scenario expects a change to
  list an inherited pair it reuses. The change that hit this pair, `technician-surface`, is merged and
  archived, and this slice does not introduce a `--brand-bg` boundary. Attributing the gap to this change
  would be dishonest, so it goes to the design system's own spec directory and is attributed to a
  design-system change that has not happened yet.
- **D5 — Widen `DS-GRAMMAR-2`, do not add a requirement.** Its first sentence already states the general
  boundary rule; only its final sentence narrows it to `PanelShell`. Removing that narrowing is the minimal
  correct edit, and it avoids inventing a requirement ID for a rule that already exists.

## Tasks

- [ ] **T1** — RED: add `web/src/components/style-boundary.test.ts`, a source walk over `src/components`
  and `src/stories` (test files excluded) asserting no JSX `<style>` injection. Watch it fail, naming
  exactly `StateMessage.tsx`, `PageFrame.tsx`, `Dashboard.tsx`, `AgendaPage.tsx`.
- [ ] **T2** — GREEN, shared components: move `PAGE_FRAME_STYLES` into the `Page composition` section of
  `primitives.css`, delete the constant and the `<style>` from `PageFrame`; move `STATE_STYLES` into a new
  `State message` section, delete the constant and the `<style>` from `StateMessage`. T1 now reports only
  the two pages.
- [ ] **T3** — GREEN, pages: move `STYLES` (`Dashboard`) and `PAGE_STYLES` (`AgendaPage`) into their own
  sections, delete both constants and both `<style>` elements. T1 is green.
- [ ] **T4** — spec delta: widen `DS-GRAMMAR-2` in `openspec/specs/panel-design-system/spec.md` so the
  no-injection rule covers every panel component, with a scenario for the source guard. Keep the
  `(Previously: …)` annotation style the spec already uses.
- [ ] **T5** — token record: write
  `openspec/specs/panel-design-system/contrast-verification.md` for `--border-strong` on `--brand-bg`,
  including the method, the reproducible luminance inputs, the 2.85:1 ratio against the 3:1 threshold, the
  passing pairs in context, the manual-calculation limitation, and the design-system attribution.
- [ ] **T6** — close the loop: update the two open items in `odd/tasks/technician-surface.md` to point at
  the record and the migration, and reconcile this file's progress against `git log`.

## Acceptance criteria

1. No source file under `web/src/components` or `web/src/stories` injects a `<style>` element, and the
   guard test proves it rather than a manual grep.
2. Every rule removed from a component is present in `primitives.css` with unchanged declarations; no
   colour value is hard-coded and no token value changed.
3. No computed-style drift from the migration: the same elements resolve the same computed values before
   and after, verified in the browser, not eyeballed.
4. `DS-GRAMMAR-2` no longer limits the no-injection rule to `PanelShell`.
5. `contrast-verification.md` records the `--border-strong` / `--brand-bg` pair with its computed ratio and
   attributes it to a design-system change.
6. `cd web && npm run test`, `cd web && npm run build` and `cd web && npx tsc -b --noEmit` pass.
7. Only the authorized files change.

## Checks

- `cd web && npm run test`
- `cd web && npm run build`
- `cd web && npx tsc -b --noEmit`
- `npx playwright test` (or a scripted computed-style comparison) for the cascade invariants
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create ds-stylesheet-boundary`); `npm ci` completed in `web/`.
- [x] Graph Check (Step 1): `graphify query` over the style boundary — the graph links `PageFrame()`,
  `StateMessage()`, `tokens.test.ts` and `Requirement: DS-SHELL-3 — Tokenized Shell Styles Without
  Injection (Slice 2)` in one community, and carries a `primitives.css (tokenized shell CSS boundary)`
  node from the PanelShell design, which is the graph-level confirmation that this boundary is a known
  contract and not a new one.
- [x] **T1** — RED observed with `npx vitest run src/components/style-boundary.test.ts`: Vitest reported
      exactly `src/components/pages/AgendaPage.tsx`, `src/components/pages/Dashboard.tsx`,
      `src/components/shared/PageFrame.tsx`, and `src/components/shared/StateMessage.tsx`; guard committed
      in `dc40a98f`.
- [x] **T2** — GREEN shared-component migration committed in `dc40a98f`; the guard then reported only the
      two page files.
- [x] **T3** — GREEN page migration committed in `3b38af18`; focused guard passed: 1 file, 1 test.
- [x] **T4** — DS-GRAMMAR-2 widened with the no-component-injection scenario; committed in the closeout
      commit recorded below.
- [x] **T5** — `contrast-verification.md` records the manual 2.85:1 `--border-strong` / effective
      `--brand-bg` calculation and inherited-design-system attribution; committed in the closeout commit
      recorded below.
- [x] **T6** — Both technician-surface open items were closed by appended lines, and this progress record
      was reconciled against `dc40a98f` and `3b38af18`; committed in the closeout commit recorded below.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-ds-stylesheet-boundary`, branch `odd/ds-stylesheet-boundary`.
- Dev server for this worktree: `cd web && npm run dev -- --host 127.0.0.1 --port 5176`, with the API proxy
  pointed at the running `infra-api-1` on `:8000` via `VITE_API_TARGET`. `:5173` is main; `:5175` was the
  retired technician worktree.
- On resume: read this file and reconcile the checkbox state against `git log`.
