# Archive Report: sdb-execute-tools

## Final status

- **Change:** `sdb-execute-tools`
- **Started:** 2026-09-13
- **Archived:** 2026-09-13
- **Result:** Complete with warnings; no blockers or critical verification findings.
- **Tasks:** 6/6 persisted implementation tasks checked.
- **Archive path:** `openspec/changes/archive/2026-09-13-sdb-execute-tools/`

## Final verification

- **Verdict:** PASS WITH WARNINGS
- **Blockers:** 0
- **Critical findings:** 0
- **Requirements:** 16/16
- **Scenarios:** 35/35
- **Test command:** Full `pytest tests/` against the dedicated SDB PostgreSQL test database
- **Test result:** Exit 0

The earlier failed verification is historical, not current. It was remediated by commit `643d6120` (`test(sdb): cover rejected and failed execution paths`) and documented by `879b4cc8` (`docs(sdd): record remediation evidence`). The historical failed report remains in commit `91085368`.

The remediation exposed and fixed a real product defect: SDB gate order was inverted. The final order is whitelist → Pydantic arguments → read-only classification → cost → project capability, so the cost gate correctly precedes project-capability validation.

## Specs synced

| Base spec | Action | Result |
|---|---|---|
| `openspec/specs/sdb-native/spec.md` | Updated | Added SDB-6, SDB-7, SDB-9, SDB-10; modified SDB-4 |
| `openspec/specs/assistant-tools/spec.md` | Updated | Added AT-6, AT-7; modified AT-1; recorded deferred-write removal |
| `openspec/specs/assistant-operations/spec.md` | Updated | Added AO-4; modified AO-2 and AO-3 |
| `openspec/specs/internal-agent-chat/spec.md` | Updated | Added IAC-8; modified IAC-2; recorded removal of terminal `not-implemented` |

The delta specs remove the `not-implemented` SDB delivery contracts across `assistant-tools`, `assistant-operations`, and `internal-agent-chat`. The durable `_run_sdb_tasks` runner is authoritative, the first read is `conversations.search`, approval routing is canonically `consumed`, and resumed results are aggregated before VERIFY.

## Warnings carried forward

1. `tests/integration/test_webhook_ingest.py::test_startup_sweep_reprocesses_received` emits an unawaited `_publish_all` RuntimeWarning.
2. fastembed emits a model-pooling UserWarning.
3. The `strict-tdd-verify.md` skill reference is not installed; this is a packaging gap, not a defect in this change.

No warning was treated as a blocker, and no fix is claimed for these unrelated warnings.

## Mechanical archive evidence

The pre-move snapshot was compared with the archived directory using `diff -r`.

```text
<empty output>
```

`diff -r` status: `0`.
