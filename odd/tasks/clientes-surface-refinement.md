# ODD: clientes-surface-refinement

## Objective

Refine the Clientes surface — the ficha (`/panel/app/clients#`) and the list
(`/panel/app/clients`) — so an operator can actually read it.

This is **Unit B** of the Clientes visual-refinement thread the owner opened on
2026-09-29. It follows Unit A (`panel-action-affordances`, PR #423, merge
`af618303`), which is delivered and closed: Unit A owns the row-action pattern and
is **not** reopened here.

This record covers Unit B as a whole but implements **slice B1 (the ficha rail)**
only. B2–B4 and the remaining action columns are tracked under *Deferred and
follow-ups* and land in their own slices, one PR each.

## Problem

Verified against base `af618303`. Every claim below was re-checked against that
exact checkout.

### The ficha's identity card is a wall of identical outline buttons

`web/src/components/pages/ClientFicha.tsx:345-366` renders `Card title="Identidad"`
holding **four** `variant="secondary"` buttons and **zero `primary`**:

- `:348` `Editar identidad`
- `:349` `Cambiar consentimiento`
- `:350` `Archivar` / `Restaurar`
- `:351` `Fusionar con otro cliente`

Two distinct defects live here:

- **No hierarchy.** `web/DESIGN_SYSTEM.md:441` states "`primary`: one per local
  action group". Four identical secondary buttons satisfy neither that rule nor the
  operator's eye.
- **The destructive actions have nowhere else to go.** `web/DESIGN_SYSTEM.md:444`
  documents a `danger` variant for "destructive or irreversible action, introduced
  with confirmation behavior", but `web/src/components/primitives/Button.tsx:7`
  implements only `primary | secondary | tertiary`. `Archivar` and `Fusionar`
  therefore fall to `secondary` because nothing else exists. Unit A recorded this
  drift as its D6 and deliberately deferred it.

The secondary button's own shape is why the row reads as a pill outline wall:
`primitives.css:30` gives `.btn` `--radius-pill`, and `primitives.css:45-52` gives
`.btn--secondary` an elevated background plus a `--border-strong` border.

### The rail carries two cards where one grouping is authorised

The two-region shell already exists and works — `detail-region` /
`detail-region__rail` / `detail-region__main` (`primitives.css:352-444`), rail sticky
above the 1024px breakpoint. Inside that rail the ficha renders two cards:
`Identidad` (`:345`) and `Estado` (`:397`, whose state control is a `Select` plus a
`Guardar estado` `primary` button).

`DESIGN_SYSTEM.md:361-366` describes the ficha as "identity, consent, state control,
notes, and history" — one grouping, not two cards. `clientes-product-register` D10
placed identity **and** the state control in the rail; it did not mandate two
separate cards.

### Confirmation dialogs use `primary` for destructive confirms

- `:383` — the archive dialog's `Confirmar archivo` button renders with the default
  `primary` variant.
- `:394` — the merge dialog's `Confirmar fusión` button renders with the default
  `primary` variant.

Both are destructive or irreversible actions that already carry confirmation
behavior, which is exactly `DESIGN_SYSTEM.md:444`'s definition of `danger`. Today
they look like the safest action on the surface.

## Scope

**In:** `web/src/components/primitives/Button.tsx`, `Button.test.tsx`,
`web/src/components/primitives/primitives.css` (the `.btn--danger` rule only),
`web/src/components/pages/ClientFicha.tsx`, `ClientFicha.test.tsx`,
`web/src/stories/pages/ClientFicha.stories.tsx` (+ its test) and
`web/src/stories/primitives/Button.stories.tsx` when their assertions depend on the
changed markup, and this document.

**Out:** the `Memo del cliente` fusion (B2); the `Historial` disclosure (B3); the
list's Cliente resource cell (B4); the four remaining `DataTable.actions` consumers
(`ClientMemories`, `UserManagement`, `AgendaPage`, `PlanningSessions`); client KPIs;
`web/src/tokens/tokens.css` values; the backend and the panel API; `DataTable`
itself; the `Mensajes`/history tables; any new dependency; any conversion of dense
data presentation away from tables.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-surface-refinement`
- Branch: `odd/clientes-surface-refinement`
- Base: `af618303` (= `main` at branch time)
- Files: as listed under **In** above.

## Constraints

- `strict_tdd: true` (`openspec/config.yaml`): RED before GREEN for every
  behavioural change. The web runner is `cd web && npm run test` (Vitest).
- `DS-GRAMMAR-2`: styles live in the tokenized stylesheet boundary
  (`primitives.css`); no component-owned `<style>`, no inline `style={{}}`, no
  hard-coded colour.
- `Button.test.tsx` asserts `primitives.css` is hex-free. Every new rule must resolve
  through existing tokens.
- No new token unless a repeated semantic role has a real consumer. `--danger`
  (`#b71c1c`) already exists and is the intended role.
- Reuse what already exists: `Button`, `Menu` (with `trigger="icon"` and
  `MenuItem.tone="danger"`), `Avatar` (initials fallback), `Card`, `Badge`, `Select`,
  `Icon`, `EmptyState`, `StateMessage`, `detail-region`, and
  `customerStateLabel` / `customerStateTone` from `shared/toneMaps.ts`.
- State vocabulary stays the eight real `customer_state` values with their approved
  Spanish labels. Do not invent states.
- Code and identifiers in English; user-facing copy in approved Chilean Spanish.
- Review freeze: any tracked byte changed after `review start` invalidates the
  receipt, this document included. Finalise it before review.

## Decisions

- **D1 — `Button variant="danger"` lands here, with real consumers.** Its first
  consumers are the two destructive confirmation buttons already on the ficha: the
  archive dialog's `Confirmar archivo` (`:383`) and the merge dialog's
  `Confirmar fusión` (`:394`). This closes the drift Unit A recorded as D6. Note the
  refinement: the handoff anticipated the rail's `Archivar`/`Fusionar` becoming
  standalone destructive buttons, but the accepted IA routes those into a `Menu` with
  `tone="danger"`, so the standalone destructive control that actually exists — and
  that matches `DESIGN_SYSTEM.md:444`'s "introduced with confirmation behavior" — is
  the dialog confirm. No variant is added without a consumer.
- **D2 — The rail collapses to one `Cliente` card.** `Identidad` and `Estado` merge
  into a single card carrying the avatar/initials, the name, the state badge, the
  labelled facts, the state `Select` and its `Guardar estado` control, and one action
  group. No new layout primitive; the existing `detail-region` shell is reused as-is.
- **D3 — One visible primary action plus one `...` menu.** `Editar identidad` keeps a
  visible control and becomes the action group's single `primary`
  (`DESIGN_SYSTEM.md:441`). `Cambiar consentimiento`, `Fusionar con otro cliente`, and
  `Archivar`/`Restaurar` move into an icon-triggered `Menu` whose accessible name
  identifies the customer; the two destructive items carry `tone="danger"`. This is
  the same pattern Unit A established for table rows, so the surface gains one action
  idiom, not two.
- **D4 — The state control's save stays `primary`; the state `Select` is inline.**
  The rail already owned the state control (D10 of `clientes-product-register`); this
  slice changes its container, not its behaviour. Two `primary` controls in one card
  would break D3's single-primary rule, so the grouping is explicit: `Editar
  identidad` is the card's action-group primary, and the state group keeps its own
  local action group with its own primary, per `DESIGN_SYSTEM.md:441`'s "per local
  action group" wording.
- **D5 — No new token, no new dependency.** `.btn--danger` resolves through the
  existing `--danger` role and the shared `.btn` base. `primitives.css` stays
  hex-free.
- **D6 — B2–B4 are deferred to their own slices.** The memo duplication, the
  `Historial` disclosure, and the list's Cliente cell are each their own PR so no
  single review exceeds the ~400-line focus budget.

## Graph check (Step 1)

Graph built from commit `af618303` (matches base; not stale). Nodes and edges
consulted before writing:

- `ClientFicha()` — `web/src/components/pages/ClientFicha.tsx:77`, community
  `ClientFicha.tsx`; `Card()` — `primitives/Card.tsx:10`; `Button()` —
  `primitives/Button.tsx:19`, community `TechnicianAgenda.tsx`; `Avatar()` —
  `primitives/Avatar.tsx:17`; `StateMessage()` — `shared/StateMessage.tsx:19`;
  `domain/ClientMemories.tsx`; `shared/toneMaps.ts`; `ClientFicha.test.tsx`;
  `ClientFicha.stories.tsx` (+ its test); `ClientesList.tsx` (same community as the
  ficha); `PanelEntry.stories.tsx` (`Rail1024`).
- Edge used: `ClientFicha` → `ClientMemories` / `shared/toneMaps` / `api.ts`.
  `graphify path Button.tsx ClientFicha.tsx` reports no directed path — `Button` is
  consumed by `ClientFicha` only through the community that groups them, so the
  variant union change was checked against its full consumer set by reading the
  primitive's contract rather than trusting an edge.

## Tasks

- [ ] **T1** — RED: `Button.test.tsx` covers `variant="danger"` — it renders the
  `btn--danger` class, it stays operable and disabled-state correct, and the existing
  hex-free assertion over `primitives.css` still holds. Observed failing against the
  unmodified `Button`.
- [ ] **T2** — GREEN: add `"danger"` to the `Button` variant union and the
  `.btn--danger` rule to `primitives.css`, resolving only through the existing
  `--danger` role.
- [ ] **T3** — RED: `ClientFicha.test.tsx` covers the collapsed rail — there is one
  `Cliente` card and no separate `Identidad` / `Estado` cards; the avatar/initials,
  name and state badge render; the facts are present; the state control and its save
  still work; there is exactly one visible `primary` action plus one menu trigger
  whose accessible name identifies the customer; no visible action label repeats the
  customer name; the menu carries `Cambiar consentimiento`, `Fusionar con otro
  cliente` and `Archivar`/`Restaurar` as a `danger`-toned item when applicable; and
  each item still calls the same handler as before.
- [ ] **T4** — GREEN: rewrite the rail in `ClientFicha.tsx` per D2/D3/D4, and switch
  the archive and merge dialog confirms to `variant="danger"` per D1. Every existing
  handler, guard and `LocalFeedback` surface is preserved.
- [ ] **T5** — stories: update `ClientFicha.stories.test.tsx` assertions for the new
  rail and add the `danger` variant to `Button.stories.tsx` if its coverage needs it.
  Viewport presets stay global.
- [ ] **T6** — verification of record: `cd web && npm run test`,
  `cd web && npx tsc -b --noEmit`, `cd web && npm run build`,
  `cd web && npm run build-storybook`, `git diff --check`.

## Acceptance criteria

1. The ficha rail renders exactly one `Cliente` card; no `Identidad` or `Estado`
   card remains.
2. The rail's action group has exactly one visible `primary` action; every other
   action is reachable from a single menu trigger whose accessible name identifies
   the customer.
3. No visible action label repeats the customer name.
4. `Archivar`/`Restaurar` and `Fusionar` are distinguishable from neutral actions
   without relying on colour alone, and each still opens the same confirmation.
5. `Button variant="danger"` exists and is used by the archive and merge dialog
   confirm buttons; no variant is added without a consumer.
6. The state control, its save action, and every `LocalFeedback` surface behave
   exactly as before.
7. No inline `style={{}}`, no component-owned `<style>`, no hard value and no new
   token is introduced; `tokens.css` is unchanged and `primitives.css` stays
   hex-free.
8. Only the authorized files change.
9. Every existing `ClientFicha` test that is not about the replaced markup keeps
   passing unchanged.

## Checks

- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- `cd web && npm run build-storybook`
- `git diff --check`
- `git status --short`

## Progress

- [x] Created this ODD record in the unit worktree before the first source change.
- [x] Worktree created (`rapso worktree create clientes-surface-refinement
  --yes`, after explicit owner consent).

## Size

Forecast for slice B1 under `web/`: `Button.tsx` (+1), `Button.test.tsx` (+~25),
`primitives.css` (+~5), `ClientFicha.tsx` (~+30/-15), `ClientFicha.test.tsx` (+~90),
stories (+~15) — roughly **180–200 changed lines**, inside the ~400 review-focus
budget. Running count from work-unit commits is recorded as slices land.

## Deferred and follow-ups

- **B2 — memo fused into memories.** Delete the `Memo del cliente` card
  (`ClientFicha.tsx:445-447`) and present the `customer_memo` entry as a featured
  block inside `ClientMemories`. Verified as a **deletion, not a merge of distinct
  data**: `app/panel/api/routes/clients.py:478` builds the memories list from
  `list_for_entity(scope="customer", entity_id=customer_id)`, and
  `app/services/tukulpan.py`'s `list_for_entity` filters only on `proyecto`, `scope`
  and `entity_id` — no `topic_key` filter — so the `customer_memo` row that
  `clients.py:275` projects separately already appears in that list.
- **B3 — `Historial` collapsible.** Reuse the existing disclosure pattern over the
  four sub-regions; do not rebuild them.
- **B4 — the list's Cliente resource cell.** Avatar/initials plus semibold name with
  the phone in muted text, then drop the separate `Teléfono` column. Keep
  `.table__link` semantics: `DESIGN_SYSTEM.md:364` makes the customer name the
  drill-down link, so it is presented as a resource, not removed.
- **The four remaining `DataTable.actions` consumers**, one slice each:
  `ClientMemories.tsx:78`, `UserManagement.tsx:87`, `AgendaPage.tsx:239-250`,
  `PlanningSessions.tsx:70`. Extract `RowActions` from `Menu` when the second one
  lands.
- **Client KPIs** stay separate: they need a spec delta plus an aggregate endpoint,
  because `GET /panel/api/clients` is capped at 100 rows and `to_customer_dict`
  exposes only customer columns.

## Recovery

- Worktree: `/home/stefan/repos/lumat-agent-odd-clientes-surface-refinement`,
  branch `odd/clientes-surface-refinement`, base `af618303`.
- On resume: read this file and reconcile the checkbox state against `git log`
  before continuing.
- Predecessor unit: `odd/tasks/panel-action-affordances.md` (PR #423, merge
  `af618303`). Do not rebuild it.
