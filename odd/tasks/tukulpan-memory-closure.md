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
- T1 reuses the existing read path because the human decided it (see T1). No new persisted
  schema or new dependency without an explicit human decision.
- Spec deltas only where behavior actually changes (T1). Pinning tests do not need spec text.

## Tasks

- [x] **T1 — query-less recall: bounded digest in `memory.read`** (audit item 1)
  Decision taken: **extend the existing read path**, not a new tool and not optional `query`.
  When `scope`/`entity_id` are absent, the own-axes read returns a digest: the existing
  interleave order preserved, plus a bounded per-item projection (bounded `contenido` and the
  identifying metadata), instead of unbounded raw rows.
  Evidence: `registry.py:273-297` (read), `registry.py:222-235` (`_plain` bounds collections, not
  strings), `registry.py:278-292` (interleave), specs `assistant-tools/spec.md:30-61` (AT-8) and
  `memory/spec.md:50-82` (MEM-3).
  Checks: unit test for the digest bound + a test that the digest shape is stable at `limit`;
  AT-8 and MEM-3 amended; existing own-read tests still green.
  Status: **accepted**. Code + tests + spec clauses committed (`3f243d18`, `52149dce`,
  `243d0cbb`, `c35c67c0`). Independent verification: mutation check proved the digest test
  load-bearing; ORM projection verified against `app/models.py:480-520` (`contenido` is
  `NOT NULL`, `app/models.py:490`, `db/migrations/009_memory.sql:28`); no consumer depends on the
  untruncated own read. Acceptance evidence: `tests/unit + tests/spec + guardrails` green.
- [x] **T2 — AT-10: pin `memory.search` failure degradation** (audit item 2)
  `tests/unit/test_assistant_tool_loop.py:96` only exercises `memory.read`. Parameterize (or add
  a sibling test) for `"memory.search"` and assert status `degraded`, the responder continuation,
  and that the raw exception is absent from the response and evidence (AT-10,
  `assistant-tools/spec.md:210-222`; shared dispatch branch `registry.py:586-591`).
  Status: **accepted** (`02768888`). Parameterized over `memory.read`/`memory.search`; asserts the
  bounded payload and that the raw error is in neither response nor evidence.
- [x] **T3 — tukulpan unit test gaps** (audit item 6, part 1)
  Pin, without changing source: `_embed()` retry/backoff (`tukulpan.py:142-160`), service-level
  `update()` missing-ID and embedding failure (`tukulpan.py:589-613`), `_bounded_json()`
  truncation edge that still yields valid JSON (`tukulpan.py:445-455`), `write_recap()` with
  empty `source_message_ids` and bounded `source_tokens` (`tukulpan.py:498-537`), and
  `_write_memory` not leaking raw `str(exc)` as `degraded_reason`
  (`odd/tasks/read-failure-truthfulness.md:197-203`).
  Status: **accepted** (`c204880b`, `16f57d1d`, `6d21725b`). Five of five pinned. Four were pinning
  only (`_embed` retries/backoff/final log, `update()` missing-ID + embedding failure,
  `_bounded_json` byte bound with valid JSON, `write_recap` empty sources + token bounds). The
  fifth became a real fix by human decision: `_write_memory` and its siblings returned the raw
  `str(exc)` as `degraded_reason` (`registry.py:382`, `:416` update, `:426` delete, and
  `tukulpan.py:537` recap) — a documented deferral (`read-failure-truthfulness.md`, "Remaining
  backlog") whose recap variant was pinned as expected by a pre-existing spec test. Now each site
  returns an operation-specific bounded reason ("Memory write/update/delete/recap unavailable")
  and the raw detail goes to the server log, matching the read path's contract
  (`nodes.py:712`). The deferral note in that doc was closed with a single line, not rewritten.
  Evidence: `tests/unit + tests/spec` exit 0. The writer reported two failures in
  `tests/integration/test_assistant_harness_session.py` (thread creation) that it could not
  attribute; the parent re-run is **green (11 passed, exit 0)**, so it is recorded as an
  unreproduced signal, not as a candidate-caused failure.
- [x] **T4 — relations duplicate candidate IDs** (audit item 6, part 2)
  Pin `relations._parse_verdicts()` with duplicated candidate IDs (`app/services/relations.py:61-94`),
  style `tests/spec/test_memory_relations_spec.py:158-195`.
  Status: **accepted** (`189a2b1d`). Pinned: a duplicated `candidate_id` is rejected
  deterministically (`ValueError("invalid verdict value")`) and no relation is attributed.
- [x] **T5 — pin the declared two-writer ceiling** (audit item 3)
  Pin, do not "fix": `tukulpan.py:340-341` declares two concurrent writers as the ceiling. Add an
  integration test in the style of `tests/integration/test_memory_write_conflict.py` proving a
  third writer re-raises instead of silently half-applying.
  Status: **accepted** (`fc2af216`). Deterministic event choreography (no sleeps) forces the third
  writer to lose both bounded attempts and re-raise `IntegrityError`, with only the second
  writer's row persisted. Parent re-ran it three times consecutively: exit 0 each.
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

- [x] **T8 — align the public memory scope contract across spec, prose and prompt** (found by
  T1's independent verification; human decided to close it inside this unit)
  The code contract is `scope="own" | "customer"` (`registry.py:95-101`, discriminated union);
  the server derives the panel and agent axes internally. Three artifacts still describe
  `panel`/`agent` as public tool scopes:
  1. AT-8's own scenarios: `assistant-tools/spec.md:34-46` ("Panel read binding", "scope outside
     `panel` or `customer`") and `:63-71` ("Canonical agent scope"). T1's rewrite of AT-8's
     requirement sentence left them contradicting it.
  2. The compaction prompt tells the assistant to use a scope that validation rejects:
     `app/chat/assistant/nodes.py:263-265` ("Pull it with memory.read with scope=panel and no
     entity_id"). The guardrail rejects the plan and falls back
     (`test_assistant_harness_guardrails.py:506-515`), so the recap cannot be pulled after a
     compaction — a live functional gap, not a cosmetic one.
  3. Tests asserting the stale instruction: `tests/unit/test_assistant_planner.py:578-590` and
     the guardrail fixture above.
  Also fold in the verification advisory: assert the digest bound once against the **real ORM
  path** (the existing DB-backed assertion in `tests/spec/test_memory_spec.py:872-879` exercises
  the projection but does not assert the bound; the unit digest test is mock-based).

## Delivery

- Strategy: `ask-on-risk` (default). Forecast at planning: **~840 authored changed lines**
  (T1 ~120, T2 ~30, T3 ~200, T4 ~40, T5 ~80, T6 ~60, T7 ~250, T8 ~60) → **over the 400-line review
  budget, so chained PRs are required** unless the maintainer accepts `size:exception`.
  Chain strategy: **`stacked-to-main`** (human decision). Slices, each targeting `main`:
  1. `odd/tukulpan-memory-closure` — T1 + T8 (done).
  2. `odd/tukulpan-memory-pinning`, stacked on slice 1 — T2 + T3 + T4 + T5.
  3. `odd/tukulpan-memory-surface`, stacked on slice 2 — T6 + T7.
  Each slice's diff reduces to its own work once its predecessor merges. Resolve the `chained-pr`
  skill by registry name before planning or creating any PR.
- Work-unit commits, tests and docs with their behavior, Conventional Commits.
- Push, PR and merge stay human decisions.

## Progress

- Worktree + record created.
- **T1 accepted** (`3f243d18`, `52149dce`, `243d0cbb`, `c35c67c0`): owned digest bounded to 500
  characters, interleave preserved, entity-scoped reads untouched, AT-8/MEM-3 amended.
- **T8 accepted** (`4d742ad5`, `bea3a589`, `ac2c8464`): the compaction prompt now uses the real
  `scope=own` (it was ordering a call validation rejects, which silently lost the recap after a
  compaction), AT-8's scenarios describe the real contract, and the digest bound is asserted on
  the real ORM path.
- **T2 accepted** (`02768888`): AT-10's `memory.search` degradation is now pinned alongside
  `memory.read`, with the raw error asserted absent from response and evidence.
- **T3 accepted** (`c204880b`, `16f57d1d`, `6d21725b`): four contracts pinned; the fifth turned
  into a real fix — the write path no longer returns raw `str(exc)` as `degraded_reason`.
- **T4 accepted** (`189a2b1d`) and **T5 accepted** (`fc2af216`): slice 2 (pinning) is complete.
- Verification of record for T1+T8: `tests/unit + tests/spec + tests/integration/test_assistant_harness_guardrails.py`
  → exit 0, tree clean.
- Slice 2 verification of record: `tests/unit + tests/spec` and
  `tests/integration/test_memory_write_conflict.py` → exit 0, the concurrency test re-run three
  times consecutively (exit 0 each), tree clean.
- Authored lines: **501** on the branch against base (slice 1 ≈ 308, slice 2 = 193), task doc
  included.
- Decisions taken by the human: T1 = extend `memory.read`; T8 = align everything to `own`/`customer`;
  T3.5 = sanitize the write path's `degraded_reason` family; delivery = `stacked-to-main`.
- Re-validated context: audit #4769 still holds at base `a2092b92`; the audit's "hardcoded 22
  tools" claim is stale (current whitelist: 21 entries, `agent/registry.yaml:59-79`).
- Findings the audit did not have: T8 (the planner prompt ordering an invalid scope) and T3.5's
  real severity (a documented deferral, not a missing test). Both came from verifying the
  candidate instead of trusting the doc.

## Next step

T4 + T5 (mechanical pinning, no open decisions) close slice 2, then resolve the T6/T7 open
decisions for slice 3.
