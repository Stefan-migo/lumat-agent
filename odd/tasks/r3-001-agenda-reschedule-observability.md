# ODD — r3-001-agenda-reschedule-observability

## Objective

Give the reschedule flow a failure path: when the technician lookup rejects, tell the operator why
the technician select is empty instead of silently offering an unusable dialog.

## Problem — verified in `main`

`web/src/components/pages/AgendaPage.tsx:240` — the row action that opens the reschedule dialog:

```tsx
void fetchTechnicians().then((response) => setTechnicians(response.technicians));
```

There is no rejection handler. If `GET /panel/api/technicians` fails (network, `500`, `403`), the
promise rejects unhandled, the `Select` keeps only its placeholder, and the operator sees no
explanation. Submitting then fails at `:126` with `"Completa todos los campos de la reprogramación"`,
which names a symptom and hides the cause.

The create flow already does this correctly and is the pattern to mirror (`openCreate`, `:155-167`):

```tsx
try { ... } catch (error) {
  setCreateFeedback({ tone: "danger", title: "No pudimos cargar las opciones de la visita", detail: ... });
}
```

The reschedule dialog already owns the feedback slot: state `rescheduleFeedback` (`:57`) rendered as
`<StateMessage tone="danger" role="alert">` at `:299`. The fix only needs to write to it.

**Honest framing.** The missing rejection handler was **not** introduced by PR #430. The original
code was `void fetchUsers().then(...)`, with the exact same gap; PR #430 swapped the function and
preserved the shape. This is a pre-existing defect the change touched. It is not a regression.

## Provenance

Non-blocking advisory from the native review of PR #430, lineage `review-9c8ba34af6ec1f0e`. The
review contract treats advisories as follow-up work, never as grounds to re-run that candidate's
review — hence a separate unit. Prior unit record: `odd/tasks/agenda-technician-picker.md` (PR #430,
`e5964680`).

## Scope

**In**

- `web/src/components/pages/AgendaPage.tsx` — rejection handler on the reschedule technician lookup.
- `web/src/components/pages/AgendaPage.test.tsx` — a test asserting the operator receives the danger
  feedback when `fetchTechnicians` rejects during reschedule. Current coverage is success-only
  (`:226`, `:230`, `:241`).
- This record, and `web/src/stories/pages/AgendaPage.stories.test.tsx` only if its mock needs it.

**Out (deliberate)**

- The `/panel/api/technicians` endpoint and its backend test — already delivered in PR #430.
- The create flow — already correct.
- L8, the pre-existing web-suite flake under parallel load (documented observation, not fixed here).
- F3 — `scheduling.py` content in English (audit-only, unrelated).
- The validation message at `:126`. It stays as-is: this unit fixes the cause's visibility, not the
  symptom's wording.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-r3-001-agenda-reschedule-observability`
- Branch: `odd/r3-001-agenda-reschedule-observability`
- Base: `c0c78ebe` (`main`, re-measured 2026-09-29 — unchanged from the handoff)
- Files:
  - `odd/tasks/r3-001-agenda-reschedule-observability.md`
  - `web/src/components/pages/AgendaPage.tsx`
  - `web/src/components/pages/AgendaPage.test.tsx`
  - `web/src/stories/pages/AgendaPage.stories.test.tsx` (only if its mock requires it)

Any file outside this list needs a scope update here first.

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). This is a web-only
  change, so the cycle runs in Vitest: observe RED before the handler, then GREEN. Never invent RED
  evidence.
- No linter, no type checker, no formatter. The only type check is `cd web && npm run build`
  (`tsc -b`).
- **L8**: the full web suite flakes under parallel load — two consecutive PR #430 runs failed on two
  different, unrelated tests. Run it with `--testTimeout=20000` for a trustworthy result.
- **D6 language:** code, identifiers, comments, tests and this record in English. Operator-facing
  panel copy stays Spanish, as `AgendaPage` strings already are.
- Work-unit commits are authorized, one concern per commit, tests and docs travel with their code.
  No `Co-Authored-By`. **Push, PR and merge are separate decisions.**
- Ponytail: the smallest diff that fixes the defect. One rejection handler, one test. No extracted
  handler, no shared helper, no new state.

## Graph Check (rapso-persona Step 1)

Query: `graphify query "agenda reschedule technician picker"` — BFS depth 2, 335 nodes reached
(truncated at the 2000-token budget, 61 shown).

Nodes consulted: `reschedule()` (`app/services/scheduling.py:334`, backend of the flow — out of
scope), `AgendaPage.tsx` community (`shared/agendaTime.ts`, `shared/StateMessage.tsx`,
`shared/PageFrame.tsx`, `primitives/Button.tsx`, `primitives/Badge.tsx`), `api.ts`, `types.ts`
(`fetchTechnicians` origin), `useAsyncData()` (`web/src/hooks/useAsyncData.ts` — its own error
handling must not be duplicated), `odd/tasks/agenda-technician-picker.md` (prior unit).

`graphify path AgendaPage AgendaPage.test` → no directed path (the graph does not model test→subject).
Noted, not blocking.

Graph status: **degraded — stale** (`--update` unavailable, 402). The query returns nodes; no refresh
is claimed. `AgendaPage.tsx` appears among the report's god nodes, which reinforces keeping the diff
minimal.

## Decision log

- **D1 — copy.** Reuse `"No pudimos cargar las opciones de la visita"`, identical to the create flow.
  **Owner decision**, 2026-09-29. Consistency between both dialogs, no new string, and the dialog
  title (`"Reprogramar visita"`) already supplies the context.
- **D2 — no new state or abstraction.** Write to the existing `rescheduleFeedback` slot. It is
  already rendered inside the reschedule dialog with `role="alert"`.
- **D3 — rejection handler, not `try/catch`.** The call site is a bare `void ...then(...)` chain, not
  an awaited block; `.catch()` is the honest minimal shape. Wrapping it in `async/await` would
  restructure the handler for no behavioural gain.
- **D4 — the `:126` validation message is untouched.** Out of scope; the operator now learns the real
  cause before ever submitting.

## Tasks

- [x] **T1 — RED.** Add the Vitest case: opening the reschedule dialog with `fetchTechnicians`
  rejecting shows a danger `StateMessage` with the reused copy and the error detail. Run it and
  **observe it fail** against the current code. Record the failure output.
- [x] **T2 — GREEN.** Append the rejection handler to the lookup writing into `rescheduleFeedback`.
  Re-run T1 and observe it pass.
- [x] **T3 — Evidence.** Run every check below and record observed results.
- [x] **T4 — Record + commit.** Update this document with the evidence and commit the work unit.

## Acceptance criteria

1. When `fetchTechnicians` rejects while opening the reschedule dialog, the operator sees a danger
   `StateMessage` with title `"No pudimos cargar las opciones de la visita"` and the error message as
   detail, inside the reschedule dialog.
2. The rejection is handled — no unhandled promise rejection on that path.
3. The success path is unchanged: every pre-existing `AgendaPage` test still passes.
4. RED was observed before GREEN, with the actual failure output recorded.
5. `cd web && npm test -- --run --testTimeout=20000` is green; `cd web && npm run build` passes;
   `git diff --check` is clean.
6. Only the files in Authorized scope change.

## Checks

- `cd web && npm test -- --run src/components/pages/AgendaPage.test.tsx`
- `cd web && npm test -- --run --testTimeout=20000`
- `cd web && npm run build`
- `git diff --check`

## Route declaration

| Task | Route | Trigger evidence |
| --- | --- | --- |
| T1–T4 | **inline** | Both edits are mechanical and already understood: one appended rejection handler and one test mirroring the existing reschedule cases. Both files were already read in full by the parent. The writer trigger does **not** fire — it requires two *non-trivial* files, and it explicitly excludes a mechanical second-file edit. Delegating would mean re-uploading two files the parent already holds, with no design or research left to resolve. Declared here so the skipped delegation is observable. |

## Delivery

- Forecast: ~1 source line + ~9 test lines → well under 400 authored lines. No chain, single PR.
- Strategy: `ask-on-risk`. Branch `odd/r3-001-agenda-reschedule-observability` → `main`, exactly one
  label `type:bug`, **merge commit, never squash**.
- `branch-pr` does not apply to this repo (no PR template, no issue-check workflow, no branch
  protection, and its branch regex rejects `odd/`). Copy the body structure of PR #423/#424/#430:
  Summary, Changes, Verification, Review, Base freshness, Merge convention.
- RDD: **on** (global). Native review before delivery on the committed candidate via
  `--base-ref c0c78ebe --committed-only`.

## Progress

| When | State |
| --- | --- |
| 2026-09-29 | Worktree created and provisioned (`infra/.env`, `uv sync`, `npm ci`, test-db on 6180). Graph Check passed. Task record authored. Copy decision taken by the owner (D1). |
| 2026-09-29 | **T1 RED observed.** `npm test -- --run src/components/pages/AgendaPage.test.tsx -t "technician lookup fails"` → `Test Files 1 failed (1)`, `Tests 1 failed │ 37 skipped (38)`, `Errors 1 error`. Two distinct failures, both expected: `expect(within(dialog).findByRole('alert'))` timed out because no feedback was rendered, **and** Vitest caught `1 unhandled error — Unhandled Rejection: Error: Sin conexión`, originating at `AgendaPage.test.tsx:251`. That unhandled rejection is the defect itself, reproduced before any source change. |
| 2026-09-29 | **T2 GREEN observed.** Appended the rejection handler to the reschedule lookup. `npm test -- --run src/components/pages/AgendaPage.test.tsx` → `Test Files 1 passed (1)`, `Tests 38 passed (38)` in 19.17s (37 pre-existing + the new case), and **no unhandled error**. Acceptance criteria 1 and 2 satisfied. |
| 2026-09-29 | Full web suite: `npm test -- --run --testTimeout=20000` → `Test Files 90 passed (90)`, `Tests 860 passed (860)` in 131.81s. No load-dependent failure appeared, so L8 did not fire in this run. The `860` baseline is 8 above the `852` recorded at PR #430 — the base advanced to `c0c78ebe` (PR #431, `odd/agent-role-access-wu4`), which added tests; this unit contributes one of those eight. |
| 2026-09-29 | `npm run build` → passed (`tsc -b` clean; Vite emitted only the pre-existing >500 kB chunk advisory). `git diff --check` → clean. Diff size: 13 insertions, 1 deletion across 2 files. |
| 2026-09-29 | Scope observation: `web/src/stories/pages/AgendaPage.stories.test.tsx` was **not** touched. Its API mock uses `mockResolvedValue`, and adding a rejection handler requires no mock change — the file stayed out of the diff, as the scope anticipated ("only if its mock needs it"). |
| 2026-09-29 | **Work unit committed: `f3560c4d`** — `fix(agenda): surface technician lookup failures when rescheduling`. 3 files, 190 insertions, 1 deletion. Working tree clean afterwards. No `Co-Authored-By`. |
| 2026-09-29 | **Native review assessment** (`gentle-ai review assess --agent opencode --base-ref c0c78ebe --committed-only`): `risk: medium` (`executable_change` on `AgendaPage.test.tsx`), 3 changed paths, 191 changed lines. `review_due: false`, `review_due_reason: "under_budget"` — the slice is under the ~400 authored-line budget, so no native review is due for this commit; the boundary stays pending in the slice. RDD is `on` (decided by global). |
