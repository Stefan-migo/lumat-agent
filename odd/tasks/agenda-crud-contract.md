# ODD — agenda-crud-contract

## Objective

Amend the live agenda capability spec so its contract matches the shipped creation capability and records the approved agenda CRUD, appointment detail, and non-active register behavior.

## Problem

The live `openspec/specs/agenda-calendar-ui/spec.md` forbids creation and editing controls in AG-UI-1 and forbids creation, editing, and rebooking in AG-UI-3. Creation already shipped in PR #341 as `POST /panel/api/appointments` and the `Nueva visita` dialog (`odd/tasks/agenda-booking.md`); decision D8 only narrowed the frontend “no new controls” test guard. The live spec was not amended, and its history contains no creation-related amendment. **This unit heals the PR #341 drift between the shipped capability and its contract.**

## Why

The spec is the contract authority for the agenda. Keeping a shipped capability forbidden in the live record misleads follow-up implementation and verification. This unit records the approved scope without implementing it.

## Scope (authorized by the owner)

**In:**

- `openspec/specs/agenda-calendar-ui/spec.md`: remove the obsolete creation/editing prohibition; clarify allowed creation and booked-only editing/rescheduling while preserving the cancellation contract; add appointment detail and non-active register requirements.
- `odd/tasks/agenda-crud-contract.md`: this ODD unit record.

**Out:** application code, test changes, database or API changes, customer full CRUD, availability blocks, and appointment row deletion.

## Decision

- **D1:** A visit remains tied to a chatbot `Case`; the agenda gains the ability to create a case.
- **D2:** `Case.conversation_id` becomes nullable so a case may exist without a conversation.
- **D3:** There is no row DELETE of an appointment. Cancellation is a soft/non-active status, with non-active visits available through a register filter.
- **D4:** Manual case creation happens inline in the visit dialog's `Caso` field.

## Constraints

- Contract-only: no application code and no tests apply; this is a spec text change.
- Verification is a read-back of the amended spec plus a scope diff.
- Preserve the existing Purpose, AG-UI-2 and AG-UI-4 text, RFC 2119 keywords, and Given/When/Then scenario format.
- Do not add availability blocks, customer full CRUD, or appointment row deletion.
- Operator-facing UI copy stays Spanish. Spec text, task documentation, comments, and commit messages are English.
- Commit only the spec and this task document; do not push or open a PR.

## Graph check

Consulted `graphify-out/GRAPH_REPORT.md` (god nodes `Case`, `Customer`; community hub `AgendaPage.tsx`) and ran `graphify query "agenda calendar UI specification requirements appointments and cancellation"`. Nodes consulted included `Agenda Calendar UI Specification`, `appointments.py` (`create_appointment()`, `get_appointment()`, `cancel_appointment()`), `Case`, `Customer`, `AgendaPage`, and the AG-UI requirement set. `graphify path "agenda-calendar-ui" "appointment"` and `graphify path "agenda-calendar-ui" "ODD task documentation"` returned no directed path (first target ambiguous); no path edges were reported. Graph report states it was built from commit `8e25037c`.

## Tasks

| ID | Task | Route |
|----|------|-------|
| T1 | Amend AG-UI-1 and AG-UI-3 to align shipped creation and approved booked-only edit/reschedule and terminal cancellation contract. | local |
| T2 | Add AG-UI-5 appointment detail route/surface contract and conversation/no-conversation scenarios. | local |
| T3 | Add AG-UI-6 non-active register filter contract and scenario; preserve AG-UI-2 and AG-UI-4. | local |
| T4 | Read back spec, check scope diff and managed-block boundary, save this task mirror to Engram, and commit the two files. | local |

## Delivery

One spec text change plus one task doc → single PR against `main`, well inside the ~400-line budget, no chained slices.

## Progress / Evidence

- [x] Amend the live spec and author this task record.
- [x] Read back the full spec and verify the targeted requirements and untouched AG-UI-2/AG-UI-4.
- [x] Confirm scope is limited to these two files and the task doc is outside any `gentle-ai` managed block.
- [x] Save the task doc to Engram using the requested CLI command (observation #5027).
- [ ] Commit both files in one work-unit commit.

## Next step

Owner may review and deliver the single PR against `main`; no PR is created by this unit.
