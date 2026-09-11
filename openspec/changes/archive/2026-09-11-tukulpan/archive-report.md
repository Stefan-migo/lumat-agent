# Archive Report: tukulpan

## Result

The `tukulpan` SDD change is archived on 2026-09-11. All 12 implementation
tasks were complete at close. The final verification was **PASS WITH WARNINGS**:
5/5 requirements, 15/15 scenarios, 683 tests passed, 0 failed, and 1
pre-existing warning about an un-awaited `_publish_all` coroutine in webhook
ingest. There were 0 blockers and 0 critical findings.

The final-state handoff supersedes the earlier intermediate verification
snapshot: baseline fix commit `0022759b` restored the guardrails terminology
contract after the separate `harness-lumat` archive and updated
`tests/unit/test_assistant_extensions.py` to the archived harness spec path.
That baseline correction is not attributed to `tukulpan`.

## Specs Synced

- `openspec/specs/memory/spec.md`: updated MEM-2 and MEM-3 and added MEM-7,
  preserving MEM-1, MEM-4, MEM-5, and MEM-6.
- `openspec/specs/harness-lumat/spec.md`: updated HL-1 and HL-3 while
  preserving HL-2.
- `openspec/specs/agent-config/spec.md`: intentionally unchanged; the
  guardrails terminology contract remains intact.

No requirements were removed. One requirement was added (MEM-7), and four
existing requirements were modified: MEM-2, MEM-3, HL-1, and HL-3.

## Archive Operation

- Source: `openspec/changes/tukulpan/`
- Destination: `openspec/changes/archive/2026-09-11-tukulpan/`
- The active source directory no longer exists.
- Archived artifacts include proposal, exploration, design, both delta specs,
  tasks, apply progress, and verification report.
- Persisted `tasks.md` contains 12/12 checked implementation tasks.

Mechanical move readback:

```text
$ diff -r "$snapshot_root/source" openspec/changes/archive/2026-09-11-tukulpan

```

The `diff -r` output was empty (byte-identical pre-move snapshot and archive).

## Engram Traceability

Engram artifacts read in full:

- `sdd/tukulpan/explore` — observation 2955
- `sdd/tukulpan/proposal` — observation 2956
- `sdd/tukulpan/spec` — observation 2957
- `sdd/tukulpan/design` — observation 2959
- `sdd/tukulpan/tasks` — observation 2963
- `sdd/tukulpan/apply-progress` — observation 2964
- `sdd/tukulpan/verify-report` — observation 2977

The archive report is also persisted to Engram as
`sdd/tukulpan/archive-report`.

## Graph Check

Graphify was present and queried before archive operations. The consulted
nodes included `tukulpan.py`, `Memory`, `memory.py`, `agent_chat.py`,
`assemble_context()`, `AssistantState`, `registry.py`, `memory.read`,
`hybrid_search()`, `nodes.py`, `graph.py`, and the Tukulpan delta specs.
The consulted edges included memory-to-models, agent-chat-to-assembly,
registry-to-memory-read, Tukulpan-to-hybrid-search, and graph-to-nodes/state.
`graphify-out/GRAPH_REPORT.md` was read; it identified graph commit `a7abba4b`
as stale-but-usable relative to the final branch. The required close-of-session
incremental update ran after the archive move; Graphify completed with
fail-closed warnings for excluded/deleted corpus files and advised a future
cluster-only report regeneration. No code was changed in this archive phase.

## Risks and Warnings

- One non-blocking, pre-existing webhook coroutine warning remains.
- Coverage was not available.
- The verify suggestion to add a regression test for ID-based `delete`/`set_mark`
  on administrative non-default rows remains future work; it does not block
  this archive.
