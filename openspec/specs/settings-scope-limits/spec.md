# Settings and Scope Limits Specification

## Purpose

Let the owner (admin) define the bot's operational boundaries without code: which topics the bot resolves alone versus always escalates, configurable emergency keywords, adjustable tone/messages, and cost guardrails with spend limits and alerts.

## Requirements

### Requirement: SS-1 — Bot-Resolves vs Always-Escalate Rules

The system MUST let the owner configure, per topic/category, whether the bot resolves alone or always escalates to a human. Changes MUST apply without code changes or redeploy and MUST be respected by the conversation manager and handoff logic.

#### Scenario: Owner changes a rule
- GIVEN the owner sets "Valores → always escalate"
- WHEN a customer asks about prices
- THEN the bot escalates to a human without answering

#### Scenario: Rule change takes effect
- GIVEN the owner updates a rule in the panel
- WHEN the rule is saved
- THEN subsequent conversations use the new rule immediately

### Requirement: SS-2 — Configurable Emergency Keywords

The system MUST let the owner edit the emergency keyword list and patterns used by the deterministic detection layer (EM-1) through the panel, applying changes without code changes.

#### Scenario: Keyword added
- GIVEN the owner adds a new emergency expression
- WHEN the list is saved
- THEN the deterministic detector recognizes the new expression immediately

### Requirement: SS-3 — Cost Guardrails

The system MUST enforce configurable internal-thread and global UTC-day spend limits on AI/API usage. The global daily calculation MUST include WhatsApp spend and internal assistant spend exactly once, while WhatsApp message cost behavior MUST remain unchanged. The system MUST record planner and terminal streamed-response LLM usage on the internal request message exactly once per completed call. It MUST use explicit pricing for configured assistant models; unknown pricing or unavailable usage MUST record zero and a diagnostic rather than fabricated cost. When a thread or day approaches or exceeds its limit, the system MUST reuse the existing owner alert path and select conservative or blocked behavior according to the threshold.

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

### Requirement: SS-4 — Cost Tracking and Meta Pricing Awareness

The system MUST track message/conversation spend and MUST account for Meta's service-message pricing becoming effective 2026-10-01 (paid per delivered message inside the 24h window) when estimating costs. Spend data MUST be visible to the owner in the panel.

#### Scenario: Spend visible
- GIVEN cost tracking is active
- WHEN the owner opens cost settings
- THEN current and daily spend, with limits, are shown including Meta service-message charges

### Requirement: SS-5 — Adjustable Tone and Messages

The system MUST let the owner adjust the bot's tone, standard messages, and response rules through the panel without code changes (LumatRequest §1.12).

The supported tone styles MUST be `cercano`, `formal`, and `directo`.

The standard messages MUST include, in addition to the greeting, the cannot-answer reply and the clarification, the farewell (`messages.farewell`) and the out-of-hours notice (`messages.out_of_hours`).

The system MUST also let the owner set the business hours through the panel: a weekly schedule of opening and closing times with an explicit IANA timezone. The schedule MUST be validated when written, and an invalid value MUST be rejected rather than stored.

#### Scenario: Message edited
- GIVEN the owner edits a standard bot message or tone setting
- WHEN the change is saved
- THEN subsequent bot replies use the edited content

#### Scenario: Tone outside the supported list
- GIVEN the owner submits a tone other than `cercano`, `formal`, or `directo`
- WHEN the change is saved
- THEN the panel API rejects the request with HTTP 400

#### Scenario: Business hours saved
- GIVEN the owner submits a weekly schedule and a timezone
- WHEN the change is saved
- THEN the panel stores both and the customer chat uses them

#### Scenario: Invalid business hours rejected
- GIVEN the owner submits a weekday outside 1..7, a weekday repeated across entries, a malformed time, a window whose opening is not before its closing, a schedule that is not a list of entries, or a timezone that cannot be resolved
- WHEN the change is saved
- THEN the panel API rejects it with HTTP 400, the value is not stored, and no settings audit entry is written
