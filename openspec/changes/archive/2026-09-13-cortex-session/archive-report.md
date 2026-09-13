# Archive Report: cortex-session

## Final status

- **Change:** `cortex-session` (SDD #4, Agent Lumat series)
- **Archived:** 2026-09-13
- **Result:** Intentional archive with warnings; no blockers or critical verification findings.
- **Tasks:** T1.1–T4.3 complete, 10/10 persisted tasks checked.
- **Verification:** PASS WITH WARNINGS; 15/15 requirements and 41/41 scenarios have covering evidence, with 35 fully compliant and 6 partial warnings.

## Final verification facts

- Focused backend verification: 67 passed; exit 0.
- Full backend suite: 796 passed and one pre-existing unrelated failure in `tests/functional/test_api_assistant_capabilities.py::test_admin_capabilities_reflect_real_tools_and_runtime_config` (13 expected tools versus 19 exposed). The failure reproduces at base commit `1e4d39cf` and is outside this change.
- Frontend suite: 523 tests passed.
- `cd web && npm run build`: exit 0.
- The production defect found during verification was fixed in commit `b433bb89`: the `submit_message()` exception path now uses `merge_assistant_state(...)`, preserving an active `cortex_session` on failed turns and reload. The fix is covered by the PostgreSQL RED→GREEN recovery test.
- Graphify remains stale at `c4d13da7`. The requested post-archive `graphify --update` is blocked by the unavailable OpenAI key and was not attempted.

## Spec synchronization

The following source-of-truth specs were updated:

- `openspec/specs/cortex-session/spec.md` — created from the complete new capability spec.
- `openspec/specs/harness-lumat/spec.md` — modified HL-2/HL-3 and added HL-5.
- `openspec/specs/internal-agent-chat/spec.md` — modified IAC-2/IAC-3 and added IAC-7.
- `openspec/specs/sdb-native/spec.md` — modified SDB-1/SDB-4.
- `openspec/specs/panel-app/spec.md` — added PNL-APP-28/PNL-APP-29.
- `openspec/specs/agent-config/spec.md` — modified AC-9 and added AC-12.

### Destructive-delta warning

The five MODIFIED deltas replace existing requirement text and scenarios by OpenSpec convention. They were merged deliberately, preserving all requirements not named by the deltas. The HL-3 delta also removes the prior explicit prohibition on Cortex-session mode because the new requirement supersedes that exclusion; no unrelated requirement was deleted.

## Mechanical archive evidence

The change folder was moved mechanically with `git mv` to `openspec/changes/archive/2026-09-13-cortex-session/`. The pre-move recursive snapshot compared cleanly with the archived tree.

Verbatim `diff -r` output for the mechanical new-spec copy:

```text
```

Verbatim `diff -r` output for the pre-move archive readback:

```text
```

## Engram traceability

Engram artifact observations read before archival:

- `#3123` — `sdd/cortex-session/proposal`
- `#3124` — `sdd/cortex-session/spec`
- `#3125` — `sdd/cortex-session/design`
- `#3128` — `sdd/cortex-session/tasks`
- `#3130` — `sdd/cortex-session/apply-progress`
- `#3134` — `sdd/cortex-session/verify-report`

## Archived contents

- `proposal.md`
- `design.md`
- `tasks.md`
- `apply-progress.md`
- `verify-report.md`
- `specs/` with six delta specifications
- `archive-report.md` (this report)
