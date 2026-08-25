# Superseded Change Record

## `2026-08-20-v1-shell-header-and-bg` — abandoned at archive

Status: **superseded / abandoned** (recorded, not deleted, archived abandoned)

The change `openspec/changes/2026-08-20-v1-shell-header-and-bg/proposal.md`
describes a continuous-green-bar header that is no longer implemented. The v1
shell has since been re-authored onto the CortexDesign/Calama Operacional
contract (`--corp-*` slots, Badge/Avatar primitives) with a text-only panel
header and a dark-green sidebar — see this port, `2026-08-24-v1-shell-cortex-port`
(DS-STORY-2, DS-SHELL-1..5).

Per the supersession note in this change's delta spec (`spec.md:103-104`), the
stale directory:

- **stays on disk** — untouched, no code deletion;
- is **not** resurrected or edited here;
- is recorded as abandoned so future archive/explore passes know it is dead
  and do not treat the old header direction as current.

Scope of what was abandoned: the continuous-green-bar header layout, its
`--header-gradient` token (already removed), and the `Design system · v1.0`
tag copy. None of these are part of the current shell.
