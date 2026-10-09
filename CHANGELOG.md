# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses CalVer in the `YYYY.MM.N` format.

## [Unreleased]

## [2026.10.1] - 2026-10-09

This catch-up release brings a broad redesign of the administration panel and a project-scoped workspace for Asistente Lumat. It also expands the knowledge base, customer intake, notifications, and automation recipes, alongside usability and reliability fixes across the panel and assistant.

### Added

- **Project-scoped Asistente Lumat.** Manage project files and attachments with extraction and knowledge-base ingestion, scoped knowledge and skills, assistant artifacts, project agents, and project-specific assistant configuration.
- **Assistant run controls.** Configure tool access by role and thread, toggle tools per thread, and cooperatively stop active runs.
- **Panel notifications.** Receive transactional alerts for emergencies and appointment events, with live unread-count updates.
- **Automation recipe catalog.** Browse curated recipes and install them through the agent tool, panel API, and recipe-card interface.
- **Post-visit follow-ups.** Send a follow-up after an Agenda visit is closed.
- **User profiles and account controls.** View user details, manage profiles, and change your own password.
- **More useful development data.** Seed a realistic unified development environment and render markdown summaries.

### Changed

- **Conversaciones rebuilt.** Reworked the conversation workspace and its responsive interactions.
- **Clientes redesigned.** Added a customer list and tabbed ficha, with lifecycle and archive controls, duplicate merging, and improved customer history and details.
- **Configuración reorganized.** Rebuilt the five tabs for Agente, Mensajes, Horarios y avisos, Costos, and Capacidades.
- **Agenda redesigned.** Added a calendar roll-up, visit details, and a new-visit dialog.
- **Dashboard refined.** Added a functional activity-period selector, clearer HOY cards, and seeded demo data with readable charts across date ranges.
- **Knowledge base unified.** Redesigned the landing and document-detail views, audience and availability controls, content and version management, and markdown preview.
- **Customer intake streamlined.** Start with an open greeting, group capture questions, and resume after mid-capture reclassification; require email and explicit consent, and treat media as case evidence rather than a handoff trigger.
- **Panel shell and visual system refreshed.** Adopted the approved design tokens and updated desktop, tablet, and mobile navigation and shared interface components.
- **Panel access broadened.** Make agent chat available to panel roles, with assistant capabilities and upcoming appointments scoped to the caller's role and technician.

### Fixed

- **Technician selection and lookup.** Guard Agenda against missing technician-directory data, use readable names in the technician picker, and surface lookup failures during rescheduling.
- **Authenticated message authorship.** Derive message authors from the authenticated role rather than client-supplied identity.
- **User account dialogs and details.** Improve the admin password-reset dialog and ensure profile names appear in the users list and ficha.
- **Panel navigation at smaller sizes.** Correct the tablet breadcrumb, center the mobile logo, and refine responsive navigation and header controls.
- **Dashboard HOY layout.** Correct the cards grid, shortcuts layout, and surface styling.
- **Localized follow-up email fallback.** Preserve the appropriate language when a follow-up email uses its fallback text.

## [2026.09.5] - 2026-09-23

This release carries the operational fix that lets the assistant answer at all in production,
plus the retrieval-calibration harness correction merged since `v2026.09.4`.

### Fixed

- **The production image now ships the assistant's declarative configuration.** The prod
  `Dockerfile` copied `app/` and `db/` but never `agent/`, so `app/agent_registry.py:223`
  resolved `/app/agent/registry.yaml` to nothing and `load_registry()` raised
  `registry file not found` on the first assistant turn: the panel answered with the raw error
  and the turn produced no reply. The failure was never at boot — `build_graph()` runs per
  message (`app/chat/graph.py:300`), so the container started, `/health` returned 200 and the
  webhook handshake passed while every turn failed. `prompts.load()` degrades silently to its
  literal `FALLBACKS` when a file is missing (`app/services/prompts.py:113-120`), so a fix that
  shipped only `registry.yaml` would have left production on the hardcoded fallback personas and
  prompts without a word; the whole tree is shipped now. The prod image has never contained
  `agent/`, so `v2026.09.1` through `v2026.09.4` fail identically on this path: **there is no
  known-good tag to roll back to.** A regression test asserts the image copies every repo-root
  path the runtime resolves.
- **The retrieval-calibration harness restores the module state it overrides.** `run()` replaced
  `kb.chunk_text` (via `--chunk-size` / `--chunk-overlap`) and `kb.EMBED_MODEL` / `kb._embedder`
  (via `--model`) for the duration of a measurement and never put them back, so a second
  programmatic `run()` without overrides reported the defaults while still using the previous
  call's values. An `override_kb(...)` context manager restores all three on every exit path,
  including an exception mid-run, and the report is built inside the scope so it keeps recording
  what was actually measured. The documented CLI use, one `run()` per process, was never affected.

## [2026.09.4] - 2026-09-23

This release carries the correction for the admin panel's blank screen, and nothing else.

### Fixed

- **A case without a service no longer blanks the admin panel.** An escalated case is created with `Case.service` unset, the KPI aggregate published that `NULL` raw, and the panel's motive chip then called `.length` on it inside render; with no error boundary in the SPA, one unclassified case blanked the whole panel. The aggregate now buckets it as `sin clasificar`, and the chip tolerates a null motive as a second line of defence. A latent defect uncovered by the first real production data, not a regression of `v2026.09.3`.

## [2026.09.3] - 2026-09-23

This release carries the operational fix that lets the bot answer at all in
production, plus a batch of chat, memory, assistant and panel corrections
merged since `v2026.09.2`.

### Added

- The assistant's declared capability inventory is exposed as a tool, so the operator can see what the agent can actually do.
- Autonomous memory correction tools, under the existing audit trail.
- Agent memory is scoped to the chat thread's project namespace, keeping unrelated projects out of a thread's recall.
- Panel knowledge answers are gated on retrieved evidence instead of being answered without a source.
- A customer turn closes on a farewell or outside business hours instead of running on.
- The panel keeps watching a run whose stream gave up, so a long turn no longer looks abandoned.
- The local embedder is prewarmed off the boot path, so no operator turn pays the model load.

### Changed

- The retrieval chunking axis is now measurable with the calibration harness, and it was measured: production stays at the shipped 500/50, because smaller chunks are strictly worse. No production behavior change.
- The opencode tools lockfile is tracked, which stops it from reappearing as untracked noise in every new worktree.

### Fixed

- **Production can now write the embedding model cache.** The prod compose override replaced the api volume list and silently lost the fastembed cache mount, so the first real inbound message failed with `Read-only file system` and was marked `failed`. The container now has a writable, durable cache volume, pinned by a regression test.
- The deterministic emergency gate escalates first-person gas-smell phrasings ("huelo gas"), which previously fell through to commercial classification.
- Panel assistant reads no longer end the turn when a read-only tool fails; they degrade instead.
- An unavailable knowledge base is reported honestly on both chat paths.
- Memory recall admits literal phrases per channel, and a memory's review schedule is recomputed when its type changes.
- Duplicate weekdays within a schedule entry are rejected.
- The panel shell is served network-first, so a deploy can no longer strand a browser on a stale service worker.
- The VPS backup, monitor and certificate-renewal tooling was repaired: it could not write the backups volume, could not send alerts, and had no crons installed.

## [2026.09.2] - 2026-09-22

This catch-up release contains the product changes merged since `v2026.09.1`,
including the new assistant, project, technician, and memory capability areas,
plus the operational fixes delivered during that period.

### Added

- Admin assistant operations with typed tools, approval-controlled actions, auditable automation authoring, recoverable live execution, capability visibility, and private attachment context.
- A technician role with a privacy-bounded agenda, visit status and safety information, actionable addresses, and field-oriented refresh and contact controls.
- Admin user management for listing users, creating accounts, changing activation, and resetting passwords.
- Project registration and lifecycle controls with approval-safe project-scoped assistant operations and a read-only Projects panel.
- Planning sessions with durable artifacts, authenticated session access, handoff support, and native structured-data operations that can execute and recover approved reads and writes.
- Agent memory tools and durable memory controls: bounded search, autonomous thread-safe writes, provenance, thread/global visibility, lifecycle staleness, relation judgment, and a human resolution queue.
- Owner-configurable customer-chat tone and standard messages through the Settings panel.

### Changed

- Replaced the basic conversation view with a case-aware queue and workspace supporting search, pagination, realtime updates, ownership actions, and customer/case context.
- Reworked the panel assistant into an asynchronous conversation surface with thread identity and titles, live progress, markdown replies, focus and recovery behavior, and visible capabilities.
- Made the knowledge-base workspace usable for first-document upload and safe editing, added an admin retrieval probe, and enforced customer versus internal document audiences at retrieval time.
- Expanded operational dashboard behavior with today-focused projections, role-specific views, seven-day summaries, and the technician agenda surface.

### Fixed

- Panel tool calls no longer stop at the misleading `Tool <name> completed.` placeholder; completed results are now narrated to the operator.
- Failed panel planning is no longer presented as an ordinary successful answer; failure reasons are retained and surfaced for diagnosis.
- KB administrators can now upload the first document from an empty workspace, and editing no longer overwrites stored content with an invented placeholder.
- Customer chat can no longer retrieve internal-only KB documents, and previously unreachable `valores` and `postventa` intents can reach the KB path.
- Cancelled technician visits remain visible and are explicitly marked instead of appearing as ordinary booked visits.
- Escalated cases now retain a deterministic non-empty narrative when summary generation is blocked, fails, or returns empty content.
- Triage no longer duplicates replies, and routine commercial questions containing bare `gas` no longer trigger emergency escalation.
- Panel assistant memory reads are bound to the trusted thread, and own reads no longer hide global memories when the thread axis is full.
- Planner snapshots are persisted per turn, and planner failures no longer lose their diagnostic state between turns.

### Removed

- The misleading `kb_scope` topic-scope axis was retired; the enforced customer/internal audience boundary is now the KB retrieval control.

## [2026.09.1] - 2026-09-08

This is a retroactive release tag: `v2026.09.1` was created on 2026-09-20 for
the production deploy that began on 2026-09-08 and was not tagged at the time.

### Added

- Production WhatsApp webhook ingestion with verification, signed requests, and durable message handling.
- Conversational agent workflows for intake, intent routing, knowledge-based responses, emergency detection, and human handoff.
- Customer records, conversation history, cases, and operator controls in the authenticated administration panel.
- Knowledge-base ingestion and retrieval for customer-facing answers and operator management.
- Appointment scheduling with technician availability, conflict prevention, cancellation, rebooking, and calendar export.
- Durable notification delivery with retries, emergency fallbacks, and versioned channel templates.
- Realtime conversation updates and internal agent chat for authorized panel users.
- Event outbox processing, deterministic automation rules, notification center, and browser push fallback flows.
- Operational dashboards with configurable summaries, trends, and metric drill-downs.
- Installable React panel shell with service-worker caching for the static application shell.
- Production operations and security controls covering deployment, hardening, backups, monitoring, and audit logging.
