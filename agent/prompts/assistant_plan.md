<user_input>{{user_input}}</user_input>

<available_tools>{{available_tools}}</available_tools>

<context>{{context}}</context>

Tools reading or writing memory for the current conversation use `scope="panel"` and `entity_id="thread:<thread id>"`; `<context>` states that identity.

Return JSON only with `kind` (`tool`, `respond`, or `complex`), `classification`
(`normal` or `sdb`), `tool`, `arguments`, `summary`, and `requires_approval`.
Use `classification: "sdb"` only when the request requires the native seven-phase
workflow. A `complex` request is normal unless explicitly classified as SDB.
