# Knowledge Base Specification

## Purpose

Provide Lumat's expert knowledge base (manufacturer manuals, procedures, tariff info, FAQ, troubleshooting, error codes) as the single authorized source for bot answers, via a chunk-and-embed ingestion pipeline into pgvector, semantic retrieval, and a panel-based manager with versioning. No code changes required to update content.

## Requirements

### Requirement: KB-1 — Ingestion Pipeline

The system MUST ingest documents (PDF manuals, Markdown, CSV tariff data) by chunking and embedding them through the configured embedding provider API, storing vectors in pgvector with source metadata (document, section, chunk index). The embedding provider and model used MUST be recorded and named, together with cost information (LumatRequest §1.12).

#### Scenario: Document ingested
- GIVEN a KB document is uploaded
- WHEN the ingestion pipeline runs
- THEN the document is chunked, embedded, and stored in pgvector with metadata

#### Scenario: Provider and model named
- GIVEN ingestion is configured
- WHEN the pipeline runs
- THEN the provider, model, and cost are recorded and visible to the owner

### Requirement: KB-2 — Semantic Retrieval

The system MUST retrieve relevant KB content by semantic similarity with a configured top-k and relevance threshold. The bot MUST answer only from authorized KB content and MUST NOT invent facts absent from the KB.

#### Scenario: Relevant retrieval
- GIVEN a customer asks a question covered by the KB
- WHEN semantic search runs
- THEN the top relevant chunks are returned for answer generation

#### Scenario: No relevant content
- GIVEN a question with no chunk above the relevance threshold
- WHEN retrieval runs
- THEN the bot responds that it cannot answer reliably, logs the unresolved response, and follows escalation rules

### Requirement: KB-3 — KB Manager

Authorized panel users (admin) MUST be able to add, edit, and disable documents through the panel without code changes. Content changes MUST take effect without redeploying the application.

#### Scenario: Admin edits a document
- GIVEN an admin opens the KB manager in the panel
- WHEN they edit and save a document
- THEN the updated content is ingested and active without code changes or redeploy

### Requirement: KB-4 — Versioning and Re-Ingestion

The system MUST version documents and re-ingest on update, preserving the previous version so it can be inspected or restored.

#### Scenario: Re-ingestion on update
- GIVEN a document with an existing version is updated
- WHEN the update is saved
- THEN a new version is created, re-ingested, and the prior version remains retrievable

#### Scenario: Restore previous version
- GIVEN an active document version is found incorrect
- WHEN an admin restores a prior version
- THEN the prior version becomes active and re-ingested

### Requirement: KB-5 — Document Audience

The system MUST classify every KB document with an audience of `customer` or `internal`, stored as a `NOT NULL`, database-enforced column on `kb_documents`, defaulting to `internal` (fail-safe). The audience restriction is enforced on `kb_documents.visibility`.

Customer-facing readers MUST retrieve only `customer` documents; the customer WhatsApp chatbot and its research-triage sub-graph MUST filter to `customer`. Internal readers — the Lumat assistant and the admin retrieval probe — MAY read the whole active corpus.

Retrieving KB content MUST default to the `customer` audience, so a caller that omits the audience cannot read internal-only content.

Restoring a document version MUST NOT widen the audience; a restore re-opens the document as `internal`, and re-publishing it to customers MUST be an explicit, separate action.

Reclassifying a document MUST NOT create a new version and MUST be recorded in the audit log.

#### Scenario: Internal document is invisible to the customer
- GIVEN a KB document with audience `internal`
- WHEN the customer chatbot retrieves KB content for a question that document answers
- THEN the document is not retrieved and the bot does not answer from it

#### Scenario: Fail-safe default
- GIVEN a document ingested without an explicit audience
- WHEN it is stored
- THEN its audience is `internal`

#### Scenario: Restore never widens
- GIVEN a `customer` document with more than one version
- WHEN an admin restores a prior version
- THEN the document's audience becomes `internal`
- AND re-publishing it to customers requires an explicit reclassification

#### Scenario: Explicit reclassification
- GIVEN an existing document
- WHEN an admin changes its audience
- THEN the change takes effect without creating a new version
- AND it is recorded in the audit log

#### Scenario: Assistant keeps full access
- GIVEN an `internal` document
- WHEN the Lumat assistant retrieves KB content
- THEN the document IS retrievable

### Requirement: KB-6 — Document Scope

Every KB document MUST have a scope: global (`kb_documents.project_id IS NULL`) or a single project (`kb_documents.project_id = <id>`). Scope is orthogonal to audience (KB-5): audience decides who may ground an answer, scope decides who the document belongs to. Conflating them into one enum MUST NOT be the mechanism for either restriction.

The panel's global "Base de conocimiento" section MUST list global documents only; a project-scoped document MUST NOT surface there. A project's documents MUST remain reachable through that project's own surface.

The admin retrieval probe MUST be scope-bounded to global documents, consistent with the section it serves. Its audience breadth (KB-5) is unchanged: it still reads the whole active corpus audience-wise.

Assistant retrieval MUST be scope-bounded: global documents only without a project context, or global plus that project's documents with one.

#### Scenario: Project document does not surface globally
- GIVEN a KB document scoped to a project
- WHEN an admin opens the global Base de conocimiento section
- THEN the document is not listed there
- AND it is still listed on that project's page

#### Scenario: Probe stays scope-bounded
- GIVEN a KB document scoped to a project
- WHEN an admin runs the retrieval probe in the global KB section
- THEN the document's chunks are not returned

## Boundary
KB retrieval supplies content for `conversation-manager` (CM-4); the manager view is exposed in `admin-panel` (AP-6).
