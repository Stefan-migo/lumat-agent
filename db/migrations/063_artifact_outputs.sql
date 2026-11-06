-- 063_artifact_outputs.sql — retain published assistant artifacts as project files.
-- No foreign key is intentional: deleting a thread artifact must not delete its published file.

ALTER TABLE project_files ADD COLUMN source_artifact_root_id bigint;
CREATE UNIQUE INDEX uq_project_files_source_artifact
    ON project_files (project_id, source_artifact_root_id)
    WHERE source_artifact_root_id IS NOT NULL;

-- Rollback: DROP INDEX uq_project_files_source_artifact;
--           ALTER TABLE project_files DROP COLUMN source_artifact_root_id;
