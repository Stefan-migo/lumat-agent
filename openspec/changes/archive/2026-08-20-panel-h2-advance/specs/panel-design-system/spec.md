# Delta for panel-design-system

## ADDED Requirements

### Requirement: R-PRD-PG-14 — Conversation State Domain

`Conversation.state` SHALL be constrained to the `bot|human|closed` domain in every story mock and related rendering. The shipped H1 mock's invalid `"open"` value SHALL NOT recur (R1); `Conversation.state` in `types.ts` remains a plain `string` (typecheck-safe, no type change), so the domain is enforced by mock values and tests. This aligns with the shipped `StatusBadge` `Status` subset (`bot|human|closed`) and its tone map (S1, S2).

#### Scenario: Mock domain is valid

- GIVEN all `Conversation` mock rows under `_shared/mockData/conversations.ts`
- WHEN the test iterates every `state` value
- THEN each is exactly `bot`, `human`, or `closed`, and no `"open"` value appears

#### Scenario: StatusBadge renders every domain state

- GIVEN a mock conversation in any of the three states
- WHEN its state renders through `StatusBadge`
- THEN it maps to the `bot`/`human`/`closed` tone as defined by `statusTone` (neutral/warning/success)
