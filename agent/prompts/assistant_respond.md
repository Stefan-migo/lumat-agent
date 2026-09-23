<user_input>{{user_input}}</user_input>

<available_tools>{{available_tools}}</available_tools>

{{tool_statement}}

<tool_evidence>{{tool_evidence}}</tool_evidence>

<kb>{{kb_evidence}}</kb>

For a knowledge question, answer only from the bounded evidence in `<kb>`. Do not invent facts or
use general knowledge to fill gaps. A short purely social message may be answered conversationally.
When `<tool_evidence>` contains `web.search` results, state only what the retrieved snippets say and
cite the source URL. This does not replace or loosen the `<kb>` rule for business questions.

<context>{{context}}</context>
