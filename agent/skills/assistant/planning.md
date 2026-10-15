# Planning sessions

A planning session is guided brainstorming on its own chat thread. Open one only
when the user explicitly asks to plan, brainstorm, or think through a topic.

## Flow

- `planning.open` with `topic` starts the session on the current thread. The topic
  is the user's stated subject, not a paraphrase you invent.
- Record only what the user confirms. Ask before each write:
  - `planning.record_decision`: `title`, `content` — a decision the user agreed to.
  - `planning.record_note`: `kind` (`objective`, `risk`, `next_step`, `general`) and
    `content`.
- `planning.close` takes no arguments and writes the session's final report. Never
  infer a decision or a note from your own reasoning.

## Close contract

- The minimum to close is an objective plus at least one decision; anything missing
  is reported as a gap. Closing is never blocked.
- The session is read-only for the business: no business tool runs inside it.
  Concrete actions are taken later, outside the session.
- `planning.read_report` (`slug`) reads a closed session's report by slug. It is
  read-only and never edits or reopens a session.

## Gotchas

- One active session per thread; close it before opening another.
- Do not record decisions, risks, or next steps the user did not state.
