# ODD: clientes-memo-fusion

## Objective

Remove the redundant `Memo del cliente` card from the customer ficha and render the
`customer_memo` memory as a featured block at the top of the memories card, so the
same row stops being rendered twice on the operator's surface.

This is **slice B2** of the Clientes visual-refinement thread (Unit B). It follows
B1 (`clientes-surface-refinement`, PR #427, the ficha rail), which is delivered and
still carries its own PR. This slice is branched from `main`, not stacked on B1, by
the owner's explicit choice on 2026-09-29.

## Problem

Verified against base `e77da7d7`. B2 is a **deletion**, not a merge of distinct data.

### The memo and the memories list render the same row

- `web/src/components/pages/ClientFicha.tsx` renders `Card title="Memo del cliente"`
  with `<p>{data.memo || "Todavía no hay memo para este cliente."}</p>`.
- Immediately below, it renders `<ClientMemories memories={memories} …>`, whose
  `DataTable` lists every customer-scoped memory.
- `app/panel/api/routes/clients.py` builds `memo` with
  `memory_service.get_by_key(session, scope="customer", entity_id=str(customer_id),
  topic_key="customer_memo")`.
- The same route builds the memories list with
  `memory_service.list_for_entity(session, scope="customer", entity_id=…)`.
- `app/services/tukulpan.py`'s `list_for_entity` filters on `proyecto`, `scope`,
  `entity_id` and the owner filter — **there is no `topic_key` filter**. The
  `customer_memo` row is therefore already inside the list the memories card renders.

So the card is a single-row projection of a row that is already on screen.

### The duplication is currently asserted as correct behaviour

- `web/src/components/pages/ClientFicha.test.tsx` asserts
  `getAllByText("Prefiere contacto por la tarde.")).toHaveLength(2)` — the same
  content twice, because the ficha fixture carries `memo` and the memories fixture
  carries the identical `contenido`.
- `web/src/stories/pages/ClientFicha.stories.tsx` has to *derive* the duplicated
  value: `memo: memories.find((memory) => memory.topic_key === "customer_memo")
  ?.contenido ?? ""`. The story author is reconstructing `memo` from the memories
  list, which is the duplication stated as code.
- `web/src/stories/pages/ClientMemories.stories.test.tsx` asserts that **every**
  memory renders as a table row, and drives the pin/delete actions with
  `memories={[memories[0]]}` — and `memories[0]` **is** the `customer_memo` row
  (`web/src/stories/pages/_shared/mockData/memories.ts:14-18`).

### The remaining drift in the same file

`ClientMemories` renders the raw backend `tipo` in its Tipo column
(`<Badge tone={tipoTone(m.tipo)}>{m.tipo}</Badge>`) and carries a local `tipoTone`
helper. `web/src/components/shared/toneMaps.ts:72-73` already exports
`memoryTypeTone` and `memoryTypeLabel` — `memoryTypeLabel` maps `decision` →
`Decisión`, `preference` → `Preferencia`, `customer_memo` → `Memo del cliente` — and
**nothing consumes them**. The ficha's own invariant test asserts that the raw
identifier `customer_memo` must not appear on the surface, and today that test only
passes because the fixture happens to use `tipo: "preference"`.

## Scope

**In:** `web/src/components/domain/ClientMemories.tsx`,
`web/src/components/primitives/primitives.css` (a rule for the featured block only),
`web/src/components/pages/ClientFicha.tsx` (the memo card removal only),
`ClientFicha.test.tsx`, `web/src/stories/pages/ClientMemories.stories.tsx` (+ its
test), `web/src/stories/pages/ClientFicha.stories.tsx` (+ its test), and this
document.

**Out:** the backend and the panel API (including the now-unconsumed `memo`
projection — see *Deferred*); `app/panel/api/routes/clients.py`;
`app/services/tukulpan.py`; `web/src/types.ts`; `web/src/tokens/tokens.css`;
`ClientMemories`' relation-resolution block; the memo's storage, upsert, pin or
delete contract; B3 (`Historial` collapsible); B4 (the list's Cliente cell); the
four remaining `DataTable.actions` consumers; KPIs; any new dependency.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-memo-fusion`
- Branch: `odd/clientes-memo-fusion`
- Base: `e77da7d7` (= `origin/main` at branch time; not `af618303`, and not stacked
  on B1)
- Files: as listed under **In** above.

## Constraints

- `strict_tdd: true` (`openspec/config.yaml`): RED before GREEN for every
  behavioural change. The web runner is `cd web && npm run test` (Vitest).
- `DS-GRAMMAR-2`: styles live in the tokenized stylesheet boundary
  (`primitives.css`); no component-owned `<style>`, no inline `style={{}}`, no
  hard-coded colour.
- `Button.test.tsx` asserts `primitives.css` is hex-free. Every new rule must resolve
  through existing tokens.
- No new token and no new dependency. `UI/UX` tone for the memo already exists:
  `toneMaps.ts` declares `customer_memo` as `warning`.
- Reuse `Card`, `Badge`, `DataTable`, `Button`, `Textarea`, `.table__actions`,
  `.client-memories__section`, `memoryTypeTone`, `memoryTypeLabel`.
- `DESIGN_SYSTEM.md` authority order: OpenSpec requirements > `tokens.css` >
  `DESIGN_SYSTEM.md` > Storybook > the Jinja panel.
- Code and identifiers in English; user-facing copy in approved Chilean Spanish.
- Review freeze: any tracked byte changed after `review start` invalidates the
  receipt, this document included. Finalise it before review.

## Decisions

- **D1 — The memo is featured, not deleted.** The `customer_memo` row is rendered as
  a block above the memories table, so the information is preserved exactly while the
  duplicate card disappears. `DESIGN_SYSTEM.md:361-366` describes the ficha as
  "identity, consent, state control, notes, and history" — memo and memories are not
  even in that enumeration, so this regrouping is not a contract change.
- **D2 — Only one row is featured, and it is excluded by `id`.** The featured row is
  the first memory whose `topic_key === "customer_memo"` (memories arrive newest
  first). Only that row's `id` is filtered out of the table. If more than one row
  carries that topic key, the rest stay in the table: **the change must be lossless
  even if the topic key is not unique**, and that must hold by construction rather
  than by assuming an upsert contract.
- **D3 — The featured block keeps every action the row had.** The memo keeps its
  pin toggle (`Fijar` / `Quitar pin`) and its `Eliminar` action, wired to the same
  `onPin` / `onDelete` handlers. This is not optional: the existing tests drive the
  pin/delete contract through `memories[0]`, which is the memo row.
- **D4 — No empty placeholder replaces the card.** When no `customer_memo` row
  exists, the featured block is simply absent. The memories card already owns the
  empty state (`Sin memorias todavía`), so `Todavía no hay memo para este cliente.`
  is not re-added anywhere.
- **D5 — The memories card renders operator labels, not backend identifiers.** The
  local `tipoTone` and `statusTone` helpers in `ClientMemories` are deleted in favour of
  the exported `memoryTypeTone` / `memoryTypeLabel` and `memoryStatusTone` /
  `memoryStatusLabel` from `toneMaps.ts`, and both cells render the label. This deletes
  two duplicate helpers, consumes substrate that already existed and was unused (the
  `memoryType*` / `memoryStatus*` pair had **no consumer**), and stops the surface
  printing raw backend identifiers — which is what the ficha's own invariant test
  already forbids in spirit. The status column was not in the original plan; it is the
  same pattern in the same file with the same evidence, so leaving it raw would have
  been half the job. The featured block uses the same pair.
- **D6 — One action renderer, two call sites.** The pin/delete cell was inlined in the
  table's `actions` prop. It is now a single local `renderActions(memory)` used by both
  the featured block and the table, so the featured memo cannot drift from a row's
  actions while the two stay textually identical.
- **D7 — B3 and B4 stay in their own slices.** The `Historial` disclosure and the
  list's Cliente cell are untouched here so this review stays focused.

## Graph check (Step 1)

Graph rebuilt from `e77da7d7` (`graphify . --update`, then `graphify cluster-only .`
to regenerate `GRAPH_REPORT.md`) so it matches this slice's base exactly. Nodes and
edges consulted:

- `ClientMemories()` — `web/src/components/domain/ClientMemories.tsx:43`,
  community `ClientFicha.stories.tsx`; `statusTone()` — same file, `:24`;
  `ClientFicha.tsx`; `ClientMemories.stories.tsx` (+ its test); `memories.ts` and
  `memories.test.ts` mock data; `Customer` (`app/models.py:232`); `close_conversation()`
  (`app/services/tukulpan.py:845`); `test_mem11_close_conversation_judges_customer_memo()`.
- The graph places `ClientMemories`, its stories, its stories test and the memories
  mock data in one community, which is why the featured-block change and the mock
  data change are treated as one slice.
- Edges used: `ClientMemories` → `DataTable` / `Card` / `Badge` / `Button` /
  `Textarea`, and `ClientFicha` → `ClientMemories`.

## Tasks

- [x] **T1** — RED: `ClientMemories.stories.test.tsx` stops asserting that the memo is
  a table row and asserts the featured block instead — the memo content appears once,
  outside the table; the table holds the other memories only; the featured block keeps
  `Fijar`/`Quitar pin` and `Eliminar` wired to `onPin`/`onDelete`. Also nail the
  lossless case: with two rows sharing the `customer_memo` topic key, only the
  featured one leaves the table. Observed failing against the unmodified component.
- [x] **T2** — GREEN: feature the memo inside `ClientMemories` per D1–D3, and add the
  `.client-memories__memo` rule to `primitives.css` using existing tokens only.
- [x] **T3** — RED/GREEN: replace the local `tipoTone` with `memoryTypeTone` and
  render `memoryTypeLabel(m.tipo)` per D5. The raw identifiers stop appearing in the
  Tipo column, so the ficha's raw-identifier invariant becomes true for every memory
  type rather than by fixture accident.
- [x] **T4** — RED: `ClientFicha.test.tsx` asserts the `Memo del cliente` card is gone,
  that the memo text appears exactly **once**, and that the remaining card count and
  table count are updated. The `toHaveLength(2)` on the duplicated content becomes
  `toHaveLength(1)`. Observed failing against the unmodified ficha.
- [x] **T5** — GREEN: delete the memo card from `ClientFicha.tsx` and stop deriving
  `memo` in `ClientFicha.stories.tsx` (`ficha.memo` and the `ClientFichaView` memo
  prop are the duplication as code). Update `ClientFicha.stories.test.tsx` so the
  no-memo case asserts the absence of the duplicate instead of the removed sentence.
- [x] **T6** — verification of record: `cd web && npm run test`,
  `cd web && npx tsc -b --noEmit`, `cd web && npm run build`,
  `cd web && npm run build-storybook`, `git diff --check`.

## Acceptance criteria

1. No `Memo del cliente` card is rendered by the ficha.
2. The `customer_memo` content appears exactly once on the surface, as a featured
   block at the top of the memories card.
3. Every other memory still renders as a table row, and the total set of memories on
   screen is unchanged — no memory is lost when a topic key repeats.
4. The memo keeps its pin toggle and its delete action, wired to the same handlers.
5. When no `customer_memo` row exists, no empty memo placeholder appears.
6. The Tipo column renders operator labels, not raw backend identifiers, for every
   memory type, through `toneMaps.ts`.
7. No inline `style={{}}`, no component-owned `<style>`, no hard value, no new token
   and no new dependency; `tokens.css` is unchanged and `primitives.css` stays
   hex-free.
8. Only the authorized files change.
9. The short-circuit behaviours that already existed — the relation-resolution block,
   the add-memory textarea and its disabled state — keep passing unchanged.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook`
- `git diff --check`
- `git status --short`

## Progress

- [x] Created this ODD record in the unit worktree before the first source change.
- [x] Worktree created (`rapso worktree create clientes-memo-fusion --yes`, after
  explicit owner consent), branched from `main` at `e77da7d7` by the owner's choice.
- [x] Graph refreshed to the slice base (`e77da7d7`): 8574 nodes, 18491 edges, 720
  communities; `GRAPH_REPORT.md` regenerated.
- [x] B2 implementation Graphify check used the current `73063d63` graph; consulted
  `ClientMemories()`, `ClientFicha()`, `MEMORY_TYPE_LABELS`, `MEMORY_TYPE_TONES`,
  `DataTable`, `Card()`, `memoryTypeTone`, `memoryTypeLabel`, the related stories,
  tests, and `.client-memories__section`. Existing component dependencies remain
  `ClientMemories` → `DataTable` / `Card` / `Badge` / `Button`; `ClientFicha` →
  `ClientMemories`. No Graphify refresh was run during implementation.
- [x] **T1 RED** — focused Vitest run failed against the original component because
  the `customer_memo` content was found inside the table (`Tests 1 failed | 8
  passed`). **T2 GREEN** — featured memo, ID-only row exclusion, action preservation,
  and the tokenized `.client-memories__memo` style; the section count stays exactly
  two. Focused test passed (`9/9`).
- [x] **T3 RED/GREEN** — shared type-label assertion first failed because the featured
  badge rendered `customer_memo`; replacing `tipoTone` with `memoryTypeTone` and using
  `memoryTypeLabel` made the focused test pass (`10/10`).
- [x] **T4 RED/T5 GREEN** — ficha test first failed because the removed card heading
  was still present. Deleted the card and story derivation/prop; the fixture now
  supplies an actual `customer_memo` memory. Ficha test asserts exactly one memo text,
  no card, and three tables (the memo-only memory fixture leaves no table rows, so
  `DataTable` renders its empty surface rather than a table); Storybook tests retain
  the empty memories assertion and reject the removed placeholder. Focused ficha and
  story tests passed (`48/48`).
- [x] **T6** — implementation-side verification passed: `npx tsc -b --noEmit`,
  `npm run build`, `npm run build-storybook`, `git diff --check`, and a canonical
  `npm run test` run of 90 files / 854 tests. The Vite and Storybook builds retain the
  existing >500 kB chunk warning.
- [x] **Parent verification, after the writer's report.** Two canonical `npm run test`
  runs on this same candidate flaked under host load — `load average` **20.75 on 8
  CPUs** — and the failures **moved between runs**: run 1 timed out four tests across
  `AgendaPage.test.tsx`, `AgendaPage.stories.test.tsx` and `AppShell.test.tsx`
  (`Test timed out in 5000ms`); run 2 failed a single unrelated async assertion in
  `AgentChat.test.tsx`. Every file that failed passed on the other run, none of them is
  touched by this slice, and all three timed-out files pass in isolation on this
  candidate (**78/78**, 32s). A controlled run with bounded parallelism —
  `npm run test -- --maxWorkers=2` — is green: **90 files, 854 tests passed, exit 0**.
  With two sibling sessions live, the contention is pre-existing and not attributable
  to this candidate; it is recorded as a follow-up, not fixed here.
- [x] Phantom-token check re-run by the parent on the final candidate: prints `[]`.

## Size

Final B2 web diff from `e77da7d7`: **88 insertions, 58 deletions** across seven files
(146 changed lines), inside the ~400 review-focus budget. The ODD record is a separate
final documentation commit.

## Deferred and follow-ups

- **The API keeps a projection nothing consumes.** After this slice nothing reads
  `ClientFichaResponse.memo`, and `to_ficha` still runs one
  `memory_service.get_by_key(…)` query per ficha load to build it. Removing the field
  and that query is a backend change with its own verification (the backend suite), so
  it is deliberately not in this web slice. Evidence: `data.memo` had exactly one
  consumer, `ClientFicha.tsx`'s deleted card.
- **B3 — `Historial` collapsible.** Untouched here.
- **B4 — the list's Cliente resource cell.** Untouched here.
- **The four remaining `DataTable.actions` consumers**, one slice each:
  `ClientMemories.tsx`, `UserManagement.tsx`, `AgendaPage.tsx`,
  `PlanningSessions.tsx`. Note `ClientMemories` still renders `Fijar`/`Eliminar` as
  `variant="secondary"` buttons in `.table__actions`; B1 only introduced the menu
  idiom, it did not convert this consumer.
- **The web suite flakes under host contention.** Two canonical `npm run test` runs
  under `load average` ~20 on 8 CPUs failed timing-sensitive tests in files this slice
  does not touch, and the failing files differed between runs. `vitest` runs with its
  default 5000 ms per-test timeout and no bounded worker pool (`web/vite.config.ts`
  sets no `testTimeout` or `maxWorkers`), so a loaded host can starve the heavier React
  tests. Not fixed here: it is pre-existing test-infrastructure behaviour, outside this
  slice's scope and files. The durable fixes would be a bounded pool or a raised
  timeout in the shared vitest config, and both deserve their own slice.
- **B1 is not merged.** `ClientFicha.tsx` is touched by both slices in different
  regions, so before the second of the two merges the repository's own pre-merge
  integration check over the merged tree applies.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-memo-fusion`,
  branch `odd/clientes-memo-fusion`, base `e77da7d7`.
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing.
- Sibling slices: B1 `odd/tasks/clientes-surface-refinement.md` (PR #427). This slice
  is intentionally **not** stacked on it.
