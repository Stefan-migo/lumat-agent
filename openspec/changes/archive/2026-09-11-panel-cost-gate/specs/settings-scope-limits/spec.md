# Delta for Settings and Scope Limits

## MODIFIED Requirements

### Requirement: SS-3 — Cost Guardrails

The system MUST enforce configurable internal-thread and global UTC-day spend limits on AI/API usage. The global daily calculation MUST include WhatsApp spend and internal assistant spend exactly once, while WhatsApp message cost behavior MUST remain unchanged. The system MUST record planner and terminal streamed-response LLM usage on the internal request message exactly once per completed call. It MUST use explicit pricing for configured assistant models; unknown pricing or unavailable usage MUST record zero and a diagnostic rather than fabricated cost. When a thread or day approaches or exceeds its limit, the system MUST reuse the existing owner alert path and select conservative or blocked behavior according to the threshold.
(Previously: guardrails covered only per-conversation and daily WhatsApp spend and did not measure internal assistant calls.)

#### Scenario: Internal thread limit

- GIVEN an internal thread's persisted assistant spend reaches its configured conversation limit
- WHEN another panel request is gated
- THEN the owner alert is deduplicated through the existing alert path and the gate returns conservative or blocked mode according to the configured threshold

#### Scenario: Combined daily limit

- GIVEN WhatsApp and internal message spend together reaches the configured UTC-day limit
- WHEN further paid LLM usage is attempted
- THEN the owner is alerted through the existing deduplicated path and blocked mode prevents the LLM call until the UTC day resets

#### Scenario: Usage recorded once

- GIVEN planner usage is returned non-streaming and response usage appears in one terminal stream chunk
- WHEN the panel turn completes
- THEN both calls are accumulated once on the request message and the daily total includes that internal spend once

#### Scenario: Unknown model pricing

- GIVEN an assistant call uses a model absent from the explicit rate map
- WHEN cost recording runs
- THEN that call contributes zero monetary cost and a diagnostic identifies the unknown model

#### Scenario: WhatsApp non-regression

- GIVEN a WhatsApp outbound message is delivered
- WHEN its existing cost is recorded and daily spend is read
- THEN its `messages.cost_llm` and `cost_meta` behavior is unchanged and no synthetic panel or customer message is created
