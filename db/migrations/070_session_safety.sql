--
-- Database safety net: abort a transaction that is idle for too long.
--
-- On 2026-11-21 an assistant turn kept a transaction open while it waited on
-- external I/O. It stayed `idle in transaction` for sixteen minutes holding
-- RowShare/RowExclusive locks on internal_chat_threads, internal_chat_messages,
-- assistant_artifacts and friends; every other writer queued behind it, the
-- waiters consumed the SQLAlchemy pool (5 + 10) and every panel endpoint that
-- touches the database answered 500. Recovery required terminating the backend
-- by hand. Nothing in the database could abort that transaction: the value was 0.
--
-- 180 s is a net, not a timeout budget: the application must not hold a
-- transaction across I/O at all (that is fixed in code), so a transaction that
-- has been idle for three minutes is pathological by construction. A session
-- that exceeds it is rolled back and its statement fails, which surfaces as one
-- failed turn with its retry action instead of a wedged service.
--
-- Database-scoped on purpose: it applies to every connection to this database
-- regardless of the role that opens it (the app role, the admin role, an
-- operator's psql), and it survives a rebuilt volume because it is a migration.
-- `ALTER DATABASE ... SET` only affects sessions opened after it commits.

DO $$
BEGIN
    EXECUTE format(
        'ALTER DATABASE %I SET idle_in_transaction_session_timeout = %L',
        current_database(), '180s'
    );
END
$$;

-- Rollback: ALTER DATABASE <db> RESET idle_in_transaction_session_timeout;
