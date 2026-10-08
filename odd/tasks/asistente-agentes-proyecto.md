# asistente-agentes-proyecto

## Objective

Build the backend capability for the **Asistente Lumat** so the assistant can work *by project*:

- Documents/attachments: durable **per project** (shared across threads) + ephemeral **per thread** attachments.
- A hybrid document model: original blob (source of truth) + structured extraction (text + tables) +
  RAG index (discovery) + exact read tools (on demand) + downloadable output artifacts.
- Project-scoped knowledge base (`kb_documents.project_id`) and project-scoped skills (global + project).
- Project agents roster (Orquestador default + Verificador + Explorer) with runs/state/realtime.
- Chats without a project use the implicit `default` namespace (no visible "General" project).
- Saving a project's assistant configuration (`ProjectConfig`: instructions + tool policy + skills).

Design is closed (D1–D8). This document tracks ODD implementation by dependency-ordered slices.

## Problem

The assistant runtime already resolves `ProjectConfig` per turn (`app/chat/assistant/nodes.py:526`) and
the KB already filters by `project_id`, but the write paths and the supporting surfaces are missing:

- No route saves `ProjectConfig` (only list/detail/create exist today).
- Extraction only covers PDF/MD/CSV; project files (docx/xlsx/images, table-aware PDF) and the project
  file store do not exist.
- No read tools (`list_project_files` / `read_project_file`), no downloadable artifacts path.
- No project agents roster/runs, no skills UI, no per-thread tool toggles / stop endpoint.

## Why

The owner defined the product shape (documents by project, hybrid RAG+tools, project agents) and chose
ODD (not SDD) to implement it slice by slice, with per-work-unit commits and RDD review.

## Decisions (closed — do not re-litigate)

1. **Documents scope**: durable **per project** (shared) + thread attachments ephemeral.
2. **Hybrid 4 layers**: (1) original blob = file as-is, source of truth; (2) structured extraction
   (text + tables md/csv) at ingest; (3) RAG index = discovery; (4) exact read tools on demand +
   downloadable artifacts. Rule: RAG to find, tools to read exact, artifacts to produce.
3. **Embedding is not mandatory for everything**: embed text-extractable content by default (local
   fastembed, no API cost); do not embed binaries without text. Embedding is an index, not a blob replacement.
4. **Read tools**: create `list_project_files` / `read_project_file` (do not exist today).
5. **Tukulpan/memory**: NO auto-mirror of per-doc summaries. Light pointer (doc_id + descriptor) and a
   distilled note only when it adds value. The KB is the source; memory is not a mirror.
6. **Skills**: full system with UI (global + project, filterable); the agent may PROPOSE skills with a
   guardrail (user confirmation + audit + never escalate tool policy from content).
7. **Project agents (minimum)**: **Orquestador** (1 default per project; the project chat IS the
   orchestrator) + **Verificador** (SDB, read-only, fresh context) + **Explorer** (read-only). NO
   "general task agent" for now (would be a skill). Extensible to ERP/MCP as tool providers.
8. **Chats without project**: use the implicit `default` namespace (runtime already treats it as "no
   project"). Do NOT create a visible "General" project. Only the frontend UX changes.

## Scope

**In:** backend routes/services/models/migrations, KB ingestion for project files, document extractors,
project read tools, artifact download path, skills catalog + UI, project agents roster + runs + UI,
per-thread tool toggles + stop/cancel endpoint, and the workspace UI that exposes them.

**Out:** the settled design-system palette/tokens, unrelated panel sections, and other in-flight work
(see Concurrency). No revival of shipped capabilities.

## Constraints

- Chat in Rioplatense Spanish; artifacts, code, comments, commits in English; UI copy neutral Chilean
  Spanish. Conventional Commits, no AI attribution.
- Reuse existing services/models/patterns before adding new ones (`ProjectConfig` +
  `resolve_effective_config` already exist; KB is already project-scoped; skills lazy loader exists).
- Honest UI only: where a contract does not exist yet, render a real empty/disabled state — never
  fabricate agents, files, counts, or sources.
- Migrations idempotent via `db/migrate.sh`; dev DB already has 040/041 applied.

## Reuse inventory (verified from code)

- `app/services/project_config.py` — `ProjectConfig {instructions, tool_policy, skills}`,
  `resolve_effective_config()` (already executed in runtime at `app/chat/assistant/nodes.py:526`).
- `app/services/projects.py` — project registry ops; `app/panel/api/routes/projects.py` — list/detail/create.
- KB: `kb_documents(project_id, visibility)` + `kb_chunks` (pgvector, fastembed local 384d);
  `kb.retrieve(project_id=...)` filters global + project; tool `_retrieve_kb` already passes scope
  (`app/chat/assistant/tools/registry.py:332`). Extraction today: PDF/MD/CSV only
  (`DocumentFormat`, `app/models.py:115`).
- Skills: lazy loader `app/services/skills.py`; global catalog `assistant.skills` empty.
- Attachments: `assistant_attachments` is per THREAD (≤5MB, stored_path, sha256) — not per project.

## Backend gaps (to build)

1. Save `ProjectConfig` route + UI (Slice 1).
2. Chats without project / `default` namespace UX (Slice 2).
3. `project_files` table + upload/download + extractors (docx/xlsx/images, table-aware PDF via
   pdfplumber) + ingest to `kb_documents(project_id)` + tools + artifact download path (Slice 3).
4. Skills system: global catalog + UI + agent-proposed skills (propose → confirm → audit) (Slice 4).
5. `project_agents` roster + sub-agents (Verificador, Explorer) + runs/state + realtime + UI (Slice 5).
6. Per-thread tool toggles + stop/cancel active-run endpoint (Slice 6).

## TDD resolution

- `openspec/config.yaml`: `testing.strict_tdd: true`, runner `uv run pytest tests/` → **TDD ENABLED**
  for backend work (RED → GREEN → REFACTOR with observed evidence).
- Frontend: ordinary checks (component tests written/updated + `npx tsc -b --force --noEmit` +
  `npm run build`), not no checks. Runner `npx vitest run`.

## Delivery strategy

- Forecast: **> ~1,500 authored changed lines** across six slices (DB + backend + frontend) → exceeds
  the ~400 budget. `delivery_strategy`: `ask-on-risk`. Each slice is its own reviewable work unit with
  its own commit(s) and verification; PR/merge remain the owner's decision. `chain_strategy`:
  `stacked-to-main` (owner direction: "encadenar los chicos"; stacks to `main` in slice order).

## Work units (stable IDs)

### A1 — Save ProjectConfig
- [x] Route `PATCH/PUT /panel/api/projects/{slug}/config` (owner-scoped, validated by `ProjectConfig`).
- [x] Wire the workspace UI to edit/save project instructions (+ tool policy / skills as exposed).
- [x] Tests first (RED) for validation + owner scoping + persistence; then implement.

### A2 — Chats without project
- [x] `default` namespace as implicit "no project" for admin/operator new chats; no visible "General" project. Technicians and unspecified roles retain project selection.

### A3 — Project files (large)
- [x] `project_files` table + migration (idempotent) + upload/download. Commits `89ee041f`, `06a85ce3`; migration-test expectation fix `11ef749e`.
- [x] Extractors: docx, xlsx, images; table-aware PDF (pdfplumber). Commits `e1540d00`, `cc74ec97`. Images are stored but intentionally not text-extracted/embedded (D3).
- [x] Ingest extracted content to `kb_documents(project_id)`. Commit `e14f757e`.
- [x] Tools `list_project_files` / `read_project_file`. Commit `611383bc`; RDD assess `medium`, 164 lines, `review_due: false` (`under_budget`).
- [ ] Downloadable artifact path.
- [ ] UI "Archivos y conocimiento".

### A4 — Skills system
- [ ] Global catalog + UI (global/project, filterable) + agent-proposed skills with guardrail.

### A5 — Project agents (large)
- [ ] `project_agents` roster (Orquestador default) + Verificador + Explorer.
- [ ] Runs/state + realtime + UI "Agentes del proyecto".

### A6 — Per-thread tool toggles + stop/cancel
- [ ] Tool toggles per thread + active-run stop/cancel endpoint.

## Acceptance criteria

1. Each slice is independently green: backend `uv run pytest tests/`, frontend `npx tsc -b --force --noEmit`,
   `npx vitest run --no-file-parallelism`, `npm run build`.
2. No fabricated data: every unbacked region is an honest empty/disabled state.
3. Existing assistant behavior (stream, approvals, attachments, planning, recovery, realtime) preserved.
4. Migrations idempotent; no destructive DDL on existing data.
5. Tool-policy/authority is never escalated from ingested content (D6/D7 guardrail).

## Checks

- Backend: `uv run pytest tests/` (from the worktree root); migrations with `db/migrate.sh`.
- Frontend (from `web/`): `npx tsc -b --force --noEmit`; `npx vitest run --no-file-parallelism`; `npm run build`.
- Graph Check per repo `AGENTS.md` before editing; record nodes consulted.
- Conventional Commits, no AI attribution; ≤5 files per work-unit commit where cohesive.
- RDD: `review assess` per work-unit commit; run the returned transition verbatim when `review_due`.

## Concurrency

Another agent works "Configuración" in the primary worktree (`odd/analysis/configuracion/`, uncommitted).
Do NOT edit `PanelShell`, `primitives.css`, `panelRoutes.ts` in the same window; coordinate or defer.

## Progress log

- Worktree `../lumat-agent-odd-asistente-agentes-proyecto` on `odd/asistente-agentes-proyecto` from
  `main` = `23ff4cd1` (owner approved 2026-10-08).
- Recorded design handoff from `cortex-session/2026-10-08-backend-agentes-proyecto` (Engram #5923) and
  `.rapsodia-code/sessions/ready-for-odd/2026-10-08-backend-agentes-proyecto/report.md`.
- Slice 1 complete. Commits: backend `8485597e` (`feat(projects): persist project assistant config`);
  frontend `03e397e5` (`feat(projects): edit project instructions in workspace`). Files: backend service,
  serializer, project routes, and `tests/functional/test_api_projects.py`; frontend `api.ts`, `types.ts`,
  `ProjectsPage.tsx`, and `ProjectsPage.test.tsx`. Graph nodes consulted: `Project`, `project_config.py`,
  `routes/projects.py`, `api/serializers.py`, `types.ts`; path showed `project_config.py` and
  `routes/projects.py` both import `models.py`. RED: `eval "$(bash infra/test-db.sh env)" && uv run pytest
  tests/functional/test_api_projects.py -q` initially reported missing-route 404 failures; the owner test
  also exposed the DB JSON default `{}` (rather than `None`) in its unchanged-config assertion, which was
  corrected before GREEN. GREEN: `eval "$(bash infra/test-db.sh env)" && uv run pytest
  tests/functional/test_api_projects.py` — 12 passed; full `eval "$(bash infra/test-db.sh env)" && uv run
  pytest tests/` — 1761 passed, 2 warnings. Frontend: `npx tsc -b --force --noEmit` passed;
  `npx vitest run src/components/pages/ProjectsPage.test.tsx` — 12 passed;
  `npx vitest run --no-file-parallelism` — 97 files / 1049 tests passed; `npm run build` passed (large
  chunk warning).

- Slice 2 complete: `AgentChat.newChat()` creates a `default` thread for admin/operator when no project
  is selected; technician and unspecified roles retain the existing project-picker/no-project error flow.
  AgentChat renders no `thread.proyecto` value, and a UI assertion confirms the raw namespace is absent.
  Graph nodes consulted: `AgentChat()`, `AgentChat`, `AgentChat.tsx`, `AgentChat.test.tsx`, and
  `createChatThread()`; graph edge: `AgentChat() --calls--> createChatThread()`.
  Frontend from `web/`: `npx tsc -b --force --noEmit` passed; `npx vitest run
  src/components/pages/AgentChat.test.tsx` — 1 file / 48 tests passed; `npx vitest run
  --no-file-parallelism` — 97 files / 1051 tests passed; `npm run build` passed (existing large-chunk
  warning). Implementation commit: `986fd7f8` (`feat(assistant): start projectless chats for operators`).
- Slice 1 RDD assessment: `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref 23ff4cd1
  --committed-only` → `risk: medium` (`executable_change` in `app/panel/api/routes/projects.py`),
  `changed_paths: 9`, `changed_lines: 365`, `review_due: false` (`under_budget`) → no review opened yet;
  the reviewed boundary stays pending in the slice until a later commit reaches the ~400 budget.
  Parent spot check re-ran `uv run pytest tests/functional/test_api_projects.py` — 12 passed, workspace
  clean. Environment: worktree has `infra/.env` (gitignored, copied from the primary repo) and its own
  test DB container on `:6227`; tests require `eval "$(bash infra/test-db.sh env)"` first.
- Slices 1+2 RDD review — **approved and acknowledged** (authority burned). `review assess --base-ref
  23ff4cd1 --committed-only` on the accumulated slice returned `risk: medium`, 11 paths, 434 changed
  lines, `review_due: true` (`slice_budget_reached`). Lineage `review-cc0f651ce5f2de0c`, single lens
  `review-reliability`, 0 findings. Consent was granted by the owner via the native envelope;
  `review acknowledge-approved` returned `authority: burned`. Reviewed boundary for the next slice:
  `1cd09271`.

- A3 (Slice 3) started after this doc's slices 1–2 entry; the worktree was recreated from new `main`
  `e3575e49` and the session crashed ~2026-10-08 15:00 before documenting. Crash recovery
  2026-10-08: working tree clean, no work lost; recovered commits `89ee041f`
  (`feat(projects): persist project files` — `ProjectFile` model, `app/services/project_files.py`,
  `db/migrations/042_project_files.sql`, `tests/integration/test_project_files.py`) and `06a85ce3`
  (`feat(projects): expose project file upload and download API` — `app/panel/api/routes/project_files.py`,
  serializer, `tests/functional/test_api_project_files.py`).
- A3 partial verification and fix: the recovered slice left `tests/integration/test_migrations.py` RED
  (`test_schema_migrations_records_version`, `test_all_tables_exist` did not know `042_project_files`);
  fixed in `11ef749e` (`test(migrations): expect 042 project_files table and version`). Full backend after
  fix: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` — 1778 passed, 2 warnings.
  Graph nodes consulted: `test_migrations.py`, `test_schema_migrations_records_version()`,
  `test_all_tables_exist()`, `tests/conftest.py` (`migrated_db`), `app/config.py` (`get_settings`).
- A3 still open: extractors (docx/xlsx/images, table-aware PDF via pdfplumber), ingest to
  `kb_documents(project_id)`, tools `list_project_files`/`read_project_file`, downloadable artifact path,
  UI "Archivos y conocimiento".
- A3 RDD review — **approved and acknowledged** (authority burned). `review assess --base-ref
  e3575e49 --committed-only` returned `risk: high` (`process_boundary` in
  `tests/integration/test_migrations.py`), 11 paths, 350 lines, `review_due: true`. Lineage
  `review-253abff1f01e9da2`, 4 lenses (risk, resilience, readability, reliability), 0 blocking
  findings; owner granted consent via the native envelope; `review acknowledge-approved` returned
  `authority: burned`. Non-blocking advisory findings (follow-ups, do NOT re-review this candidate):
  (a) file bytes are written to disk before the DB row/audit flush+commit, so a failed commit can
  orphan disk files — `app/services/project_files.py:47-51` (R1-001/R3-002/R4-001); (b) the upload
  reads `max_bytes + 1` but never drains/rejects the remaining oversized request body —
  `app/panel/api/routes/project_files.py:32-33` (R3-001/R4-002).
  Reviewed boundary for the next slice: `1d511d5d`.
- A3.2 plan (extractors + KB ingest) — owner approved adding `pdfplumber`, `python-docx`,
  `openpyxl` (all missing today; `pypdf`/`fastembed` already present). Approach: extend
  `DocumentFormat` with `docx`/`xlsx` via migration `043` (`ALTER TYPE document_format ADD VALUE
  IF NOT EXISTS ...`; `db/migrate.sh` runs autocommit so this is safe); new
  `app/services/document_extract.py::extract_document_text(content, kind)` — pdf via pdfplumber
  (page text + `extract_tables()`), docx via python-docx (paragraphs + tables), xlsx via openpyxl
  (sheet rows as ` | `-joined blocks), md/txt decoded, csv reuses `kb._csv_rows_to_text`, image -> "".
  `kb.ingest_document` gains an optional `content_text` override (keeps pypdf path for attachments/KB).
  The upload route calls a new `ingest_project_file(...)` that ingests to
  `kb_documents(project_id=<project>, visibility=internal, source_meta={"project_file_id": id})`; an
  extraction failure marks `ProjectFile.status="failed"` without losing the stored blob. Must update
  `tests/integration/test_migrations.py` (`043` version in `test_schema_migrations_records_version`;
  `test_enums_materialized` document_format labels gain docx/xlsx). TDD ON (RED -> GREEN).
- A3.2 done (owner-approved deps `pdfplumber`, `python-docx`, `openpyxl`). Commits: `e1540d00`
  (`feat(kb): add docx and xlsx document formats` — `DocumentFormat.DOCX/XLSX`, migration
  `043_document_format_docx_xlsx.sql`, migration-test updates); `cc74ec97`
  (`feat(projects): extract project file text...` — `app/services/document_extract.py`,
  `tests/integration/test_document_extract.py`, deps); `e14f757e`
  (`feat(projects): ingest project file text into the project knowledge base` —
  `kb.ingest_document(content_text=...)`, `project_files.ingest_project_file` with a
  `begin_nested()` savepoint + `status="failed"` on extraction error, route wiring, tests).
  RED observed: `ModuleNotFoundError: No module named 'docx'` + `cannot import name 'ingest_project_file'`.
  GREEN: targeted 76 passed; full `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` —
  1789 passed. Graph nodes consulted: `ingest_document`, `extract_text`, `_store_chunks`, `embed_texts`,
  `retrieve`, `DocumentFormat`, `KbDocument`, `KbChunk`, `KbVisibility`, `ProjectFile`,
  `allowed_project_file`, `store_project_file`, `upload_project_file`; paths
  `ingest_document -> KbDocument` and `upload_project_file -> store_project_file`.
- A3 still open: downloadable artifact path, UI "Archivos y conocimiento".
- A3.2 RDD review — **approved and acknowledged** (authority burned). `review assess --base-ref
  1d511d5d --committed-only` returned `risk: high` (`process_boundary` in
  `tests/integration/test_migrations.py`), 13 paths, 723 lines, `review_due: true`. Lineage
  `review-0d7df7cb8bc69017`, 4 lenses, 0 blocking findings; owner granted consent; `review
  acknowledge-approved` returned `authority: burned`. Non-blocking advisory (follow-up, do NOT
  re-review this candidate): the `except Exception` in `ingest_project_file` swallows the cause and
  turns transient KB/embedding failures into a successful upload with `status="failed"` and no log —
  `app/services/project_files.py:88,97-99` (R3-001/R4-001). Reviewed boundary for the next slice:
  `f1ee53f9`.
- Branch re-synced with current `main`: `git merge origin/main` fast-forwarded the worktree to
  `f857e9f4` (PR #518, `odd/configuracion-redesign`). No conflicts; working tree clean. Because main
  advanced past the A3.2 boundary, the RDD base for A3.3 is the integration point `f857e9f4`, not
  `f1ee53f9` (which now predates unrelated main commits).
- A3.3 done (project file read tools). Commit `611383bc` (`feat(assistant): add project file read tools`);
  7 cohesive files: `app/services/project_files.py`, `app/chat/assistant/tools/registry.py`,
  `agent/registry.yaml`, `tests/unit/test_assistant_tools.py`, `tests/unit/test_tool_tiers.py`,
  `tests/unit/test_effective_config.py`, `tests/unit/test_assistant_delegation.py`. Decisions (accepted):
  (a) registry keys honor D4 exactly — `list_project_files` / `read_project_file`, not dot-namespaced — so
  the `project.` prefix owner-scoping rule does not apply; `execute_tool`'s `owner_scoped` guard and its
  dispatch were extended explicitly instead. (b) Roles **ADMIN/OPERADOR only**, mirroring `kb.retrieve`
  (the existing content-read set); TECNICO denied. (c) `project_files.owned_project()` re-verifies
  `Project.owner_id == owner_id` and never matches the null-owner namespace. (d) `read_file_text()`
  re-extracts the stored blob (D2 layer 1 = source of truth), so it works even when KB ingest failed or
  was skipped; output bounded at `MAX_FILE_TEXT_CHARS = 20_000` with a `truncated` flag; images return an
  honest empty text state and never fabricate. `agent/registry.yaml` whitelist and the tier/effective-config
  expectation snapshots updated; the frozen planner-catalog SHA-256 in `test_assistant_delegation.py` was
  rotated for the new catalog bytes. RED: `ImportError: cannot import name 'ProjectListFilesArgs'`. GREEN:
  targeted 126 passed; full `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` — 1815 passed,
  2 warnings (parent re-run exit 0, no frontend files touched). Graph nodes consulted: `execute_tool()`,
  `get_tool()`, `TOOL_REGISTRY`, `ROLE_TOOL_ALLOWLIST`, `Project`, `ProjectFile`, `services/project_files.py`,
  `registry.py`, `ProjectConfig`/`resolve_effective_config`; paths `registry.py --imports--> project_files.py`
  and `registry.py --imports--> models.py`.
- A3.3 RDD assessment: `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref f857e9f4
  --committed-only --json` → `risk: medium` (`configuration_change` in `agent/registry.yaml`), 7 paths,
  164 lines, `review_due: false` (`under_budget`) → no review opened; the reviewed boundary stays pending
  at `f857e9f4` and accumulates with the next A3 slice commit.
