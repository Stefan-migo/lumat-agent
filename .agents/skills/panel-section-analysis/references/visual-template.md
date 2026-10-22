# Section visual analysis

Lifecycle: `captured → owner-review → owner-done → code-analysis → validated → implementing → done`

## Sources

Current images:
- `refs/current/<section>/desktop.png`
- `refs/current/<section>/tablet.png`
- `refs/current/<section>/mobile.png`

Reference images:
- `<reference desktop path>`
- `<reference tablet path>`
- `<reference mobile path>`

App commit: `<commit from capture manifest>`
Capture date: `<YYYY-MM-DD>`

## Owner analysis

Owner: fill one block per screen and breakpoint with what you expect, what you see, and severity.
The agent must stop and wait until this block is complete; code analysis cannot start before then.

### <screen> — <breakpoint>

screen: <name>
breakpoint: <desktop|tablet|mobile>
expected: <what you expect to see>
actual: <what you saw>
severity: <blocker|major|minor|nit>

<!-- Repeat the block above for every screen/breakpoint. -->
