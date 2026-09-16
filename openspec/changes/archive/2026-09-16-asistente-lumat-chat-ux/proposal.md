# Proposal: Asistente Lumat Chat UX

## Intent

Restructure the assistant from a form-shaped, three-column admin view into a single centered conversation surface with ChatGPT's interaction grammar, while preserving Lumat's light forest/cream visual language. Fix the structural defects that create empty threads, detach approval context, expose inaccessible English/raw state, and make the thread navigator unusable.

## Scope

### In Scope
- Recompose `AgentChat` around a centered conversation column, progressive-disclosure history/context controls, inline plan/evidence, hero composer, streaming/retry/copy/timestamp affordances, responsive behavior, and neutral Chilean Spanish UI copy.
- Fix D1–D4 and D7–D11 across frontend, API, persistence, localization, and tests while preserving realtime, approval, recovery, attachments, planning lifecycle, deep links, and tier logic.
- Add nullable thread titles and one-time LLM generation after the first assistant response, with cost-gate check, `record_llm_cost` attribution, mandatory first-user-message fallback, rename, delete, ownership checks, filtering, grouping, active state, and predictable ordering.

### Out of Scope
- D5 (resolved stale-container incident), D6 (known cosmetic duplicate fetch), shell, other pages, token value changes, dark mode, new dependencies, and markdown renderer libraries.
- Replacing the existing assistant execution or realtime architecture.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `internal-agent-chat`: update conversation presentation, planning controls, localized failure states, and bounded thread-list identity/lifecycle semantics.
- `ui-command-center`: replace the three-zone desktop contract with a centered conversation and progressive-disclosure history/context contract; rewrite affected zone/tab tests.
- `panel-design-system`: apply the existing grammar, primitive-reuse, localization, accessibility, and responsive contracts to the assistant surface without moving token values.

## Approach

Reuse existing primitives and tokens; implement the layout and interaction model in the assistant page and its existing stylesheet boundary. Add the additive migration and minimal model/serializer/routes needed for thread title lifecycle. Generate titles inline after the first assistant response unless the cost state is non-normal, and always fall back without charging. The design system is authoritative when it conflicts with the ChatGPT reference.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/components/pages/AgentChat.tsx` and stories/tests | Modified | Conversation composition, states, controls, Spanish copy, accessibility. |
| `app/services/agent_chat.py` | Modified | Explicit thread creation and localized failure/title flow. |
| `app/panel/api/routes/chat.py`, `app/panel/api/serializers.py`, `app/models.py` | Modified | Navigator filtering/order, title, rename/delete, ownership. |
| `db/migrations/025_internal_chat_thread_title.sql` | New | Nullable title column. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Regression of durable approval/recovery or SSE behavior | Med | Preserve contracts and test persisted state plus transient streaming separately. |
| LLM title generation increases spend or delays response | Med | Check internal thread cost state, attribute cost, generate once, and use free fallback. |
| Design drift or scope expansion | Low | Reuse tokens/primitives; keep `DESIGN_SYSTEM.md` authoritative and exclude D5/D6. |

## Rollback Plan

Revert the change commit(s) and disable the new UI/API routes. The migration is additive; retain the nullable column or roll it back with a reviewed database migration if required. Existing thread/message and streaming contracts remain the fallback path.

## Dependencies

- Existing primitives, token stylesheet, cost guardrails, and migration runner.

## Success Criteria

- [ ] Assistant renders as one centered, accessible light-theme conversation surface with inline approval/evidence and progressive disclosure.
- [ ] D1–D4 and D7–D11 are covered by backend/frontend tests; existing behavior contracts remain green.
- [ ] No new dependency or token-value change; thread titles never fall back to `Thread #N` and title spend is accounted for.
