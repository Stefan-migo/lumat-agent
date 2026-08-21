# Delta for Customer Records

## ADDED Requirements

### Requirement: CR-7 — Living Customer Memo on Ficha

The customer record (ficha) MUST surface the living customer_memo stored in the memory layer (`scope=customer`). The memo MUST be visible to authorized panel users when opening a ficha and MUST reflect the latest version written at conversation close (MEM-4). Internal staff notes (`customer_notes`, CR-4) MUST remain separate and unchanged.

#### Scenario: Ficha shows memo
- GIVEN a customer whose conversations have closed and produced a memo
- WHEN an authorized user opens the ficha
- THEN the latest customer_memo content is displayed on the ficha

#### Scenario: Memo and notes coexist
- GIVEN a customer has both a customer_memo and staff notes
- WHEN the ficha is opened
- THEN the auto-generated memo and the staff-authored notes are shown as distinct, both retained

#### Scenario: No memo yet
- GIVEN a customer with no closed conversation producing a memo
- WHEN the ficha is opened
- THEN the memo surface is empty
- AND no error is raised

## Boundaries

`customer_notes` (CR-4) is unchanged. The memo is read-only in the panel (managed under the `memory` capability, MEM-6); CR-7 only surfaces it on the ficha.
