-- 030_memory_visibility_global.sql — rename the declared visibility value.
--
-- `project` named the "reachable from every thread" declaration, but it collides
-- with the `proyecto` namespace axis: 024_projects made `proyecto` a real column
-- and `agent_memory_entity()` already qualifies the agent entity as
-- `agent:<project>`. The same word ended up on both sides of one write.
--
-- The column is a pure mirror of `scope` (026_memory_provenance.sql):
-- `global` <=> `scope='agent'`.
--
-- RENAME VALUE is an in-place catalog update — it does not rewrite `memories`,
-- and every existing row keeps its meaning. The coherence CHECK has to be
-- replaced because its expression carries the literal, and the `'thread'`
-- column default is unaffected.
-- ponytail: no backfill and no dual-label window; the rename is atomic, so
-- there is no interval where both labels are accepted.

ALTER TYPE memory_visibility RENAME VALUE 'project' TO 'global';

ALTER TABLE memories
  DROP CONSTRAINT memories_visibility_scope_coherence,
  ADD CONSTRAINT memories_visibility_scope_coherence
    CHECK ((visibility = 'global') = (scope = 'agent'));
