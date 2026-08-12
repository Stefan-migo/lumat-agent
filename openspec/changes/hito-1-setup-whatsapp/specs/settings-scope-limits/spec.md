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

The system MUST enforce configurable per-conversation and daily spend limits on AI/API usage. When a conversation or the day approaches or exceeds its limit, the system MUST alert the owner and switch to conservative behavior (reduce or stop LLM usage, escalate to human).

#### Scenario: Conversation limit reached
- GIVEN a conversation approaches its configured spend limit
- WHEN the threshold is hit
- THEN the owner is alerted and the bot escalates or stops LLM processing for that conversation

#### Scenario: Daily limit reached
- GIVEN the daily spend limit is reached
- WHEN further LLM usage is attempted
- THEN the system alerts the owner and blocks further paid LLM calls until reset or escalation

### Requirement: SS-4 — Cost Tracking and Meta Pricing Awareness

The system MUST track message/conversation spend and MUST account for Meta's service-message pricing becoming effective 2026-10-01 (paid per delivered message inside the 24h window) when estimating costs. Spend data MUST be visible to the owner in the panel.

#### Scenario: Spend visible
- GIVEN cost tracking is active
- WHEN the owner opens cost settings
- THEN current and daily spend, with limits, are shown including Meta service-message charges

### Requirement: SS-5 — Adjustable Tone and Messages

The system MUST let the owner adjust the bot's tone, standard messages, and response rules through the panel without code changes (LumatRequest §1.12).

#### Scenario: Message edited
- GIVEN the owner edits a standard bot message or tone setting
- WHEN the change is saved
- THEN subsequent bot replies use the edited content
