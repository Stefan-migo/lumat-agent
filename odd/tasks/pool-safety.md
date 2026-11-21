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
talking to Postgres. The exception is the turn that resumes an approved write: it consumes its
approval and records its claim in one unit, so a commit at a boundary would let a crash look like a
consumed approval with the write half-applied. That turn keeps its single transaction and is bounded
by S1's guard instead; `test_resume_path_never_commits_or_publishes_mid_execution` is the contract it
must keep.

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
| T1 | S1 | migration `070_session_safety.sql` + apply to production + `docs/ops.md` | `1bde1665f` done |
| T2 | S2 | `app/db.py`, `app/chat/assistant/graph.py`, `app/services/agent_chat.py` | `82ecd5ca7` done |
| T3 | S3 | `app/config.py`, `app/db.py`, `infra/.env.example`, `docs/ops.md` | `37f4de3d5` done |
| T4 | S4 | `app/services/agent_chat.py`, `tests/integration/test_assistant_chat.py` | `5fedec8f6` done |

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

L7 — Delivery and deliberate trade-offs. The slice is 524 authored lines across four commits, each
one coherent work unit with its own risk line; `scripts/test.sh shape origin/main` reports
`app/config.py` and `db/migrations/070_session_safety.sql`, so the shape rule makes `full` mandatory
at this boundary. Three consequences worth knowing before reading the diff:

1. A failing turn now keeps the work its completed steps committed (artifacts, tool writes); before,
   the whole turn was one transaction and rolled back. That is the point of S2 — the work is durable
   and the connection is free — and it means "a failed turn writes nothing" is no longer true for
   step-level writes. `test_failed_run_does_not_persist_partial_response` still holds because an
   agent message is only created on success.
2. The failure recovery records the terminal state through `_fail_orphaned_run`, which does not write
   the exception's `events` entry. The exception itself is in the API log via `logger.exception`, and
   the single fail-closed primitive is worth more than the duplicated merge.
3. `STATEMENT_TIMEOUT` and `LOCK_TIMEOUT` were deliberately left untouched at the database level: the
   analytics tools legitimately run long reads, and a statement timeout would kill them. The idle
   guard plus a bounded lock wait in the recovery path cover the failure mode that actually happened.

L8 — S2 scoped by measurement, not by preference. The first `full` run after the four tasks failed
three falsification probes in `tests/integration/test_assistant_write_chain_recovery_verifier_probes.py`
and the migration inventory in `tests/integration/test_migrations.py`. The probes encode a guarantee
this request never mentioned: "a crash inside the approved write transaction leaves the approval
pending and execution_status pending -- never running, never consumed", and "`resume_thread` must not
commit or call `publish_live` between the claim and the final persist". Releasing at every node
boundary broke exactly that: a commit between the claim and the result would make a crashed write
look like a consumed approval with the write half-applied — a double-execution risk, not a cosmetic
regression. Resolution: `build_assistant_graph(release_transactions=...)`, false for the resume path;
the approval turn keeps today's behavior and S1's guard covers it. The migration inventory simply
gained `070_session_safety`.

Two process notes worth keeping:

- The first `full` invocation reported exit 0 while four tests failed, because it was piped into
  `tail`: the pipeline's status is `tail`'s. Redirect to a file and echo `$?` instead.
- `full` at this boundary was not ceremony. `quick` was green twice over code that broke the
  approval claim, because that contract lives only in the probes the fast tiers do not run.

Delivery: 4 work-unit commits plus this amendment, ~560 authored lines on `odd/pool-safety`. The two
shape surfaces (`app/config.py`, `db/migrations/070_session_safety.sql`) are what made `full`
mandatory. If the owner prefers smaller review units, the natural split is T1 (database guard + docs),
T2+T4 (turn transaction and failure path), T3 (pool sizing).
