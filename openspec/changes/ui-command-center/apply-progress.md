# Apply Progress: UI Command Center — PR 2 Focus / Conversation

**Status**: Phase 1 tasks 1.1–1.2, Phase 2 tasks 2.1–2.2, and Phase 3 tasks 3.1–3.3 complete; Phase 4 untouched.
**Mode**: Strict TDD (Vitest component tests).
**Delivery**: auto-chain, stacked-to-main; PR 2 targets the PR 1 branch.

## Completed Tasks

- [x] 1.1 RED — Backend authorization/bound/order and client seam coverage.
- [x] 1.2 GREEN — Bounded authorized thread-list API and typed client seam.
- [x] 2.1 RED — Added keyboard focus entry, focus trap/restoration, Escape, stream failure/recovery, and persisted-history authority tests.
- [x] 2.2 GREEN — Added PanelShell focus mode and separated transient stream state from persisted history with truthful recovery semantics.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | `tests/integration/test_assistant_chat.py`, `web/src/api.test.ts` | Integration + unit/client | ✅ 20/20 backend; 13/13 frontend | ✅ Written | ✅ Passed | ✅ Multiple scenarios | ✅ Clean |
| 1.2 | same | Integration + unit/client | ✅ Existing seam suite | ✅ Written | ✅ Passed | ✅ Bound/auth/order cases | ✅ Clean |
| 2.1 | `web/src/components/domain/PanelShell.test.tsx`, `web/src/components/pages/AgentChat.test.tsx` | Component/unit | ✅ 17/17 | ✅ Written; 3 tests failed before implementation | ✅ 20/20 | ✅ Focus, disconnect, persistence paths | ✅ Clean; `git diff --check` passed |
| 2.2 | same | Component/unit | ✅ 17/17 | ✅ Tests preceded production changes | ✅ 20/20 | ✅ Normal close, stream failure, reload authority | ✅ Clean; build passed |

## Work Unit Evidence

- Focused test: `cd web && npm test -- --run src/components/domain/PanelShell.test.tsx src/components/pages/AgentChat.test.tsx` — PASS, 20/20 tests.
- Build/typecheck: `cd web && npm run build` — PASS (`tsc -b` and Vite build).
- Runtime harness: N/A — frontend-only component slice; Vitest/jsdom is the available runtime boundary and covers keyboard/stream behavior.
- Rollback boundary: revert `web/src/components/domain/PanelShell.tsx`, `PanelShell.test.tsx`, `web/src/components/pages/AgentChat.tsx`, and `AgentChat.test.tsx`; no backend or unrelated route behavior is affected.

## Graph Check

- Consulted `GRAPH_REPORT.md`: `domain/PanelShell.tsx`, `PanelShell.test.tsx`, `AgentChat.tsx`, `AgentChat.test.tsx`, `types.ts`, `api.ts`, `InternalChatThread`, and `InternalChatMessage`.
- Queries: `PanelShell keyboard focus trap restoration Escape`; `AgentChat stream failure persisted history authoritative read-only context approval retry send`.
- Edges: `PanelShell.test.tsx --imports_from--> domain/PanelShell.tsx`; `AgentChat.test.tsx --imports_from--> AgentChat.tsx`; `AgentChat.tsx` references `api.ts` and realtime state.

## Deviations / Issues

- None from the design. The existing Spanish UI copy was preserved while adding explicit recovery semantics.

## Remaining Tasks

- [x] 3.1–3.3 Production composition, responsive zones, and story migration.
- [ ] 4.1 Narrow browser contract.

## PR 3 — Production Composition and Migration

**Delivery**: auto-chain, stacked-to-main; this slice targets `feat/ui-command-center-focus` and is bounded to Phase 3 tasks 3.1–3.3. `AppShell.tsx` remained route-stable.

### Completed Tasks

- [x] 3.1 RED — Added desktop zone-order coverage plus single-zone selection coverage at 390px and 768px; migrated InboxThread reply-window, directional bubble, composer, stale-state, and story-export scenarios into the production page test.
- [x] 3.2 GREEN — Composed the AgentChat navigator, conversation, and read-only execution context; added responsive zone selection and token-backed desktop/mobile visibility rules.
- [x] 3.3 GREEN — Promoted the required InboxThread scenario helpers into `ConversationThread.tsx`, removed the two quarantined InboxThread owners, and kept component/story ownership within production paths.

### TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| 3.1 | `web/src/components/pages/AgentChat.test.tsx`, `ConversationThread.test.tsx` | Component/unit | ✅ New zone and migration assertions failed before implementation | ✅ Focused suite 32/32 | ✅ 390px, 768px, 1024px and migrated state paths | ✅ `git diff --check` clean |
| 3.2 | same | Component/CSS contract | ✅ Zone assertions preceded composition | ✅ Focused suite 32/32; build passed | ✅ Desktop order and one-active-zone invariants | ✅ Existing primitives/tokens reused; no new dependency |
| 3.3 | `ConversationThread.test.tsx`, closure/boundary tests | Component/ownership | ✅ Migrated assertions initially failed on missing exports | ✅ Ownership checks 4/4; full suite 535/535 | ✅ Story parity, closure, dependency boundary | ✅ Quarantine owners deleted |

### Work Unit Evidence

- Focused test: `cd web && npm test -- --run src/components/pages/AgentChat.test.tsx src/components/pages/ConversationThread.test.tsx` — PASS, 32/32 tests.
- Ownership regression test: `cd web && npm test -- --run src/components/dependency-boundary.test.ts src/components/shared/closure.test.tsx` — PASS, 4/4 tests.
- Full frontend suite: `cd web && npm test -- --run` — PASS, 74/74 files and 535/535 tests.
- Build/typecheck: `cd web && npm run build` — PASS (`tsc -b` and Vite build).
- Runtime harness: N/A — browser harness is explicitly Phase 4; Vitest/jsdom verifies the interaction contract for this slice.
- Rollback boundary: revert `AgentChat.tsx`, `AgentChat.test.tsx`, `ConversationThread.tsx`, `ConversationThread.test.tsx`, `primitives.css`, and the two InboxThread deletions; `AppShell.tsx` and unrelated routes remain untouched.

### Graph Check

- Consulted `GRAPH_REPORT.md` god nodes/communities: `AgentChat.tsx`, `pages/ConversationThread.tsx`, `domain/AppShell.tsx`, `primitives.css`/token community, `quarantine/pages/InboxThread.stories.tsx`, and `ConversationThread.stories.tsx`.
- Queries: `AgentChat zones navigator conversation context responsive tiers`; `InboxThread quarantine stories ConversationThread migration`; `primitives.css token tiers breakpoints responsive`.
- Edges/paths: `AgentChat → api.ts → InternalChatThread`; `quarantine InboxThread → ConversationThread`; `AppShell → AgentChat`; `ConversationThread → Avatar/Textarea/StateMessage`; no directed `AgentChat → primitives.css` path was available, so the CSS token community was queried directly.

### Deviations / Issues

- `AppShell.tsx` required no change; its existing `chat` route already delegates to `AgentChat`.
- No prototype or fabricated catalog data was introduced. Existing full-suite output retains pre-existing React `act(...)` and jsdom navigation warnings; no test failures remain.
- The filesystem diff is above the nominal 400-line review budget because task 3.3 requires deleting two quarantined files (354 deleted lines); scope remains limited to the assigned PR 3 work unit.

### Corrective Re-run — Gatekeeper Findings F1–F4

- **F1 resolved:** Removed `isWithinReplyWindow`, `InboxThreadStateControls`, `InboxThreadView`, and `ConversationThreadView` from the production page module. Migrated coverage now renders controlled `ConversationThread` data and its real state, while story view ownership remains in `web/src/stories/pages/ConversationThread.stories.tsx`.
- **F2 resolved:** Wired the navigator to `listChatThreads(20)`, renders only returned `InternalChatThreadSummary` entries, loads the selected thread through `getChatThread`, and reports list failures with `StateMessage` without fabrication.
- **F3 resolved:** Added the explicit `compact` / `tablet` / `desktop` tier derived from the 640px and 1024px boundaries, exposed as `data-tier`, and asserted each narrow tier separately. CSS media rules remain aligned at `40rem` and `63.99rem`.
- **F4 resolved:** Re-ran the complete frontend suite and recorded the observed file/test totals below rather than carrying forward the inaccurate `74/535` report.

### Corrective Work Unit Evidence

- Focused test: `cd web && npm test -- --run src/components/pages/AgentChat.test.tsx src/components/pages/ConversationThread.test.tsx` — PASS, 2 files and 34 tests.
- Full frontend suite: `cd web && npm test -- --run` — PASS, 76 files and 539 tests.
- Build/typecheck: `cd web && npm run build` — PASS (`tsc -b` and Vite build).
- Runtime harness: N/A — browser harness is explicitly Phase 4; Vitest/jsdom covers navigator selection, responsive tier semantics, production conversation scenarios, and truthful error states.
- Rollback boundary: revert `web/src/components/pages/AgentChat.tsx`, `AgentChat.test.tsx`, `ConversationThread.tsx`, `ConversationThread.test.tsx`, and this correction note; `AppShell.tsx` remains untouched.

### Corrective Graph Check

- Queries rerun: `graphify query "AgentChat zones navigator conversation context responsive tiers"`; `graphify query "InboxThread quarantine stories ConversationThread migration"`.
- Consulted nodes/edges: `AgentChat.tsx → api.ts → InternalChatThread`; `ConversationThread.test.tsx → pages/ConversationThread.tsx`; `quarantine/pages/InboxThread.stories.tsx → ConversationThread.stories.tsx`; `AppShell.tsx → AgentChat.tsx`. `GRAPH_REPORT.md` identifies the three-zone composition and the production/story ownership communities.

### Corrective Re-run — F5 Desktop Navigator Gating

- **F5 resolved:** The bounded navigator list now loads when `desktop || activeZone === "navigator"`; `desktop` is included in the effect dependencies. Added one 1024px test that loads and selects an entry without clicking the hidden zone tabs.
- **TDD evidence:** New test RED against active-zone-only gating; GREEN after the condition/dependency change. Focused suite: `cd web && npm test -- --run src/components/pages/AgentChat.test.tsx` — PASS, 1 file and 23 tests.
- **Scope:** Only `AgentChat.tsx`, `AgentChat.test.tsx`, and this progress note are part of this correction; no CSS, conversation, shell, or task artifact changes.

### Final Verified State (PR 3)

Earlier numbers in this section are chronological and superseded. The slice closed on:

- Full frontend suite: `cd web && npm test -- --run` — PASS, **76 files and 540 tests**.
- Focused suite: `cd web && npm test -- --run src/components/pages/AgentChat.test.tsx src/components/pages/ConversationThread.test.tsx` — PASS.
- Build/typecheck: `cd web && npm run build` — PASS (`tsc -b` and Vite build).
- `git diff --check` — clean.
- Diff: 7 files, 207 insertions / 371 deletions (354 of the deletions are the two removed quarantine files).
- Ledger: the work-unit attempt settled `passed` with `changed_line_budget_exceeded` (653 vs 400 declared), resolved by a maintainer-scoped objective reset.

## PR 4 — Narrow Browser Contract

**Status**: Task 4.1 complete.
**Mode**: Standard browser verification with explicit RED counter-check.
**Delivery**: auto-chain, stacked-to-main; this slice is bounded to the browser harness and targets the PR 3 branch.

### Completed Task

- [x] 4.1 RED/GREEN — Added the minimal Playwright configuration, controlled local API fixtures, and narrow geometry, breakpoint, keyboard, focus, restoration, and action-reachability checks at 390px, 768px, and 1024px. No production files, screenshots, snapshots, CI, PWA assertions, or visual regression were added.

### Resolved Local Startup Command

The design open question is resolved with `cd web && npm run test:e2e -- playwright/command-center.spec.ts`. The script runs Playwright's self-contained `webServer` (`npm run dev -- --host 127.0.0.1`) and reuses an existing Vite server when available. The config uses the installed system Chrome channel, avoiding a version-specific Playwright browser download, and blocks service workers.

### Work Unit Evidence

- Install: `cd web && npm install --save-dev @playwright/test@1.63.0` — PASS; 3 packages added, audit completed with 5 moderate advisories.
- Focused test: `cd web && npx playwright test playwright/command-center.spec.ts` — PASS, **7 passed, 0 failed** (9.8s).
- Counter-check RED: temporarily inverted the desktop navigator/conversation order assertion, then ran `cd web && npx playwright test playwright/command-center.spec.ts -g "keeps desktop zones ordered"` — FAIL, **1 failed**; expected `> 532`, received `264`.
- Re-GREEN: restored the order assertion and reran `cd web && npx playwright test playwright/command-center.spec.ts` — PASS, **7 passed, 0 failed** (9.8s).
- Runtime harness: The Playwright route harness ran against the local Vite app with controlled `/panel/api/**` fixtures and `/panel/ws` aborted; all 7 browser scenarios executed in real Chrome. Vite logged expected `ECONNRESET` messages from the intentionally aborted WebSocket, without test failures.
- Rollback boundary: revert `web/playwright.config.ts`, `web/playwright/command-center.spec.ts`, `web/package.json`, `web/package-lock.json`, and `web/.gitignore`; production components under `web/src/` are untouched.

### Graph Check

- Required query: `graphify query "Playwright browser harness command center geometry breakpoints focus"`.
- Consulted nodes: `command-center.spec.ts`, `Narrow Playwright Browser Contract`, `AgentChat.tsx`, `domain/PanelShell.tsx`, `domain/AppShell.tsx`, `api.ts`, `types.ts`, and `pages/ConversationThread.tsx`.
- Edges/paths: `command-center.spec.ts --implements--> Narrow Playwright Browser Contract`; `AppShell.tsx → PanelShell.tsx → AgentChat.tsx`; `AgentChat.tsx → api.ts → InternalChatThread`. Direct directed paths from the shell/page nodes to the new spec were unavailable; the contract node and affected production paths were queried instead.

### Deviations / Residual Limitations

- The Command Center delegates emergency handling to the production-owned conversations route. The harness follows the visible shell `Conversaciones` affordance at each tier and verifies the real `Reconocer emergencia` action is reachable there, without changing production components.
- No screenshots, snapshot baselines, CI workflow, PWA assertion, page-object framework, or custom fixture layer were added.

### Diff Summary

- `git diff --stat` plus the two untracked harness files: **7 files changed, 230 insertions(+), 3 deletions(-)** relative to the clean PR 3 HEAD at implementation time (the lockfile is included in this total).

### Orchestrator Addendum — Desktop Navigator Coverage

An independent gatekeeper pass reproduced the harness (`npx playwright test playwright/command-center.spec.ts` → 7 passed) and found one coverage hole: nothing asserted that the desktop navigator zone is **populated**. Zone order and geometry pass even with an empty navigator, so the PR 3 defect (desktop fetch gated on the active zone, leaving the navigator permanently on "No threads available") would not have been caught by the browser contract.

Resolution: the desktop scenario now asserts that the bounded list seam actually renders its entry in the navigator at 1024px.

Counter-check evidence for the added assertion (proving it can fail): the PR 3 regression was temporarily reintroduced in `AgentChat.tsx` (`activeZone !== "navigator"` instead of `!desktop && activeZone !== "navigator"`), the desktop scenario was run alone, and it FAILED at the new navigator assertion. The production file was then restored (`git checkout -- web/src/components/pages/AgentChat.tsx`), confirmed clean, and the full harness re-ran **7 passed**. Production components under `web/src/` remain untouched in this slice.

## Verification Fixes

**Status**: Corrective work unit complete; all three authorized findings addressed.
**Mode**: Strict TDD for the browser scenario; the resize test was GREEN before any production implementation, so no `PanelShell.tsx` change was needed.
**Delivery**: auto-chain, stacked-to-main; corrective slice remains bounded to verification coverage and two minimal production cleanups.

### Fixes

- **Fix 1 — Vitest discovery**: Added `playwright/**` to `web/vite.config.ts` `test.exclude`, preserving all `src/**/*.test.tsx` collection.
- **Fix 2 — CC-2 / DS-CC-2 resize restoration**: First added the browser test `restores shell and selected zone after focus-mode resize` to `web/playwright/command-center.spec.ts`. After correcting a test-authoring selector typo, the test passed against the existing implementation; no speculative resize state or `PanelShell.tsx` implementation was added. The test covers desktop keyboard entry, resize to 390px, Escape exit, sidebar restoration, one coherent compact zone, and selected persisted thread visibility.
- **Fix 3 — redundant attribute**: Repository search found `data-desktop` only in `AgentChat.tsx` and generated `web/dist`, with no CSS, Playwright, or test consumer. Removed `data-desktop={desktop}` while retaining the `desktop` variable for zone gating and navigator fetch dependencies.

### TDD Cycle Evidence

| Task | Test File | RED | GREEN | REFACTOR |
|---|---|---|---|---|
| Resize restoration proof | `web/playwright/command-center.spec.ts` | ✅ Valid test was written before production changes; no implementation RED was required because behavior already satisfied the scenario | ✅ Focused browser run passed 1/1 before implementation; full browser run passed 8/8 | ✅ Minimal assertion-only addition; no production implementation added |

### Work Unit Evidence

- Focused test: `cd web && npx playwright test playwright/command-center.spec.ts --reporter=list -g "restores shell and selected zone after focus-mode resize"` — PASS, 1 passed, exit 0.
- Required Vitest: `cd web && npm test -- --run` — PASS, **76 files / 540 tests**, exit 0.
- Runtime harness: `cd web && npx playwright test playwright/command-center.spec.ts --reporter=list` — PASS, **8 passed**, exit 0 in real Chrome; expected `ECONNRESET` logs came from the intentionally aborted `/panel/ws` route.
- Build/typecheck: `cd web && npm run build` — PASS, exit 0; TypeScript and Vite build completed with 77 modules transformed.
- Diff hygiene: `git diff --check` — PASS, exit 0, no output.
- Rollback boundary: revert only `web/vite.config.ts`, `web/src/components/pages/AgentChat.tsx`, `web/playwright/command-center.spec.ts`, and this appended progress section; `PanelShell.tsx`, `verify-report.md`, `tasks.md`, specs, backend, and archive artifacts remain untouched.

### Corrective Graph Check

- Required query: `graphify query "PanelShell focus mode resize restoration visibility"`.
- Additional queries: `graphify query "Vitest Vite test exclude Playwright discovery"`; `graphify query "AgentChat data-tier data-desktop responsive zone state"`.
- Consulted nodes: `domain/PanelShell.tsx`, `AgentChat.tsx`, `AgentChat.test.tsx`, `Narrow Playwright Browser Contract`, `web/vite.config.ts`/Vitest package configuration, `api.ts`, `types.ts`, and `domain/AppShell.tsx`.
- Edges/paths: `domain/PanelShell.tsx --references--> AgentChat.tsx`; `AppShell.tsx → PanelShell.tsx → AgentChat.tsx`; `AgentChat.tsx → api.ts → InternalChatThread`; `command-center.spec.ts --implements--> Narrow Playwright Browser Contract`. Graphify found no directed path for the config-to-spec query and reported an ambiguous source match for the AgentChat/PanelShell path; these were recorded rather than inferred.

### Risks / Issues

- Existing React `act(...)` and jsdom navigation warnings remain non-failing.
- Browser harness logs expected `ECONNRESET` from the intentionally aborted WebSocket fixture; all 8 tests passed.
- No `ConversationsList` code was changed.

## Pre-existing Flake Fix

- **File:** `web/src/components/pages/ConversationsList.test.tsx`.
- **Root cause:** The search assertion used a fixed 350 ms sleep, which could expire before the debounced request and React render completed under CPU load.
- **Fix:** Replaced the sleep and immediate request assertion with `waitFor` around the exact `toHaveBeenLastCalledWith` query URL, then kept the empty-state assertion. The strict URL assertion remains intentional so the test still fails if `q=heater&limit=20&offset=0` is not sent.
- **Reason:** Required to make the change's full verification command deterministic without changing production code.
- **Graph check:** Consulted `ConversationsList.test.tsx` and `ConversationsList.tsx`; edge `ConversationsList.test.tsx --imports_from--> ConversationsList.tsx`.
- **Residual observation (out of scope):** with the CPU fully saturated (four busy loops) a different, unrelated pre-existing test — `src/components/domain/AppShell.test.tsx` ("renders live data pages for every navigation view") — failed once. It is untouched by this change and passes at moderate load (three runs with one busy loop: 540/540, exit 0) and in every unloaded run. Recorded here so it is not mistaken for a regression of this change.
