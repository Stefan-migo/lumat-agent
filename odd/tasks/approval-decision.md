# Project approval decision

Defect: `project.create` and the candidate-selection path of `project.find` can never execute from the
chat, because the chat approval surface has no way to produce the `decision` the tool boundary demands.
Fix: publish a decision envelope on the pending approval, accept the owner's decision at the approval
endpoint, and bind it into the approved payload inside the same atomic consumption.

## Specs

- **S1** The real chain `guardrails → POST /chat/threads/{id}/approval → execute_tool` must create the
  project when the owner approves with an explicit decision. Today it fails with
  `project create approval is missing an explicit decision`, surfaced to the operator as
  `Tool execution failed: project create approval is missing an explicit decision`.
- **S2** Without a decision, the approval must not be consumed and the tool must not mutate anything.
  The endpoint answers a distinct refusal (`project decision required`), never the misleading
  `approval is invalid, expired, or already consumed`.
- **S3** `project.find` with semantic candidates: the owner selects one of the candidates the server
  returned (`selected_slug`), and the resume resolves that project. A slug outside the persisted
  candidate set is refused without consuming the approval.
- **S4** Second informed gate: when an exact purpose duplicate exists, `projects.create` returns
  `requires_approval` with the conflicting project even when the approved decision is
  `create_distinct`, and creates only after that second explicit decision. Chosen by the owner:
  "Segundo gate informado (recomendado)" — the first gate is consent, the second is conflict resolution.
- **S5** The panel renders the decision picker only when the pending approval carries a decision
  envelope, and refuses to approve without a choice, showing the reason. Settled scope:
  "Arreglo completo: backend + picker en el panel + test e2e".
- **S6** `project.rename`, `project.archive` and `project.merge` keep requiring no decision; their
  existing approval behavior is unchanged.

## Tasks

| ID | Spec | Route | Commit |
| --- | --- | --- | --- |
| T1 | S1, S2, S3 | backend · approval envelope + decision validation + candidate publication | `ee51d8070` |
| T2 | S1, S2, S3 | backend · atomic decision injection in `approve_plan` + endpoint contract | `d54f8a321` |
| T3 | S4 | backend · informed second gate in `projects.create` | `d54f8a321` |
| T4 | S1, S2, S3, S4, S6 | tests · unit matrix, DB e2e, HTTP contract | `ee51d8070`, `d54f8a321`, `2a5413e60` |
| T5 | S5 | panel · types, api client, PlanCard picker, web tests, DESIGN_SYSTEM entry | this commit |

## Log

### L1 — user request (verbatim)

Hola Chat, después de hacer el deploy y el release en el servidor volví a testear el asistente LUMAT y
pudimos avanzar. Hay mejoras interesantes, pero también hay errores en algunos, en algunas tools. Aquí
te dejo dos archivos. Uno es la conversación del último hilo que abrí con el asistente LUMAT en el panel.
Y además el artifact que venimos trabajando con el testeo de todas las tools. Esto es lo que el mismo
asistente escribió y dejo registrado

'/home/stefan/repos/LumatData/asistenteLumatChats/18-11/herramientas-probadas-hilo-84.md'
'/home/stefan/repos/LumatData/asistenteLumatChats/18-11/retomar-evaluacion-de-tools-de-Asistente-Lumat.md'

### L2 — reported evidence (verbatim, from the artifact)

- `project.create` → `project create approval is missing an explicit decision` — "**Reproducido 2
  veces** con el mismo plan (`E2E temporal`)". The artifact conclusion was "Es un bug de la capa de
  aprobación, no de `project.create`" and "el runtime no registra una decisión explícita del owner".
- `conversations.search` "responde OK pero **0 filas** pese a existir conversaciones de caldera".
- KB hit rate 0% with `kb.retrieve` returning fragments.
- "33 herramientas" declared by `assistant.capabilities`.

### L3 — diagnosis in this session

Read-only inspection found the click *was* consumed: `Tool execution failed:` is emitted by the execute
node (`app/chat/assistant/nodes.py:1214`), i.e. after `approve_plan` flipped the approval to `consumed`
and re-entered the graph. Root cause:

1. `guardrails` issues the pending approval from a plan carrying only `{tool, arguments}`
   (`app/chat/assistant/nodes.py:840-843`).
2. `issue_approval` canonicalizes a project payload without `decision`
   (`app/chat/assistant/approval.py:23-35`).
3. `approve_plan` only flips `assistant_state.approval.status` (`app/services/agent_chat.py:880-905`).
4. `execute_tool` demands `set(project_payload) == {"operation","arguments","decision"}`
   (`app/chat/assistant/tools/registry.py:1403-1418`) and raises.

Same latent defect for `project.find` candidate selection (`registry.py:1416`), invisible so far because
the tested query matched an exact slug. Coverage gap: every project approval in the suite is built by
hand (`tests/unit/test_assistant_tools.py:947-957`); no test exercises the real issuance path.

### L4 — owner decisions

- Scope: "Arreglo completo: backend + picker en el panel + test e2e".
- Worktree: "Sí, crear el worktree" → `../lumat-agent-odd-approval-decision`, branch `odd/approval-decision`.
- Duplicate policy: "Segundo gate informado (recomendado)" → S4.
- Out of scope for this feature, recorded as follow-ups: `conversations.search` does not search summary
  text (`app/services/conversations.py:42-51`); `kb_hit_rate` reads 0% from n=1 (`app/services/analytics.py:42-83`).

### L5 — slices and evidence

- **Slice 1 (backend contract)** — commit `ee51d8070`: decision envelope published on the pending
  approval, candidate publication at the tool boundary, `create_anyway` accepted, unit matrix in
  `tests/unit/test_assistant_approval_decision.py`. RED proven on the base commit `0762e8c9f`:
  `issue_approval` published `project_decision: None` and `execute_tool` answered
  `project create approval is missing an explicit decision`.
- **Slice 2 (backend consumption + panel)** — this commit: atomic decision binding in `approve_plan`,
  endpoint contract (400 on an unanswered decision), the informed duplicate gate in `projects.create`,
  `tests/integration/test_assistant_project_approval_decision.py`, and the panel picker.
- Gates observed: `scripts/test.sh shape` → "no shape surface touched"; `scripts/test.sh quick` green;
  `scripts/test.sh db` over the touched files green (158 tests). Two real defects surfaced while
  writing the tests: `jsonb_set` needs the digest JSON-encoded, and a plan carrying the bound payload
  poisoned the digest check of the *next* approval in a parked chain.

### L6 — panel evidence and review fixes

- S5 shipped through `gentle-ai-worker` with six allowed surfaces; parent review before commit found and
  corrected four things: the invented `project_hash` type (the real key is `project_sha256`), a picker
  that could render with zero options and disable "Aprobar" forever, a static radio `name` shared across
  cards, and an unrequested `@media` rule that restyled every plan card's button row.
- The second-gate web test now mirrors the envelope the backend actually publishes
  (`["selected_slug", "create_anyway"]`) instead of an impossible three-option list, and asserts the
  deliberate-duplicate radio starts unselected.
- Gates observed: `npx vitest run src/components/pages/AgentChat.test.tsx` → 85 passed;
  `npm run build` (`tsc -b`) green; `npm test` → 121 files / 1439 tests passed.
