# clientes-operativa — review advisories (WU2 + WU3)

Status: in progress
Branch: `odd/clientes-operativa-advisories`
Worktree: `../lumat-agent-odd-clientes-operativa-advisories`
Base: `main` `c1fff81c` (WU3 merged via PR #404; unit WU1 #401, WU2 #402, WU3 #404)

## Objective

Close the four non-blocking advisories left open by the WU2 and WU3 native reviews, without
reopening those reviews, without adding scope, and without changing the public JSON contract.

## Problem

The WU2/WU3 reviews approved their candidates and offered no correction for these findings; they
are separate later work. Four are still open:

- **R1-001 (WU3, risk/WARNING)** — `app/panel/api/serializers.py:177`: the stored `NUMERIC` is
  converted to a binary float. The review recorded *"no loss is evidenced at CLP-sized values"*,
  so the risk is theoretical at this scale but undocumented.
- **R3-001 (WU3, reliability/WARNING)** — `web/src/components/pages/ClientFicha.tsx:181`: the
  amount editor converts with `Number()` without a finiteness or non-negative check, so a negative
  or malformed value can reach the API and only surface as generic feedback.
- **R2-001 (WU2, readability)** — `app/panel/api/routes/clients.py:63` / PATCH `:384`: the
  equipment `PATCH` distinguishes "omitted = keep" from "explicit `null` = clear" through
  `model_fields_set`, but the contract is not written in the model or the endpoint.
- **R3-001 (WU2, reliability)** — `web/src/components/pages/ClientesList.tsx:163-175`: a stale
  async `getClientFicha` response can overwrite the state options of a dialog opened later.

## Why

The users of these endpoints are operators; the two frontend advisories are real input/race
defects, and the two backend advisories are an undocumented boundary and an undocumented
precision bound. Closing them costs little and removes four known open findings.

## Scope

**In:** exactly the four advisories above.

**Out:** everything in the unit's out-of-scope list (kanban/pipeline, quoting, payments, service
catalogue, funnel/conversion reporting, per-channel consent, email/SMS as a channel, custom
fields/tags/segments, organizations, recurrence). No new migration: the latest on `main` is `036`
(`db/migrations/036_case_amount.sql`) and none of these advisories needs a schema change.

## Constraints

- The `amount` JSON contract stays a **number** (`web/src/types.ts`), so R1-001 does not switch to
  a string. Precision preservation as a string was considered and rejected: it changes the
  contract, forces frontend and fixture changes, and the review evidenced no loss at CLP scale.
- R2-001 is **docs-only**: no behavior change, no new test.
- Keep the existing `float(...)` convention: `serializers.py:445` already serializes
  `cost_meta` the same way.

## Authorized scope

The four files named above plus their tests: `app/panel/api/serializers.py`,
`app/panel/api/routes/clients.py`, `web/src/components/pages/ClientFicha.tsx`,
`web/src/components/pages/ClientesList.tsx`, and the backend/frontend test files that cover them.

## TDD mode

Test-first (RED → GREEN), adopted from the unit's established practice: WU1–WU3 in
`odd/tasks/clientes-operativa.md` each recorded a RED step before GREEN. No `strict_tdd` config
exists in the project. Runners:

- Backend: `eval "$(infra/test-db.sh env)" && uv run pytest tests/ -q` (focused: pass the test path)
- Frontend: `cd web && npm test` (vitest run); build/typecheck: `cd web && npm run build`

## Graph Check (mandatory)

Graph in `/home/stefan/repos/lumat-agent/graphify-out/` (gitignored). Report: 8124 nodes · 17552
edges · 673 communities. Built at `16ba9cbf`, which **predates WU2/WU3 and this branch's base
`c1fff81c`** — treated as navigation only, every result verified against source.

- `graphify query "case serializer amount to_case_dict"` → `to_case_dict()`
  (`app/panel/api/serializers.py:169`), `Case` (`app/models.py:349`), `serializers.py`.
- `graphify query "client ficha case amount edit dialog input validation"` → `Input()`
  (`web/src/components/primitives/Input.tsx:16`), `Dialog()`
  (`web/src/components/primitives/Dialog.tsx:16`), `ClientFicha.tsx`, `ClientFicha.test.tsx`,
  `WU3 — A Case cannot record an amount` (`odd/tasks/clientes-operativa.md:42`).
- `graphify query "equipment PATCH null omit model_fields_set clients route"` → `EquipmentBody`
  (`app/panel/api/routes/clients.py:63`), `clients.py`,
  `test_client_ficha_omits_visit_history_but_keeps_appointments()`
  (`tests/functional/test_api_clients.py:483`).
- `graphify query "ClientesList getClientFicha stale async response state dialog"` →
  `getClientFicha()` (`web/src/api.ts:167`), `ClientesList()` (`ClientesList.tsx:68`),
  `AsyncDataState` / `useAsyncData.ts:4`, `Dialog()`.
- `graphify path "update_case" "to_case_dict" --undirected` (logged in the WU3 work) → route path
  `update_case() <--calls-- case_update() --calls--> to_case_dict()`; the directed query found no
  path (known node-resolution limitation, the edge is direct in code).

## Tasks

- [ ] **AD0 — task doc** — this file, committed as `docs(odd): plan clientes-operativa advisories`,
  mirrored in Engram under `odd/clientes-operativa-advisories/tasks`.
- [ ] **AD1 — R1-001** — document the CLP precision bound where the amount is serialized and add a
  regression test proving an exact round-trip at CLP scale. Files:
  `app/panel/api/serializers.py`, `tests/functional/test_api_cases.py`.
  - RED: a test asserting the serialized amount equals the stored integer exactly (fails only if
    the serializer rounds — documents the bound, so it must actually exercise `to_case_dict`).
  - GREEN: the docstring/comment stating the bound; test passes.
- [ ] **AD2 — R3-001 (WU3)** — guard the amount editor before submit: a non-empty input that is not
  finite or is negative must not call the API and must show a specific message. Files:
  `web/src/components/pages/ClientFicha.tsx`, `web/src/components/pages/ClientFicha.test.tsx`.
  - RED: a test submitting `-1` (and a malformed value) asserts the API is NOT called and feedback
    is shown.
  - GREEN: the guard.
- [ ] **AD3 — R2-001 (WU2)** — document "omitted = keep / explicit `null` = clear" on
  `EquipmentBody` and the equipment `PATCH` endpoint, reusing the `_UNSET` keep-vs-clear wording
  style from `app/panel/api/routes/cases.py:12-15`. Docs-only, no behavior change, no new test.
  File: `app/panel/api/routes/clients.py`.
- [ ] **AD4 — R3-001 (WU2)** — add a request-identity guard to `openState` so a stale
  `getClientFicha` response cannot overwrite the options of a dialog opened later. Files:
  `web/src/components/pages/ClientesList.tsx`, `web/src/components/pages/ClientesList.test.tsx`.
  - RED: a test where the first request resolves after a second was opened asserts the second
    dialog's options are not overwritten.
  - GREEN: a `useRef` sequence token, the pattern already used in `Dialog.tsx` / `AgentChat.tsx`.
- [ ] **AD-VERIFY** — full backend suite, `npm test`, `npm run build` over this tree; plus focused
  runs first. Record exact commands and results.

## Acceptance criteria

1. The four advisories are addressed with the minimal change each needs; no advisory is closed by
   assumption.
2. R1-001 has an executed test proving exactness at CLP scale; the contract stays a number.
3. R2-001 is documentation only — `git diff` shows no executable change for it.
4. R3-001 (both) have frontend tests that fail before the guard and pass after.
5. No out-of-scope change; no new migration; the existing suite stays green.

## Progress

- [x] **Provisioned** — `rapso worktree create clientes-operativa-advisories --yes` (consent given
  in-session), base `main c1fff81c`. `infra/.env` copied, `uv sync`, `web/npm install`, isolated
  test DB up. Baseline focused backend green (`test_api_cases.py` + `test_api_clients.py`).
- [x] **Graph Check** — run; recorded above. Graph stale (`16ba9cbf`), declared and used as
  navigation only.
- [ ] AD1, AD2, AD3, AD4, AD-VERIFY.

## Verification evidence

(to be filled per task: RED command + observed failure, GREEN command + observed pass)

## Next step

AD1 (R1-001): write the RED test, then document the bound.

## Recovery

- Branch `odd/clientes-operativa-advisories`, worktree `../lumat-agent-odd-clientes-operativa-advisories`.
- Other live worktrees — do not touch: `../lumat-agent-odd-agenda-agente-whatsapp`
  (`odd/agenda-agente-whatsapp-s3-cancel`), `../lumat-agent-odd-usuarios-aislamiento`
  (`odd/usuarios-aislamiento-wu2`), and the principal worktree.
- Test DB is slug-derived: `bash infra/test-db.sh up|down|env`.
- `graphify-out/` is gitignored; query from the principal worktree. Refresh once at session close
  (`graphify . --update`; if the LLM labeler fails, `graphify update . --no-cluster` and declare it).
