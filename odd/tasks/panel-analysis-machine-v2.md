# ODD Task: panel-analysis-machine-v2

Status: in progress
Worktree: `/home/stefan/repos/lumat-agent-odd-panel-analysis-machine-v2`
Branch: `odd/panel-analysis-machine-v2`
Base: `5660cf5d` (= `origin/main`, after PR #466)
Source: owner planning session `2026-10-02-panel-analysis-machine-v2`
Delivery strategy: `ask-on-risk`
Chain strategy: `stacked-to-main` (owner standing decision)
TDD: not applicable (docs + a capture script). The capture script gets a real smoke run.

## Objective

Replace the v1 analysis machine (one shared ledger, code-first) with a **v2** that is **image-first**,
**per-section**, and **committed per section**, plus an **automated capture tool** so the owner can
produce the visual evidence and drive the code analysis with it.

## Why this unit exists

v1 (`.opencode/skills/panel-section-analysis/SKILL.md` + one ledger) produced one dashboard run and
then stopped growing. Two concrete failures: the analyst's first pass was materially incomplete, and
the gate passed a semantically inverted row and a row bundling two findings. More importantly, the
analyst classified **symptoms** without the owner's visual guide; the owner's eye found the causes.

The owner's new flow: capture current Desktop/Tablet/Mobile → look at the reference
Desktop/Tablet/Mobile → **the owner writes the analysis** → only then the agent reads code, guided by
that analysis.

## Decisions (from the planning session — recorded in Engram)

- **D1** Automated capture (Playwright, 3 viewports: 1280x900 / 768x1024 / 390x844) with **clean
  content**: hide `#panel-shell-sidebar`, `.panel-shell__footer-nav`, `.panel-shell__header-row`.
- **D2** Captures live at `refs/current/<section>/{desktop,tablet,mobile}.png` + `manifest.json`,
  **gitignored**, in the **primary worktree**.
- **D3** Durable analysis per section, committed: `odd/analysis/<section>/visual.md` (owner guide),
  `odd/analysis/<section>/findings.md` (validated code findings), `odd/analysis/README.md` (index +
  shared-primitive roll-up).
- **D4** Hard gate: no code reading before the owner's analysis exists in `visual.md`.
- **D5** Hardened validator: one finding per row, semantic consistency with the owner note, and the
  analyst must walk the whole section (not single labels).

## Section slugs and routes

| Slug | Route |
| --- | --- |
| `dashboard` | `/panel/app/` |
| `clientes` | `/panel/app/clients` |
| `conversaciones` | `/panel/app/conversations` |
| `agenda` | `/panel/app/agenda` |
| `usuarios` | `/panel/app/users` |
| `conocimiento` | `/panel/app/kb` |
| `configuracion` | `/panel/app/settings` |

## Work units

### WU1 — the capture tool

- **`web/scripts/capture-section.mjs`** (new): Node ESM, uses `@playwright/test`'s `chromium`
  (`channel: "chrome"`), driven by a section slug argument.
  - Slugs are the table above; refuse an unknown slug.
  - Credentials: `process.env.PANEL_ADMIN_USERNAME` / `PANEL_ADMIN_PASSWORD`, else parse
    `infra/.env` from the primary worktree.
  - Base URL: `CAPTURE_URL`, default `http://127.0.0.1:5173/panel/app/`.
  - Flow: `goto(base)` → if the login form is present (`getByLabel("Usuario")`), log in → wait for
    `#panel-shell-sidebar` → `goto(route)` → wait for the page to settle → inject a `<style>` that
    hides the three shell selectors (so the screenshot is section content only).
  - For each viewport, `setViewportSize`, settle, then `screenshot({ fullPage: true })`.
  - Output root: resolve the **primary worktree** with
    `git rev-parse --path-format=absolute --git-common-dir` (its parent) and write to
    `refs/current/<slug>/`. Print the resolved path.
  - Write `manifest.json`: `{ section, route, captured_at, app_commit, origin, viewport, files{sha256}, hidden_chrome }`.
  - Exit non-zero with a clear message on any failure (missing creds, login failure, navigation).
- **`web/package.json`**: add `"capture:section": "node scripts/capture-section.mjs"`.
- **`.gitignore`**: add `refs/current/`.

**Smoke run (verification of record):** with the app running on `:5173` and the seeded dev DB, run
`npm run capture:section -- configuracion`. Assert: 3 PNGs + `manifest.json` written, non-trivial
height (the page scrolls), and the shell is absent from the image (read the PNG back).

### WU2 — the skill v2 and the analysis layout

- **Rewrite `.opencode/skills/panel-section-analysis/SKILL.md`** to v2:
  - Input: a section slug + the capture produced by WU1 (or an existing `refs/current/<slug>/`).
  - Mandatory phases, in order:
    0. **Capture** the section (WU1) if the current shots are missing/stale.
    1. **Compare** — load the 3 current + the 3 reference images and present them. **Prohibited: reading code in this phase.**
    2. **Owner analysis** — `expected` / `actual` / `severity` per breakpoint, written to `visual.md`. **The agent stops and waits.** This is the gate.
    3. **Code analysis (read-only)** — only once `visual.md` holds the owner's block; guided by it; each finding cites the owner note as evidence.
    4. **Validator gate** — fresh-context, read-only.
    5. **Implementation** — sequential per section; shared-primitive first.
  - Output: `odd/analysis/<section>/findings.md` rows; the index/roll-up in `odd/analysis/README.md`.
  - Keep the Adjudication Rule, the classification (`local` / `shared-primitive` / `token-palette`),
    and the three-part evidence bar.
  - Add the per-section lifecycle in `visual.md`: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`.
- **Rewrite `references/validator-gate.md`**: add **one finding per row** (reject bundled rows), and a
  **semantic consistency** check (the finding's direction must match the owner note), on top of the
  existing schema/evidence/classification/duplicate checks.
- **Add `references/visual-template.md`**: the `visual.md` skeleton — lifecycle header, `## Sources`
  (current + reference paths, app commit, date), and the `## Owner analysis` block per breakpoint.
- **Create `odd/analysis/README.md`**: the section index (slug, status, links to `visual.md` /
  `findings.md`) + the **shared-primitive roll-up** (one upstream unit before per-section implementation).
- **Migrate** the v1 shared ledger → `odd/analysis/dashboard/findings.md` (the 12 rows +
  the owner adjudications), preserving the content verbatim. Replace the old ledger with
  `odd/analysis/README.md`; note in the README that the dashboard run predates v2. Delete the old
  ledger file (git history keeps it).
- **Do not** re-analyze any section; this unit only builds the machine and migrates the record.

## Constraints

- Artifacts in English; UI/ownerenotes keep their original language; Conventional Commits, no AI
  attribution; merge commits, never squash; exactly one `type:*` label per PR.
- No new dependency (Playwright is already a devDependency).
- The capture script must not require the backend container to be reachable beyond what the app needs.
- `refs/` stays gitignored; never commit PNGs.

## Checks

- Capture: `npm run capture:section -- configuracion` → 3 PNGs + `manifest.json`; read one PNG back.
- `git diff --check`.
- Docs: read the rewritten files back; assert the gate language is present.
- Frontend suite is untouched, but the PR still runs CI (`panel` job).

## Recovery

- Base `5660cf5d`. `graphify-out/` is gitignored: query from `/home/stefan/repos/lumat-agent`.
- The v1 ledger is on `main`; its dashboard record is `odd/analysis/dashboard/findings.md`.
