# ODD: tukulpan-memory-closure

Repository-relative locator: `odd/tasks/tukulpan-memory-closure.md`
Worktree: `/home/stefan/repos/lumat-agent-odd-tukulpan-memory-closure` | Branch `odd/tukulpan-memory-closure` | Base `a2092b92` (v2026.09.4)

## Objective

Close every open item of the assistant memory subsystem (`tukulpan`), as listed by the audit
`backlog/memory-subsystem-audit-2026-09-23` (Engram #4769, re-validated at this base).

## Problem

The memory subsystem is shipped and production-working, but five follow-ups and six test gaps
are open. One of them (query-less recall) is a functional gap; the rest are coverage,
advisories and one product surface.

## Why

The audit's own conclusion is that the subsystem cannot be called "complete" while the recall
gap, the untested declared ceiling, the two review advisories and the missing project entry
point stay open. Closing them removes the only functional hole and turns declared-but-untested
behavior into pinned behavior.

## Scope (authorized)

Backend: `app/chat/assistant/tools/registry.py`, `app/services/tukulpan.py`,
`app/services/relations.py`, `app/services/agent_chat.py`.
Specs: `openspec/specs/assistant-tools/spec.md`, `openspec/specs/memory/spec.md`.
Prompts (only if T1 requires it): `agent/prompts/assistant_plan.md`.
Tests: `tests/unit/`, `tests/spec/`, `tests/functional/`, `tests/integration/`, `web/src/**/*.test.tsx`.
Web (T7): `web/src/components/pages/ProjectsPage.tsx`, `web/src/components/domain/AppShell.tsx`,
`web/src/components/domain/panelRoutes.ts`, `web/src/components/pages/AgentChat.tsx`, `web/src/api.ts`.

Out of scope: any change to WhatsApp/n8n flows, the SDB writer, the embedder cache, and the
KB calibration worktree (`odd/kb-calibration-state-restore`, owned by another session).

## Constraints

- **TDD**: ON. Source: `openspec/config.yaml` (`testing.strict_tdd: true`). Runner: `pytest tests/`.
  T1 must show RED before implementation, then GREEN, then REFACTOR. T2-T6 are *pinning* tests of
  already-shipped behavior: they are expected to be GREEN on first run — record that explicitly
  instead of faking RED. T7 follows test-first on the web suite (`npm run test`).
- Do not weaken existing behavior to make a test pass. The own-axes interleave of `memory.read`
  (`registry.py:278-292`, unit `memory-own-read-limit`) is protected: preserve it.
- Smallest honest change per item (ponytail). No new tool, no new table, no new dependency.
- Spec deltas only where behavior actually changes (T1). Pinning tests do not need spec text.

## Tasks

- [ ] **T1 — query-less recall: bounded digest in `memory.read`** (audit item 1)
  Decision taken: **extend the existing read path**, not a new tool and not optional `query`.
  When `scope`/`entity_id` are absent, the own-axes read returns a digest: the existing
  interleave order preserved, plus a bounded per-item projection (bounded `contenido` and the
  identifying metadata), instead of unbounded raw rows.
  Evidence: `registry.py:273-297` (read), `registry.py:222-235` (`_plain` bounds collections, not
  strings), `registry.py:278-292` (interleave), specs `assistant-tools/spec.md:30-61` (AT-8) and
  `memory/spec.md:50-82` (MEM-3).
  Checks: unit test for the digest bound + a test that the digest shape is stable at `limit`;
  AT-8 and MEM-3 amended; existing own-read tests still green.
- [ ] **T2 — AT-10: pin `memory.search` failure degradation** (audit item 2)
  `tests/unit/test_assistant_tool_loop.py:96` only exercises `memory.read`. Parameterize (or add
  a sibling test) for `"memory.search"` and assert status `degraded`, the responder continuation,
  and that the raw exception is absent from the response and evidence (AT-10,
  `assistant-tools/spec.md:210-222`; shared dispatch branch `registry.py:586-591`).
- [ ] **T3 — tukulpan unit test gaps** (audit item 6, part 1)
  Pin, without changing source: `_embed()` retry/backoff (`tukulpan.py:142-160`), service-level
  `update()` missing-ID and embedding failure (`tukulpan.py:589-613`), `_bounded_json()`
  truncation edge that still yields valid JSON (`tukulpan.py:445-455`), `write_recap()` with
  empty `source_message_ids` and bounded `source_tokens` (`tukulpan.py:498-537`), and
  `_write_memory` not leaking raw `str(exc)` as `degraded_reason`
  (`odd/tasks/read-failure-truthfulness.md:197-203`).
- [ ] **T4 — relations duplicate candidate IDs** (audit item 6, part 2)
  Pin `relations._parse_verdicts()` with duplicated candidate IDs (`app/services/relations.py:61-94`),
  style `tests/spec/test_memory_relations_spec.py:158-195`.
- [ ] **T5 — pin the declared two-writer ceiling** (audit item 3)
  Pin, do not "fix": `tukulpan.py:340-341` declares two concurrent writers as the ceiling. Add an
  integration test in the style of `tests/integration/test_memory_write_conflict.py` proving a
  third writer re-raises instead of silently half-applying.
- [ ] **T6 — project authorization inside the turn failure boundary** (audit item 5)
  `_thread_project_authorization()` runs before the turn's `try` (`agent_chat.py:633-640`), so its
  failure escapes the turn handler (`agent_chat.py:749-773`) and lands in the outer wrapper
  (`agent_chat.py:781-810`). Move it inside the protected boundary or catch it and write the same
  bounded failure metadata. **Open decision**: same user-visible failure as an ordinary turn, or a
  distinct authorization diagnostic.
- [ ] **T7 — panel entry point: open a conversation bound to a project** (audit item 4)
  Threads already carry `proyecto` (migration 031) and the API accepts it
  (`app/panel/api/routes/chat.py:55-81`), but the UI never binds it: `createChatThread()` posts
  `{}` (`web/src/api.ts:102-108`, `AgentChat.tsx:535-545`) and the project page only shows SDB
  artifacts (`ProjectsPage.tsx:13-30`). **Open decision**: where the entry point lives and whether
  the project binding is URL-addressable.

## Delivery

- Strategy: `ask-on-risk` (default). Forecast at planning: **~780 authored changed lines**
  (T1 ~120, T2 ~30, T3 ~200, T4 ~40, T5 ~80, T6 ~60, T7 ~250) → **over the 400-line review budget,
  so chained PRs are required** unless the maintainer accepts `size:exception`.
  Chain strategy: **not chosen yet** (must be `stacked-to-main` or `feature-branch-chain`).
- Work-unit commits on this branch, tests and docs with their behavior, Conventional Commits.
- Push, PR and merge stay human decisions.

## Progress

- Worktree + record created. No task started.
- Re-validated context: audit #4769 still holds at base `a2092b92`; the audit's "hardcoded 22
  tools" claim is stale (current whitelist: 21 entries, `agent/registry.yaml:59-79`).

## Next step

T1 (decision already taken), then T2/T3/T4/T5 (mechanical pinning), then resolve T6/T7 decisions.
