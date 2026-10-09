# frontend-polish

Feature id: `frontend-polish`
Branch: `odd/frontend-polish`
Worktree: `/home/stefan/repos/lumat-agent-odd-frontend-polish` (base `origin/main` 9550ffa4)
Created: 2026-10-09

## Objective

Make every **control boundary** in the panel use the light decorative border
(`--border`), removing the dark `--border-strong` control borders left over from
earlier slices, so the whole panel matches the lighter look already approved in
Configuración (e.g. the Costos inputs).

## Problem / Why

Two border tokens exist (`web/src/tokens/tokens.css`):

- `--border: #d5dad1` — light hairline, documented as *decorative, not a control boundary*.
- `--border-strong: #7e858f` — dark, the AA-compliant control boundary (3.09:1 on `--surface`).

During the redesigns, Configuración overrode its field borders to `--border`
(`Settings.css`) while the shared primitives (`.field__control`, `.search-input`,
`.menu__trigger`, `.btn--secondary`, `.day-toggle__day`) and other pages kept
`--border-strong`. Result: inconsistent borders — search / filter / inputs dark,
Configuración inputs light.

Owner decision (2026-10-09): **direction A — unify everything to the light `--border`.**
This knowingly waives the WCAG 2.2 AA non-text 3:1 rule for control boundaries
(`--border` is 1.18:1 on `--surface`). The trade-off is accepted and must be recorded
in `DESIGN_SYSTEM.md`, not hidden.

## Scope

- Change **control-boundary** borders from `--border-strong` to `--border`.
- Remove the now-redundant Settings overrides that force `border-color: var(--border)`.
- Document the decision in `DESIGN_SYSTEM.md`.

## Non-goals — do NOT change

- `--border-strong` **token value** (stays `#7e858f`; `tokens.test.ts:249` keeps passing).
- Decorative (non-boundary) uses of `--border-strong`:
  `.assistant-chat__send:disabled` background, `.user-mobile-actions__handle`
  background, `.settings-capabilities__availability > span` dot.
- `.field__control[aria-invalid="true"]` (state emphasis, out of scope).
- No copy, no logic, no component `.tsx` changes.

## Constraints

- Worktree `odd/frontend-polish` only.
- Artifacts in English; Conventional Commits, no AI attribution.

## Tasks

- [x] **T1** `primitives.css` — control-boundary rules → `--border`
- [x] **T2** page CSS — control-boundary rules → `--border`
- [x] **T3** `Settings.css` — remove redundant overrides (dark `.menu__trigger` + redundant field `--border`)
- [x] **T4** `DESIGN_SYSTEM.md` — record the decision
- [ ] **T5** verify — `npm test` green, `npm run build` OK, visual check

## Acceptance

- No **control boundary** in the panel uses `--border-strong` (only decorative
  fills / dots remain on it).
- Configuración and the rest of the panel render the same light border.
- `npm test` and `npm run build` pass.

## Verification

- `cd web && npm test`
- `cd web && npm run build`
- Visual: Conversaciones search + filter, Settings inputs, secondary buttons, dropdowns.

## Progress log

- 2026-10-09 — created.
- 2026-10-09 — T1–T4 implemented. Contract tests updated
  (Button/Input/Select/SearchInput/Textarea/AppShell). `npm run build` OK.
  `npm test` green in isolation; the full-suite timeouts were load-induced
  (another agent's suite was running concurrently, load avg ~26). Visual
  confirmation (T5) pending owner review.
