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
  its own commit(s) and verification; PR/merge remain the owner's decision. Chain strategy to be
  confirmed by the owner before the first over-budget commit.

## Work units (stable IDs)

### A1 — Save ProjectConfig
- [x] Route `PATCH/PUT /panel/api/projects/{slug}/config` (owner-scoped, validated by `ProjectConfig`).
- [x] Wire the workspace UI to edit/save project instructions (+ tool policy / skills as exposed).
- [x] Tests first (RED) for validation + owner scoping + persistence; then implement.

### A2 — Chats without project
- [ ] `default` namespace as implicit "no project" for new chats; no visible "General" project.

### A3 — Project files (large)
- [ ] `project_files` table + migration (idempotent) + upload/download.
- [ ] Extractors: docx, xlsx, images; table-aware PDF (pdfplumber).
- [ ] Ingest extracted content to `kb_documents(project_id)`.
- [ ] Tools `list_project_files` / `read_project_file`.
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
