# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses CalVer in the `YYYY.MM.N` format.

## [Unreleased]

## [2026.10.12] - 2026-10-29

A release for one operator-visible failure of the panel assistant and the two defect
classes behind it, plus the instrument that measures tool health.

### Fixed

- **The assistant no longer reports that a tool never arrived when it did.** The turn
  bootstrap ran `memory.read(scope=own)` and appended the result to the tool-results list,
  so the planner saw a fake "Prior tool evidence" block on its first plan and the responder
  saw that memory blob inside `<tool_evidence>` as the output of whatever tool the operator
  had asked for. Production said "project.find never arrived" while `audit_log` shows it
  completed three times. Own memory is now labelled context that states the harness read it
  before the turn, rendered tool results carry tool, status and arguments, a budget-truncated
  chain still lists every executed step, and a recorded execution stall reaches the responder.
- **A cold import cycle no longer kills the first `conversations.*` tool call of a process.**
  `app.services.conversations` imported a panel serializer at module level, which loaded every
  route module, which imported the conversation service back.
- **The panel API router assembles on first access.** `app.services.dashboard` had the same
  cycle, intermittently, because the same eager package init dragged all 20 route modules
  behind any serializer import. Two occurrences made it a class, so it is fixed at the
  amplifier instead of per service.
- **`assistant.capabilities` reports the turn's effective catalog** (role allowlist and
  enabled opt-in tools) instead of the global 33, so it no longer claims tools that
  `guardrails` will refuse.

### Added

- `scripts/probe_assistant_tools.py` reports, tool by tool, what actually works in a given
  environment: status, latency and a shape-only summary, never row values. Writes are never
  executed and report `requires-approval`. A test ties its fixtures to the live registry so
  coverage cannot rot silently.

## [2026.10.9] - 2026-10-28

A patch release for one defect that the previous deploy's own verification found:
a knowledge-base search filtered by topic could return nothing while rows matched
the filter.

### Fixed

- **A filtered KB search cannot come back empty while its filter matches rows.**
  `retrieve(..., source_ids=[...])` returned 0 chunks in production with 2 rows
  matching: pgvector's HNSW scan hands back `hnsw.ef_search` neighbours and the
  `WHERE` applies afterwards, so one 258-chunk document dominating the
  neighbourhood left nothing for the topic filter to keep. The filtered path now
  filters in SQL and ranks in Python — the matching set is one document — so the
  answer no longer depends on which plan the planner picks. The unfiltered path
  keeps the index, where the ordering is the selection itself.

### Changed

- **The release record carries what verification found.** `docs/ops.md` gains the
  `v2026.10.8` row and change-log entry, including the operator action that left no
  audit trail (the four customer KB documents were renamed with `psql`) and the
  retrieval defect this release fixes.

## [2026.10.8] - 2026-10-28

This release makes the bot's words and the bot's calendar come from the same
place. The knowledge base now says Saturday can be booked because Saturday can
be booked, the offer engine only proposes days and hours the business actually
sells, and a document that restates a configured value fails a check instead of
drifting until a customer notices. The assistant panel also settles down: tabs
survive navigation, a background run can be reattached, and the retired
planning feature is gone from both the backend and the UI.

### Added

- **Reschedule onto the day the customer asks for.** Slot offers filter by the
  day and franja resolved from the request, move forward when that window is
  empty, and format choices as `dd/mm/yyyy a las HH:MM` instead of raw ISO.
- **The business window narrows every offer.** A visit is proposed only when it
  starts and ends inside `hours.schedule`; a 60-minute visit is never offered at
  17:30 by a business that closes at 18:00. An empty schedule means no
  restriction, which is what the setting ships with.
- **KB drift control.** `scripts/kb_doc_drift.py` flags values in `docs/kb/*.md`
  that the configuration owns — covered communes, clock literals, prices,
  durations, weekday ranges — and fails on a finding that is not in the
  checked-in baseline, so today's accepted restatements are visible debt rather
  than silent drift. The seed report prints the same summary.
- **Panel assistant runs.** Workspace tabs survive section changes and reloads,
  a background run raises an alert and a toast when it ends, and opening the
  thread again reattaches to a run in flight.
- **Project files without auto-indexing.** Uploads are stored locally instead of
  being ingested into the project knowledge base, and the upload path no longer
  touches a project's existing documents.

### Changed

- **Out-of-hours closure is an explicit opt-in.** `hours.closure_enabled`,
  `false` by default. The window narrows the offers; the switch decides whether
  the chat also goes quiet outside it. The panel reads the state and cannot flip
  it — that stays an operator action, documented in `docs/ops.md` §2.6.
- **The release check for the knowledge base can run in production.** The image
  ships `scripts/` and `docs/kb/`, `.dockerignore` keeps `docs/kb` in the build
  context, and `docs/ops.md` §2.5 states what the customer KB is, how it is
  seeded, and why a seeded document must not be hand-edited in the panel.
- **Planning is retired.** The planner's sessions, UI and documentation are gone;
  planner JSON is read tolerantly so one malformed plan no longer poisons a run.

### Fixed

- **A new version of a KB document kept its topic routing.**
  `kb.update_document` wrote the new version without `source_meta`, and topic
  routing filters on exactly that key: a re-seeded or panel-edited document
  stopped being eligible for its own topic and the turn fell back to the
  similarity threshold, answering "no tengo ese dato" with the document sitting
  right there. The new version now inherits the metadata, and the seed repairs a
  document that lost it in place — no re-embedding, no invented version, with an
  audit row.
- **A re-wrapped document is the same document.** The seed's digest compared line
  by line, so a document the panel textarea re-wrapped read as drifted; combined
  with a title that no longer matched the repository heading, the next seed would
  have created a duplicate document instead of re-versioning it.
- **An answer to a slot offer no longer falls into the complaint gate.** Naming a
  day or a window in reply to an offer is read as an answer, not as a complaint
  about the offer.
- **The knowledge base says Saturday is bookable online**, and keeps Sunday and
  holidays with an advisor, matching what the agenda can actually staff.

## [2026.10.7] - 2026-10-27

This release ships a conversation evaluator and the defects it measured: the
chatbot now greets, understands courtesy, rephrases and offers paths before it
derives, and never stores a capture answer that does not answer the question.
The human conversation thread gains WhatsApp media in both directions, and the
Configuración section is regrouped into four super-sections and redesigned.

### Added

- **Conversation evaluator.** A versioned corpus of customer conversations, a
  runner against `run_conversation` with no channel, and a two-layer evaluation
  (deterministic gates plus a rubric judge run with repetitions) that produces a
  report comparable between versions, with transcripts, a diff against the
  previous run, and a stamp naming the tree a run actually measured.
- **WhatsApp media in the conversation thread.** Images, audio, video and
  documents arrive in the thread and are served by an authenticated panel
  endpoint instead of Meta's temporary lookaside URL; the operator attaches and
  sends media, records audio, and keeps the same `pending`/`sent`/`failed`
  states and retry as text. A media that cannot be downloaded from Meta stops
  after a bounded number of attempts and says so instead of showing a file that
  will never arrive. Migration `058` adds the metadata to `messages`.
- **Settings super-sections.** The eleven flat tabs become four groups —
  Chatbot, Operación, Integraciones, Costos — with vertical sub-tabs. Tab ids and
  labels do not change, so the existing deep links keep working.
- **Chatbot settings redesign.** Agente with a sticky save bar and version
  history, Persona with markdown preview, Conducta with a data table, the capture
  questions and a derivation editor with preview, Mensajes with search and a
  WhatsApp preview.
- **Operación settings.** A compact team-hours editor, one technician schedule
  selected at a time, and hours, coverage and rates integrated on one surface.
- **Capture phrasing switch in the panel.** `chat.conduct.redaccion` gets its
  control; a payload that omits the key preserves the stored value.
- **Visits assigned on a 30-minute grid by daily load**, a paginated slot offer
  that names the technician in the confirmation, and a greeting that uses the
  customer's name and asks for it when missing.
- **A panel surface that explains the chatbot**, and an urgent-cases card that
  counts only open emergencies without an acknowledgement, shows at most three
  rows, and opens the conversation or the customer's cases tab.

### Changed

- **The chatbot treats a conversation as a conversation.** A greeting and a
  courtesy are understood turns instead of comprehension failures, platform
  messages are ignored, one detector decides when the customer is asking for a
  human, and consecutive unknowns are counted so the third one derives.
- **Rephrase before deriving.** After a failure the bot rephrases, then offers
  the two paths, and derives only after three failures; a knowledge miss offers
  the two paths instead of deriving immediately.
- **Retrieval runs once per turn** and falls back to the classified service on a
  miss, so the measurement and the answer describe the same retrieval.
- **Capture asks a validated answer.** Consent is a decision, not another field:
  nothing is persisted or reserved without an explicit yes, a refusal derives,
  and an unclear answer is re-asked up to the limit. The capture never stores
  the current message as the answer to a question it did not answer. The model
  may word the question behind a validator.
- **One owner for `reply.texts`.** The 25 keys are edited only in Conducta, with
  one save covering all of them; the duplicated block leaves Mensajes, and the
  dead conduct key is removed.
- **The five customer-facing derivations have their own text**, and the coverage
  rule outranks an exhausted pending field.

### Fixed

- **Published prices are answered from the tariff** instead of the knowledge base.
- **A schedule question is answered mid-capture** and the capture resumes, even
  without a question mark.
- **An explicit email refusal is honoured** while another field is pending.
- **The emergency no longer hides its escalation**: the case records the
  `escalation` event the analytics and the panel read, and the goodbye no longer
  gets a sales pitch on top.
- **A soft knowledge miss is recorded as activity** without inventing a
  conversation that was never persisted.
- **A knowledge answer is retrieved from the routed topic document**, including
  when the raw message missed.

### Development

- **The project runs on Pi through Gentle Shell**, with the agent contract in
  `AGENTS.md` and its skills and extensions in `.agents/` and `.pi/`.
- **Tiered backend verification.** `scripts/test.sh gate|unit|quick|db|shape|full`
  replaces "always the full suite", and `shape` decides mechanically when the
  full suite becomes mandatory.

## [2026.10.6] - 2026-10-22

This release turns the customer chatbot's behavior into configuration: the price
list, the fixed copy, the conduct rules, the capture questions, and the persona
with its emergency protocol now live in settings instead of code. It also pins the
five invariants that must never be switchable and makes retrieval fall back to the
classified service when the raw message misses.

### Added

- **Price list in settings.** `tarifa.precios` resolves by date in
  `America/Santiago` and injects only the prices in force as a `<tarifario>` block,
  so the customer knowledge base no longer carries a price document.
- **Configurable copy.** The fixed messages, including `greeting_short`, the capture
  questions, and the booking, cancellation, and derivation texts move to settings on
  top of the preset-message catalog.
- **Conduct object.** `chat.conduct` holds the capture order, the wording source
  (`llm` or `template`), the question budget per message, and the derivation rules,
  with closed options validated on save.
- **Editable persona and emergency protocol.** Admins edit both with version, diff,
  and restore; mustache placeholders and unknown body fields are rejected.
- **Panel surface for conduct and capture.** The panel exposes conduct, capture
  questions, flow replies, and service durations, and lists only the derivation
  rules that have a reader.

### Changed

- **One capture question per message.** Capture asks one field at a time in the
  configured order, answers a mid-capture question before resuming the field, and
  derives after a single reformulation.
- **Customer retrieval order.** The chat embeds the raw message first and falls back
  to the classified `service` only on a miss, so conversational filler no longer
  causes a handoff on a question the knowledge base can answer.

### Fixed

- **Spend limit and emergency keywords could be switched off.** A zero limit
  returned a permanent `0.0` percentage and an empty keyword list compiled a pattern
  that never matched. Both are refused on write and fail closed on read.
- **Derivation rules without a reader.** The panel no longer offers the four rules
  the bot never consults, and legacy rows are sanitized.
- **Message-catalog slot contract.** The documentation now matches the code: a
  template skips empty slots instead of failing.

## [2026.10.5] - 2026-10-17

This release adds configurable email delivery, the technician field workflow, and
Meta template delivery for automation recipes. It also turns the assistant into a
project-scoped configuration layer with multi-step write chains, and finishes the
panel's role-scoped shell and project workspace.

### Added

- **Configurable email (SMTP).** Settings gains a Correo tab for the server, port,
  sender, user, TLS mode, and a write-only password, with the password kept in the
  encrypted panel secret store. Notifications deliver through one SMTP transport
  instead of the previous hardcoded localhost relay, so WhatsApp is no longer the
  only configured channel.
- **Technician field workflow.** Technicians get field quick actions with WhatsApp
  send and a resend cooldown, a visit close action, and a privacy-scoped detail
  view. The office sees a field-state semaphore on the agenda and the visit
  detail, and the technician contract no longer carries the customer phone.
- **Project folders and knowledge-base scope.** Create, rename, and move project
  files through a folder tree, and keep panel knowledge-base documents and
  retrieval scoped to global or single-project documents.
- **Project-scoped assistant configuration.** Personality, response format, memory
  behavior, knowledge-base relationship, skills, agents, and planning sessions are
  configurable per project on top of a global baseline. The seven opt-in tools ship
  enabled by default, the role and tier gates still apply to destructive ones, and
  the capabilities panel reflects the resolved policy.
- **Assistant tools and media.** Attach docx, xlsx, and markdown files to threads;
  inspect images on demand with `view_image` and multimodal tool results; page
  through project files with `read_project_file`; pin project resources and read
  planning reports on demand; and add the TecnicoLumat agent for the technician
  role.
- **Write chains.** An approved tool write re-enters the assistant graph instead of
  ending the turn, chains further writes behind a fresh approval per step, settles a
  rejected step as terminal with an audit record, and emits each executed step in
  the chain timeline before the next approval.
- **Chatbot operations.** Admins get a metrics view for containment, handoffs,
  knowledge-base hits, resolution turns, and conversation costs; inspection tools
  read recent conversations; the assistant can propose settings writes behind
  approval; and guided planning sessions offer the SDB handoff on close.
- **Automation templates.** Recipe notifications deliver through their Meta
  template, appointment reminders and follow-ups run from the recipe engine, booking
  confirmations are scoped to panel origin, and installed recipe installations can
  be uninstalled.

### Changed

- **Panel shell.** One role-scoped shell and navigation serves every role, with
  shared project chrome, a Contexto tab, redesigned Agentes and Skills tabs, a wired
  Hilos tab, and a file manager that moves files between folders.
- **Panel layout and feedback.** Global toasts, corrected page headers, a tab bar
  that holds at smaller sizes, stacked skill rows, and an embedded project tab that
  scrolls instead of clipping.
- **Assistant loop budget.** The tool loop now fits a three-step write chain.

### Fixed

- **Knowledge-base panel scope.** The document list and the admin retrieval probe now
  read global documents as well as the selected project's.
- **Assistant turn hygiene.** Handoff verification persists on the normal turn,
  message values are bounded, and transcript events are capped to the latest window.
- **Automation uninstall dialog.** Removed the duplicate error banner behind it.

## [2026.10.4] - 2026-10-14

This release improves WhatsApp conversation quality, expands the panel assistant,
and adds safer controls for model credentials, knowledge-base documents, users,
and customer cases.

### Added

- **Tukulpan memory handoff.** Mark persistent memories as handoff points, read
  the assistant's own memories at the start of a turn, and keep the
  `memoria-tukulpan` guidance available to the responder.
- **Model API key settings.** Admins can configure, validate, replace, and clear
  the encrypted DeepSeek key from the panel; the chatbot and panel assistant use
  it without a restart, while the UI exposes only masked status.
- **Curated chatbot messages.** Add approved preset responses in Settings for
  the bot to select and fill with real customer and visit details.
- **Chatbot performance metrics.** The panel assistant can read bounded-window
  metrics for containment, handoffs, knowledge-base hits, resolution turns, and
  conversation costs.
- **Knowledge-base and account controls.** Admins can permanently delete
  visible knowledge-base documents and guardedly delete users; closed customer
  cases can be archived and restored from the ficha.

### Changed

- **WhatsApp conversation flow.** Replies now use the message being processed
  and recent conversation and booking context, format appointment slots for
  people, and recognize conversational farewells.
- **First-turn greeting.** The bot combines its introduction with the answer in
  one message and skips the redundant opening question when the customer has
  already explained their need.
- **Panel assistant behavior.** The assistant is prompted to use tools for
  requests that need data or action, treating the knowledge base as one source
  rather than a prerequisite.

### Fixed

- **Panel status and customer views.** Realtime connection banners reflect the
  current socket state, prior cases are paginated, and conversation summaries
  display labeled details without dropping unrecognized content.
- **Model key cache consistency.** Key changes invalidate the resolver cache
  only after the database transaction commits, and both assistant consumers use
  the configured key.

## [2026.10.3] - 2026-10-13

This release brings the phone layout of Asistente Lumat: a dedicated mobile
control header, bottom sheets for navigation, projects, and thread detail, and a
composer sized for phones — while preserving the tablet and desktop behavior it
builds on.

### Added

- **Asistente Lumat on phones.** A dedicated mobile control header, a bottom
  navigation sheet (new conversation, history, projects), a project picker
  sheet, and a thread-detail sheet, all reachable from the assistant view below
  the phone breakpoint.
- **Mobile composer and empty state.** A composer and empty state sized for
  phones, with the reference empty-state copy scoped below the breakpoint.

### Changed

- **Single-column assistant workspace below the breakpoint.** The phone and
  tablet workspace collapses to a single column, thread tabs are hidden on
  phones, and the thread's project is shown in the mobile header.

### Fixed

- **Assistant navigation.** Restore the app drawer in the assistant view and
  drop obsolete assistant actions from the panel shell.
- **Mobile project selection.** Load projects from the mobile selector and
  streamline the project picker.

### Docs

- Record the mobile redesign work units (M1–M6), the D2/D4 decisions, and the
  visual-pass and native-review outcomes.

## [2026.10.2] - 2026-10-13

This release turns the automation catalog into real time- and calendar-driven
triggers on the worker tick, redesigns the Asistente Lumat workspace, reworks
Agenda booking around per-technician schedules, and adds panel web push.

### Added

- **Time- and calendar-driven automation recipes.** The worker tick now
  evaluates time-offset recipes (appointment review requests, post-visit
  maintenance) and calendar summary recipes (daily and weekly summaries),
  alongside the event-driven recipes.
- **Per-technician weekly schedules.** Define and edit each technician's weekly
  availability from the Agenda, in a register tab with an inline editor, and use
  it to drive booking.
- **Panel web push.** Deliver real Web Push notifications for panel alerts, with
  a PWA install path and hardened subscription reliability.
- **Per-service chatbot visit duration.** Configure how long the chatbot treats
  a visit as lasting, per service.

### Changed

- **Automatizaciones redesigned.** Reworked the recipe catalog page with real
  recipe descriptions.
- **Asistente Lumat redesigned.** New workspace and composer, a left sidebar
  with tabs, history, and planning sessions plus a compact rail, and a
  redesigned thread detail panel.
- **Conversaciones queue.** Closed conversations are excluded from the live
  queue and paginated at 10.

### Fixed

- **Automation configuration errors in the dialog.** Surface configuration
  errors inside the open recipe dialog instead of only outside it.
- **Cooperative-stop follow-ups.** Close the terminal race and revoke stale
  approvals.
- **Development seeder re-runs.** Purge child rows when the development seeder
  re-runs.
- **Worker observability.** Log one summary line per worker run, so the
  standalone cron log gains evidence on each tick.

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
