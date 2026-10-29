-- 059_memory_user_scope.sql — admit authenticated-user global memories.
--
-- The user axis shares global visibility with the existing agent axis. Thread
-- visibility remains exclusive to the panel axis; global visibility is limited
-- to agent and user scopes.

ALTER TABLE memories
  DROP CONSTRAINT memories_visibility_scope_coherence,
  ADD CONSTRAINT memories_visibility_scope_coherence
    CHECK ((visibility = 'global') = (scope IN ('agent', 'user')));
