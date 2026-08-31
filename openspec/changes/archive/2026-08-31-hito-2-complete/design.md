# Design: Complete H2 Production Human Inbox

## Technical Approach

Add a thin command/service layer to the existing `/panel/api` JSON surface. Keep `ConversationState`, `set_conversation_state()`, `Message`, `send_text()`, `record_audit()`, same-origin session auth, and the H1 webhook guard authoritative. Extend the existing state-based `AppShell`; archived router and Storybook boundaries remain dependencies, not reimplementation.

Graph evidence: `ConversationState` → `state.py` → `Conversation`/`Message`; panel `conversations.py` → `models.py` ← `send.py`; `send_text()` → Meta Cloud API; frontend path `AppShell` → `ConversationThread` → `api.ts`. The backend-to-frontend directed path is absent in Graphify, so that edge was verified from source.

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Ownership | Conversation-level nullable `responsible_id` FK, not `Case.responsible_id`. | A live inbox owner is distinct from historical/multiple cases. |
| Mutation concurrency | Add `conversation.version` (integer). State and assignment requests require `request_id` and `expected_version`; service locks the conversation row with `SELECT FOR UPDATE`, validates the version and legal transition, mutates, audits, increments version, and commits. A stale/missing precondition returns JSON `409 conflict` and never overwrites. Requests are serialized per conversation; repeated `request_id` with the same operation returns the committed result, while a different payload returns `409`. | Explicit optimistic preconditions plus one short database lock preserve H1 side effects without lost updates. |
| Authorization | `admin` and `operador` may use inbox commands. `take` is self-assignment. Admins may assign or clear any active `operador`; operators may assign only themselves and clear only their own assignment. Assignment target must exist, be active, and have an allowed role; server checks these rules regardless of UI. `return` is `human→bot` and clears the caller’s assignment; `close` retains ownership. | Least privilege while permitting operational reassignment. |
| Delivery | Add `author_id`, unique outbound `request_id`, `delivery_status` (`pending`, `sending`, `sent`, `failed`, `unknown`), error, attempt metadata, and timestamps. Commit row/audit before Meta; claim under lock, call Meta outside the transaction, then finalize. | Prevents duplicate claims and preserves unknown-outcome safety. |

## Data Flow and Contracts

```text
SPA → auth → command service → locked Postgres/audit commit
                              └→ claim → Meta → sent/failed/unknown
Webhook → H1 guard → inbound persistence → human: no bot run
```

`POST /conversations/{id}/state` body `{state, expected_version, request_id}` and `POST /conversations/{id}/assignment` body `{responsible_id|null, expected_version, request_id}` return `{ok:true, conversation}`. Legal transitions remain `bot→human`, `human→bot`, `human→closed`, `closed→bot`; `take` assigns self. The latest customer inbound determines the 24-hour free-text window; absent/stale means `422 policy_error`, no message or Meta call.

`POST /conversations/{id}/messages` body `{text, request_id}` creates one durable operation. `POST /conversations/{id}/messages/{message_id}/retry` body `{request_id, expected_status:"failed"}` is the only retry contract. Only `failed` is retryable. `pending`/`sending` returns `409 in_progress`; `sent` returns the existing success; `unknown` returns `409 outcome_unknown` and is never automatically retried. Concurrent retries serialize: one claims the row, duplicates with the same key return its result, and other keys observe the resulting state without a second send. Definite provider rejection is `failed`; timeout/transport ambiguity is `unknown`.

Errors are JSON `401/403/404/409/422`; all accepted, rejected, and delivery actions are append-only audited with actor, cause, conversation, and request key.

## File Changes

| File | Action | Description |
|---|---|---|
| `db/migrations/010_h2_human_inbox.sql`, `app/models.py` | Create/modify | Version, assignment, outbound delivery fields, constraints/indexes. |
| `app/services/conversations.py`, `app/services/send.py` | Create/modify | Locked commands, authorization, window, claim/finalize/retry. |
| `app/panel/api/routes/conversations.py`, `serializers.py` | Modify | Filters and contracts. |
| `web/src/{api.ts,types.ts,components/pages/{ConversationsList,ConversationThread}.tsx}` | Modify | Typed controls, delivery states, refetch; no router. |
| `tests/functional/`, `tests/integration/`, `web/src/**/*.test.*` | Modify | RED concurrency, authorization, retry, Meta, webhook, and UI tests. |

## Testing Strategy

Unit tests cover transitions, version conflicts, authorization, window boundary, and retry state rules. PostgreSQL/`respx` integration tests cover migration, lock races, commit-before-Meta, 4xx vs unknown, duplicate/concurrent retries, audit, and H1 human webhook continuity. React tests cover filters, permissions, 409/policy/delivery states, and refresh.

## Threat Matrix

| Boundary | Applicability / required RED coverage |
|---|---|
| Documentation-like paths, Git selection, commit/push/PR commands | N/A — no executable classification or VCS automation. |
| Meta process integration | Applicable — validate recipient/text, never log token, commit before call, serialize claims, preserve rows on every outcome; test payload, race, 4xx, timeout/unknown, and retry identity. |

## Migration / Rollout

Apply migration 010 idempotently. Existing conversations get null assignment and version zero; legacy bot rows remain readable. Roll back routes/UI first and retain outbound/audit rows until unknown outcomes are reconciled. No migration or branding change beyond H2 fields.

## Non-Goals

H4 internal chat, PWA, broader roadmap items, a new router/provider, media or template sending, and unrelated branding are explicitly excluded. Archived router/UI work and existing H1 webhook/state authorities are preserved.

## Open Questions

None blocking. Template sending outside the 24-hour window is later scope.
