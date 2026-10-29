# Tukulpan memory

Use memory tools only for relevant durable context. Read before relying on prior
decisions or facts; write only when the information is likely to matter later.

## When to write

Capture durable learning immediately after: (1) a completed fix, (2) a decision,
(3) a discovery, (4) a configuration change, (5) an established pattern, or
(6) a stated owner preference. A person-level fact belongs to the user axis later;
this tool writes only assistant-owned memory.

## Axes and ownership

- `scope="own"` is the default for `memory.read` and `memory.search`. It combines
  this trusted thread's `panel` memories with `agent` memories in the bound project.
- `scope="customer"` addresses one customer's memory only. Supply that customer's
  explicit `entity_id` (`"customer:<id>"` or the numeric id as a string); never
  guess or derive a customer id from unrelated context.
- The storage scopes are `panel` (thread), `agent` (project), and `customer`.
  The read/search tools accept `own` or `customer`, not `panel` or `agent` directly.
- Every memory tool call requires an authenticated owner, supplied by the runtime,
  not by the model. Own-axis access is bound to the trusted thread/project; own
  reads/searches use the project's owner, and writes/updates/deletes enforce it.
  Do not supply an owner, project, thread, or write target.
- `memory.write` writes assistant-authored memory to the thread, project, or
  user axis; it cannot create customer-axis memories. Customer records belong
  on the customer axis and are not editable through this tool.
- Use `visibility="user"` for a person's memory. It is readable across projects
  and is never another user's memory; the server binds it to the authenticated
  user, not to a project's owner. Project facts remain on the project axis.

## Tool arguments

Use these JSON shapes (include only the shown optional fields when needed):

```json
{"topic":"agent:planning","limit":10}
```

`memory.read`: `scope` defaults to `own`; optional `topic`, `limit`. For customer
memory use `{"scope":"customer","entity_id":"customer:42"}` with optional
`topic` and `limit`. For own memory, omit `entity_id` or set it to `null`.

```json
{"query":"deployment decision","limit":5}
```

`memory.search`: `scope` defaults to `own`; required `query`, optional `limit`.
For a customer search use `{"scope":"customer","entity_id":"customer:42",
"query":"service preference"}`. Own search must omit `entity_id` or set it to
`null`.

```json
{"titulo":"Release choice","contenido":"...","topic_key":"agent:release",
 "tipo":"decision","visibility":"global","handoff":false}
```

`memory.write` requires `titulo`, `contenido`, `topic_key` beginning with
`agent:`, and `tipo` (`decision`, `discovery`, `pattern`, or `preference`).
`visibility` is `global` by default or `thread` for thread-only context.
`handoff` is optional (default `false`); set `handoff: true` when the memory
leaves a continuation point — an open thread of work or the pending ordering of
tasks — so later turns surface it right after pinned memory when they read own
memory. Leave it `false` for durable facts that need no resumption.

```json
{"id":123,"contenido":"Corrected fact"}
{"id":123}
```

`memory.update` requires an existing `id` and at least one of `titulo`,
`contenido`, or `tipo`. `memory.delete` requires only the existing `id`.

## Gotchas

- Never pass `scope`/`entity_id` for own reads as `panel` or `agent`; those are
  storage scopes, not accepted tool selectors.
- `memory.write` defaults to `visibility="global"` (project-visible), not
  thread-only. Choose `thread` explicitly for conversational episodic details.
- Update/delete are limited to assistant-owned `agent:` memories on this thread's
  `panel` axis or the bound project's `agent` axis; an arbitrary memory id fails.
