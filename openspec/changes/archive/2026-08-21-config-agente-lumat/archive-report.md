# Archive Report: config-agente-lumat

**Change**: `2026-08-21-config-agente-lumat`
**Project**: LumatAgent
**Status**: CLOSED
**Date**: 2026-08-21
**Agent**: sdd-archive (`sdd-archive` skill, delegate executor)
**Artifact store**: hybrid (openspec files on disk + engram persistence)
**Branch**: `feat/config-agente-lumat-s3` (stacked-to-main chain s1/s2/s3; PRs #43/#44/#45 OPEN — not created/merged here)

## Executive Summary

Closed the config-agente-lumat change: a behavior-preserving extraction moving every LLM-facing prompt out of hardcoded node constants into a declarative `agent/` tree (personas/, prompts/, skills/, registry.yaml) behind a single loader (`app/services/prompts.py` with `load()` + strict `render()` and frozen literal FALLBACKS). Implementation is 100% (15/15 tasks, incl. phases 1–4), verification PASS (native `sdd-verify-validate` valid, verdict pass, 8/8 requirements, 11/11 scenarios, 464/464 full suite on fresh migrated test DB, unit 26/26, 0 CRITICAL / 0 WARNING). Delta spec synced to main specs (`openspec/specs/agent-config/` created). Change folder moved to `openspec/changes/archive/2026-08-21-config-agente-lumat/`. Delivery via the open stacked chain (PRs #43/#44/#45) — merge in order.

## Final-State Authority

The following facts describe the change AT CLOSE (highest-ranked sources):

- **Native review authority (`reviewGate`)**: structurally ABSENT — receipt-driven development is NOT enabled for this candidate (no kill switch, no discovered review artifact). Archive proceeds under ordinary repository policy; zero review code ran and nothing to read or block on. Per the Native Review Receipt Gate, absence is not a defect to investigate.
- **Persisted tasks artifact** (`openspec/changes/archive/2026-08-21-config-agente-lumat/tasks.md`): **15/15 implementation tasks marked `[x]`**, including Phase 4 (4.1 README D6 triggers, 4.2 dead-constant cleanup). No stale unchecked implementation boxes. Task Completion Gate passed without reconciliation.
- **Explicit final-state facts (orchestrator launch prompt)** — forward the authoritative final counts:
  - Verify PASS: all 8 requirements (AC-1..AC-8) / 11 scenarios COMPLIANT.
  - Full suite **464/464 passed** against a fresh migrated test DB; unit **26/26 passed**.
  - **0 CRITICAL / 0 WARNING** (per `gentle-ai sdd-verify-validate`: valid, verdict pass).
  - All 15 tasks complete.
  - Agent README stale-reference issue RESOLVED by follow-up docs commit `0649d0bc` ("docs(agent): refresh README after node constant removal") — the SUGGESTION finding in verify-report is closed.
  - `verify-report.md` EXISTS in the change folder (was uncommitted; committed as part of this archive).
  - Runtime ledger: all attempt objectives closed (complete), no pending remediation.

Per Final-State Authority, no stale `apply-progress`/`verify-report` pending claims are echoed as current facts; the only intermediate claims that mattered (task completion, counts, warnings) are independently confirmed by the higher-ranked sources above.

## Verification Summary (Final)

- Native validator: `gentle-ai sdd-verify-validate` → `valid: true`, verdict **pass**, `blockers: 0`, `critical_findings: 0`.
- Requirements: **8/8 COMPLIANT** (AC-1 Declarative agent/ layout; AC-2 Single loader w/ constant fallback; AC-3 Behavior-preserving extraction; AC-4 Data-only registry; AC-5 Strict typed template rendering; AC-6 Skills as reference files; AC-7 DB-migration triggers documented; AC-8 Test-import compatibility).
- Scenarios: **11/11 COMPLIANT**.
- Tests: **464 passed** (full suite) — `.venv/bin/pytest tests/`, exit 0, on a fresh migrated test DB (`docker compose -f infra/docker-compose.yml --profile test down` + volume rm + up; conftest `migrated_db` ran `db/migrate.sh`). Unit subset: 26/26 passed.
  - output hash `sha256:9cac9cbf12787554fb05a4f48dbf07740f73cea1a020a677376a2a9e5fcbcefc`; build `compileall` for touched modules exit 0, hash `sha256:e3b0c442...`.
- Coverage: N/A (no coverage tool configured in pyproject.toml).
- Warnings: **None** (0 WARNING; the single SUGGESTION about stale README references is resolved by `0649d0bc`).
- CRITICAL: **None** — nothing blocks archive.
- Design coherence: D-A1..D-A8 all followed; design open question (loader test placement) resolved → `tests/unit/` (new DB-free dir with own conftest).
- TDD compliance: 6/6 checks passed (RED-first `tests/unit/test_prompts.py` + conftest; GREEN 26/26 unit + 464/464 full; triangulation ≥2 tests per AC-2/AC-3/AC-5).

## Known Non-Blocking Nuance (documented, final)

- **CM-7 `<memory>` block travels inside `kb_text`**: due to the frozen `prompts/respond.md` template (a `<memory>{{memory}}</memory>` slot is not a separate template section; the memory block is embedded within the `<kb>{{kb_text}}</kb>` value). Content is identical and reachable; `test_memory_pipeline` 3/3 green. This is an intentional, documented layout reality of the frozen template, not a defect. Recorded for the future H2 router / template redesign, not acted on here.

## Per-Capability Delta Sync

| Capability | Status in main specs | Action | Requirements added |
|------------|----------------------|--------|--------------------|
| `agent-config` | Did not exist | **Created** `openspec/specs/agent-config/spec.md` (byte-identical mechanical copy of the delta) | AC-1..AC-8 |

- `agent-config` main spec copied byte-identical from the delta via shell `cp` → `diff -r` → `mv` (empty diff readback), permission normalized to `644` to match sibling specs.
- No MODIFIED / REMOVED / RENAMED deltas existed, so no destructive merge — no warning required per `openspec/config.yaml` archive rule (`Warn before merging destructive deltas`).
- Proposal declares `agent-config` as a NEW capability (not a merge target into `memory` or `conversation-manager`); the memory capability spec covers a separate DB-level memory layer and was untouched.

## Mechanical Copy Contract (readback evidence)

Both mandatory `diff -r` readbacks passed EMPTY (no differences — the only passing evidence):

1. **Spec sync** — source `openspec/changes/.../specs/agent-config/spec.md` vs staged temp → then vs final `openspec/specs/agent-config/spec.md`: empty diff, byte-identical.
2. **Archive move** — pre-move recursive snapshot (`mktemp` snapshot root, `cp -R openspec/changes/config-agente-lumat`) vs `openspec/changes/archive/2026-08-21-config-agente-lumat/`: empty diff, byte-identical. Source directory confirmed absent after the move.
3. Archive-report.md is additive-only (did not exist in the source snapshot) and excluded from the comparison.

No file content passed through the model Read/Write path; `cp -R` / `mv` / `chmod` were the only copy mechanisms. `git` detects the change folder files as renames (`R`) into the archive.

## Task Completion Gate

- Persisted tasks artifact inspected **before** spec sync / archive move: **15/15 `[x]`**, zero `[ ]` boxes. No orchestrator-approved stale-checkbox reconciliation was needed. The archived audit trail contains NO stale unchecked implementation tasks for completed work.

## Delivery State

- **Strategy**: auto-chain, chain strategy = stacked-to-main.
- **Branches / PRs**: `feat/config-agente-lumat-s1` (PR #43), `s2` (PR #44), `s3` (PR #45) — all OPEN, stacked in order. Archive commits land on `feat/config-agente-lumat-s3`; PRs #43/#44/#45 are merged first, then this branch. Do NOT merge/create PRs here (per orchestration).
- Prerequisites on this branch: PR #43/#44 (s1/s2) content already merged into `feat/config-agente-lumat-s3` (commits `2c760a5e`, `57bd0bdf` present in log).

## Graph Notes (cortex 5-Step Execution Gate, Step 1)

- Graph present but **STALE** (built from commit `d8f26896`; HEAD `0649d0bc`); no semantic backend API key → refresh NOT attempted (per orchestration). Structural queries only.
- `graphify query "chat nodes and services touched by agent config change"` (BFS depth 2, start config/AgentChat/AGENTS/nodes-emergency/services-kb) → 490 nodes found (67 shown within token budget). Relevant consult: `respond.py` (Community respond), `classify_intent.py` (Community classify_intent), `summary.py` (Community summary), `state.py` (Community ConversationState), `graph.py` (LangGraph conversation graph), `services/kb.py`, `app/services/prompts.py` (new), `config.py`/`get_settings()`, `llm.py` (`openai_client()`, `CHAT_MODEL`).
- GRAPH_REPORT god nodes / communities consulted: `Message`, `Conversation`, `get_or_create_customer()`, `respond.py`, `classify_intent.py`, `summary.py` community hubs; "app/chat/nodes/ — chat node modules"; `main.ts`/`main.py` config-wiring areas.
- ⚠️ Graph node note: a `prompts.py → respond.py` edge is absent (pre-wiring snapshot at `d8f26896`); expected. Wired wiring verified by unit-level byte-equality (FALLBACKS == agent/*.md) and the full runtime suite instead.
- Graph refresh deferred to session close (per cortex `sdd-archive` integration: update runs once per session at close; if archive closes the session, run `graphify . --update` then).

## Risks / Notes

- **No CRITICAL / WARNING issues.** Nothing blocks archive. Status: **CLOSED** (no intentional partial archive, no warnings-ship).
- Non-blocking documented nuance (CM-7 `<memory>` inside `kb_text`) carried forward to the H2 router / template redesign; `test_memory_pipeline` 3/3 green.
- Open stacked PRs #43/#44/#45 must be merged in order before/with this branch; this archive did not create or merge any PR.
- Graph is stale and was not refreshed (no API key); refresh at session close per cortex gate.

## Engram Persistence

Archive report + graph nodes + final-state facts persisted to Engram observation `sdd/config-agente-lumat/archive-report` (`mem_save`, capture_prompt=false, scope=project lumat-agent).

## Audit Trail Note

The archived folder is immutable per archive policy — no future edits to `openspec/changes/archive/2026-08-21-config-agente-lumat/`; further changes go through a new SDD change.
