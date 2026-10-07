ALTER TABLE kb_documents
  ADD COLUMN project_id BIGINT NULL REFERENCES projects(id) ON DELETE CASCADE;

CREATE INDEX idx_kb_documents_project_id ON kb_documents (project_id);
