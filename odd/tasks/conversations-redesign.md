# ODD: conversations-redesign

## Objective

Bring the **Conversaciones** surface (queue list + conversation detail) back in line with the
current design system, and remove a regression the previous inspector unit left behind.

## Problem

The owner reported that this section never went through the redesign after the last
`DESIGN_SYSTEM.md` update, and flagged the detail page specifically: the thread background, a
missing top padding in the right inspector, and a title/subtitle pair that "does not follow the
logic we have been working with".

Investigation found five concrete, evidence-backed items — one of them a regression, not old debt.

## Why

- **The "Details" title is not ours.** `ConversationThread.tsx:47` and `:51` wrap the entire
  inspector in a stray `<details open>` with no `<summary>`. The user agent injects its own default
  summary label, which Chromium renders as the literal word "Details". Introduced by `6d6c70fb`
  ("fix(web): keep conversation actions reachable at every width"), part of the **PR #350** merge
  (`b181d5b2`) — the unit that was supposed to fix that very inspector. Explains both the foreign
  title and the missing top padding in the right column.
- **State action labels are abbreviated.** The UI renders `Tomar` / `Devolver` / `Cerrar`
  (`ConversationThread.tsx:88`, and `Tomar` again in `ConversationsList.tsx:91`) while
  `DESIGN_SYSTEM.md:377` names the required direct labels: `Tomar conversación`,
  `Cerrar conversación`, `Devolver al agente`, `Enviar respuesta`. The composer already complies
  with `Enviar respuesta`.
- **List rows are missing two required fields.** `DESIGN_SYSTEM.md:371` requires rows to show
  *customer, explicit conversation state, assignee, summary, freshness, and created date*. The row
  (`ConversationsList.tsx:76-93`) shows customer, state badge, summary and freshness —
  **assignee and created date are absent**, even though `Conversation.responsible_id` and
  `Conversation.created_at` already exist on the type (`types.ts:208,215`).
- **Card-like containers use the wrong radius.** `.conversations-queue__row`
  (`primitives.css:1875`) and `.conversation-workspace` (`primitives.css:1911`) use
  `var(--radius-md)` (8px). `DESIGN_SYSTEM.md:276-277` says *"Cards use `--radius-lg` (12px);
  dialogs and larger containers may use `--radius-xl` (16px)."*
- **The white background is NOT retired.** `DESIGN_SYSTEM.md:196-197` still assigns
  `--surface` (#FFFFFF) to *cards, tables, controls, dialogs*, and `.conversation-workspace` is a
  bordered rounded container — i.e. exactly that role. `DESIGN_SYSTEM.md:279` states *"Borders are
  the default separation mechanism"*, and the inspector already carries a `border-left`
  (`primitives.css:1697`). So the owner's premise needs measuring before any token is swapped: the
  likely real problem is that the workspace stretches to fill the content area at desktop width and
  therefore stops reading as a card. That is a layout/hierarchy decision, not a retired token.

## Scope

**Authorized (in scope):**

- `web/src/components/pages/ConversationsList.tsx` and `ConversationThread.tsx`
- the `conversations-queue__*` and `ai-agent-grammar__*` blocks in
  `web/src/components/primitives/primitives.css`
- their tests (`ConversationsList.test.tsx`, `ConversationThread.test.tsx`), plus a new CSS contract
  test if a declaration is the thing under test

**Explicitly out of scope:**

- **Renaming the section to "chatbot" + a WhatsApp icon — evaluated and rejected.** `DESIGN_SYSTEM.md:531`
  requires Lucide as the single outline icon family and `lucide-react` ships no brand marks; the
  sidebar already carries two names for the assistant view (`chat` is "Asistente Lumat" at
  `PanelShell.tsx:39` and "Agente Lumat" at `:441`), so a third AI-flavoured label would make the
  assistant indistinguishable from the customer queue. If the channel needs marking, the place is
  the conversation row, not the nav item.
- The `chat` nav label duplication itself (owner decision pending — not authorised here).
- The `.btn` global `min-height: 40px` gap, the suite flake, the parked 403 unit, and the text-zoom
  200% reflow unit (owned by another worktree).
- The `--radius-md` → `--radius-lg` question is **in scope**; changing the workspace height/rhythm
  is **not** (that belongs to the background decision).

## Constraints (verified facts, not preferences)

- **Strict TDD is ON** (`openspec/config.yaml:38`). Web runner: `cd web && npm test` (`vitest run`,
  `web/package.json:15`). RED before implementation, GREEN after, no invented evidence.
- Type check / build is the only static gate: `cd web && npm run build` (`tsc -b`). The repo has no
  linter and no formatter.
- **CI gates pytest only.** The ~732 web tests are local evidence; nothing in CI protects them.
- UI copy the operator reads is **Spanish**; code, identifiers, comments, tests and docs are
  **English**.
- No `Co-Authored-By`, conventional commits, merge commits (not squash).
- **CSS contract tests** read the stylesheet with `readFileSync` and assert declarations —
  precedent at `Dashboard.test.tsx:99-105` and `Button.test.tsx:65`. That is the house pattern.
- `jsdom` has no layout: a vitest test cannot prove visual spacing. Anything visual must be
  measured in Chromium.

## Tasks

| ID  | Task | Route |
| --- | --- | --- |
| **T1** | Remove the stray outer `<details>` in the inspector so no UA-generated summary exists; assert in a test that every `<details>` inside `.ai-agent-grammar__inspector` has its own `<summary>`. | delegated writer |
| **T2** | Use the direct state-action labels from `DESIGN_SYSTEM.md:377` (`Tomar conversación`, `Devolver al agente`, `Cerrar conversación`) in the detail header and in the queue row; update the tests that assert the old strings. | delegated writer |
| **T3** | Card radius: `.conversations-queue__row` and `.conversation-workspace` to `var(--radius-lg)`, with a CSS contract test. Confirm the mobile reset at `primitives.css:1942` stays intentional. | delegated writer |
| **T4** | List rows must show the assignee and the created date (`DESIGN_SYSTEM.md:371`), and a human-assigned row may take a warning-tinted leading treatment (`:371`). **Blocked on a decision:** `Conversation.responsible_id` is a bare id. The name-resolution precedent exists (`CasesList.tsx:26-29` `responsibleLabel(id, users)` → `username`, fed by its own `data.users`), but the conversations response carries **no** `users`, `AppShell.tsx:117` renders `ConversationsList` without even the existing `customerName` prop, and the only users endpoint (`api.ts:174` `fetchUsers`) is **admin-only** while the conversations view is open to every role. Decide the users source before rendering a name. | pending decision |
| **T5** | Background/hierarchy of the detail page: measure the workspace at desktop widths inside the real shell, then decide whether the thread area should sit on the canvas `--bg` while the inspector stays `--surface`. No token swap before the measurement. | pending measurement |

## Acceptance criteria

- No browser-injected label is visible anywhere in the inspector; the first visible inspector text is
  an intentional heading.
- Every state-action label matches `DESIGN_SYSTEM.md:377`.
- The queue row and the workspace use `--radius-lg`, proven by a CSS contract test.
- `cd web && npm test` green and `cd web && npm run build` clean at the end of each task.
- No `…conversación` label change makes a narrow-width action bar lose an action
  (`DESIGN_SYSTEM.md:327` never hides handoff/acknowledge/send/retry).

## Delivery

- Forecast: ~150–250 authored lines including tests — **under** the ~400 line budget, single PR.
- Strategy: `ask-on-risk`. If the running count passes ~400, stop and ask before the next commit.
- PR number goes into this doc as a docs-only commit **before** the merge.

## Checks

- `cd web && npm test`
- `cd web && npm run build`

## Route and delegation record

- T1–T3: **delegated writer** (`general`). Trigger: each task touches a non-trivial component plus
  its test, and reading that prepares the write is delegated with it.
- T4–T5: not started; both are blocked on a human decision, not on effort.

## Graph

Nodes consulted (`graphify query "Conversaciones list page and conversation detail surface…"`):
`ConversationsList()`, `ConversationThread()`, `.conversation-workspace`,
`.ai-agent-grammar__inspector` (`primitives.css`), `PageFrame()`, `StateMessage`, `PanelShell.tsx`,
`useAsyncData()`, plus the archived `panel-conversaciones-redesign` change and the
`unified-conversation-queue` spec.

## Progress

- [x] Unit opened; worktree `../lumat-agent-odd-conversations-redesign`, branch
      `odd/conversations-redesign`, base `66625430`.
- [x] **T1** — `d3e75dfc` *fix(web): drop the stray details wrapper from the conversation inspector*
- [x] **T2** — `8e07c9d6` *fix(web): use the direct state action labels in conversations*
- [x] **T3** — `237972a5` *fix(web): use the card radius on the conversation surfaces*
- [ ] T4 — blocked on the users-source decision
- [ ] T5 — blocked on measurement

## Verification evidence

Observed, not asserted. RED and GREEN below are the vitest summary lines as printed.

| Task | Test added/changed | RED | GREEN |
| --- | --- | --- | --- |
| T1 | `gives every inspector details element its own summary` (new) | `1 failed \| 737 passed (738)` | `738 passed (738)` |
| T2 | `refetches the thread after a successful close command`, `keeps conversation actions in the thread header and context actions-free`, `production conversations list`, `renders the interactive story action set` (labels updated in three files) | `4 failed \| 734 passed (738)` | `738 passed (738)` |
| T3 | `uses card radius for conversation cards and preserves the mobile workspace reset` (new) | `1 failed` | `739 passed (739)` |

- Final full suite, **re-run by the orchestrator as the parent spot check**, not taken from the
  writer's report: `Test Files 86 passed (86)` / `Tests 739 passed (739)`.
- `cd web && npm run build`: passed, `✓ built in 4.12s` (Vite chunk-size warning only).
- `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref 66625430 --committed-only --json`:
  `risk: "medium"`, `changed_lines: 184`, `changed_paths: 7`, **`review_due: false`,
  `review_due_reason: "under_budget"`**. The candidate stays pending inside the slice; no native
  review is due yet and none was started.
- RDD is **on** for this clone (decided by global), verified with `gentle-ai review mode status`.

**Not verified** (stated honestly, not claimed as done):

- Actual narrow-viewport browser layout after T2's longer labels. The CSS wraps on both action bars
  and the updated rendered-action tests pass, but no browser measurement was run — T5's measurement
  session must cover it.
- The visual spacing effect of removing the T1 wrapper. `jsdom` has no layout, so no vitest test can
  prove it; the fix is structural and correct by construction, but the rendered result is unmeasured.
- Known nit from review of the diff: the T1 test's `for (const details of …)` loop passes vacuously
  if the inspector ever renders zero `<details>`; the fixture supplies `captured_data`, so the inner
  disclosure is present today.

## Delivery

No PR yet. Three fix commits plus one docs commit sit on `odd/conversations-redesign`; nothing has
been pushed.
