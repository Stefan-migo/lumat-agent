# ODD — chatbot-assistant-settings-write

Feature: `chatbot-assistant-settings-write` (Frente 2, unit 3 — approval loop)
Branch: `odd/chatbot-assistant-settings-write` · Cut from `origin/main` = `41cee9f4`
Delivery: single PR · Test runner: `uv run pytest tests/`

## Objective

Close the Frente 2 loop: the panel assistant can **propose → (human approves) → apply** a
Nivel 1-2 chatbot settings change live, audited, without a deploy. One new **approval-gated
write** tool, `settings.update`, bounded by a server-side allowlist. No new UI — the existing
assistant approval flow (`issue_approval` → `approve_plan`) already applies it.

## Specs

**S1 — `settings.update` (write, approval-gated).**
Args `SettingsUpdateArgs`, `extra="forbid"`: `key: str` (required), `value: Any` (required).
`read_only=False`, tier `default`. In `APPROVED_WRITE_ALLOWLIST` (never
`AUTONOMOUS_WRITE_ALLOWLIST`). Roles: **ADMIN only** — matching the panel Settings server-side
guard (`require_admin_json`); OPERADOR/TECNICO denied.

**S2 — Writable-key allowlist (server-side, single source of truth).**
`ASSISTANT_WRITABLE_SETTINGS` in `app/services/settings.py` = exactly:
`tone.style`, `messages.greeting`, `messages.greeting_short`, `messages.farewell`,
`messages.clarification`, `messages.cannot_answer`, `messages.out_of_hours`,
`hours.timezone`, `hours.schedule`. Any other key → `ToolValidationError`.

**S3 — Value validation per key** (`validate_assistant_setting`, raises `ValueError`):
- `tone.style` ∈ `TONE_STYLES`.
- `messages.<key>`: non-empty `str` (stripped).
- `hours.timezone`: non-empty `str` and a valid IANA zone (`ZoneInfo`).
- `hours.schedule`: `list` of `{days: [int 1..7, unique across entries], open: "HH:MM",
  close: "HH:MM"}`, `open < close` — mirroring `routes/settings.py::_parse_hours`.

**S4 — Handler `_update_setting(session, args)`:**
validate → `set_setting(session, key, value, actor="assistant")` → return
`{"key": key, "value": value, "updated": True}`. No commit in the handler (the run commits);
`set_setting` already writes the `settings.change` audit.

**S5 — Approval gate.** Without a consumed, exact-match approval, `execute_tool` refuses
(`"write tool requires consumed exact approval"`); with it, the change applies exactly once.

**S6 — Wiring.** `TOOL_REGISTRY` + `ROLE_TOOL_ALLOWLIST` (ADMIN) +
`agent/registry.yaml` `assistant.tools_whitelist` + `DEFAULT_TOOLS` in BOTH
`tests/unit/test_tool_tiers.py` and `tests/unit/test_effective_config.py` + the planner-catalog
SHA-256 pin in `tests/unit/test_assistant_delegation.py`.

**S7 — Subagents never mutate settings.** `settings.update` is whitelisted only on
`assistant:` (never on any `sub_agents:` scope). Tool description lists the valid keys.

**S8 — No UI change.** The existing approval-and-apply flow is reused; this unit is backend-only.

## Tasks

| ID | Task | Specs | Route |
|---|---|---|---|
| T1 | RED+GREEN: `ASSISTANT_WRITABLE_SETTINGS` + `validate_assistant_setting` (tone/messages/hours) + tests | S2,S3 | inline |
| T2 | RED+GREEN: `SettingsUpdateArgs` + `_update_setting` handler + tests (allowed key writes + audits; disallowed key + bad value refuse) | S1,S2,S3,S4,S8 | inline |
| T3 | RED+GREEN: register the tool (read_only=False, tier default, `APPROVED_WRITE_ALLOWLIST`, ADMIN role); approval-gate test | S1,S5 | inline |
| T4 | Wire `agent/registry.yaml` + both `DEFAULT_TOOLS` sets + planner-catalog SHA pin + assistant-catalog unit tests | S6,S7 | inline |
| T5 | Checks: targeted + full `uv run pytest tests/ -q` | — | inline |

Single writer; each task closes with one work-unit commit (≤5 files).

## Constraints (verified)

- **Strict TDD ON** (`openspec/config.yaml:28,:38`). RED before implementation.
- Panel Settings is **ADMIN only** (`routes/settings.py:190` `require_admin_json`) → the tool is
  ADMIN only, consistent with the panel it mirrors.
- Adding a tool breaks THREE pinned places: `test_tool_tiers.py` DEFAULT_TOOLS,
  `test_effective_config.py` DEFAULT_TOOLS, and the planner-catalog SHA-256 in
  `test_assistant_delegation.py`.
- Tool must be in `TOOL_REGISTRY` **and** `assistant.tools_whitelist` or the catalog drops it.
- Write tools in `APPROVED_WRITE_ALLOWLIST` still require a consumed approval in `execute_tool`.
- `set_setting` audits `settings.change`; the approver is recorded by `approve_plan`.
- Schedule/timezone validation mirrors `routes/settings.py::_parse_hours` (which raises
  HTTPException); the service validator raises `ValueError` and does not touch the route.
- Test DB: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"`.

## Acceptance criteria

- AC-1: `settings.update` is registered, `read_only=False`, tier `default`, in
  `APPROVED_WRITE_ALLOWLIST`, ADMIN-only (OPERADOR/TECNICO denied), whitelisted, not on subagents.
- AC-2: an allowed key + valid value applies via `set_setting` and writes the audit.
- AC-3: a key outside `ASSISTANT_WRITABLE_SETTINGS`, or an invalid value, is refused and does NOT
  write.
- AC-4: without a consumed matching approval the write is refused; with it, applied once.
- AC-5: `uv run pytest tests/ -q` green.

## Checks

- `uv run pytest tests/integration/test_assistant_settings_write.py tests/unit/test_assistant_tools.py tests/unit/test_tool_tiers.py tests/unit/test_effective_config.py tests/unit/test_assistant_tool_roles.py tests/unit/test_assistant_delegation.py -q`
- `uv run pytest tests/ -q`

## Graph nodes consulted

`issue_approval()`, `consume_approval()`, `validate_execution()`, `set_setting()`,
`record_audit()`, `execute_tool()`, `ToolValidationError`, `Assistant`, `write()` —
communities `unit/test_assistant_tools.py` / `services/settings.py` / `Unit`.

## Log

**L1 (user, 2026-10-14, verbatim):** "arranca unidad 3".

**L2 (user, 2026-10-14, verbatim):** "si agrega tambien lo del disponibilidad." — confirma el
allowlist de la unidad 3: tono + mensajes **+** `hours.schedule` / `hours.timezone`.

**L3 (design ref, `odd/handoffs/chatbot-config-and-assistant-tools.md`):** Nivel 1-2 = settings
→ `set_setting` en vivo, auditado, reversible, sin deploy. Escritura = aprobar-y-aplicar (el
contrato de tools ya tiene `requires_approval`). Un subagente NO muta settings solo.

**L4 (evidence, 2026-10-14):** T1–T5 done in `odd/chatbot-assistant-settings-write`. RED→GREEN observed
for T1 (`ImportError: cannot import name 'ASSISTANT_WRITABLE_SETTINGS'`). End-to-end approval loop
proven: `approve_plan` applies `messages.farewell` through the real graph. Adding the tool moved the
planner-catalog SHA-256 pin (`f4bc1a5c…`); verified the only catalog delta is `settings.update`. Full
backend suite green.

**L5 (verification, 2026-10-14):** independent verifier: S1–S8 met, **no blockers**. Security
invariants held — 10 disallowed keys each refused with a valid consumed approval, approval binds
exact arguments (mismatch/unconsumed/reuse refused), OPERADOR/TECNICO denied even with an approval,
non-autonomous. Advisory actioned: `messages.*` had no size bound → added a 2000-char cap
(`ASSISTANT_MESSAGE_MAX_LENGTH`); the schedule is already bounded (≤7 entries by unique-weekday).
Added the verifier's durable probes (near-miss/privileged keys, approval-bound-to-other-args,
unconsumed approval). Full suite green again.

## Progress

- [x] T1 — `b3affa8c` feat: `ASSISTANT_WRITABLE_SETTINGS` + `validate_assistant_setting` (+19 unit tests)
- [x] T2+T3 — `76ece3cd` feat: register `settings.update` (args, handler, `TOOL_REGISTRY`, `ROLE_TOOL_ALLOWLIST` ADMIN-only, `APPROVED_WRITE_ALLOWLIST`) + pinned contracts
- [x] T4 — `ebaf58f2` test: typed/registration/roles unit test + approval-loop integration coverage
- [x] T5 — full suite `uv run pytest tests/` exit 0

## Next step

Unit 3 complete pending PR + review. Do NOT start unit 4 (prompt PRs — owner standby).
