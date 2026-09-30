# Apply Progress: panel-design-system-final — Slice 1

## Status

Complete — tasks 1.1 and 1.2 are implemented and verified. The parent-authorized single assertion update in the AppShell story test reconciles a stale palette expectation. Both work-unit commits were created after the full suite and build passed.

## Task completion

- [x] 1.1 — WU1 palette and token guard.
- [x] 1.2 — WU2 final design direction documentation.

## Completed work

### WU1 — task 1.1: palette and token guards

- Changed `web/src/tokens/tokens.test.ts`: exact canonical palette checks, alias/color-mix resolution with fail-closed unsupported color handling, resolved no-pure-white surfaces, measured contrast assertions and decorative dispositions, radius/depth assertions, and removal of obsolete palette spot checks.
- Changed `web/src/tokens/tokens.css`: approved canonical roles and adjusted muted/warning values; semantic surfaces and corp aliases remain indirections; existing primary scale preserved; radius values tuned; raised elevation disabled for flat cards; status/decorative comments updated.
- Changed `web/src/tokens/tokens.ts`: retained the spacing/radius/z-index mirror subset and synchronized the radius values to CSS (10px/14px).
- Parent-authorized change in `web/src/stories/domain/AppShell.stories.test.tsx`: renamed the v1 cream-bg test to approved sage-bg guidance and changed only its expected value to `#dbe1d6`; the separate `--header-gradient` assertion remains unchanged.
- Focused RED: after extending the guard and before production edits, `cd web && npm run test` failed on the new palette/surface/radius assertions (token test: 4 failures; full suite: 91 files passed, 1 failed; 873 passed, 4 failed).
- Focused GREEN: `cd web && npx vitest run src/tokens/tokens.test.ts` passed, 21/21 tests.
- Final full suite passes after the parent-authorized obsolete assertion update. This assertion is intentionally redundant with the canonical token guard; record consolidation as a Slice 3 Ponytail finding, not a current edit.
- Build: `cd web && npm run build` passed after removing one unused local, including `tsc -b`; Vite emitted its existing >500 kB chunk-size warning.
- Ponytail: the finite resolver only implements the declared CSS forms in use (aliases, supported sRGB `color-mix()`, and hex). No simpler form preserves the required resolve-and-fail-closed behavior. No dependency or extra abstraction introduced.
- Rollback boundary: revert `web/src/tokens/tokens.css`, `web/src/tokens/tokens.test.ts`, and `web/src/tokens/tokens.ts` together; the mirror file is paired with tuned CSS radii.

### WU2 — task 1.2: direction documentation

- Changed `web/DESIGN_SYSTEM.md`: replaced stale cream/white and old geometry guidance with final role values, measured contrast results/dispositions, flat card/radius/shadow rules, responsive shell direction, no-dark-mode statement, and committed logo asset references; removed the obsolete production-logo convergence item and low-resolution-JPG warning.
- RED: added document-to-token consistency checks to `tokens.test.ts`; `cd web && npx vitest run src/tokens/tokens.test.ts` failed against stale documentation (2 documentation assertions failed).
- GREEN: after updating the guide, `cd web && npx vitest run src/tokens/tokens.test.ts` passed, 23/23 tests.
- Final full suite and build pass. Parent-authorized shell-story assertion remains redundant with the token guard; consolidate during Slice 3 only.
- Ponytail: documentation now states each final role once in its palette table; the existing comprehensive component and workflow sections remain intact. No simpler documentation reduction identified without discarding requested guidance.
- Rollback boundary: revert `web/DESIGN_SYSTEM.md` only; token guard additions should remain paired with WU1.

## Verification evidence

| Command | Observed result |
|---|---|
| `cd web && npm run test` (base safety net) | Passed: 92 test files, 876 tests. |
| `cd web && npm run test` (WU1 RED) | Expected RED: token suite had 4 assertion failures; 91 files passed, 1 failed; 873 passed, 4 failed. |
| `cd web && npx vitest run src/tokens/tokens.test.ts` (WU1 GREEN) | Passed: 1 file, 21 tests. |
| `cd web && npm run test` (after WU1/WU2 changes) | Failed: 1 stale, out-of-scope assertion in `src/stories/domain/AppShell.stories.test.tsx` expects `--bg: #F1F1E8`; 91 files passed, 1 failed; 878 passed, 1 failed. |
| `cd web && npm run test` (final, after parent authorization) | Passed: 92 test files passed (92); 879 tests passed (879). |
| `cd web && npx vitest run src/tokens/tokens.test.ts` (WU2 RED) | Expected RED against stale docs: 1 file failed, 2 documentation assertions failed. |
| `cd web && npx vitest run src/tokens/tokens.test.ts` (WU2 GREEN) | Passed: 1 file, 23 tests. |
| `cd web && npm run build` | Passed: `tsc -b` and Vite production build. Vite reports a chunk larger than 500 kB. |
| `cd web && npm run build` (final) | Passed: `tsc -b` and Vite production build; Vite reported a chunk larger than 500 kB. |
| `git diff --check` | Passed: no whitespace errors. |

## Ponytail finding — defer to Slice 3

The exact `--bg` value is asserted both in `web/src/tokens/tokens.test.ts` (canonical token guard) and `web/src/stories/domain/AppShell.stories.test.tsx` (shell story guard). The story-test copy is why the stale value survived. Slice 3 should consolidate the redundant assertion; it was retained here as explicitly directed.

## Parent-authorized scope adjustment

The parent authorized exactly one additional source file for Slice 1: `web/src/stories/domain/AppShell.stories.test.tsx`. Only the stale cream assertion's test name and expected value were changed; the `--header-gradient` assertion and all other assertions remain unchanged. This was necessary to align an existing shell test with the newly approved canonical `--bg` palette value.

## Graph check

- Graph report is stale: `GRAPH_REPORT.md` identifies build commit `96a6f69b`; this worktree is at `29f79311ad1e9b4998dea5af72035c8ff31a3221`. Per instruction, no rebuild was run.
- WU1 query consulted `tokens.test.ts`, `cssVars`, `resolveColor()`, `contrast()`, `web/src/tokens/tokens.css`, `tokens.ts`, and `web/package.json`.
- WU1 graph path query `tokens.test.ts` to `cssVars`: `tokens.test.ts --contains--> cssVars`; no direct directed path was found between `tokens.test.ts` and `tokens.css`.
- WU2 reused the same token guard and documentation-consistency node family; no second path query was run because both are the same affected token/doc relationship.
- Resumed apply query consulted `AppShell.stories.test.tsx`, `AppShell.stories.tsx`, `AppShell()`, `AppShell.tsx`, `tokens.test.ts`, and `web/package.json`. No directed path was found from `tokens.test.ts` to `AppShell.stories.test.tsx`; graph report remained stale and was not rebuilt.

## Commits

- `765eb23c` — `feat(tokens): apply approved panel palette and guards`
- `06618293` — `docs(web): document final panel design direction`

No push or remote operation was performed.

## Next step

Slice 1 is ready for the orchestrator's next SDD phase. Slice 3 should consider consolidating the redundant `--bg` assertion in the shell story test with the canonical `tokens.test.ts` guard; do not consolidate during this slice.
