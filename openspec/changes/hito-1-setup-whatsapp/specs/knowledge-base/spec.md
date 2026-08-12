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

## Boundary
KB retrieval supplies content for `conversation-manager` (CM-4); the manager view is exposed in `admin-panel` (AP-6).
