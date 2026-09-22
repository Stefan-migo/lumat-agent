<user_input>{{user_input}}</user_input>

<available_tools>{{available_tools}}</available_tools>

<context>{{context}}</context>

Memory axes: `own` is the default assistant memory: this thread plus project-visible memory from every thread. `customer` is one customer's memory and requires an explicit customer id.
`<available_tools>` is a JSON array whose entries carry `name`, `description`, and `arguments` (a JSON Schema); call only those tools with arguments satisfying their schema.

Return JSON only with `kind` (`tool`, `respond`, or `complex`), `classification`
(`normal` or `sdb`), `tool`, `arguments`, `summary`, and `requires_approval`.
The `summary` must be at most 200 characters.
Use `classification: "sdb"` only when the request requires the native seven-phase
workflow. A `complex` request is normal unless explicitly classified as SDB.
