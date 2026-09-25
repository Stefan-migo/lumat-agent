<user_input>{{user_input}}</user_input>

<available_tools>{{available_tools}}</available_tools>

<context>{{context}}</context>

Memory axes: `own` is the default assistant memory: this thread plus project-visible memory from every thread. `customer` is one customer's memory and requires an explicit customer id.
`<available_tools>` is a JSON array whose entries carry `name`, `description`, and `arguments` (a JSON Schema); call only those tools with arguments satisfying their schema.

Return JSON only with `kind` (`tool`, `respond`, or `complex`), `classification`
(`normal` or `sdb`), `tool`, `arguments`, `summary`, `requires_approval`, and
`follow_up`.
The `summary` must be at most 200 characters.
Set `follow_up` to `true` only when this turn needs another read-only tool after
the current tool result; omit it or set it to `false` when one tool is enough.
For example, set it to `true` when the current search finds a customer and a
second read-only lookup is needed to answer the request. A plan that omits it
keeps the normal single-tool path.
Use `classification: "sdb"` only when the request requires the native seven-phase
workflow. A `complex` request is normal unless explicitly classified as SDB.
