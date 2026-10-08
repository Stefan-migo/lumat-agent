ALTER TYPE document_format ADD VALUE IF NOT EXISTS 'docx';
ALTER TYPE document_format ADD VALUE IF NOT EXISTS 'xlsx';

-- Rollback: PostgreSQL cannot drop enum values; retain 'docx' and 'xlsx'.
