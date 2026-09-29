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
- **D5 — The Tipo column uses the shared labels that already exist.** The local
  `tipoTone` helper in `ClientMemories` is replaced by the exported
  `memoryTypeTone`, and the cell renders `memoryTypeLabel(m.tipo)`. This deletes a
  duplicate helper, consumes substrate that already exists and was unused, and stops
  the surface printing raw backend identifiers — which is what the ficha's own
  invariant test already forbids in spirit.
- **D6 — B3 and B4 stay in their own slices.** The `Historial` disclosure and the
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

- [ ] **T1** — RED: `ClientMemories.stories.test.tsx` stops asserting that the memo is
  a table row and asserts the featured block instead — the memo content appears once,
  outside the table; the table holds the other memories only; the featured block keeps
  `Fijar`/`Quitar pin` and `Eliminar` wired to `onPin`/`onDelete`. Also nail the
  lossless case: with two rows sharing the `customer_memo` topic key, only the
  featured one leaves the table. Observed failing against the unmodified component.
- [ ] **T2** — GREEN: feature the memo inside `ClientMemories` per D1–D3, and add the
  `.client-memories__memo` rule to `primitives.css` using existing tokens only.
- [ ] **T3** — RED/GREEN: replace the local `tipoTone` with `memoryTypeTone` and
  render `memoryTypeLabel(m.tipo)` per D5. The raw identifiers stop appearing in the
  Tipo column, so the ficha's raw-identifier invariant becomes true for every memory
  type rather than by fixture accident.
- [ ] **T4** — RED: `ClientFicha.test.tsx` asserts the `Memo del cliente` card is gone,
  that the memo text appears exactly **once**, and that the remaining card count and
  table count are updated. The `toHaveLength(2)` on the duplicated content becomes
  `toHaveLength(1)`. Observed failing against the unmodified ficha.
- [ ] **T5** — GREEN: delete the memo card from `ClientFicha.tsx` and stop deriving
  `memo` in `ClientFicha.stories.tsx` (`ficha.memo` and the `ClientFichaView` memo
  prop are the duplication as code). Update `ClientFicha.stories.test.tsx` so the
  no-memo case asserts the absence of the duplicate instead of the removed sentence.
- [ ] **T6** — verification of record: `cd web && npm run test`,
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

## Size

Forecast for B2 under `web/`: `ClientMemories.tsx` +~30, `primitives.css` +~8,
`ClientFicha.tsx` −~5, the two component/story test files +~60, the stories files
−~10 — roughly **110–140 changed lines**, inside the ~400 review-focus budget. The
running count from work-unit commits is recorded as the slice lands.

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
