# Apply Progress — panel-design-system

> Change: `panel-design-system` · Project: LumatAgent · Phase: sdd-apply · Strict TDD active (vitest) · Delivery: auto-chain, stacked to main (PR 1 = B9 → PR 2 = B10).

## Batch 9 (B9) — Token foundation + drift guard + Storybook config — 2026-08-15

Work unit: **B9** (T9.1, T9.2, T9.3). Scope: `web/src/tokens/tokens.css`, `web/src/tokens/tokens.test.ts`, `web/.storybook/preview.ts` only.

### Completed tasks

- **T9.1** Token additions (DS-TKN-1..7): 25 new tokens appended inside their group sections per the design's order (type → leading → weight → focus → motion → breakpoints → shadow-3 after --shadow-2), each group with a `/* Type — DS-TKN-3 */`-style banner. Diff append-only (+36/−0 in tokens.css); every pre-existing declaration byte-identical; `--font-sans` unchanged; no `clamp()`. Values match the design table exactly.
- **T9.2** Drift-guard extension (DS-TKN-8/9): 5 new `it` blocks / 25 assertions appended (type 12, focus 3, motion 5, breakpoints 3, shadow-3 1), reusing the same line regex the Tokens page uses (`/^\s*(--[\w-]+)\s*:\s*([^;]+);/` — one pattern, two consumers, D11). No existing assertion edited or removed; `tokens.ts` absent from the diff (DS-TKN-9).
- **T9.3** Storybook config (DS-STORY-6/7): autodocs enabled + `--bp-*` viewport presets (640/1024/1280, all 900px tall) + desktop-first default in `preview.ts`; `main.ts` untouched (glob unchanged, PDW-CMP-1).

### TDD Cycle Evidence (`cd web && npm test`, vitest)

| Phase | Action | Result |
|---|---|---|
| RED | Appended the 5 new-group spot-checks to `tokens.test.ts` only (tokens.css untouched) | **FAIL** — 5 failed / 40 passed (45 total); all 5 new `it` blocks failed with `undefined` (new tokens absent) |
| GREEN | Added the 25 tokens to `tokens.css` | **PASS** — 13 files / 45 tests |
| TRIANGULATE | Full design-table matrix written at RED (25 asserts across type/leading/weight, focus, motion, bp, shadow-3); nothing missing | **PASS** — 45/45 |
| REFACTOR | None needed (additive CSS, append-only tests); map-hoisting rejected — would edit the existing mirror test (forbidden) | **PASS** — 45/45 |

### Verification (DS-VER-1)

- `cd web && npm test` → **Test Files 13 passed (13) · Tests 45 passed (45)** — drift-guard pinned palette, `tokens.ts` mirror equality, and no-hard-coded-hex walk all green.
- `cd web && npm run build-storybook` → **`✓ built in 11.69s`**, zero errors (only the informational chunk-size warning); built `storybook-static/index.json` = **22 story + 10 docs entries** (autodocs page for every existing story file; B10 adds the 11th docs page).
- Hex-walk confirmation: the only hex introduced outside `tokens.css` is the `#256f51` pin in `tokens.test.ts` (walk-exempt `*.test.ts`); `preview.ts` introduces none; drift-guard test itself proves acceptance.
- Diff: 3 files, **+97/−0** (web-only; `tokens.css` append-only; `tokens.ts`, `main.ts`, `src/components/**`, `app/`, `db/`, `infra/` absent).

### Deviations from design text

1. **Autodocs mechanism (DS-STORY-6) — evidence-backed**: design/spec prescribed `parameters.docs.autodocs: true` in preview.ts; **inert in installed Storybook 8.6.14** (traced `@storybook/core/dist/core-server/index.cjs` `getProjectTags` — the only global switch is `options.docs.autodocs === true` from main.ts; addon-docs preset defaults `autodocs: "tag"`; no code path reads `parameters.docs.autodocs`; verified empirically: 0 docs entries in built index.json). Fixed **in-scope** by adding global `tags: ['autodocs']` to the preview export (the SB 8.6 project-tags mechanism, still preview.ts only — main.ts untouched); the parameter is kept as intent documentation. Evidence: built index.json went 0 → 10 docs entries.
2. **`defaultViewport` vs `initialViewport`**: design text says `initialViewport: 'bp-lg'`; the viewport addon's real parameter is `defaultViewport` (`initialViewport` is dead config). Used `defaultViewport: 'bp-lg'` to realize the stated desktop-first intent.

### Graph Check (mandatory per AGENTS.md — recorded)

Knowledge graph: `graphify-out/` (built from commit `a756502c`; HEAD now `95269e74` — stale by design; orchestrator runs `graphify . --update` at archive).

- **Nodes consulted**: `web_src_tokens_tokens` (community 68), `web_src_tokens_tokens_{spacing,radius,zindex}` (68), `web_src_tokens_tokens_test` (68), `web_storybook_preview` (68), `web_storybook_preview_preview`, `web_storybook_preview_withpanelsurface`, `web_package` (community 7), `web_storybook_main` (thin).
- **Edges consulted**: `tokens.test.ts --imports_from--> tokens.ts` (drift-guard → mirror); `preview.ts --imports_from--> tokens.ts`; `preview.ts --indirect_call--> withPanelSurface()`; `tokens.ts --contains--> {spacing,radius,zindex}`; known graph gap: the `preview.ts → tokens.css` CSS import has no AST node (CSS not extracted).
- Read-only `graphify query/path` calls mutated `graphify-out/` cache files; restored to HEAD — **no graphify update run** (parent-owned at archive).

### Remaining (B10 — not this batch)

- Unchecked implementation tasks: T10.1, T10.2, T10.3, T10.4, T10.5 (exact `- [ ]` lines in `tasks.md`).
- Unchecked parent gates: bounded review B9 (PR 1) before chaining PR 2; bounded review B10 (PR 2) before archive; archive `graphify . --update`.

### Attempt ledger

- Attempt: **B9-foundation-tokens**, ordinal 1, token `sha256:5cc543…`, outcome running (parent-held); executor authenticated with `--token` → `proceed` (zero mutation). Evidence goal: web tests green + storybook build green — both met above. Settle is parent-owned (orchestrator lifecycle).
