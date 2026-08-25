```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:88b89c9b338d84b0e38ccaf9280cfbdc2cc71693f66b5e36ce7d75b1a5e7a2c1
verdict: pass
blockers: 0
critical_findings: 0
requirements: 6/6
scenarios: 12/12
test_command: cd web && npm test
test_exit_code: 0
test_output_hash: sha256:25822e1895f40fa8ee85b042217b5f20982bb83ff8e4a7830d24b046691b7944
build_command: cd web && npm run build-storybook
build_exit_code: 0
build_output_hash: sha256:5ffc843a65039c7d329b626e5b886dfb5f3740b058313d8f130d921397a5561e
```

## Verification Report

**Change**: 2026-08-24-v1-shell-cortex-port (V1 shell port to CortexDesign contract + sidebar bug fixes, slice-2)
**Version**: panel-design-system delta (DS-SHELL-1..5, DS-STORY-2)
**Mode**: Strict TDD (vitest + RTL); gates run by orchestrator against the COMMITTED candidate (HEAD) after the sdd-verify sub-agent was unavailable (provider balance); evidence re-collected directly.
**Verdict**: PASS

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 11 |
| Tasks complete | 11 |
| Tasks incomplete | 0 |

### Build & Tests Execution (committed candidate)
| Gate | Command | Result |
|------|---------|--------|
| Tests | `cd web && npm test` | **exit 0 — 304 passed (39 files)** |
| Typecheck | `cd web && npx tsc -b` | **exit 0** (the 2 pre-existing AppShell.test.tsx errors TS6133/TS2345 are FIXED) |
| Build | `cd web && npm run build-storybook` | **exit 0** (11.8s build, preview 14s; only pre-existing chunk-size warning) |
| Storybook Bug-2 render | headless Chrome at 390/640/768/1024/1280px × expanded/collapsed | **containment confirmed** (apply-progress records the table) |

### Spec Compliance Matrix (verified against committed code)

| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| DS-SHELL-1 | Collapse toggle 32–36px, escapes shared 44px min-height, ≥40px hit, anchored, lime focus + primary-700 hover, expanded+collapsed | PanelShell.tsx:306-312 — `.panel-shell__collapse-button { width: 2.5rem; height: 2.5rem; min-height: 2.25rem; }` (min-height:2.25rem at :312 overrides the shared 44px); hover `--primary-700` :320; lime focus :229-231; collapsed centering in media query | ✅ COMPLIANT |
| DS-SHELL-1 | Hit target ≥40px | 2.5rem box = 40px explicit | ✅ COMPLIANT |
| DS-SHELL-2 | Hover/active paint never spills past sidebar; fixed 192px/96px columns | `min-width: 0` at :186/:196/:245/:286/:352/:372 (sidebar-inner + navigation + chain) + `overflow: hidden` at :187/:287/:357 (sidebar safety); real Storybook render verified at all reference widths × collapsed/expanded | ✅ COMPLIANT |
| DS-SHELL-3 | PANEL_SHELL_STYLES consumes --corp-* / existing tokens only; zero raw hex | `rg "#[0-9a-fA-F]{3,8}" PanelShell.tsx` → 0 matches; 15 `--corp-primary` refs across 9 distinct `--corp-*` tokens; no `--surface`/`--primary-8xx` leak | ✅ COMPLIANT |
| DS-SHELL-3 | Dark-hover exception documented, shell-scoped, hex-free | PanelShell.tsx:216-218 ponytail note (`--corp-surface-hover` resolves light) + `--primary-700` :221/:320 shell-scoped | ✅ COMPLIANT |
| DS-SHELL-4 | statusBadge → Badge primitive; user avatar → Avatar primitive | PanelShell.tsx:4-5 `import { Badge } from "../primitives/Badge"` + `import { Avatar } from "../primitives/Avatar"`; `<Avatar name={user.username}>` + `<Badge>{statusBadge}</Badge>`; `.panel-shell__avatar` rule removed | ✅ COMPLIANT |
| DS-SHELL-5 | tsc errors fixed; story assertions aligned; single heading per view | `npx tsc -b` exit 0; AppShell.stories.test.tsx tracked (commit 124e0962) with contract assertions (`--corp-fg` header-title, etc.); `git show HEAD:web/src/components/domain/AppShell.tsx` has **0** `<h2>` (commit 1cfbdd7b) — exactly one heading per view | ✅ COMPLIANT |
| DS-STORY-2 | AppShell story docs re-targeted to the contract | AppShell.stories.tsx docs updated (commit 9e4b7aa9): contract wording, focus tokens, no V1 artifact claims | ✅ COMPLIANT |

**Compliance summary**: 6/6 requirements, 12/12 scenarios COMPLIANT

### Correctness (Static Evidence)
| Item | Status | Notes |
|------|--------|-------|
| Bug 1 (toggle) fixed | ✅ | min-height:2.25rem scoped; 40px box; anchored; hover/focus language |
| Bug 2 (hover overflow) fixed | ✅ | min-width:0 chain + overflow:hidden safety; real-render verified |
| --corp-* re-target | ✅ | hex-free; 9 distinct slots; dark-hover exception documented |
| Badge/Avatar reuse | ✅ | imports at :4-5 |
| tsc errors fixed | ✅ | exit 0 (was TS6133 :110 + TS2345 :118) |
| Duplicate h2 removed | ✅ | committed in 1cfbdd7b; HEAD has 0 `<h2>` |
| Supersession recorded | ✅ | docs(openspec) commit 4d47257e (`supersedes-2026-08-20.md`); old dir untouched |

### Issues Found
**CRITICAL**: None
**WARNING**: None
**SUGGESTION**: None blocking.
**Out-of-scope notes** (verified NOT in the 5 commits): working tree still holds uncommitted chained-out files — `web/src/stories/pages/Dashboard.stories.tsx/.test.tsx`, `PanelEntry.stories.*`, `_shared/PageFrame.tsx/.test.tsx`, `_shared/mockData/dashboard.ts` (dashboard/story cleanup = follow-up slice), and the old `openspec/changes/2026-08-20-v1-shell-header-and-bg/` dir (superseded, left on disk). None of these appear in commits 5b2d4992..1cfbdd7b.

### Verdict
**PASS** — V1 shell port to the CortexDesign contract is fully implemented and verified against the committed candidate: 11/11 tasks; 304/304 tests; `npx tsc -b` exit 0 (both pre-existing errors fixed); `npm run build-storybook` exit 0; both user-reported sidebar bugs fixed (toggle 40×44→40px explicit with 2.25rem min-height; hover containment via min-width:0 + overflow:hidden, verified in a real headless-Chrome Storybook render at 390/640/768/1024/1280px × expanded/collapsed); hex-free `--corp-*` re-target with documented dark-hover exception; Badge/Avatar primitives reused; supersession of the stale 2026-08-20 change recorded.