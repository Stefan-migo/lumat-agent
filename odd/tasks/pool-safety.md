# pool-safety

Production availability fix for the 2026-11-21 incident: a wedged assistant turn held an open
transaction for 16 minutes, blocked every writer, exhausted the SQLAlchemy pool (5+10) and turned
every DB-touching panel endpoint into a 500. Four fixes: DB safety guard, no transaction across
external I/O, pool configuration, and a failure path that survives a deadlock.

## Specs

S1 — Production carries `idle_in_transaction_session_timeout = 180s` as a safety net, and the
setting is reproducible from the repository (a migration), not a hand-run `ALTER DATABASE` that a
rebuilt database silently loses.

S2 — An assistant turn never holds an open transaction while it waits on external I/O (the provider
call or a tool's own work). At every such boundary the work already done is committed and the pooled
connection returns to the pool, so a slow turn occupies a connection only while it is actually
talking to Postgres.

S3 — The connection pool is configurable per environment (`pool_size`, `max_overflow`,
`pool_timeout`, `pool_recycle`) with defaults that do not let a handful of concurrent turns collapse
the whole API, and a request that cannot get a connection fails fast instead of silently waiting the
driver default.

S4 — When the database aborts the failure path itself (deadlock / `OperationalError` while recording
the failure), the operator-facing message still ends `failed` with the exact text
`"El agente no pudo procesar este mensaje. Reinténtalo."`, the thread stays retryable, and the
bookkeeping error never escapes the background task.

S5 — No behavioural regression for the paths that already worked: the SSE stream still releases its
pooled connection, a normal successful turn still persists its response, an approval turn still
parks, and a cancelled turn still ends `cancelled`.

## Tasks

| ID | Spec | Route | Commit |
|---|---|---|---|
| T1 | S1 | migration `070_session_safety.sql` + apply to production + `docs/ops.md` | `1bde1665f` |
| T2 | S2 | `app/db.py`, `app/chat/assistant/graph.py`, `app/services/agent_chat.py` | (this commit) |
| T3 | S3 | `app/config.py`, `app/db.py` | — |
| T4 | S4 | `app/services/agent_chat.py` | — |

## Log

L1 — Owner request, verbatim:

> "hey chat necesito que entres al VPS ahora busca en la memoria de engram como hacerlo. ya tienes la
> autorizacion. entra modo solo lectura. necesito que chequees el asistente lumat que al parecer se
> ha crasheado. pero no lo puedo solucionar desde el panel. puedes ejecutar algun comando solo si la
> situacion es critica y necesita solucionarse ahora"

L2 — Incident evidence gathered read-only on production (VPS `179.199.148.175`, release v2026.11.13,
commit `3796477f`). Containers healthy, 0 restarts, disk 12%, RAM fine: the server was never down.
`pg_stat_activity` showed backend `4016327` `idle in transaction` for 16 minutes (last statement
`RELEASE SAVEPOINT sa_savepoint_1`) holding RowShare/RowExclusive on `internal_chat_threads`,
`internal_chat_messages`, `assistant_artifacts`, `audit_log`, `project_files`, `projects`, `users`.
`pg_blocking_pids()` showed a 6-deep chain of waiters behind it. The waiters consumed the pool
(5+10), and after 30 s every DB-touching endpoint raised
`sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached`, including
`/panel/api/chat/active-runs` (500). The application's own failure handler then deadlocked trying to
mark message 214 as failed, which is why nothing self-healed. Wedge source: thread 55, message 214,
run `7b5891661c0b492486ee10337491e40d`, stage `planning`, status `running` from 17:49:54 UTC.

L3 — Emergency action (authorized by L1 for a critical, must-fix-now situation): single
`SELECT pg_terminate_backend(4016327)` against the lock holder only. Result: locks released, pool
back to 7 connections, message 214 recorded `failed`, a new run `464bd1772a68425988d2dd7197a7cad6`
completed in thread 55, `/health` 200 and `/panel/api/*` 401 (auth) instead of 500.

L4 — Root cause in code, located: `run_agent_turn` opens one session and `_run_agent_turn_session`
runs `assemble_context` + `compact_session` (which write) and then `run_assistant` — the whole
provider call and tool loop — on that same session, so the transaction opened by the pre-work stays
open and idle for the entire turn. Tool implementations in `app/chat/assistant/tools/registry.py`
(893, 941, 960, 1022, 1183, 1231) also flush into that session, extending the window.

L5 — Production DB had no safety net at all: `idle_in_transaction_session_timeout = 0`,
`statement_timeout = 0`, `lock_timeout = 0`, `max_connections = 100`. Nothing would ever abort a
wedged transaction.

L6 — Owner decisions: worktree ODD `../lumat-agent-odd-pool-safety` on `odd/pool-safety` (explicit
per-feature consent), and `idle_in_transaction_session_timeout = 180s` for production.
