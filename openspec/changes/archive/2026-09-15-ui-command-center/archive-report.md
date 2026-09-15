# Archive Report: UI Command Center

## Final State

The `ui-command-center` change shipped as a stacked chain of four merged pull requests on `main` at `f892df94`: #197 (bounded internal thread-list endpoint and typed client), #198 (PanelShell focus mode and authoritative stream recovery), #199 (three-zone composition, responsive tiers, and InboxThread quarantine removal), and #200 (narrow Playwright browser contract plus verification fixes).

Final verification was **PASS WITH WARNINGS**: 11/11 requirements and 23/23 scenarios compliant, with 0 CRITICAL findings. The backend suite exited 0; Vitest passed twice at 76 files / 540 tests; the real-Chrome Playwright contract passed 8 tests; `npm run build` exited 0; and `git diff --check` was clean.

## Tasks

All 8 implementation tasks are checked in `tasks.md`.

## Specs Synced

- `ui-command-center`: created `openspec/specs/ui-command-center/spec.md` from the complete delta, containing CC-1 through CC-4 (0 → 4 requirements).
- `panel-design-system`: appended DS-CC-1 through DS-CC-4 to the existing specification (56 → 60 requirements); all existing requirements were preserved.
- `internal-agent-chat`: added IAC-9 and replaced IAC-4 and IAC-6 with their modified contracts (8 → 9 requirements); all unrelated requirements were preserved.

The delta-only `Graph Check Consulted` sections were not copied into source specs.

## Final Findings and Residual Risks

Two non-blocking warnings remain: pre-existing React `act(...)`, jsdom, and backend runtime warnings; and resize-restoration browser coverage that enters focus mode with the default zone rather than proving restoration of a non-default selected zone. One suggestion remains for future work: `AgentChat.tsx` recovery calls `getChatThread(thread.id)` twice, causing a redundant duplicate fetch.

Two verification defects were fixed before close: Vitest now excludes `playwright/**` in `web/vite.config.ts`, and the redundant `data-desktop` attribute was removed. An unrelated pre-existing `ConversationsList.test.tsx` fixed-sleep flake was changed to `waitFor` to unblock verification; it is not part of this change. Under artificially saturated CPU, the unrelated pre-existing `src/components/domain/AppShell.test.tsx` may still fail. None of these residuals blocks archive.

## Graph Check

Required query: `graphify query "ui-command-center three zones navigator context responsive focus"`.

`graphify-out/GRAPH_REPORT.md` was read. It is stale: it describes `/home/stefan/repos/lumat-agent-ui-command-center` and was built from commit `040ce318`, whereas this checkout closed at `f892df94`.

Consulted nodes: `AgentChat.tsx`, `domain/PanelShell.tsx`, `domain/AppShell.tsx`, `api.ts`, `types.ts`, `chat.py`, `InternalChatThread`, `InternalChatMessage`, `command-center.spec.ts`, `Narrow Playwright Browser Contract`, `ConversationThread.tsx`, and the `UI Command Center Proposal` community.

Consulted edges/paths: `AppShell.tsx → PanelShell.tsx → AgentChat.tsx`; `AgentChat.tsx → api.ts → InternalChatThread`; `command-center.spec.ts --implements--> Narrow Playwright Browser Contract`; `ConversationThread.test.tsx → ConversationThread.tsx`.

Filesystem artifacts were read directly from the main checkout; no Engram artifact observation IDs were available for these reads.

## Mechanical Readback

The change tree was snapshotted with `cp -R`, moved with `git mv`, and compared against the pre-move snapshot with:

```text
diff -r "$snapshot_root/source" "openspec/changes/archive/2026-09-15-ui-command-center"
```

Verbatim output: empty (no differences).

## Archive Contents

The complete pre-move change tree is archived at `openspec/changes/archive/2026-09-15-ui-command-center/`. The active `openspec/changes/ui-command-center/` directory no longer exists. The archive contains proposal, design, tasks, apply-progress, verify-report, and all three delta-spec artifacts.
