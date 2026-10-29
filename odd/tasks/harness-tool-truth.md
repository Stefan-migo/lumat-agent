# ODD: harness-tool-truth
Branch: `odd/harness-tool-truth`
Base: `origin/main` at `23d1d29f`; follow-up defects found while fixing `odd/tasks/assistant-evidence-integrity.md`.

## Specs

### S1 — Cold conversation tool imports
Importing `app.services.conversations` before `app.panel.api` must work, and `execute_tool(..., "conversations.list", ...)` must succeed on the first call of a cold process. Fix the cycle at its narrowest point, leave a comment naming the cycle, and do not make `app/panel/api/__init__.py` lazy. The cold-interpreter regression test must assert exit code 0 and an expected stdout marker.

Reproduced ImportError (verbatim):
```text
ImportError: cannot import name 'assign' from partially initialized module 'app.services.conversations'
  (most likely due to a circular import) (/app/app/services/conversations.py)
```

### S2 — Turn-effective capability catalog
`assistant.capabilities` remains `tier="default"` and read-only. It must report `tool_count` and the per-tool list from the calling turn's effective whitelist (global whitelist ∩ role authorization ∩ enabled opt-in tools), and make clear that the catalog applies to this turn's scope. Pass the whitelist through the supported handler keyword-argument channel without changing other handlers' contracts. If no whitelist reaches the handler, retain the prior global-catalog behavior and document that fallback in code and tests.

Operator quote: “luego no hay certeza de que esten todos los tools realmente funcionando.”

When the handler falls back to the global catalog because no turn whitelist reached it, the output must not
claim the list is scoped to this turn: the fallback is the widest list, which is exactly where that header
would mislead.

### S3 — End the cold-import class at the amplifier, not per service
`app/services/dashboard.py` reproduced S1 exactly (`cannot import name 'compute_kpis' from partially
initialized module 'app.services.dashboard'`), found by the tool probe. Two occurrences make it a class: any
service importing `app.panel.api.serializers` at module level drags all 20 route modules because
`app/panel/api/__init__.py` assembled the router on import. The package init must stay free of routes and
build `api_router` on first access, so the router is still assembled exactly once for the app and a
serializer import never loads it.

## Tasks
- T1 — S1 cold-import regression and narrow cycle fix — commit: `e6c69ac4`
- T2 — S2 effective capabilities and compatibility coverage — commit: `4a53b744`
- T3 — S3 lazy router assembly plus the dashboard cold-import regression — commit: TBD

## Log

### L1 — Operator request
> primero hay cosas, al parecer la ejecucion de multiples tools esta fallando. o algo incluso mas allá dentro del harness. luego no hay certeza de que esten todos los tools realmente funcionando.

### L2 — Reproductions supplied for this unit
```sh
uv run python -c "import app.services.conversations as c; import app.panel.api.routes.conversations"
```
Output:
```text
ImportError: cannot import name 'assign' from partially initialized module 'app.services.conversations'
  (most likely due to a circular import) (/app/app/services/conversations.py)
```

The first cold `conversations.*` tool call imports the service lazily and fails; a later call succeeds. This reproduction was supplied as the observed production defect; it has not yet been rerun in this worktree.

### L3 — Test-first RED
Command:
```sh
uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_conversations_import_cycle.py
```
Observed: exit code 1; 3 failed, 104 passed in 4.74s.
- `test_assistant_capabilities_omits_opt_in_tools_outside_effective_whitelist`: expected count 2, observed 33.
- `test_assistant_capabilities_lists_enabled_opt_in_tool`: expected count 3, observed 33.
- `test_conversations_service_imports_before_panel_api_and_first_tool_call_succeeds`: subprocess exit code 1 with the ImportError above.

### L4 — GREEN
The same focused command passed: 107 passed in 4.15s (exit code 0). The cold subprocess emitted its asserted `COLD_CONVERSATIONS_TOOL_OK` marker.

### L5 — Parent review: one honesty defect fixed, one claim verified independently
- The delivered fallback prefixed every answer with `Available in this turn's scope:` — including the
  no-whitelist path, where the list is the global 33-tool catalog. The header would lie precisely where the
  list is widest. RED first: `assert "turn's scope" not in result["capabilities"]` added to
  `test_assistant_capabilities_without_whitelist_keeps_global_catalog_shape` failed; the header is now
  conditional on a whitelist actually arriving.
- The cold-import claim was re-verified by the parent directly, not from the worker's report:
  `uv run python -c "import app.services.conversations; import app.panel.api.routes.conversations"` →
  `COLD_IMPORT_OK` (exit 0). On `origin/main` the same ordering raised the ImportError quoted in S1.
- `tests/conftest.py` already exports the settings it sets through `os.environ` and already spawns
  subprocesses with `os.environ.copy()`, so the subprocess-based regression follows the repository pattern
  rather than inventing one.
- **L6** (gates and delivery state): `bash scripts/test.sh full` → exit 0 on the final tree (the two warnings are pre-existing and outside this diff: an unawaited `_publish_all` coroutine in `tests/integration/test_webhook_ingest.py` and the FastEmbed mean-pooling notice in `tests/spec/test_projects_spec.py`). Focused unit run → 0; the assistant chat/guardrails integration files → 0. Delivered as two commits, `e6c69ac4` (S1, 44 authored lines) and `4a53b744` (S2, 75). Not pushed at the time this entry was written; push and PR stay the owner's decision.
- **L7** (S3, found by the new tool probe): `scripts/probe_assistant_tools.py` reported `dashboard.summary`
  failing with `cannot import name 'compute_kpis' from partially initialized module 'app.services.dashboard'`.
  It is S1's defect at a second site, and it is order-dependent: the same probe call had reported `ok` in an
  earlier run where something else had already imported the routes. Fixed at the amplifier instead of a
  second per-service deferral: `app/panel/api/__init__.py` now exposes `build_api_router()` and resolves
  `api_router` through a module `__getattr__`, still built once and still the object
  `app/panel/routes/__init__.py` re-exports. Two new RED tests: importing `app.panel.api` must leave
  `app.panel.api.routes.*` unloaded, and importing `app.services.dashboard` first must still run its tool.
