# Exploration: Complete H2 Production Scope

> Change candidate: `hito-2-complete`
> Artifact mode: hybrid (OpenSpec + Engram)
> Authority: current `openspec/specs/**`; older roadmap and proposal material are context only.

## Executive Finding

H2 is split across two already-archived changes, but only one half is production-complete. `h2-router-langgraph` implements the multi-agent router (AO-1..AO-10). `panel-h2-advance` implements Storybook UI for the human inbox, while `panel-adoption` makes the read-only SPA shell live. The production capability explicitly deferred by SDD remains missing: an authenticated operator must be able to take/assign a human WhatsApp conversation, send a reply through Meta, enforce the 24-hour customer reply window, and persist/audit the resulting state and outbound message.

The later proposal MUST be a new change, not a continuation or rewrite of archived changes: `hito-2-complete`.

## Authoritative H2 Requirements and Status

### Already implemented and archived

| Requirement family | Evidence | Status |
|---|---|---|
| AO-1..AO-10: five-agent registry, startup reader, deterministic dispatch, gate envelope, thin sub-graphs, whitelist, KB scope, bounded retry, invisible tone, multi-LLM cost sums | `openspec/specs/agent-orchestration/spec.md`; `app/agent_registry.py`; `app/chat/graph.py`; `app/chat/nodes/orchestrate.py`; `app/chat/subgraphs/research_triage.py`; `app/services/kb.py`; archived `2026-08-24-h2-router-langgraph/verify-report.md` | Implemented. Archived verification reports 11/11 requirements, 20/20 scenarios, 497 tests passing. Do not reimplement. |
| R-PRD-PG-8..PG-14: Storybook inbox list/thread, mock state domain, composer/state-control visuals, 24h visual notice, dedicated chat mock, and gates | `openspec/specs/panel-h2-advance/spec.md`; `web/src/stories/pages/InboxThread.stories.tsx`; `web/src/stories/pages/ConversationsList.stories.tsx`; `_shared/mockData/{conversations,users,chat}.ts`; archived `2026-08-20-panel-h2-advance/verify-report.md` | Implemented as UI/story artifacts only. Archived verification reports 6/6 requirements, 12/12 scenarios, 209 frontend tests, typecheck and Storybook build green. |
| Live SPA adoption and AP-9 read-only list/thread | `web/src/components/domain/AppShell.tsx`; `web/src/components/pages/{ConversationsList,ConversationThread}.tsx`; `app/panel/api/routes/conversations.py`; `tests/functional/test_api_conversations.py`; archived `2026-08-25-panel-adoption/verify-report.md` | Implemented. AP-9 list is authenticated, serialized, ordered, and read-only; thread is chronological. |
| H1 handoff foundation | `openspec/specs/human-handoff/spec.md`; `app/models.py`; `app/chat/state.py`; `app/services/cases.py`; `app/webhook/ingest.py` | Implemented: `bot|human|closed`, transition events, deriva bundle/case, and continued inbound persistence in `human` state. |
| Existing Meta outbound primitive | `app/services/send.py`; `app/config.py`; `tests/integration/test_send_costs.py` | Partially reusable: `send_text()` posts text to Graph API; `deliver_outbound()` sends pending processed outbound rows, stores Meta WAMID and `cost_meta`, and avoids resend when WAMID exists. It is not a panel command and is not sufficient for operator-authored replies. |

### Missing production behavior required to complete H2

These are the production acceptance requirements implied by the SDD boundary (`HH-5` says panel reply is H2; `panel-h2-advance` says real state is H2 and 24h enforcement lands in H2). They need to become an explicit delta spec in the proposal so the capability is not silently omitted:

1. **Human inbox data contract** — authenticated `admin` and `operador` users can list human/open conversations, see customer/thread metadata and assignment, filter by `bot|human|closed` as applicable, and drill into chronological messages. Existing AP-9 is read-only and has no assignee.
2. **Take/return/close transitions** — panel actions MUST validate legal state transitions, pause/resume bot processing consistently, update `closed_at`, record `conversation_events` with actor/cause, and return the authoritative updated conversation. Reuse `set_conversation_state()` rather than a parallel state machine.
3. **Assignment** — the inbox needs a persisted responsible operator and an authenticated assignment/clear operation. `Case.responsible_id` already exists for cases, but `Conversation` has no assignee. The design MUST explicitly decide whether H2 reuses the latest case assignment or adds a conversation assignment column; it MUST NOT leave the Storybook assignee as a fake field.
4. **Operator reply command** — a panel API MUST validate non-empty text and authorization, persist an outbound `Message` before/with delivery, associate it with the conversation, identify the acting operator, and send it through Meta Cloud API to `Conversation.wa_phone`. The response MUST expose delivery/pending/failure state without losing the local message.
5. **24-hour window enforcement** — calculate from the latest customer inbound message (not an arbitrary UI timestamp). Within 24 hours ordinary text replies are allowed; outside it, free-form send MUST be rejected/disabled and only an explicitly supported Meta template path may be allowed. The backend is authoritative; the UI notice is not enforcement.
6. **Idempotency and delivery failure** — retries MUST not double-send an operator message. Existing `deliver_outbound()` uses `wamid IS NULL` but has no claim/lock/idempotency key for concurrent panel requests and marks no explicit send failure. H2 must define request idempotency, status transitions, Meta error handling, and retry/reconciliation behavior.
7. **Audit and authorization** — state, assignment, send, rejection, and delivery outcomes MUST be attributable to the signed-in panel user and protected server-side. Existing JSON dependencies provide 401/403 patterns; existing `record_audit()` and conversation events provide two distinct audit channels that the design must assign deliberately.
8. **Frontend production wiring** — `InboxThread` is only under `web/src/stories/pages/`; the production `ConversationThread` is deliberately read-only and `ConversationsList` has no assignment/filter/state mutation. H2 must add or adapt production page components, typed API contracts, loading/error/empty/permission states, optimistic-vs-refetch behavior, and wire them through the existing state-based `AppShell` (no router is currently used).
9. **End-to-end proof** — cover API authorization, state/assignment/send/window/error contracts, DB persistence, Meta request shape (mocked), duplicate request behavior, and the webhook guard that persists inbound messages while human-owned. Add frontend tests for enabled/disabled composer and post-action refresh. Existing suites prove H1 and read-only H2 surfaces but do not prove panel-to-Meta reply.

## Dependency Map

| Layer | Current entry points | H2 completion dependency |
|---|---|---|
| Panel/API | `app/panel/api/routes/conversations.py`, `app/panel/api/deps.py`, `app/panel/api/serializers.py`, `app/panel/api/__init__.py` | Add thin authenticated command routes and response serializers; preserve JSON 401/403, same-origin cookie, no redirect/CORS. |
| Domain/services | `app/chat/state.py`, `app/services/cases.py`, `app/services/send.py`, `app/services/audit.py` | Reuse state transition and Meta client primitives; add only the smallest operator-reply/assignment orchestration needed. |
| Database | `app/models.py`, `db/migrations/001_init.sql`, `db/migrations/006_handoff_deriva.sql` plus numbered migrations through `009_memory.sql` | No current conversation assignee, outbound author/idempotency/send-attempt fields, or reply-window record. Migration depends on the assignment and idempotency design decision. |
| WhatsApp/Meta | `app/config.py`, `app/webhook/router.py`, `app/webhook/ingest.py`, `app/services/send.py` | Keep webhook HMAC/persist-before-process and HH-5 human guard. Add production operator send semantics, 24h/template policy, delivery failure and retry proof. |
| Admin UI | `web/src/components/pages/{ConversationsList,ConversationThread}.tsx`, `web/src/stories/pages/InboxThread.stories.tsx`, `web/src/components/domain/AppShell.tsx`, `web/src/api.ts`, `web/src/types.ts` | Stories are visual reference, not runtime wiring. Production components/types/API calls must gain human inbox behavior without mutating H1's read-only contract accidentally. |
| Tests | `tests/functional/test_api_conversations.py`, `tests/integration/test_send_costs.py`, `tests/integration/test_webhook_ingest.py`, `tests/functional/test_conversation_flows.py`, `web/src/**/*.test.*` | Extend with production command and cross-layer scenarios; current archived counts are baselines, not evidence of operator replies. |

## Explicit Scope Boundaries

### In scope for `hito-2-complete`

- Production human inbox for `admin`/`operador` on the existing `/panel/api/*` and SPA surfaces.
- Persisted assignment (or an explicitly justified reuse of case responsibility), state controls, operator-authored outbound text, Meta delivery, 24-hour enforcement, auditability, idempotency, and failure recovery.
- Required DB migration(s), typed API/UI contracts, and backend/frontend/integration tests.
- Regression protection for AO-1..AO-10, WH-1..WH-7, HH-1..HH-5, AP-1/AP-2/AP-4/AP-5/AP-9 and existing panel app behavior.

### Non-goals

- Rebuilding the archived LangGraph router or changing AO-1..AO-10 semantics, gates, thresholds, prompts, KB scoping, or memory scope.
- Rebuilding Storybook-only `InboxThread`/`ChatWithAgent`; H4 internal chat remains out of scope even though the old UI advance bundled a chat mock.
- Calendar/ICS, notifications center, automations/event bus, PWA/push, advanced dashboards, public website (M2), payments/catalog (M3), media upload/composition, voice/media outbound, group chats, or a new frontend router.
- Replacing H1's webhook processing model or adding a LangGraph checkpointer.
- Broad CRM redesign, pagination/search infrastructure beyond what the inbox needs, or a new messaging provider.

## Approaches

1. **Thin production command layer over existing conversation/send services (recommended)** — add the smallest panel command API, persisted assignment/idempotency data only where required, and production components that reuse current serializers, `set_conversation_state()`, `send_text()`/`deliver_outbound()`, and same-origin auth.
   - Pros: preserves H1/H2 foundations, minimal migration, clear rollback, low semantic drift.
   - Cons: requires careful transaction/idempotency design around Meta's non-transactional boundary.
   - Effort: High, best delivered as chained slices under the 400-line review budget.

2. **Separate outbound/message worker subsystem** — introduce a durable outbound queue and worker with provider acknowledgements.
   - Pros: stronger concurrency and retry semantics at scale.
   - Cons: new infrastructure and operational behavior not justified by current single-worker/tens-of-conversations design; risks turning H2 into H4 automation infrastructure.
   - Effort: Very high; reject unless production volume or deployment constraints require it.

## Recommendation

Use `hito-2-complete` with approach 1. The proposal should begin with a contract/design decision for assignment ownership and outbound idempotency, then implement in reviewable slices: (1) schema/domain contracts, (2) panel inbox list/thread plus state/assignment commands, (3) operator reply + 24h/Meta failure handling, and (4) frontend wiring and end-to-end verification. Archived H2 changes remain immutable evidence and dependencies, not implementation tasks.

## Risks

- Meta send is an external side effect: a DB transaction cannot atomically commit with the Graph API call; idempotency and reconciliation must be specified before coding.
- The 24-hour window can be miscomputed if the implementation uses `Conversation.last_message_at`, which is not explicitly inbound-only; query the latest customer inbound message.
- Reusing `Case.responsible_id` avoids a migration but couples inbox assignment to case lifecycle; adding a conversation field is cleaner but changes schema and serializers.
- The current `Message` model has no operator identity; adding it affects migration, serializer privacy, and audit expectations.
- `HH-5` requires inbound persistence during human ownership; state transitions must not accidentally resume the bot or create duplicate outbound replies.
- The working tree contains unrelated uncommitted web branding/UI changes. Any later apply must preserve them and scope commits only to H2 files.

## Verification Evidence

- Graph preflight: `graphify-out/graph.json` exists and is non-empty; `GRAPH_REPORT.md` reports 3,052 nodes and 6,389 edges, built from commit `f09fba0b` (stale versus current HEAD, so used for structure only).
- Graph query: `graphify query "H2 admin inbox WhatsApp reply from panel production behavior"` surfaced `panel-h2-advance`, `Admin Panel Specification`, `InboxThread.stories.tsx`, `Message`, `deliver_outbound()`, `state.py`, and `FastAPI/Jinja Production Panel`.
- Graph path: `api/routes/conversations.py --imports_from--> models.py <--imports_from-- send.py` (undirected path requested because no direct directed route was available). Directed paths from WhatsApp Webhook to Admin Panel and from Message to PanelShell were unavailable; this is recorded rather than inferred.
- Archived router verification: `openspec/changes/archive/2026-08-24-h2-router-langgraph/verify-report.md` records 497 passing backend tests and AO 11/11, 20/20.
- Archived UI verification: `openspec/changes/archive/2026-08-20-panel-h2-advance/verify-report.md` records 209 passing frontend tests, typecheck and Storybook build green.
- Archived panel adoption verification: `openspec/changes/archive/2026-08-25-panel-adoption/verify-report.md` records 499 backend tests, 319 frontend tests, and AP-9/read-only SPA evidence.
- Static current-code evidence: `app/panel/api/routes/conversations.py` exposes only GET list/thread; `app/panel/routes/conversations.py` explicitly declares read-only H1; `app/webhook/ingest.py:357-362` persists human-state inbound messages without bot processing; `app/services/send.py:37-104` contains only generic outbound text/delivery primitives.

## Ready for Proposal

Yes. Create a new proposal for `hito-2-complete`; treat AO/router and Storybook/UI archives as implemented dependencies, and make the missing production reply/state/assignment/window/idempotency behavior explicit delta requirements before implementation.
