-- 034_project_owners.sql — add owner-scoped project and memory namespaces.

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
