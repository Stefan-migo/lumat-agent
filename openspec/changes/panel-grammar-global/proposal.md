# Proposal: Panel Grammar — Global Appearance, Control-Room Physiology

## Intent

Restore the grammar scope the owner decided on 2026-09-04 and that the
`panel-ai-agent-grammar` delta narrowed by accident: the agent-app appearance
applies to the **whole panel**, while dense content keeps **control-room
physiology**. Remove that drift from the governing spec before the Clientes pilot
is built against it.

## Why now

The Clientes product-register pilot is the first surface to apply the grammar
outside the conversation routes. Built against the current `DS-GRAMMAR-1`, it
would violate a live `MUST`. Built against a silently ignored `MUST`, it would set
the precedent that the spec is advisory. Neither is acceptable, so the contract is
corrected first and the pilot becomes its first consumer.

## Evidence of drift

| Source | Statement |
|---|---|
| `sessions/archived/2026-09-04-frontend-redesign-panel/report.md:11` | "Gramática AI-agent global: apariencia de app de agente en **toda la app**, fisiología de control room en primitivas de contenido denso." |
| `changes/archive/2026-09-07-panel-ai-agent-grammar/proposal.md` | The capability it declares it modifies — `panel-design-system`: "**appearance of agent app, physiology of control room**". |
| `changes/archive/2026-09-07-panel-ai-agent-grammar/specs/panel-design-system/spec.md:7` | "…`PanelShell`, `ConversationThread`, `ConversationsList`, and `AgentChat` expose the agent-app grammar… `Dashboard`, `ClientesList`, `ClientFicha`… MUST retain control-room… primitives." |
| `specs/panel-design-system/spec.md:742` (live) | The delta above, merged verbatim. |

The change kept the physiology half of its own proposal and dropped the
app-wide appearance half. The result is a panel that reads as two products: an
agent application for conversations and an unstyled admin tool everywhere else.

The duplicate `MUST` that lived in `PNL-APP-12` was already superseded by
`panel-conversaciones-redesign`, which rewrote that requirement as
`PNL-APP-12 — Conversation Workspace Context` and carries no dense-page clause.
`panel-app` therefore needs **no delta**; verified by searching the live spec for
`dense` and `control-room` (no matches).

## What changes

- **`panel-design-system` → `DS-GRAMMAR-1` (MODIFIED).** The appearance axis
  covers every production surface. The physiology axis keeps `DataTable`, KPI,
  `Badge`, filter, and state primitives as the data layer for dense pages, and
  conversation-specific components are explicitly barred from them.

## What does not change

- No token value changes (`DS-TKN-2` still governs; additive only).
- No dependency, no CSS framework, no font, no dark mode.
- No backend, API, or permission behaviour.
- No change to the conversation surfaces' own contracts (`DS-CC-1`, `DS-CC-3`,
  `DS-RT-1`, `DS-RT-2`, `IAC-4`).
- No conversion of dense data presentation from tables to another form: the
  physiology axis is preserved deliberately, because it protects the operational
  density the owner accepted as a risk.

## Approach

One modified requirement plus one added scenario, delivered **with its first
consumer** rather than as an abstract spec-only change. This follows the
repository's own pattern: every archived OpenSpec change pairs its deltas with an
implementation and an apply/verify record. The amendment ships in the first
Clientes slice, so the contract change and its evidence of use are reviewed
together.

`web/DESIGN_SYSTEM.md` gains the same statement in product-doc form, so the
two-axis rule is not discoverable only through the spec.

## Rollback

Revert the delta commit. `DS-GRAMMAR-1` returns to its current text and the pilot
must be re-scoped to composition-only. No production behaviour depends on this
change on its own.

## Affected areas

| Area | Impact | Description |
|---|---|---|
| `openspec/changes/panel-grammar-global/specs/panel-design-system/spec.md` | Added | The delta itself. |
| `openspec/specs/panel-design-system/spec.md` | Modified at archive | Delta syncs into the live spec when the change is archived. |
| `web/DESIGN_SYSTEM.md` | Modified | Direction at a glance plus a two-axis subsection. |
| `odd/tasks/clientes-product-register.md` | Modified | The pilot is the first consumer; its plan carries the amendment. |
