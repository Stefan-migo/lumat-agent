# assistant-attachments Specification

## Purpose

Provide private, thread-scoped assistant uploads for images and supported documents.

## Requirements

### Requirement: AA-1 — Validated Private Uploads

The system MUST accept only images, PDF, CSV, and plain-text attachments within configured size and count limits. Stored references MUST be private, thread-scoped, authorized, and MUST NOT expose filesystem paths or WhatsApp URLs.

#### Scenario: Supported upload
- GIVEN an authorized administrator uploads a permitted file within limits
- WHEN the upload completes
- THEN a thread-scoped attachment reference is persisted and available to that thread

#### Scenario: Rejected upload
- GIVEN an unsupported type or oversized file
- WHEN upload validation runs
- THEN the request is rejected, no usable attachment reference is created, and the thread remains unchanged

### Requirement: AA-2 — Context Preparation

PDF, CSV, and text attachments MUST be processed through `kb.extract_text()` before being supplied as assistant context. Images MUST be supplied as multimodal OpenRouter content using a design-validated vision model and configured cost limits.

#### Scenario: Document context
- GIVEN a valid document attachment
- WHEN the assistant processes the message
- THEN extracted text is attached to the run context and its source attachment is identifiable

#### Scenario: Image model limit
- GIVEN an image exceeds configured vision size or cost limits
- WHEN context preparation runs
- THEN the image is rejected or marked unusable with a recoverable error and no model call is made

### Requirement: AA-3 — Lifecycle and Authorization

Attachment access MUST require thread authorization, and cleanup MUST remove orphaned or expired assistant files and metadata without affecting WhatsApp media.

#### Scenario: Cross-thread access denied
- GIVEN an attachment belongs to another private thread
- WHEN an administrator requests it
- THEN the server returns an authorization error and no content is disclosed

#### Scenario: Cleanup preserves active files
- GIVEN an active thread attachment and an orphaned attachment
- WHEN cleanup runs
- THEN only the orphaned or expired attachment is removed
