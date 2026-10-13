# ODD: asistente-lumat-persona-prompt

**Branch**: `odd/asistente-lumat-persona-prompt`
**Worktree**: `../lumat-agent-odd-asistente-lumat-persona-prompt`
**Base**: `2554aff2` (= `main` at branch time; el handoff citaba `63fde6d9`, main avanzó 2 commits de release/docs)
**Status**: in progress
**Source**: `odd/handoffs/asistente-lumat-persona-prompt.md` (Engram obs 6408) + `.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-ejecucion-y-prompt/{report.md,session.md}` (Engram obs 6405/6402/6398).

## Objective

Reescribir la **persona + prompts** del asistente del panel para que **actúe** (ejecute tools) en vez de pedir permiso o devolver un plan, trate la **KB como una fuente entre varias** (no como gate/bloqueo), y tenga **personalidad + formato** (español chileno de Santiago, cálido y conciso ~5–8 líneas).

## Problem (verified, not inferred)

Diagnóstico H3 cerrado: **no hay bug de ejecución — el agente nunca emite el tool call.**

- El schema del plan permite `kind: "respond"` sin tool y el plan prompt no exige tool (`agent/prompts/assistant_plan.md:14-18`, `app/chat/assistant/state.py:32-40`); un plan sin tool va a respond/KB sin ejecutar (`app/chat/assistant/nodes.py:684-687`).
- Causa raíz: persona + responder **KB-céntricos** (`agent/personas/assistant.md:1`: *"answer only from the bounded `<kb>` evidence block; if it is absent or insufficient, do not synthesize facts"*; `agent/prompts/assistant_respond.md:11-16`).
- El `<kb>` vacío **no** bloquea el planning (`nodes.py:864-908`, `graph.py:53-55`): solo la ruta no-tool dispara la refusal de grounding.
- El tag "Assistant response generated" = fallback genérico sin evidencia de tool (`nodes.py:1116-1120`).

## Reconciliation with prior art (CRITICAL — verificado, no asumido)

La persona/respond KB-céntrica **no es un accidente**: la instaló el ODD `assistant-grounding-gate` (PR **#299**, `5f7d9033`), que agregó un contrato de grounding a nivel de **nodo/grafo** + spec + test:

| Artefacto | Qué impone |
|---|---|
| `app/chat/assistant/nodes.py` (`retrieve_kb`, `guardrails`) | En la **ruta no-tool** (`kind:"respond"`), una pregunta no social pasa por `retrieve_kb`; sin chunks → `PANEL_GROUNDING_REFUSAL` determinística, **sin llamar al responder** |
| `app/chat/assistant/graph.py:36-54` | `guardrails → retrieve_kb → (respond_stream \| END)`; `grounding_refusal`/`kb_unavailable` → END. **La ruta `kind:"tool"` NO toca `retrieve_kb`** |
| `openspec/specs/internal-agent-chat/spec.md:44-69` | Requirement MUST: evidencia KB antes de responder una *knowledge question* no conversacional; responder solo de chunks no vacíos; clarification determinística sin evidencia; `kb_unavailable` ≠ clarificación |
| `tests/unit/test_assistant_grounding_gate.py` | 186 líneas que asertan el comportamiento del **nodo/grafo** |

**Conclusión verificada**: el gate está en el nodo, no en el prompt. Por lo tanto:

1. **No hace falta tocar código, ni el spec, ni borrar tests.** Los cambios son solo 3 archivos de prompt/persona.
2. El fix H3 es compatible con el gate: una *data request* enruta a `kind:"tool"` (ruta que ya bypassa el gate) y el responder debe poder responder de **tool results**; el gate sigue disparando para *knowledge questions* sin evidencia.
3. La reconciliación real es **de redacción**: la persona/respond deben decir "KB vacío **con** tool evidence no bloquea" **y** preservar "sin evidencia de NINGUNA fuente → decilo, no inventes" (invariante anti-síntesis del spec).

### Incorrecciones del borrador v1 corregidas aquí

- v1 decía `memory.*` como allowlist de escritura; el allowlist **real** es `AUTONOMOUS_WRITE_ALLOWLIST = frozenset({"memory.write", "memory.update", "memory.delete", "artifact.save"})` (`app/chat/assistant/tools/registry.py:35`). Se usa el wording exacto (ya presente en la persona actual).
- La persona actual dice *"never load or execute skills"* (contradice D8: el planner **declara** skills que sí se cargan) → se reemplaza.

## Constraints (preservar)

- **Preservar** el párrafo de delegación en `assistant_plan.md` (`kind: "delegate"` + `sub_agent: "customer_records"`): lo assertea `tests/unit/test_assistant_delegation.py:349-353`.
- **No** tocar `agent/registry.yaml` (los paths `personas/assistant.md`, `prompts/assistant_plan.md`, `prompts/assistant_respond.md` los assertean `tests/unit/test_agent_registry.py:275-278` y `tests/functional/test_api_assistant_capabilities.py:108-110`).
- **No** tocar ejecución de tools, schema del plan, `nodes.py`, `graph.py`, ni el spec.
- Respetar **D10/D11/D12** (global = seguridad + baseline; proyecto aditivo; proyecto vacío hereda el global).
- **No** incluir la Feature B (uploader KB): va por el track `asistente-agentes-proyecto` A3.5.

## Plan (tasks)

- [x] **T1** — `agent/personas/assistant.md`: reemplazo completo (secciones Environment / How you act / Knowledge and evidence / Memory / Skills / Personality and format / Safety). Registrar chileno.
  - Route: **delegated** (writer). Trigger: 3 archivos no triviales (writer trigger).
- [x] **T2** — `agent/prompts/assistant_plan.md`: delta "preferí `kind:"tool"` cuando el pedido necesita datos o acción". Preservar delegación.
  - Route: delegated (misma unidad que T1).
- [x] **T3** — `agent/prompts/assistant_respond.md`: reemplazar la regla KB-gate por "respondé de tool evidence + `<kb>`; `<kb>` vacío no bloquea; sin evidencia de ninguna fuente, decilo; registro chileno conciso".
  - Route: delegated.
- [x] **T4** — Guard test de regresión: assert que el plan prompt prefiere tool y que el respond prompt ya no tiene el gate KB-only. (Consistente con `test_planner_prompt_advertises_executable_delegation`.)
  - Route: delegated (misma unidad).
- [ ] **T5** — Commits atómicos con Conventional Commits, sin atribución IA.

## Verification

- `python -m pytest tests/unit/test_assistant_grounding_gate.py -q` — gate intacto (no debe cambiar).
- `python -m pytest tests/unit/test_prompts.py tests/unit/test_assistant_delegation.py tests/unit/test_agent_registry.py tests/unit/test_assistant_config.py -q` — carga/registro intactos.
- `python -m pytest tests/integration/test_assistant_harness_*.py -q` — wiring/approval verde.
- `python -m pytest tests/functional/test_api_assistant_capabilities.py -q` — capacidades intactas.
- **No** borrar ni relajar `test_assistant_grounding_gate.py`.

## Acceptance criteria (observable)

1. Reproducir el caso de producción (pedido de datos con `<kb>` vacío): el agente **ejecuta tools**, no pide permiso ni devuelve un plan. (Reproducción end-to-end requiere provider real; se verifica por prompt + suite; se declara honestamente.)
2. `<kb>` vacío con tool evidence **no** bloquea la respuesta.
3. Respuesta concisa en español chileno de Santiago.
4. Suite del harness verde y gate de grounding intacto.

## Delivery

- Cadena: PR único sobre `main` (forecast chico: 3 prompts + 1 test).
- RDD: `gentle-ai review assess` sobre el commit.

## Evidence log

- Commit 1: `793a2cb3` — `docs(odd): record the assistant persona/prompt act-first ODD`.
- Verification 1 (as requested): `uv run pytest tests/unit/test_assistant_prompt_contract.py tests/unit/test_assistant_grounding_gate.py tests/unit/test_prompts.py tests/unit/test_assistant_delegation.py tests/unit/test_agent_registry.py tests/unit/test_assistant_config.py -q` — EXIT=1; 4 failures in `tests/unit/test_assistant_config.py` because its existing assertions require persona wording that the mandated exact replacement removes. Prompt contract, grounding gate, prompt, delegation, and registry tests passed.
- Verification 1 (compatible subset): `uv run pytest tests/unit/test_assistant_prompt_contract.py tests/unit/test_assistant_grounding_gate.py tests/unit/test_prompts.py tests/unit/test_assistant_delegation.py tests/unit/test_agent_registry.py -q` — EXIT=0.
- Verification 2: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_harness_context.py tests/integration/test_assistant_harness_session.py tests/integration/test_assistant_harness_compatibility.py tests/integration/test_assistant_harness_production.py tests/functional/test_api_assistant_capabilities.py -q` — EXIT=1; PostgreSQL at `127.0.0.1:6271` refused connections during migration (connection refused).
- Commit 2: prompt/persona implementation and test; hash to be recorded in the follow-up evidence update after commit.
