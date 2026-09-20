# ODD: memory-decay-ttl

**Branch**: `odd/memory-decay-ttl`
**Worktree**: `../lumat-agent-odd-memory-decay-ttl`
**Base**: `0b9f3c2e`
**Status**: completed

## Objective

Give `review_after` both a writer and a reader. Machine-generated snapshots (`SUMMARY`, `SESSION`)
become visibly stale after their review date; nothing is deleted, nothing is filtered silently, and
everything else is explicitly declared non-decaying.

## Problem (verified)

`review_after` (`app/models.py`, `db/migrations/009_memory.sql:32`) is written by nobody and read by
nobody. `MemoryStatus.NEEDS_REVIEW` is never assigned by the system. `openspec/specs/memory/spec.md`
declares decay deferred and schema-only.

Meanwhile the data grows in a shape that needs it: `write_recap` builds its key as
`assistant-recap:{thread_id}:{last_source_message_id}`, so **every turn writes a new row**. Old recaps
of the same thread are never superseded; they compete on similarity in `hybrid_search` (which orders
by distance, not recency) against the current one. And `SESSION` uses a fixed key that `upsert`
appends to, so it goes stale by *silence*, not by age.

## Product policy (agreed with the user — do not re-litigate)

| Decision | Value |
|---|---|
| What decays | Only `MemoryType.SUMMARY` and `MemoryType.SESSION` |
| Everything else | `review_after = NULL` — never decays on a clock |
| TTL | 30 days |
| Trigger | Lazy: stamped on write, evaluated on read. No cron, no worker |
| Reset | Yes, on every write of a decaying row |
| Tool path (`hybrid_search`) | Adds `stale: true/false` to the result dict |
| Injection path (`load_customer_context`) | **Annotates** the line (user chose this over excluding) |
| Deletion on a clock | Never |
| `NEEDS_REVIEW` | Stays human-set. The system must not write it |

**Why only snapshots.** Most of this memory is *assertional*, not *ephemeral*: "the customer prefers
afternoons" does not become false in 90 days, it becomes false when contradicted — which is the
relations worker's job, not decay's. A TTL on assertional data silently invalidates true facts.
Decay answers *trust by recency*, not correctness.

**Why annotate instead of exclude (injection path).** Excluding is silent invalidation, and the
content is still legitimate history (a March recap is useful in September, it just is not *current
state*). Annotating keeps D4's real principle: never let unverified data present itself as verified.

## Authorized scope

- `app/services/tukulpan.py` — policy constant, two helpers, `_upsert_resolved`, `hybrid_search`,
  `load_customer_context`.
- `openspec/specs/memory/spec.md` — the deferred sentence at `:186` becomes false once this ships;
  replace it and add `MEM-10`.
- `tests/spec/test_memory_spec.py` — `MEM-10` coverage.
- `tests/integration/test_chat_state.py` — annotation coverage, next to `test_s2_from_db_carries_memory_context`.
- `odd/tasks/memory-decay-ttl.md` — this record.

## Out of scope (do not touch)

- Relations worker, batch compression, user-prompt store, sync, WhatsApp memory push.
- Any deletion, any filtering, any ranking change. Stale must not reorder `hybrid_search` results.
- Writing `NEEDS_REVIEW` from the system. The panel keeps that lever (`set_mark`).
- The panel API/serializers: `stale` is not exposed there in this slice.
- Embedding/semantic anything.

## Implementation contract

```python
MEMORY_DECAY_DAYS = 30
DECAYING_TYPES = frozenset({MemoryType.SUMMARY, MemoryType.SESSION})

def _review_after(tipo: MemoryType, *, now: datetime | None = None) -> datetime | None:
    """The review instant for a decaying type, or None when the type never decays."""

def _is_stale(review_after: datetime | None, *, now: datetime | None = None) -> bool:
    """True only when a review instant exists and has passed. None is never stale."""
```

- Export the public names through the module `__all__` the way `MEM_MIN_SIM` / `DEFAULT_TOP_K` are.
- Use aware datetimes (`datetime.now(timezone.utc)`). `review_after` is `TIMESTAMPTZ`; never compare
  an aware value with a naive one.
- `_upsert_resolved`: compute the review instant once per call and assign it on **all three** write
  branches, because the existing code leaves the column untouched and a keyed rewrite would otherwise
  inherit a stale value from a previous life:
  - **insert** → from the incoming `tipo`;
  - **keyed rewrite** → from the incoming `tipo` (the row becomes that type);
  - **fold by hash** (duplicate seen under a different `topic_key`) → from the **row's own** `tipo`,
    not the incoming one: the survivor's lifecycle must not change because a duplicate arrived
    labelled differently. Re-seeing identical content is evidence the memory is still live, so it
    refreshes.
- `hybrid_search`: add `"stale": _is_stale(m.review_after)` beside `"status"`. Do **not** change the
  `where`, the ordering, the `min_sim` gate, or `top_k`.
- `load_customer_context`: compute `now` once, then render
  `f"{m.titulo}: {m.contenido}"` for a fresh row and
  `f"{m.titulo} (stale since {m.review_after.date().isoformat()}): {m.contenido}"` for a stale one.
  Keep one line per memory, keep the existing `titulo: contenido` base, and keep the empty-string
  behaviour when the customer has no memories.
- **Marker language is English** (`stale since YYYY-MM-DD`): it reads as system metadata rather than
  as something the customer said, which is exactly the distinction the marker exists to make.
- No new dependency. `datetime`/`timedelta` are already imported in the module.

## Existing behaviour that must survive

- `test_s2_from_db_carries_memory_context` (`tests/integration/test_chat_state.py:275`) writes a
  `CUSTOMER_MEMO` and asserts `"tarde" in state.memory_context`. `CUSTOMER_MEMO` has
  `review_after = NULL`, so that line must stay **unannotated** and that test must stay green.
- `test_chat_state.py:190` asserts `memory_context == ""` for a customer with no memories.

## Tasks

- [x] **T1 — RED (policy).** `tests/spec/test_memory_spec.py`: `review_after` is set for `SUMMARY` and
      `SESSION` (≈ 30 days ahead), stays `NULL` for `CUSTOMER_MEMO`, `DECISION`, `PATTERN`,
      `PREFERENCE`, `DISCOVERY`, and is refreshed when a decaying row is rewritten.
- [x] **T2 — RED (read path).** `tests/spec/test_memory_spec.py`: a fresh row reports `stale: False`;
      a row whose `review_after` is in the past reports `stale: True`; a row with `review_after NULL`
      reports `stale: False`; and staleness does not change the returned order.
- [x] **T3 — RED (injection path).** `tests/integration/test_chat_state.py`: a stale `SESSION` line is
      annotated with `stale since`; a fresh one is not; a `CUSTOMER_MEMO` is never annotated.
- [x] **T4 — GREEN.** Implement the contract above.
- [x] **T5 — Spec.** Replace `decay` in the deferred sentence at `openspec/specs/memory/spec.md:186`
      and add `### Requirement: MEM-10 — Lifecycle Decay` with RFC 2119 keywords and
      Given/When/Then scenarios. Requirements currently end at `MEM-9`.
- [x] **T6 — Verify.** Focused suites, then the full suite, counts measured and reported.

## Acceptance criteria

1. Each RED test provably failed before the fix, with the failure text recorded in Progress.
2. Non-decaying types keep `review_after NULL` in every path, including the fold branch.
3. Nothing is deleted, filtered, or reordered by staleness.
4. The full suite is green; the baseline at this base is **964 passed**.
5. The diff touches only the five authorized files.

## Checks

```bash
export PATH="$HOME/.local/bin:$PATH"
eval "$(infra/test-db.sh env)"
uv run pytest tests/spec/test_memory_spec.py tests/integration/test_chat_state.py -v
uv run pytest tests/
```

`pyproject.toml` sets `addopts = "-q"` — do not add a second `-q`. No linter, type checker, or
formatter exists; the tests are the verification.

## Progress

- [x] Worktree created and provisioned; `.opencode/tools/package-lock.json` removed.
- [x] Graph Check: `load_customer_context` → `.from_db()` (`app/chat/state.py:225`),
      `run_conversation()`; `hybrid_search` → HL-1 spec; nodes `Memory` (`app/models.py:457`),
      `tukulpan.py`, `test_memory_spec.py`, `test_chat_state.py`.
- [x] T1–T6.

### Implementation progress

- Graph Check: consulted `tukulpan.py`, `_upsert_resolved()`, `hybrid_search()`, `load_customer_context()`, `Memory`, `test_memory_spec.py`, and `test_chat_state.py`; no directed path was available between the service and test nodes, but the affected nodes and Tukulpan community were present in the graph report.
- T1 RED: `uv run pytest tests/spec/test_memory_spec.py -k test_mem10_write_policy_stamps_only_decaying_types -v` failed with `assert None is not None` at `tests/spec/test_memory_spec.py:51`.
- T2 RED: `uv run pytest tests/spec/test_memory_spec.py -k test_mem10_hybrid_search_reports_staleness_without_reordering -v` failed with `KeyError: 'stale'` at `tests/spec/test_memory_spec.py:114`.
- T3 RED: `uv run pytest tests/integration/test_chat_state.py -k test_s2_memory_context_marks_stale_snapshots_only -v` failed with `AssertionError: assert 'session (stale since ' in 'session: stale session content\nfresh summary: fresh summary content\ncustomer memo: permanent customer content'` at `tests/integration/test_chat_state.py:336`.
- T4/T5 GREEN: focused command `uv run pytest tests/spec/test_memory_spec.py tests/integration/test_chat_state.py -v` — `36 passed in 5.62s`.
- T6 full verification: `uv run pytest tests/` — `989 passed, 2 warnings in 136.09s (0:02:16)`. An earlier run with the required environment and a 120-second tool timeout stopped at 58% without a test failure; the complete rerun used a 300-second timeout and passed.

## Next step

None — T1–T6 are complete.
