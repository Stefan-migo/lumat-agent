# Archive Report — Panel Real Design — Page-First Storybook Workflow (LumatAgent)

> Change: `2026-08-19-panel-real-design` · Project: LumatAgent (client: Lumat, gasfitería, Chile)
> Phase: sdd-archive · Date: 2026-08-19 · Status: **ARCHIVED** — complete
> Artifact store: openspec (file-based) + Engram secondary. This report is the terminal record of the SDD cycle for this change.

## Summary

The `panel-real-design` change is fully implemented, verified, and archived. It recreated all 9 panel pages (Dashboard, ClientesList, ClientFicha, ConversationThread, CasesList, ConversationsList, KbList, Settings, Login) as Storybook page stories under `web/src/stories/pages/`, composed from the archived `panel-design-system` primitives plus story-local helpers and typed mocks. Storybook-only additive delta: zero new CSS, zero production changes, `web/src/components/**` and `.storybook/main.ts` untouched (R-PRD-PG-1 guard). All 9 pages are in the built index.

The spec delta `panel-design-system` (R-PRD-PG-1..7) was synced into the canonical spec store. The change folder was moved to the archive per the OpenSpec archive convention.

## Deliverables (final state — what shipped)

Delivered as 10 chained PRs, stacked to main, per the auto-chain strategy (5 batches split at PR creation to keep every PR ≤400 changed lines):

| Batch | PR(s) | Commits | Content |
|---|---|---|---|
| B1 shared infra | #20 | `e73e6284` | `_shared/` helpers (DataTable, PageHeader, StatCard, EmptyState, FlashMessage), `toneMaps` + RED→GREEN coverage test, `mockData/dashboard.ts` |
| B2 Dashboard + ClientesList | #21 | `2669553a`, `81c3a4a8`, `02bafc19` | `mockData/clients.ts` (4 states), `pages/Dashboard`, `pages/ClientesList` (+ tests) |
| B3a mocks + thread | #22 | `0d00cf93`, `1fcd62e2` | `mockData/conversations.ts` + messages, `pages/ConversationThread` (+ bubble variant) |
| B3b ficha | #23 | `74628159` | `pages/ClientFicha` (customer card + state form + notes + 3 history tables) |
| B4a cases mock | #24 | `1e055d4d` | `mockData/cases.ts` (4 statuses, emergency EM-4, users) |
| B4b CasesList | #25 | `de9ef19c` | `pages/CasesList` (tone-wired badges, inline update/ack) |
| B4c ConversationsList | #26 | `e0beeb3e` | `pages/ConversationsList` (design D5; flags GET /conversations backend gap) |
| B5a kb+settings mocks | #27 | `9e0455e5` | `mockData/kb.ts` + `mockData/settings.ts` |
| B5b KbList | #28 | `f84be99b` | `pages/KbList` (add-doc card, native `<details>` edit, disable/restore) |
| B5c Settings + Login | #29 | `0082c461`, `4e97f063` | `pages/Settings` (6 form cards + spend snapshot), `pages/Login` (auth card + error) |

Main at close: `7313d8c4`. All batch slices passed a bounded RDD review (10 approved lineages; see Final-State RDD below).

## Verification Outcome

**Final state: PASS.** The verify report (`verify-report.md`, verdict `passed`) recorded at HEAD `7313d8c4`:

- **7/7 requirements**, **15/15 scenarios** passed.
- `cd web && npm test` → **31 files / 169 tests passed**.
- `cd web && npx tsc -b` → **exit 0**.
- `cd web && npm run build-storybook` → **green**, all 9 `pages/*` stories in built index.
- Diff review (`git diff --name-only 5d5c6103..HEAD`): web/-only; zero CSS; no `web/src/components/**`; no `.storybook/main.ts`.

## Final-State RDD (bounded review receipts)

All 10 batch slices were reviewed with the native review facade (medium risk → one reliability lens each) and APPROVED. Two slices required corrections within budget:

| Slice | Lineage | Outcome | Correction |
|---|---|---|---|
| B1 | `review-6c34ef49d0bde271` | approved (1 correction) | 3 CRITICAL fixed: toneMaps `?? "neutral"`, DataTable empty-state always renders, `rowKey` prop |
| B2 | `review-f294aac0e9420a31` | approved (1 correction) | 1 CRITICAL (R3-001) fixed: Dashboard Motivos assertions scoped per row (exact match) |
| B3a | `review-aba1068bcce25296` | approved (clean) | — |
| B3b | `review-cea6f048b90ab0b7` | approved (clean) | — |
| B4a | `review-ce95d0769d5c1d64` | approved (clean) | — |
| B4b | `review-ec37323d0d5b1da2` | approved (clean) | — |
| B4c | `review-809817442bd0d531` | approved (clean) | — |
| B5a | `review-e3b483a73561b0ed` | approved (clean) | — |
| B5b | `review-bf7c789d5f02bb54` | approved (clean) | 3 advisory findings (2 WARNING + 1 SUGGESTION, informational) |
| B5c | `review-2bded03c199c042e` | approved (clean) | — |

Delivery gates (pre-commit / pre-pr) returned ALLOW for every slice.

## Graphify Refresh (archive gate)

`graphify . --update` ran at close. The knowledge graph grew from **2117 → 2269 nodes** (pre-change graph built from `5d5c6103`). The web/ area now includes the 9 page-story nodes, the `_shared/` helpers, and the typed mocks. Community structure re-balanced for the Storybook/pages cluster (see `graphify-out/GRAPH_REPORT.md`). If the semantic backend (OpenAI key) is unavailable, structural AST extraction still completes; the semantic refresh outcome is recorded in the graph manifest.

## Risks / Follow-ups (accepted at close)

- **High (advisory): GET /conversations backend list endpoint does not exist.** Only the thread GET is live. `ConversationsList` is designed from `Customer`/`Conversation` shapes (design D5) and the gap is flagged in the story docs + apply notes. Needs a future backend endpoint for production wiring.
- **SUGGESTION**: tone-map test enumerates status/state literals inline rather than importing the union from `types.ts`; matches today, but importing the union would eliminate future drift.
- Advisory WARNINGs from B5b review (KbList) are informational and non-blocking.

## Final State Facts

- 9 page stories in built Storybook index: Dashboard, ClientesList, ClientFicha, ConversationThread, CasesList, ConversationsList, KbList, Settings, Login
- 5 story-local helpers under `web/src/stories/pages/_shared/`: DataTable, PageHeader, StatCard, EmptyState, FlashMessage
- 6 typed mocks: dashboard, clients, conversations, cases, kb, settings (+ toneMaps)
- 169 vitest tests green; typecheck clean; Storybook build green
- 10 chained PRs (#20–#29) merged to main; main @ `7313d8c4`
- Spec delta R-PRD-PG-1..7 synced into `openspec/specs/panel-design-system/spec.md`
- Change folder moved to `openspec/changes/archive/2026-08-19-panel-real-design/`
