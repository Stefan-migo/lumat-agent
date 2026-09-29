-- 034_project_owners.sql — add owner-scoped project and memory namespaces.
--
-- Legacy-row enumeration (D9 — run and confirm BEFORE applying this migration).
-- The backfill below only fires when EXACTLY ONE admin exists; with zero or two
-- or more admins every ownership update is a deliberate no-op, which leaves
-- legacy non-default projects and their panel/agent memory ownerless (invisible
-- to every panel route, which filters by owner) and requires manual reassignment.
-- Confirm the list against the intended owner before applying:
--
--   SELECT count(*) AS admin_count FROM users WHERE role = 'admin';   -- must be 1
--   SELECT id, slug, name FROM projects WHERE slug <> 'default';
--   SELECT id, proyecto, scope, entity_id, topic_key
--     FROM memories WHERE proyecto <> 'default' AND scope IN ('panel', 'agent');
--
-- (These queries deliberately avoid owner_id, which does not exist until this
-- migration runs.)

ALTER TABLE projects ADD COLUMN IF NOT EXISTS owner_id BIGINT REFERENCES users(id);
ALTER TABLE project_aliases ADD COLUMN IF NOT EXISTS owner_id BIGINT REFERENCES users(id);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS owner_id BIGINT REFERENCES users(id);

-- Legacy projects and project-axis memory belong to the sole admin. If the admin
-- identity is absent or ambiguous, these updates are intentionally no-ops.
WITH admin AS (
    SELECT min(id) AS id FROM users WHERE role = 'admin' HAVING count(*) = 1
)
UPDATE projects
SET owner_id = (SELECT id FROM admin)
WHERE slug <> 'default' AND owner_id IS NULL AND EXISTS (SELECT 1 FROM admin);

UPDATE project_aliases AS alias
SET owner_id = project.owner_id
FROM projects AS project
WHERE alias.project_id = project.id AND alias.owner_id IS NULL
  AND project.owner_id IS NOT NULL;

WITH admin AS (
    SELECT min(id) AS id FROM users WHERE role = 'admin' HAVING count(*) = 1
)
UPDATE memories
SET owner_id = (SELECT id FROM admin)
WHERE proyecto <> 'default' AND scope IN ('panel', 'agent') AND owner_id IS NULL
  AND EXISTS (SELECT 1 FROM admin);

DROP INDEX IF EXISTS uq_projects_normalized_slug;
CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_owner_normalized_slug
    ON projects (owner_id, lower(btrim(slug))) NULLS NOT DISTINCT;

ALTER TABLE project_aliases DROP CONSTRAINT IF EXISTS uq_project_aliases_alias;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'project_aliases'::regclass
          AND conname = 'uq_project_aliases_owner_alias'
    ) THEN
        ALTER TABLE project_aliases ADD CONSTRAINT uq_project_aliases_owner_alias
            UNIQUE NULLS NOT DISTINCT (owner_id, alias);
    END IF;
END $$;

ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_proyecto_scope_entity_id_topic_key_key;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'memories'::regclass
          AND conname = 'uq_memories_owner_project_scope_entity_topic'
    ) THEN
        ALTER TABLE memories ADD CONSTRAINT uq_memories_owner_project_scope_entity_topic
            UNIQUE NULLS NOT DISTINCT (owner_id, proyecto, scope, entity_id, topic_key);
    END IF;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON projects, project_aliases TO app;
GRANT SELECT, INSERT, UPDATE, DELETE ON memories TO app;

-- Rollback plan (manual and conditional — NOT a single executable script).
--
-- 034 cannot be reversed by one safe statement. The owner_id columns it adds are
-- required by the application shipped with this unit, and restoring global
-- uniqueness fails as soon as two owners legitimately share a slug or alias.
-- Reverse only together with the application, and only when every precondition
-- below holds. Dropping the owner_id columns discards ownership permanently.
--
-- Preconditions — each must hold, or the matching step fails:
--   1. no two owners share a normalized project slug
--   2. no two owners share an alias
--   3. no two owners share a (proyecto, scope, entity_id, topic_key) key
--
-- Steps, in order:
--   ALTER TABLE memories DROP CONSTRAINT IF EXISTS uq_memories_owner_project_scope_entity_topic;
--   ALTER TABLE memories ADD CONSTRAINT memories_proyecto_scope_entity_id_topic_key_key
--       UNIQUE (proyecto, scope, entity_id, topic_key);
--   ALTER TABLE project_aliases DROP CONSTRAINT IF EXISTS uq_project_aliases_owner_alias;
--   ALTER TABLE project_aliases ADD CONSTRAINT uq_project_aliases_alias UNIQUE (alias);
--   DROP INDEX IF EXISTS uq_projects_owner_normalized_slug;
--   CREATE UNIQUE INDEX uq_projects_normalized_slug ON projects (lower(btrim(slug)));
--
-- Destructive, and only when the ownership data is deliberately abandoned:
--   ALTER TABLE projects DROP COLUMN IF EXISTS owner_id;
--   ALTER TABLE project_aliases DROP COLUMN IF EXISTS owner_id;
--   ALTER TABLE memories DROP COLUMN IF EXISTS owner_id;
--
-- (Unlike 037 this block is not a runnable blob on purpose: no line is prefixed
-- with the 037 rollback marker, so a marker-based extractor cannot execute it
-- blindly.)
