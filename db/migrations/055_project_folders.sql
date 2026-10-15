-- 055_project_folders.sql — folders that group project files.
CREATE TABLE project_folders (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_id BIGINT REFERENCES project_folders(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_project_folders_project ON project_folders(project_id);
CREATE INDEX idx_project_folders_parent ON project_folders(parent_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON project_folders TO app;
GRANT USAGE, SELECT ON SEQUENCE project_folders_id_seq TO app;

-- A file belongs to at most one folder. Deleting a folder detaches its files
-- (moves them to the project root) as a safety net; recursive folder deletion is
-- done in the service so each file's linked KB document is removed with it.
ALTER TABLE project_files ADD COLUMN folder_id BIGINT REFERENCES project_folders(id) ON DELETE SET NULL;
CREATE INDEX idx_project_files_folder ON project_files(folder_id);

-- Rollback: DROP INDEX IF EXISTS idx_project_files_folder; ALTER TABLE project_files DROP COLUMN IF EXISTS folder_id; DROP TABLE IF EXISTS project_folders;
