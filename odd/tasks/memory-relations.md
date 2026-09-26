# ODD: memory-relations

**Branch**: `odd/memory-relations`
**Worktree**: `../lumat-agent-odd-memory-relations`
**Base**: `0de327d4`
**Status**: merged — PR #271 (`06768699`, 2026-09-20). The unit scoped here landed with `app/services/relations.py`, migration `029_memory_relation_resolution.sql`, the memory spec and tests in the same pull request.

## Objective

Close the correctness gap that makes a contradicted memory keep being retrieved as current: judge
newly written assertional memories against their near neighbours, record the verdict as a relation,
and annotate the verdict on every read path — with a human queue for the cases the judge is not sure
about.

## Problem (verified)

- `memory_relations` (`app/models.py:524-539`) is fully designed and never written. The only touches
  anywhere are FK re-pointing during folds (`app/services/tukulpan.py:199-205`,
  `app/services/projects.py:295-303`). No path inserts a relation.
- The vocabulary is already declared: `db/migrations/009_memory.sql:46` —
  `supersedes|conflicts|related|compatible|scoped|not_conflict`, mirroring Engram's `mem_judge`.
- The candidate gate is already declared: `app/services/tukulpan.py:57` —
  `REL_MIN_SIM = 0.85  # cosine pair gate for suggest_relations (S3+)`. What was never decided is
  *who judges*, not *how candidates are found*.
- `hybrid_search` (`app/services/tukulpan.py:609-680`) ranks by fused similarity only. It does not
  consult relations, and it does not filter `status` — so an `ARCHIVED` memory is still retrieved,
  and `status` is only projected into the result dict (`:665-678`).
- `load_customer_context` (`app/services/tukulpan.py:683-699`) loads every customer memory and
  injects it into the WhatsApp responder prompt with no interpretation
  (`app/chat/nodes/respond.py:81-99`).
- Consequence: `"the customer prefers afternoons"` and `"the customer prefers mornings"` are both
  returned, both presented as current, and the model picks by similarity.
- Deferred by the original design (`openspec/changes/archive/2026-08-20-memoria-persistente-lumat/design.md:16`),
  restated in the live spec boundary (`openspec/specs/memory/spec.md:211-213`), and explicitly handed
  to this worker by the decay unit (`odd/tasks/memory-decay-ttl.md:41-43`): *"does not become false in
  90 days, it becomes false when contradicted — which is the relations worker's job"*.

## Decisions (agreed with the user — do not re-litigate)

| Decision | Value |
|---|---|
| Judge model | **Hybrid.** The LLM *proposes*; a confidence threshold decides; a human resolves the rest |
| Authority | The LLM is never the authority and never destructive. It cannot delete, hide, or rewrite a memory |
| Candidate gate | Cosine similarity ≥ `REL_MIN_SIM` (0.85), already declared — **no new constant** |
| Auto-annotate threshold | `confidence ≥ 0.7`; below that the pair lands in the human queue (Engram's own rule) |
| Read path | **Annotate, never hide** — same choice the user made for decay's injection path |
| `ARCHIVED` | **Excluded** from retrieval: a human explicitly retired it |
| `NEEDS_REVIEW` | **Annotated, not excluded** — it means "look at me", the content may still be valid. The system must not write it (decay decision) |
| Ephemeral types | `SESSION` / `SUMMARY` (`DECAYING_TYPES`) are **not judged**: snapshots are not assertions to contradict |
| Human queue | **In scope.** Judgment endpoint + panel surface. A queue nobody can act on is not a queue |
| Explicitly skipped | embedding-similarity dedup, automatic deletion, `NEEDS_REVIEW` as a system signal, outbox/async processing (see Notes) |

## Authorized scope

- `db/migrations/` — one additive migration for relation resolution (see T1).
- `app/models.py` — the matching columns on `MemoryRelation`.
- `app/services/relations.py` — new: candidate gate, judge call, relation recording.
- `app/services/tukulpan.py` — read paths (`hybrid_search`, `load_customer_context`) and the
  assertional write call sites.
- `app/services/llm.py` — only if the existing client surface must be extended; prefer reusing it.
- `app/panel/api/routes/` + `serializers.py` — the pending-queue list and the judge endpoint.
- `web/src/components/domain/` + any panel page wiring — the queue surface.
- `openspec/specs/memory/spec.md` — a new `MEM-11`; update the boundary sentence if the deferral
  changes.
- `odd/tasks/memory-relations.md` — this record.
- `tests/` — backend; `web/src/**/*.test.tsx` — vitest/RTL.

## Out of scope (do not touch)

- **The outbox worker has no runner.** `app/ops/worker.py` is a correct, tested, lease-safe worker
  whose process is not started by anything: `infra/docker-compose.prod.yml` has only `api`, `db`,
  `nginx`, `certbot`; the only systemd unit is certbot's; the only cron in `docs/ops.md:355` is
  `daily_summary`. So this unit runs **inline at the write path**, not through `DomainEvent`. Raising
  the missing runner is its own work unit — do not fold it in here.
- Batch compression, the user-prompt store (`MemoryType.PROMPT`), memory sync, WhatsApp memory push.
- The catch-up deploy of the commits production is behind. Separate concern, separately decided.
- Any change to the embeddings model or to `MEM_MIN_SIM` / `FTS_BOOST`.
- Deduplication behaviour, including semantic near-duplicate merging (deliberately deferred: a
  silent false-positive merge is irreversible loss).

## Implementation contract

1. **One place owns the judge.** `upsert()` stays storage-only — its docstring already states the
   service stages rows and never commits (`app/services/tukulpan.py:10-13`). Do not call an LLM from
   inside it. Keep the judged pass in `app/services/relations.py` and call it explicitly.
2. **Never guess on a bad answer.** If the judge call fails, times out, or returns anything that does
   not validate against the expected JSON shape, **record no relation**. A missing relation is a
   no-op; a fabricated one is a false statement about a customer's data.
3. **Bounded work.** The judge sees at most `top_k` candidates and makes **one** LLM call per written
   memory, not one per pair. No unbounded scans; the pair search is scoped to
   `(proyecto, scope, entity_id)`.
4. **Additive schema only.** The new columns are nullable/defaulted so existing rows stay valid and no
   backfill is required.
5. **Read paths annotate.** `hybrid_search` gains the relation/verdict signal in its result dict;
   `load_customer_context` renders it in the injected block. Neither may silently drop a row on the
   basis of staleness. `ARCHIVED` is the only exclusion, and it is a human decision.
6. **The queue must be resolvable end to end.** A pending pair must be listable, judgable, and must
   stop being pending once judged. If the UI is not wired, the requirement is not met.
7. **Reuse the existing LLM plumbing and its test doubles.** Do not invent a second client, a new
   configuration surface, or a new mocking pattern. No new runtime dependency.
8. **Cost stays bounded and visible.** The judge runs only for assertional writes (never for
   `DECAYING_TYPES`), and only when a candidate pair exists. Do not wire the panel cost gate; do not
   add a background poller.

## Tasks

- [ ] **T1 — Resolution schema.** Additive migration on `memory_relations`: how the row was produced
      (`judge` vs `human`) and when it was human-resolved. Plus the index the pending query needs.
      `MemoryRelation` gains the matching columns.
- [ ] **T2 — Candidate gate.** `app/services/relations.py`: cosine pair search within
      `(proyecto, scope, entity_id)` at `REL_MIN_SIM`, bounded to `top_k`, excluding self, excluding
      `ARCHIVED`, skipping `DECAYING_TYPES`. Pure DB, no LLM.
- [ ] **T3 — Judge.** One LLM call per written memory returning one verdict per candidate: relation +
      `confidence` + `reason`. Strict JSON validation; malformed or failed ⇒ no relation written.
      `≥ 0.7` is recorded as judged; below is recorded as pending for the queue.
- [ ] **T4 — Write-path wiring.** Call the judged pass from the assertional write paths
      (`upsert` callers: the agent tool at `app/chat/assistant/tools/registry.py:264` and the panel
      route at `app/panel/api/routes/clients.py:214`), after the row is staged. Nothing on the
      per-turn `SESSION` path (`app/chat/graph.py:266`) — those rows are not judged.
- [ ] **T5 — Read path.** `hybrid_search` excludes `ARCHIVED`, exposes the relation verdict, and
      annotates `NEEDS_REVIEW`; `load_customer_context` annotates the contradicted/superseded line.
      Never hide on staleness.
- [ ] **T6 — Human queue API.** List pending pairs (scoped to a client) and judge one: verdict →
      relation updated, marked human-resolved, no longer pending. Reuse the existing panel auth and
      serialization conventions.
- [ ] **T7 — Panel surface.** A pending-relations surface in the panel where a human sees both
      contents and resolves the pair, plus a vitest/RTL test. Today the UI wires **no** memory
      mutation at all (`web/src/components/domain/ClientFicha.tsx:147-152`), so this is net-new wiring;
      keep it minimal.
- [ ] **T8 — Verify.** Focused tests, then the full backend suite, then the web suite and typecheck,
      with counts measured and reported.

## Acceptance criteria

1. Writing a contradicting assertional memory produces a `memory_relations` row with a verdict,
   `confidence`, and `reason` — proven by a test, not asserted.
2. A judge failure, timeout, or malformed response writes **no** relation and does not fail the write
   it was judging (proven by a test that forces each).
3. `SESSION`/`SUMMARY` writes never trigger a judge call (proven by a test).
4. `hybrid_search` no longer returns `ARCHIVED` rows, and still returns `NEEDS_REVIEW` rows annotated
   as such (proven by tests).
5. A pending (below-threshold) pair is listable through the API, resolvable through the API, and stops
   being pending — verified with a real request, not by assertion.
6. The panel surface lists a pending pair and resolves it; the vitest test covers the wiring.
7. The full backend suite and the web suite are green, and the baseline counts are measured **before**
   anything is changed.
8. No LLM call is made when no candidate pair exists above `REL_MIN_SIM` (proven by a test).

## Checks

TDD mode: **strict, enabled** — source `openspec/config.yaml` (`testing.strict_tdd: true`,
`apply.tdd: true`), recorded in `sdd/lumat-agent/testing-capabilities` (#1554). RED before GREEN,
then refactor. Do not invent evidence.

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(infra/test-db.sh env)"        # REQUIRED before pytest, or role alteration fails
uv run pytest tests/                  # runner; do NOT use `python -m pytest`
```

```bash
cd web && npm test                    # vitest run
cd web && npx tsc -b                  # typecheck
```

`pyproject.toml` sets `addopts = "-q"` — a second `-q` suppresses the summary line. There is no
linter, formatter, type checker, or pre-commit for the backend: the tests are the verification.

## Graph Check

Graph was built at `26b463a2`; this base is `0de327d4`. It is **stale**. Nodes to consult:
`tukulpan.py` (community hub), `app_models_memoryrelation`, `app_services_tukulpan_hybrid_search`,
`app_services_tukulpan_fold_duplicate`, `app_services_projects_merge`, `respond.py`, panel
serializers/routes. Record the nodes/edges actually consulted here before editing.

## Progress

- [ ] Worktree created (`odd/memory-relations`, base `0de327d4`); provisioned; `.opencode/tools/package-lock.json` removed.
- [ ] Graph Check.
- [ ] T1–T8.

## Notes for the executor

- `main` moves in parallel — it advanced `fd8c6885 → 0de327d4` during the scoping session alone.
  Re-measure the base before the first write; a pinned base is not a frozen base.
- Other live worktrees are other lines' work: do not touch `lumat-agent-odd-kb-min-sim` or any
  `odd/kb-*` worktree.
- `infra/.env` is absent in a fresh worktree (`rapso worktree provision` does not copy it). Copy it
  from the main worktree or the DB-backed tests will not run.
- The relation vocabulary is fixed by the migration comment; do not invent new values.
- `mem_judge` in Engram is the behavioural reference: it asks the human when confidence is low and
  when the verdict would supersede or conflict with an architecture/policy/decision memory.
