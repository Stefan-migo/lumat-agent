---
name: ponytail-plan
description: >
  Review plans, designs, and tasks before code is written. Finds over-engineering
  early: YAGNI features, stdlib alternatives, scope that can shrink, tasks that
  can merge. One line per finding: section, what to cut, what replaces it.
  Trigger: reviewing specs, designs, task lists, implementation plans, or
  anything /ponytail-plan.
license: MIT
metadata:
  author: DietrichGebert
  version: "1.0"
source: github.com/DietrichGebert/ponytail
---

Review plans, designs, and task lists for unnecessary complexity before a
single line of code is written. Same philosophy as ponytail-review but applied
to structured text content — proposals, design documents, and task lists —
instead of code diffs.

## Format

`Section "<heading>": <tag> <what>. <replacement>.`

Tags:

- `delete:` dead scope, unrequested feature, non-goal that leaked into the plan.
- `stdlib:` over-engineered approach the standard library already covers. Name the function.
- `native:` platform or existing dependency that already solves it.
- `yagni:` abstraction with no second consumer, config nobody will set, layer with one caller.
- `shrink:` tasks that can merge, scope that can narrow, sections that can condense.

## Examples

❌ "The architecture section proposes a message queue for a cron job that runs once per day. Have you considered whether this level of abstraction is necessary at this point?"

✅ `Section "Architecture": yagni: message queue for a daily cron job. The cron handler calls the service directly, no broker needed.`

✅ `Section "Data Layer": stdlib: hand-rolled UUID generation in three files. `uuidgen`/`std::uuid`, 0 deps, delete the helper module.`

✅ `Section "Tasks": shrink: "Validate config schema" and "Write config tests" are one task. Task 4.2 + 4.3 → "Validate config with tests".`

✅ `Section "Scope": delete: "Export to PDF" is flagged as a non-goal in the PRD. Remove task group 7 entirely.`

✅ `Section "Frontend": native: custom dropdown component. `<select>` with CSS, 0 JS, done.`

## Scoring

End with: `No plan to cut from. Clean slate.` if nothing to flag.
Otherwise: `net: -<N> items cut from plan.`

## Boundaries

Operates on structured text content only — proposals, design docs, task lists,
implementation plans. Not for code diffs (use ponytail-review for that).
Does not apply the fixes, only lists them.

"stop ponytail-plan" or "normal mode": revert to verbose review style.
