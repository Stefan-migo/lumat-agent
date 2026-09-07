# Proposal: Conversation Realtime

## Intent

Bring the human panel inbox to realtime: live updates, agent activity, token streaming, and a truthful “Conversaciones activas” rail.

## Scope

### In Scope
- Authenticated WebSocket channel at `/panel/ws`; existing POST commands remain the submission API.
- Best-effort updates with initial snapshots and reconnect refetch.
- Minimal persisted activity events (`classified`, `kb_retrieved`, `escalation`) in existing `ConversationEvent`.
- Active-summary GET read model with customer name and repaired `last_message_at` writer.
- Internal-chat token events while preserving the synchronous POST response contract.
- SPA WebSocket client, live rendering, active rail wiring, Vite proxy, and nginx upgrade configuration.

### Out of Scope
- No tools in internal chat, global commands, or a general event bus/replay system.
- No multi-worker/cluster fan-out; v1 assumes one API process.
- No roadmap D views/Jinja removal, payments/M2-standalone, or unrelated notifications.

## Capabilities

### New Capabilities
- `conversation-realtime`: authenticated WebSocket, live updates, token streaming, reconnect behavior, and active-summary read model.

### Modified Capabilities
- `conversation-manager`: persist activity and maintain recency.
- `human-handoff`: publish escalation and state changes.
- `internal-agent-chat`: publish tokens without changing POST persistence/authorization.
- `panel-app`: consume updates and active summaries while retaining POST commands.
- `panel-design-system`: represent live states with existing primitives/tokens.

## Approach

Use WebSocket as the single public channel with `{type, conversation_id?, data}` for typed token, message, conversation, activity, and snapshot events. Delivery is best-effort: initial snapshot on connect; REST refetch after reconnect, not replay. Active means `state IN (bot, human)` and non-null `last_message_at` within 24 hours; closed/stale/null rows are excluded. Add `GET /panel/api/conversations/active` with a customer-name join, fix the missing recency writer, and split into TDD slices under 400 lines.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/panel/api`, `app/services`, `app/chat`, `app/models.py` | Modified | Backend realtime and read model. |
| `web/src`, `infra/nginx`, Vite config, tests | Modified | Client, routing, coverage. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dropped events or stale ordering | Med | Snapshot/refetch fallback; REST/DB remains authoritative. |
| Streaming changes chat behavior | Med | Keep POST synchronous and test both paths. |
| `last_message_at` repair changes ordering | Med | Regression tests and explicit null behavior. |

## Rollback Plan

Revert WS, client, proxy, activity, read-model, and streaming changes. REST commands, synchronous chat, and persisted data remain usable.

## Dependencies

- Existing auth, events, state enum, and panel APIs.

## Success Criteria

- [ ] `cd web && npm test` and `uv run pytest tests/` pass.
- [ ] Reconnect restores truth through snapshot/refetch, without replay infrastructure.
- [ ] Tests cover inbox, activity, streaming, and active rail.
- [ ] Each delivery slice stays at or below 400 changed lines.
