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

- [ ] **A1 — derive and commit the one-line lockup.** Generate `lumat-logo-line.png` (528×158) from
  the owner's `LumatLinea.png` with the recipe above and commit it under `web/public/brand/`.
- [ ] **A2 — bar-scoped one-line lockup.** Give `Brand()` a bar-only variant so the **mobile bar**
  renders `lumat-logo-line.png` while the **drawer keeps the stacked** `lumat-logo.png`. Any width
  override must be mobile-scoped — do not touch the shared `--brand-logo-max-width`.
- [ ] **A3 — settle the mobile bar order.** Reorder the bar to `[menu] | lockup | bell | avatar` per
  `mobilePanelShell.png`. Recorded decision (reference governs layout).

### Slice 2 — Unit B (favicon + PWA)

- [ ] **B1 — icon set.** Bring the owner's generated set into `web/public/brand/` under a normalized
  lowercase name, drop the generated `site.webmanifest`, and **produce a real maskable 512** with the
  mark at ~80% and ≥10% margin all around.
- [ ] **B2 — manifest.** Merge the icons into `web/public/manifest.webmanifest`: correct `src` paths
  (`/panel/app/brand/…`), correct `sizes`, honest `purpose` (`any` for the mark, `maskable` for the
  real maskable), and palette-correct `theme_color` / `background_color`.
- [ ] **B3 — `index.html` icon links.** Add `<link rel="icon">` (`/panel/app/brand/…favicon.ico` and
  the PNG favicons) and `<link rel="apple-touch-icon">`.
- [ ] **B4 — shrink the committed assets.** Replace `lumat-mark.png` and `lumat-logo.png` with the
  optimized derivatives (spec-visible, see Constraints) and amend the DS-SHELL-8 clause.
- [ ] **B5 — tests + rendered verification.** Extend `pwa.test.ts` so an icon-link claim in
  `index.html` is asserted, and refresh the icon assertions to the merged manifest. Rendered pass
  over the mobile bar, the drawer, and the installer icon.

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

- **PWA `theme_color` / `background_color`** (B2). Recommendation: forest chrome `#143c2c`
  (`--primary-800`) for `theme_color`; confirm before applying, it is a palette decision. Carried
  from the handoff as an explicit owner call.

## Route decisions

| Task | Route | Trigger evidence |
| --- | --- | --- |
| A1 | inline | mechanical asset derivation, no research |
| A2+A3 | delegated writer | 2 non-trivial files (PanelShell.tsx + primitives.css) |
| B1+B2 | inline | mechanical asset generation + a JSON manifest |
| B3 | inline | one HTML file, already understood |
| B4+B5 | delegated writer | asset replacement + spec amendment + tests across files |

## Progress and evidence

_(none yet)_
