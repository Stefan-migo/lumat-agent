# ODD — brand-assets

Base: `7aee1b2e` (main). Worktree: `../lumat-agent-odd-brand-assets`, branch `odd/brand-assets`.
Sources: handoff `.rapsodia-code/handoffs/2026-10-01-brand-assets-mobile-lockup-and-pwa-icons.md`
(gitignored, main worktree), the owner-delivered assets, and directly measured render boxes.
References: `refs/Diseño Lumat/mobileTablet/mobilePanelShell.png` (mobile bar + overlay drawer),
`refs/Diseño Lumat/headerShell.png`. `refs/` is gitignored — read it from the main worktree
(`/home/stefan/repos/lumat-agent/refs/…`), it does not exist in this worktree.

## Objective

Close the shell-header unit's last task (**M3** — the one-line mobile lockup) and settle the
favicon/PWA icon debt, without rebuilding the design system and without inventing destinations,
routes, or tokens.

## Problem

### Unit A — one-line mobile lockup (closes M3)

- The mobile bar renders the **stacked** `lumat-logo.png` (1864×1264, aspect 1.47) → at the bar's
  ~48px inner height the wordmark is unreadable. That is why the owner produced a one-line version.
- Render measurement: `.panel-shell__brand-image` caps at `--brand-logo-max-width: 11rem (176px)` /
  `--brand-logo-max-height: 4rem (64px)` (`web/src/tokens/tokens.css:156-157`). The sidebar is
  height-limited → 94×64; the mobile bar renders ≈176×53.
- **Bar order differs from the reference.** `PanelShell.tsx:424-447` renders
  `Brand | [bell, avatar, menu]`; `mobilePanelShell.png` shows `[menu] | lockup | bell | avatar`
  (menu at the far left). The reference controls geometry and layout (adjudication rule), so the
  order is corrected here — recorded deliberately, not silently.
- `.panel-shell__mobile-brand .panel-shell__brand-mark { display: none }` (`primitives.css:1063`).
- `--brand-logo-max-width` is **shared with the sidebar** → do not change the shared token; scope any
  mobile width locally.
- `<Brand mobile />` is rendered in **two** places: the mobile bar (`:425`) and the drawer heading
  (`:463`). The reference keeps the **stacked** lockup in the drawer → the one-line asset must be
  **bar-scoped**, not `mobile`-scoped.

### Unit B — favicon + PWA icons

The owner's generated set (correct dimensions) has four integration problems:

1. **`site.webmanifest` must not ship.** The repo already has `web/public/manifest.webmanifest`
   (name "Lumat Panel", `start_url`/`scope` `/panel/app/`, `display: standalone`). The generated file
   has `"name":""`, `theme_color:"#ffffff"` and root-relative icon paths. Merge the icons into the
   existing manifest and drop the generated file.
2. **No real maskable icon.** `android-chrome-512x512.png` content margins measure L 11.3% / T 3.9% /
   R 9.2% / B 5.3% → a circular Android mask clips the top and bottom. A maskable variant needs the
   mark at ~80% and centred (≥10% margin all around). The current manifest even declares
   `lumat-mark.png` as `purpose: "maskable"`, which it is not.
3. **Paths.** The generated manifest points at `/android-chrome-*.png` at the root; this app serves
   public assets under `/panel/app/`. Icons must resolve under `/panel/app/brand/…`, and
   `favicon.ico` should be reachable at `/favicon.ico` (or linked explicitly).
4. **`web/index.html` has no icon links at all** — no `<link rel="icon">`, no apple-touch. Only
   `theme-color` and the manifest.

Existing PWA debt found while reviewing (independent of the new assets):

- `manifest.webmanifest` declares `lumat-mark.png` at **192x192 and 512x512**, but the file is
  **2860×2736 (4.43 MB)** → the PWA downloads 4.4 MB for an icon.
- `theme_color: "#17324d"` (navy) and `background_color: "#f7f8fa"` are not Lumat palette values.
  `web/index.html` carries the same `theme-color #17324d`.
- `lumat-mark.png` (4.43 MB) and `lumat-logo.png` (930 KB) are grossly oversized for their rendered
  sizes.

## Measured evidence (this session, ImageMagick 7.1.2)

| Asset | Current | Max render box | Target (3×) | Optimized bytes |
| --- | --- | --- | --- | --- |
| `lumat-mark.png` | 2860×2736 · 4.43 MB | **112×107** (TechnicianShell, `width: 7rem`) | 336×321 | 17.5 KB |
| `lumat-logo.png` | 1864×1264 · 930 KB | 94×64 (sidebar, height-limited) | 282×191 | 10.2 KB |
| `LumatLinea.png` → `lumat-logo-line.png` | 1440×431 · 424 KB | 176×53 (mobile bar) | 528×158 | 18.7 KB |

Total 5.79 MB → **~46 KB** (99.2% less). Recipe (verified visually on the dark chrome, no banding,
no halo):

```
magick <src>.png -filter Lanczos -resize WxH -colors 64 -strip \
  -define png:compression-level=9 PNG32:<dst>.png
```

`-colors 256 PNG8:` was rejected: it collapses alpha to binary (2 alpha levels → hard edges).
`-colors 64` on a truecolor+alpha output keeps 25 alpha levels at 0.87% RMSE.

Corrects the handoff: the mark's max render box is **112×107**, not ≤40px — `TechnicianShell.tsx`
(live, mounted from `app.tsx`) renders it at `width: 7rem`.

## Scope

**In:** the one-line mobile lockup and the mobile bar order; the favicon/PWA icon set, the existing
manifest, `index.html` icon links; and shrinking the two oversized committed brand assets.

**Out:** palette and tokens (except the PWA `theme_color`/`background_color` values, which are a PWA
concern), other primitives, other pages, the sidebar/drawer surfaces already adjudicated in
`odd/tasks/panel-sidebar-refine.md`, the drawer's own logo treatment, and any new route/destination.

## Constraints

- Files authorized: `web/public/brand/**`, `web/public/manifest.webmanifest`, `web/index.html`,
  `web/src/components/domain/PanelShell.tsx`, `web/src/components/primitives/primitives.css`,
  `web/src/components/domain/PanelShell.test.tsx`, affected `web/src/stories/**` and their tests,
  `web/src/pwa.test.ts`, and the DS-SHELL-8 clause in `openspec/specs/panel-design-system/spec.md`.
- No new dependency, no new destination, route, or parallel navigation model.
- **DS-SHELL-8 (`panel-design-system/spec.md:945`) enumerates the committed brand assets and states
  "this change produces no new asset".** Adding `lumat-logo-line.png` and replacing
  `lumat-mark.png` / `lumat-logo.png` are therefore **spec-visible**: the requirement is amended to
  name the current assets. This is recorded, not silent. (Note also that DS-SHELL-8 calls
  `lumat-logo.png` a "horizontal lockup" while the file is actually stacked — the amendment corrects
  the description.)
- `web/src/pwa.test.ts:20-23` asserts the manifest contains an icon with `src`
  `/panel/app/brand/lumat-mark.png` **and** an icon whose `purpose` contains `"maskable"`. Both must
  hold after the merge; the maskable icon may be a different asset.
- Verification for every task: `cd web && npm run build` (the **only** type-check path; a green
  Vitest suite does not prove the tree type-checks) plus the affected test files via
  `npx vitest run <files>`. Full `npm run test` once per slice.
- Rendered pass: `cd web && npm run build-storybook -- --quiet`, serve `storybook-static`, drive it
  with Playwright `chromium.launch({ channel: 'chrome' })` — the bundled chromium is **not**
  installed. `storybook-static/` is gitignored and can be stale — always rebuild before a visual pass.
- Artifacts and code comments in English; user-facing UI copy in neutral Chilean Spanish.
- One work-unit commit per task, tests alongside the behaviour, conventional commits, **no AI
  attribution**.

## Tasks

### Slice 1 — Unit A (closes the header unit)

- [x] **A1 — derive and commit the one-line lockup. DONE.** Generated `lumat-logo-line.png` (528×158,
  18.7 KB) from the owner's `LumatLinea.png` with the documented recipe and committed it under
  `web/public/brand/`.
- [x] **A2 — bar-scoped one-line lockup. DONE.** `Brand()` gained a `line` prop; the mobile bar passes
  it, the drawer does not. Styling is scoped to `.panel-shell__mobile-brand--line`; the shared
  `--brand-logo-max-width` is untouched.
- [x] **A3 — settle the mobile bar order. DONE.** The bar now renders `[menu] | lockup | [bell, avatar]`
  per `mobilePanelShell.png`. Recorded decision (reference governs layout); the menu button's props
  and behaviour were preserved exactly.

### Slice 2 — Unit B (favicon + PWA)

- [x] **B1 — icon set. DONE.** The owner's set is shipped under normalized lowercase names
  (`favicon.ico`, `favicon-16.png`, `favicon-32.png`, `apple-touch-icon.png`, `icon-192.png`,
  `icon-512.png`); the generated `site.webmanifest` is not shipped; a real maskable
  `icon-maskable-512.png` was produced (mark at ~62% centred on forest `#143c2c`, inside the 80%
  safe zone).
- [x] **B2 — manifest. DONE.** Icons merged into `web/public/manifest.webmanifest` with correct
  `/panel/app/brand/…` paths, honest `sizes`/`purpose`, and `theme_color: #143c2c` /
  `background_color: #dbe1d6` (owner-approved from the desktop forest chrome).
- [x] **B3 — `index.html` icon links. DONE.** `favicon.ico`, the two PNG favicons, and the
  apple-touch link added; `theme-color` moved to `#143c2c`.
- [x] **B4 — shrink the committed assets. DONE.** `lumat-mark.png` 4.43 MB → 9.1 KB and
  `lumat-logo.png` 930 KB → 4.9 KB; DS-SHELL-8's asset clause amended to name the one-line lockup
  and correct the "horizontal lockup" description (recorded, not silent).
- [x] **B5 — tests + rendered verification. DONE.** `pwa.test.ts` refreshed to the merged manifest,
  the palette colours and the `index.html` icon links (the service-worker sample URL moved from the
  retired `lumat-mark.png` manifest entry to `icon-192.png`). Rendered pass over the mobile bar and
  the drawer at 390×844, plus the built `dist/` PWA surface.

## Acceptance criteria

- The mobile bar renders the one-line lockup at ≈176×53 with a legible wordmark, ordered
  `[menu] | lockup | bell | avatar`; the drawer still renders the stacked lockup.
- No new dependency; no new destination or route; the shared `--brand-logo-max-width` is unchanged.
- `web/index.html` carries icon links; `manifest.webmanifest` has correct paths, sizes, an honest
  `purpose`, a real maskable 512, and palette-correct colours.
- `lumat-mark.png` + `lumat-logo.png` are ≤ ~25 KB each; the PWA no longer downloads a 4.4 MB icon.
- DS-SHELL-8 names the current committed assets; the amendment is recorded, not silent.
- `npm run build` passes; affected tests pass; the full suite passes once per slice.
- Rendered verification confirms the mobile bar and the drawer on the dark chrome.

## Open owner decision

- **PWA `theme_color` / `background_color`** (B2) — **RESOLVED by the owner 2026-10-01:** follow the
  desktop version's chrome logic → `theme_color: #143c2c` (`--corp-primary`, the forest chrome the
  desktop sidebar and the mobile bar share) and `background_color: #dbe1d6` (`--bg`).

## Route decisions

| Task | Route | Trigger evidence |
| --- | --- | --- |
| A1 | inline | mechanical asset derivation, no research |
| A2+A3 | delegated writer | 2 non-trivial files (PanelShell.tsx + primitives.css) |
| B1+B2 | inline | mechanical asset generation + a JSON manifest |
| B3 | inline | one HTML file, already understood |
| B4+B5 | delegated writer | asset replacement + spec amendment + tests across files |

## Progress and evidence

**Slice 1 (Unit A) — code complete.**

- Commits: `8c941866` charter, `78b47b0d` A1 asset, `66945ccc` A2+A3 code.
- A2/A3 solution: `Brand()` gained a boolean `line` prop; the bar renders `<Brand mobile line />` while
  the drawer keeps `<Brand mobile />`. Bar scoping lives in `.panel-shell__mobile-brand--line`
  (`flex: 0 1 11rem; margin-right: auto`) plus a bar-only `max-height: 3rem` on
  `.panel-shell__brand-image`. The menu button was hoisted out of `.panel-shell__mobile-actions` to
  become the bar's first child, with its `ref`, `aria-*` and `onClick` unchanged. One DOM-level test
  added asserting the bar renders `lumat-logo-line.png`, the drawer renders `lumat-logo.png`, and the
  menu button is first.
- Checks: `npm run build` → `tsc -b` + Vite OK (only the pre-existing large-chunk warning).
  Affected test files (`PanelShell`, `AppShell`, `AppShell.stories`, `PanelEntry.stories`) → 4 files /
  83 tests passed. Full suite → **92 files / 909 tests, exit 0** (123s). Parent spot check: `npm run
  build` re-run independently → OK.
- Native RDD: `review assess --base-ref 7aee1b2e --committed-only` → risk **medium**
  (`executable_change`), `review_due: false`, `review_due_reason: under_budget` (227 changed lines).
  Under the delivery budget → boundary stays pending, no review yet.
- Rendered verification: **pending**, to run once in B5 (mobile bar + drawer + installer icon).

**Engram mirror: PENDING.** `mem_save` for `odd/brand-assets/tasks` is failing with "multiple active
runtime sessions match the current project and directory". The charter file on this branch is the
source of truth; the mirror must be re-pushed when the session ambiguity clears.

**Slice 2 (Unit B) — code complete.**

- Commits: `65b2062d` icon set + manifest + index links + refreshed assertions, `226e7366` brand
  asset shrink + DS-SHELL-8 amendment, `7f771fc1` re-encode pass.
- Owner decision applied: `theme_color: #143c2c` (`--corp-primary`) and `background_color: #dbe1d6`
  (`--bg`), derived from the desktop chrome surfaces rather than the retired navy `#17324d`.
- **Encoder finding.** The `PNG32:` output prefix forces a truecolor container; for the transparent
  assets the default palette container is byte-equivalent in quality (same alpha levels, same RMSE)
  at roughly half the size. Corrected in `7f771fc1`. The **opaque maskable is the exception**: there
  `PNG32:` compresses better (29.8 KB vs 42.8 KB), so it keeps it. Measured before/after:
  `icon-512` 97.3 → 45.9 KB, `apple-touch` 30.5 → 6.6 KB, `icon-192` 33.7 → 7.1 KB,
  `lumat-mark` 17.5 → 9.1 KB, `lumat-logo` 10.2 → 4.9 KB, `lumat-logo-line` 18.7 → 8.7 KB.
- **`web/public/brand/` now totals 125 KB** (was 5.79 MB of source art + a 355 KB icon set).
- Checks: `npm run build` OK; affected vitests 4 files / 68 tests; full suite **92 files / 909
  tests, exit 0**. Rendered pass at 390×844: bar order `menu-button → brand(--line) → actions`; bar
  brand box **176×48** rendering `lumat-logo-line.png`; drawer brand `lumat-logo.png` (stacked).
  Built `dist/brand/` carries all ten assets and no `site.webmanifest`; `dist/index.html` and
  `dist/manifest.webmanifest` carry the icons, links and palette colours.
- Native RDD (boundary `7aee1b2e`): risk **medium** (`executable_change`), `review_due: false`,
  `review_due_reason: under_budget` (296 changed lines < 400, 18 paths). No review due; boundary
  stays pending.

**Slice boundaries for delivery:** Slice 1 = commits `8c941866`→`efc2056c` (Unit A). Slice 2 =
`65b2062d`→`7f771fc1` (Unit B). Not yet pushed; PRs are the owner's call.
