# ODD: capabilities-evidence

Branch `odd/capabilities-evidence` · base `main` = `4ae76ca1` · worktree `../lumat-agent-odd-capabilities-evidence`.
Problem: `assistant.capabilities` puts its whole catalog into the responder's tool evidence and, at 38 tools, consumes ~4,100 of the 5,500 characters the whole turn shares.

## Specs

- **S1.** The responder's evidence for `assistant.capabilities` MUST carry the inventory's count and one entry per tool naming the tool and its access class, and MUST NOT carry the registry descriptions. Owner's words: "(a) Proyección por tool en _render_tool_evidence: para assistant.capabilities, citar solo tool_count + nombres, sin descripciones. El detalle queda en el planner. La más quirúrgica." The projection happens in `_render_tool_evidence` only: the tool's own result stays complete, because "AT-12 — Declared Assistant Capability Inventory" (`openspec/specs/assistant-tools/spec.md:237`) fixes that result ("MUST preserve the exact whitelist count and include one capability line for every whitelisted tool, without relying on the generic item limit").
- **S2.** A test MUST fail when the relation between the real capability inventory, the projected evidence and `_TOOL_EVIDENCE_LIMIT` breaks, deriving every size from the constant and the catalog instead of hardcoding it. Owner's words: "la guarda que falta, que es más valiosa que el arreglo: un test que falle cuando la relación CAPABILITIES_TEXT_LIMIT vs _TOOL_EVIDENCE_LIMIT vs tamaño del catálogo se rompa. Hoy esa relación la sostiene un comentario."
- **S3.** No comment, test or doc in the touched surface may cite `CAPABILITIES_TEXT_LIMIT`. That constant does not exist: it and its slice were deleted in `r3-deferred-warnings` W2 (PR #313) because the bound already lived in `_render_tool_evidence`. The comment at `app/chat/assistant/nodes.py:41` still cites it as a live bound.
- **S4.** The projection MUST NOT drop a tool: every name in the turn's whitelist appears in the projected evidence regardless of catalog size, which is what `_plain`'s `MAX_ITEMS = 20` would silently break if the inventory were projected as a returned list. Owner's words: "Devolver una lista de tools. _plain() trunca dicts y listas a MAX_ITEMS = 20: un catálogo de 22+ pierde tools en silencio. Es exactamente el bug que el unit original evitó".
- **S5.** The ceiling stays at its current value. Owner's words: "Subir el techo otra vez. No resuelve la tensión: cada tool nueva que engorde el catálogo vuelve a acercar el turno al borde." Lowering it is equally out of scope: it would change the budget of every turn, which this unit does not measure.

## Tasks

- T1 — S1, S4 — project the capability payload in `_render_tool_evidence` and pin it with RED/GREEN — commit: see L5.
- T2 — S2 — guard test derived from the real catalog and `_TOOL_EVIDENCE_LIMIT` — commit: see L5.
- T3 — S3, S5 — rewrite the budget comment with the measured post-projection numbers — commit: see L5.

## Log

- **L1** (owner handoff, verbatim): "Handoff — deuda de assistant.capabilities … assistant.capabilities devuelve {tool_count, capabilities: "<una línea por tool>"}, acotado por CAPABILITIES_TEXT_LIMIT = 4_000 en app/chat/assistant/tools/registry.py. Ese payload entra completo en la evidencia del responder, bajo un presupuesto global _TOOL_EVIDENCE_LIMIT en app/chat/assistant/nodes.py, hoy 5_500. Una sola tool puede comerse ~4.000: casi todo el presupuesto." — Options offered: (a) per-tool projection, (b) shorter descriptions, (c) per-result budget, (d) own system-block route. Two directions excluded explicitly: returning a list of tools, and raising the ceiling again.
- **L2** (owner, verbatim): "continuamos desde aca. dame un overview antes de comenzar".
- **L3** (owner decision): option (a), per-tool projection in `_render_tool_evidence`.
- **L4** (measurement the parent re-ran before starting, in `main`): `agent/registry.yaml` → `assistant.tools_whitelist` has 38 entries; the capability text built from registry literals is 3,416 chars and the runtime payload is ~4,077 because `settings.update` joins `ASSISTANT_WRITABLE_SETTINGS` and `automation.create_rule` joins `RECIPES` at import time; `_TOOL_EVIDENCE_LIMIT = 5_500` is already committed on `main` (`7c7fbb8c`). `CAPABILITIES_TEXT_LIMIT` exists nowhere in the code — only in the comment at `nodes.py:42`, which is what S3 corrects. `_planner_tool_catalog` (`nodes.py:320`) already sends `{name, description, arguments}` for the same whitelist to the planner every turn, which is why the descriptions in the evidence are a second copy.
