# asistente-lumat-config-layer

Objective: give the Lumat assistant a real **configuration layer** that models it — turn the
opt-in tools on by default, connect the assistant workspace's right sidebar, add a project
**Recursos** selector, let the agent read files/images on demand (hybrid context), add three
global skills, and create a dedicated **TecnicoLumat** agent for the technician role.

Branch: `odd/asistente-lumat-config-layer` (worktree `../lumat-agent-odd-asistente-lumat-config-layer`), base `143ced8b`.
Delivery: `ask-on-risk`. Runner: `uv run --no-sync pytest tests/` (backend) + `npm test` / `npm run build` (web).

## Specs

S1 — Opt-in tools on by default.
The seven `opt_in` tools start enabled by default: `web.search`, `web.fetch`,
`automation.create_rule`, `project.create`, `project.rename`, `project.archive`,
`project.merge`. Today `ToolPolicy.opt_in_enabled` defaults to `[]`
(`app/services/project_config.py:15-16`). The tier gate (prior art D7) and the
destructive-operation confirmation MUST keep applying even when a tool is enabled.
Note: a thread override (`thread.assistant_state["tool_policy"]`) still *replaces* the
project policy (`resolve_effective_config`, `project_config.py:110-113`); default-on only
affects projects/threads with no explicit stored override.

S2 — Sidebar "Capacidades del asistente" connected.
Exact current placeholder string: `Sin datos` (`AssistantWorkspace.tsx:699`), because
`AgentChat.tsx:846` renders `<AssistantWorkspace>` without the `capabilities` prop. Fix:
fetch `GET /panel/api/assistant/capabilities` (already returns
`{tools[], personas[], prompts[], kb_available, memory_available}`, `chat.py:448`) and pass
it. The section must show real tool count and KB/memory availability.

S3 — Sidebar "Recursos del proyecto" = functional selector (Option B).
Exact current placeholder string: `Selección de recursos aún no disponible.`
(`AssistantWorkspace.tsx:698`). The section becomes a selector. Owner scope, verbatim:
"B definitivamente. pero solo me parece interesante los archivos del proyecto y las
sesiones de planning quizas las skills tambien estarian bien en recursos." → the selector
covers **project files**, **planning sessions**, and **project skills**.
Semantics (owner decision, verbatim: "b marca +lectura por tool"): fixing a resource
**marks** it for the thread (persisted in `thread.assistant_state["resources"] =
{project_files: [ids], planning_sessions: [slugs], skills: [names]}`) and surfaces a
**compact reference** (names/ids/slugs) in the turn context. Content is read **on demand
with tools**, never injected in full every turn:
- project files → existing `read_project_file` (S6 adds `offset`/`limit`),
- planning reports → a new `planning.read_report` tool (owner request, verbatim: "deberia
  exsitir una tool que permita leer un reporte. lo podriamos agregar aca?"),
- skills → the existing declared-skill mechanism (bodies via `_skill_context`).

S4 — Tray vs library separation.
Owner, verbatim: "los archivos del hilo no deberian mostrarse en el tray del chatbox. solo
los archivos sleccion para proximo mensaje. si deberian mostrarse en el tray." The chatbox
tray = **selection for the next message** (ephemeral, cleared after send). The **thread file
library** = all thread files (persistent), shown in the sidebar/popover, never in the tray.
Today the tray keeps every attachment and re-sends all ids on each message
(`AgentChat.tsx:670`), so files are re-injected every turn.

S5 — Multimodal tool results (agent views an image via a tool).
Owner, verbatim: "no hay forma de que el agente pueda seleccionar una imagen del proyecto y
verla solo a traves de tools es lo unico que me queda pendiente. eso tambien solucionaria
que una imagen del hilo no se inyecte constantemente en cada mensaje." A tool returns an
image handle; the harness adds the image as an `image_url` part to the model call. Today
tool results are text JSON only (`_render_tool_evidence`, `nodes.py:788-794`) and
`build_multimodal_content` only reads attachments (`attachments.py:70`). The agent must be
able to view a project image AND a thread image on demand.

S6 — Partial reads (`offset`/`limit`) + multiple runs.
Owner, verbatim: "se podria mejorar aun mas la tool de lectura, y permitirle al agente que
parte del archivo leer? y que pueda hacer mas de una corrida si necesita leer un archivo
completo?" `read_project_file` caps at `MAX_FILE_TEXT_CHARS = 20_000` and returns
`truncated: true` (`project_files.py:141`). Add `offset`/`limit` so the agent reads in
chunks across tool-loop turns (the loop already re-plans, `graph.py:100`).

S7 — `docx`/`xlsx`/`md` as thread attachments.
Owner, verbatim: "lo otro que hay de los formatos docx y xlsx? podemos agregarlos para que
el agente pueda leerlos. es posible?" Project files ALREADY accept and extract `docx`
(`python-docx`) and `xlsx` (`openpyxl`) via `document_extract.py` and
`project_file_allowed_types` (`config.py:62`). Thread attachments do NOT
(`attachments.py:_DOCUMENTS` = pdf/csv/txt; `assistant_attachment_allowed_types` =
`["pdf","csv","txt","image"]`). Extend the attachment path to accept `docx`/`xlsx`/`md`,
reusing `extract_document_text`.

S8 — Three global skills.
Owner decision D5: adopt `planning`, `tools`, `kb` as global assistant skills;
`lumat-concept` stays deferred. Today the assistant has exactly one skill
(`agent/skills/assistant/memoria-tukulpan.md`, declared in `agent/registry.yaml:61-64`).
The three skills must be loadable by the planner.

S9 — TecnicoLumat agent.
Owner, verbatim: "si que tambien entre. en el mismo odd." and "hay una idea de crear un
'agente TecnicoLumat' con el cual el tecnico va a poder hablar para hacer consultas sobre
lumat o de gasfiteria. o sea este agente ayudaria al tecnico a resolver dudas ya sea de las
politicas, precios, detalles de lumat. o ayuda con gestion tecnica." Today there is a single
`assistant` (one persona/prompts/skills/tools/memoria_scope) and `actor_role` only gates
tools (`ROLE_TOOL_ALLOWLIST`, `registry.py:896-933`); it never selects a persona or agent.
Requires: a role→agent binding (tecnico → TecnicoLumat), the agent declaration
(persona/tools/skills/memoria_scope), and a KB/memory policy for the technician role
(`kb.retrieve` is currently denied to `tecnico`, `registry.py:905`).

Non-goals (explicitly dropped after review):
- Extending `ProjectConfig` with seven dimensions — over-engineering; those dimensions are
  already covered by separate slices (`asistente-skills`, `asistente-kb-scope`,
  `asistente-lumat-persona-prompt`, `asistente-planning`, `asistente-agentes-proyecto`).
- The three UI wiring bugs of the assistant workspace — owned by another agent
  (`odd/panel-visual-alignment`).

## Tasks

| ID | Spec | Route | Status | Evidence |
| --- | --- | --- | --- | --- |
| T0 feature doc | — | inline | done | this commit |
| T1 default-on 7 opt-in | S1 | inline | done | 49227b57 |
| T2 sidebar Capacidades wired | S2 | inline | done | fd5e39e2 |
| T3a Recursos selector + persistence | S3 | inline | done | b1313675, b1f670c0 |
| T3b pinned resources in context | S3 | inline | pending | — |
| T3c planning.read_report tool | S3 | inline | done | 51e9643f, 46d39657 |
| T4 tray/library separation | S4 | inline | pending | — |
| T5 multimodal tool results | S5 | inline | pending | — |
| T6 partial reads (offset/limit) | S6 | inline | pending | — |
| T7 docx/xlsx/md attachments | S7 | inline | pending | — |
| T8 three global skills | S8 | inline | pending | — |
| T9 TecnicoLumat agent | S9 | inline | pending | — |

## Log

L1 (owner, verbatim): "hey chat. Necesito que comencemos con este trabajo pendiente:
/home/stefan/repos/lumat-agent/.rapsodia-code/sessions/ready-for-odd/2026-10-13-asistente-lumat-config-layer.
dame un overview antes de continuar."

L2 — Overview. Read the rapsodia session (`session.md`, `report.md`) and the handoff
`odd/handoffs/asistente-lumat-config-layer.md`. Verified the code: `ProjectConfig` still has
3 fields (`instructions`, `tool_policy`, `skills`); `ToolPolicy.opt_in_enabled` default `[]`;
`resolve_effective_config` thread override replaces project policy. Finding: the report's
premise ("solo instructions + tool_policy + skills", "fundación primero") is partly stale —
most of the 7 dimensions already have their own merged/advanced ODD slices. The real
remaining gap is narrower than the report implies.

L3 (owner, verbatim): "1. hay que hacer." → default-on confirmed.
"3. los bugs ya se esta haciendo cargo otro agente." → the three UI bugs are out of scope.

L4 (owner, verbatim): "aqui solo me interesa saber si se van a poder 'crear agentes' como
crear un agente especifico. por ahora no es necesario que este en el ui. pero hay una idea
de crear un 'agente TecnicoLumat'..." → feasibility check: today NO (single assistant, role
only gates tools), but the registry shape supports it; the missing piece is a role→agent
selector. Feasible without touching `ProjectConfig`.

L5 (owner, verbatim): "si que tambien entre. en el mismo odd." → TecnicoLumat enters this
ODD as S9.

L6 — Read-only inspection of the `odd/panel-visual-alignment` worktree (owner request):
- T5 "Hilos wire" (the third UI bug) is implemented but **UNCOMMITTED** (working tree +
  untracked `ProjectThreads.tsx`/`.test.tsx`, plus `serializers.py` `preview` field).
- Sidebar "Capacidades" (`AssistantWorkspace.tsx:699`) and "Recursos"
  (`AssistantWorkspace.tsx:698`) are still placeholders there. Bugs #1/#2 remain.

L7 (owner, verbatim): "B definitivamente. pero solo me parece interesante los archivos del
proyecto y las sesiones de planning quizas las skills tambien estarian bien en recursos."
→ S3 scope = project files + planning sessions + skills.

L8 — Attachment pipeline investigation (answers to the owner's three questions):
- Attachments are **thread-scoped** (`AssistantAttachment.thread_id`); there is no
  per-message association (`create_run_message` ignores `attachment_ids`, `agent_chat.py:343`).
- Injection: docs → extracted text (cap `assistant_attachment_max_context_chars = 20_000`,
  `config.py:57`); images → `image_url` base64 into the responder (`nodes.py:1108`).
- The tray re-sends every attachment id each message (`AgentChat.tsx:670`) → re-injection
  every turn. Fix is mostly frontend (S4).
- No tool can return an image; tool results render as text JSON.

L9 — Vision confirmed working. Owner attached the image for real and the model described it
correctly. Earlier the model had *speculated* it had no vision because nothing in the
persona/prompts or tools tells it otherwise. So the mechanism was never broken; it was
never exercised.

L10 (owner, verbatim): "no hay forma de que el agente pueda seleccionar una imagen del
proyecto y verla solo a traves de tools es lo unico que me queda pendiente. eso tambien
solucionaria que una imagen del hilo no se inyecte constantemente en cada mensaje." → S5.

L11 (owner, verbatim): "lo otro que hay de los formatos docx y xlsx? podemos agregarlos para
que el agente pueda leerlos. es posible?" → S7. Correction recorded: project files ALREADY
support docx/xlsx/md; only the thread-attachment path lacks them. (My earlier "gotcha" that
docx/xlsx were rejected was wrong — it came from a truncated read of `_DOCUMENTS`.)

L12 (owner, verbatim): "esta perfecto asi." → slicing approved.

L13 — Worktree created with explicit owner consent:
`rapso worktree create asistente-lumat-config-layer --yes` →
`/home/stefan/repos/lumat-agent-odd-asistente-lumat-config-layer`, branch
`odd/asistente-lumat-config-layer`, base `143ced8b`. Feature doc written here (T0).

L14 — T1 done (49227b57). Option A chosen by the owner ("a"): `ToolPolicy.opt_in_enabled`
now uses `Field(default_factory=_default_opt_in_tools)`, deriving the default from every
`tier == "opt_in"` entry in `TOOL_REGISTRY` (future-proof: a new opt-in tool is default-on
automatically). Explicit project/thread policies still win, so the security invariant holds.
TDD: RED first (3 failing tests asserting the new default), then GREEN. Updated four tests
that encoded the old `[]` default: `test_project_config.py` (default set), `test_effective_config.py`
(global + empty-project now expect `DEFAULT_TOOLS | OPT_IN_TOOLS`; the skill-body test now
uses `OPERADOR` + `automation.create_rule` to keep proving a skill body cannot grant a
role-denied tool), and `test_assistant_effective_config.py` (thread override now disables
with `[]` instead of enabling `web.search`). Evidence: focused unit + integration green;
full backend suite green (2166 collected, 0 failures). Env: worktree `.venv` synced and the
isolated test DB raised with `infra/test-db.sh up` (port 6376).
RDD assess (`--base-ref 143ced8b --committed-only`): risk `medium`, `review_due=false`
(`under_budget`) → boundary stays pending in the slice.

L15 — T2 done (fd5e39e2). The "Capacidades del asistente" section was stuck on `Sin datos`
because nothing fetched `GET /panel/api/assistant/capabilities`. First attempt put the fetch
in `AgentChat` on mount, but that broke 12 order-sensitive tests (`mockResolvedValueOnce`
chains) with an extra request. Final design: `AssistantWorkspace` loads it itself
(uncontrolled) and only when the context panel is visible (`contextVisible ||
threadDetailOpen`), still honoring a parent-supplied `capabilities` prop (controlled).
TDD: RED test in `AgentChat.test.tsx` asserts the fetch and the rendered counts; GREEN after
the move. Evidence: `AgentChat.test.tsx` 72/72, `AssistantWorkspace.test.tsx` 31/31, full
frontend suite 1190/1191 (the one failure is the pre-existing load-flaky
`ClientesList > distinguishes a filtered-empty result…`, green in isolation 42/42), `npm run
build` green. Env: `npm install` in `web/` (the worktree had no `node_modules`).
RDD assess: risk `medium`, `review_due=false` (`under_budget`).

L16 — T3 design closed. Owner chose (b) "marca +lectura por tool" for project files, and
asked for a planning-report read tool. Design: fixing a resource marks it in
`thread.assistant_state["resources"]` and surfaces a compact reference in context; content
is read on demand (`read_project_file`, new `planning.read_report`, declared skills). T3 is
split into T3a (selector + persistence), T3b (pinned resources in context), T3c
(`planning.read_report` tool).

L17 — T3a done (backend b1313675, frontend b1f670c0). Backend:
`app/services/thread_resources.py` (+ `ThreadResources` model) stores the selection in
`thread.assistant_state["resources"]`; routes GET/PUT/DELETE
`/panel/api/chat/threads/{id}/resources` mirror `tool-policy` (owner-scoped, 409 while a run
is active) and validate every reference against the thread's project (files/skills) and
owner (planning sessions). Frontend: `ThreadResources.tsx` selector (3 groups with a toggle
per item, whole-selection PUT), wired into the context panel's "Recursos del proyecto"
section; it fetches lazily when the section is expanded. Evidence: backend
`test_api_thread_resources.py` 5/5, full backend suite 2171 collected / 0 failures;
frontend full suite 1192/1192, `npm run build` green. Two tests encoding the old placeholder
were updated. Note: the frontend full suite crashed once on this box (low memory) and was
re-run with `--maxWorkers=2`. RDD assess: risk `medium`, `review_due=false`
(`under_budget`, 788 changed lines).

L18 — T3c done (`51e9643f` refactor, `46d39657` feat). New read-only tool
`planning.read_report` (args `{slug}`, `tier="default"`, ADMIN/OPERADOR) returns a closed
session's persisted report by slug. Extracted `find_session_thread` (slug→owner thread) and
`report_memory` (persisted report `Memory`) from the chat route into `app/services/planning.py`
and reused them in both the route and the tool. Registered in `agent/registry.yaml`
(`tools_whitelist`) + `ROLE_TOOL_ALLOWLIST` + `DEFAULT_TOOLS` (`test_tool_tiers.py`,
`test_effective_config.py`); refreshed the frozen planner-catalog hash in
`test_assistant_delegation.py`. TDD: RED first (four functional `read_report` tests + the
exact-set assertions), then GREEN. Evidence: focused 55/55; full backend suite green (EXIT 0);
no frontend change. RDD assess (`--base-ref 143ced8b --committed-only`): risk `medium`,
`review_due=false` (`under_budget`, 1047 changed lines) → boundary stays pending in the slice.
Next: T3b (surface the pinned resources as a compact reference in the turn context).
