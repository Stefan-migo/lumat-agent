-- 027_kb_visibility.sql — KB audience classification.
--
-- `customer` documents may reach the customer-facing chatbot; `internal`
-- documents are for internal surfaces only. `internal` is the fail-safe
-- default, and this audience axis is orthogonal to source_meta.category, the
-- topic axis defined by AO-7.

CREATE TYPE kb_visibility AS ENUM ('customer', 'internal');

ALTER TABLE kb_documents
  ADD COLUMN visibility kb_visibility NOT NULL DEFAULT 'internal';
