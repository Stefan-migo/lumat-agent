# Design: H1 — Setup + WhatsApp operativo (LumatAgent)

> Change: `hito-1-setup-whatsapp` · Project: LumatAgent (Lumat, gasfitería, Chile) · Phase: sdd-design · Date: 2026-08-11
> Contract signed, Pago 1 received, kickoff 17-ago-2026. Greenfield — no source exists.
> Satisfies specs: whatsapp-webhook, conversation-manager, customer-records, knowledge-base, emergency-detection, human-handoff, admin-panel, settings-scope-limits, security-hardening.
> Artifact language: English (technical). Graphify knowledge graph does not exist (noted per orchestration).

## Technical Approach

Single-repo monorepo (FastAPI + LangGraph + PostgreSQL/pgvector) deployed with Docker Compose on a Hostinger KVM 2 (São Paulo, Ubuntu LTS). One API container serves the WhatsApp webhook, the LangGraph conversation engine, and the admin panel (Jinja2); Postgres is the single source of truth. Inbound WhatsApp → signature verify → persist raw → 200-first → async in-process graph run (no broker). Deterministic emergency/scope gates run before any LLM call; LLM answers only from pgvector-retrieved KB content. Panel = server-rendered, session auth, roles admin/operador. Hardening checklist + prompt-injection suite are acceptance deliverables.

## Architecture Overview

```
                         ┌──────────────────────────────────────────────┐
 Meta Cloud API ──HTTPS──▶│ nginx (TLS 443)                             │
                         │  └─ /webhook/whatsapp → api                  │
                         │  └─ /panel/*          → api (Jinja2)         │
                         ├──────────────────────────────────────────────┤
                         │ api (uvicorn, 1 worker, read-only fs)        │
                         │  ├─ webhook router (verify, persist, 200)    │
                         │  ├─ background task: LangGraph run           │
                         │  ├─ services (emergency, KB, customers,      │
                         │  │             send, costs, audit)           │
                         │  └─ panel (sessions, roles, views)           │
                         ├──────────────────────────────────────────────┤
                         │ postgres + pgvector (volume, backups volume) │
                         └──────────────────────────────────────────────┘
```

- **No worker container in H1**: processing runs in-process after the 200 (FastAPI BackgroundTasks) + startup recovery sweep (`status='received' FOR UPDATE SKIP LOCKED`). Tens of conversations/day; ceiling noted (`ponytail:` upgrade = separate worker + DB queue when H4 event bus arrives).
- **No message broker, no staging VPS, no observability stack** — cron scripts for monitoring.
- Repo layout:

| Path | Contents |
|---|---|
| `app/` | FastAPI app: `main.py`, `config.py`, `webhook/`, `chat/` (LangGraph), `services/`, `db.py`, `models.py` |
| `app/panel/` | `routes/`, `templates/`, `static/` |
| `db/migrations/` | Numbered SQL migrations + `migrate.sh` (schema_migrations table; alembic deferred — H2) |
| `infra/` | `docker-compose*.yml`, `nginx/`, `certbot/`, `backup.sh`, `restore-test.sh`, `monitor/*.sh`, `.env.example` |
| `tests/` | `integration/`, `functional/`, `injection/` |
| `docs/` | `hardening.md`, `ops.md` |

## Architecture Decisions

| # | Decision | Choice | Alternatives rejected | Rationale |
|---|---|---|---|---|
| D1 | Worker | None — in-process async + recovery sweep | Celery/RQ/ARQ broker | YAGNI at tens conv/day; dedup+wamid gives at-least-once without queue |
| D2 | LangGraph checkpointer | None — rebuild state from Postgres per message | LangGraph Postgres/SQLite saver | Messages table is already the source of truth; saver adds a store and a migration (H2 multi-agent will re-evaluate) |
| D3 | LLM provider | OpenAI only: chat `gpt-4o-mini`, embeddings `text-embedding-3-small` | Anthropic/Meta/Cohere | One vendor = one key, one cost ledger, one client lib; Spanish quality sufficient at min cost |
| D4 | Emergency secondary validation | None — deterministic hit → emergency; weak hit → escalate to human | LLM validation after keyword match | LLM on safety path adds latency+cost+false negatives; EM-5 conservative default is simpler and safer |
| D5 | Config storage | Single `settings` KV table (jsonb) | Per-domain config tables (`emergency_rules`, `spend_limits`, ...) | All config is KV; 8 tables → 1. Admin edits = UPSERT + audit row |
| D6 | Cost tracking | Cost columns on `messages` (`cost_llm`, `cost_meta`) + SQL SUM | Separate `spend_ledger` table | Daily = SUM(today), per-conv = SUM(conv); no join, no write path duplication |
| D7 | Panel stack | FastAPI + Jinja2 + vanilla JS, signed-cookie sessions, `bcrypt` | OAuth, React, htmx, chart libs | 8 views, server-enforced roles; no client framework needed. CSV export via stdlib `csv` |
| D8 | Versioning/restore | `kb_documents.version + active_version`; chunks tagged by version; restore = pointer flip | Re-embed on restore | Re-embedding a restored version is redundant work — chunks persist per version |
| D9 | Case/notification channel | Notification = WhatsApp utility template `emergency_alert` + email fallback; ack via reply keyword or panel button | Panel-only, SMS | Owner needs push even outside 24h window; template is the only allowed business-initiated channel |

## Data Model

| Table | Key fields | Notes |
|---|---|---|
| `customers` | id, phone_e164 UNIQUE, name, email, comuna, address, state enum(nuevo…postventa), consent_status, consent_at, created_at | CR-2 dedup: normalize to E.164 at ingest; unique index |
| `users` | id, username UNIQUE, password_hash(bcrypt), role enum(admin/operador), active, failed_logins, locked_until | AP-1/AP-2 |
| `conversations` | id, customer_id FK, wa_phone, state enum(bot/human/closed), summary, last_message_at, created_at, closed_at | HH-1 |
| `messages` | id, wamid UNIQUE (partial, inbound), conversation_id FK, direction, msg_type, text, media_url, status enum(received/processing/processed/failed), payload jsonb, cost_llm, cost_meta, created_at | WH-5 dedup via `ON CONFLICT (wamid) DO NOTHING` |
| `cases` | id, conversation_id FK, customer_id FK, service, priority, status, responsible_id FK→users, summary, escalated_at, closed_at | CM-3, HH-2, AP-5 |
| `conversation_events` | id, conversation_id FK, event, cause, created_at | HH-1 transitions, operador-visible (audit_log is admin-only) |
| `kb_documents` | id, title, format(pdf/md/csv), content, version, active_version, active bool, created_at, updated_at | KB-3/4 |
| `kb_chunks` | id, document_id FK, version, chunk_index, content, source_meta jsonb, embedding vector(1536) | KB-1; HNSW index (vector_cosine_ops); retrieval filters `active_version` |
| `settings` | key PK, value jsonb, updated_by FK→users, updated_at | SS-1..5: scope rules, emergency keywords, tone, spend limits, meta pricing, safety instructions |
| `audit_log` | id, actor, action, entity, entity_id, before jsonb, after jsonb, created_at | SH-5; app DB role = INSERT+SELECT only (append-only enforced by grants) |

Relations: customer 1—N conversations 1—N messages; conversations 1—N cases (a case may span convs later); customer N—N cases; kb_documents 1—N kb_chunks.

## Data Flow

**Webhook ingest** (WH-1..7):

```
POST /webhook/whatsapp
  → HMAC-SHA256(raw body) vs X-Hub-Signature-256   [fail → 403, drop]
  → not messages event | error 131051              [200, debug log, skip]
  → normalize (phone E.164, wamid, type, text/media)
  → INSERT messages(status=received) ON CONFLICT(wamid) DO NOTHING
  → return 200                                      [WH-3: before any processing]
  → BackgroundTask: run graph → status=processed|failed
Startup sweep: status='received' FOR UPDATE SKIP LOCKED → reprocess (crash recovery)
```

**Conversation graph** (CM-1..6):

```
receive → emergency_gate ──hit──▶ emergency_node (skip LLM)
                    └─miss─▶ handoff_gate ──trigger──▶ handoff
                                    └─clear─▶ classify_intent (LLM)
                                                 └─▶ route
                                          ┌───────────┴───────────┐
                                    capture sub-flow        kb_retrieve (pgvector)
                                    (one field/turn)              │ hit/miss
                                          └────────────▶ respond (LLM, KB-grounded)
                                                         └─▶ summary_gate (on completion/escalation)
```

**State** (`app/chat/state.py`): `{customer_id, conversation_id, phone, turn, intent, case{service,priority,status}, captured{}, summary, emergency, escalate, escalate_reason, window[messages]}` — rebuilt from DB each message (D2).

**Deterministic gates before LLM**:
1. `emergency_gate` — compiled regex over settings.emergency_keywords on raw text (EM-1). Hit → emergency node (safety instructions from settings, case flagged, notification, state→human). Weak hit (e.g., "huele raro", "gas" stem) → handoff (EM-5 conservative).
2. `handoff_gate` — triggers not needing LLM: menu "Hablar con una persona", 2nd failed comprehension (unknown-intent counter), media evidence (photos/videos → technical review HH-3), complaint/warranty keywords, SS-1 scope rule = always_escalate. Complaints also match here deterministically; everything else escalates via intent/retrieval failure.

**Edge cases**: unknown intent → increment `unknown_count`; at 2 → handoff. KB miss (below threshold) → CM-4 "cannot answer reliably" + log unresolved (`unresolved_questions` view over messages with status flag) + SS-1 rule. Multi-turn: state from DB; context window = last N turns (10). Summary generated once at completion or escalation (CM-5), stored on conversation + case.

## Webhook Pipeline

| Concern | Design |
|---|---|
| Verify handshake | GET: `hub.mode=subscribe` + `hub.verify_token` match → 200 `hub.challenge`; else 403 + audit log (WH-1) |
| Signature | HMAC-SHA256(raw body, app_secret), constant-time compare (WH-2) |
| 200-first | Persist then return 200; graph runs in BackgroundTask (WH-3/4) |
| Dedup | `wamid` unique partial index; `ON CONFLICT DO NOTHING` → duplicate delivery = 200, skipped (WH-5) |
| Unsupported/131051 | Filter before persist, debug log only (WH-6) |
| Retry storm | Dedup + idempotent processing; sweep bounded by status column; no queue to grow (WH-7) |
| Rate limit | In-memory per-phone sliding window (e.g. 15 msgs/min) in single worker (`ponytail:` resets on restart — acceptable) |
| Media | image/video/audio → record media_url + async download to `media/` volume (evidence, §1.5); download failure → retry in sweep; media in normal flow → handoff for review |

## KB Pipeline

- **Formats**: PDF (pypdf extract), Markdown (direct), CSV (rows grouped per topic → chunks) — LumatRequest §1.6.
- **Chunking**: `RecursiveCharacterTextSplitter` (langchain-text-splitters, already in LangGraph dep tree), chunk_size=500 tokens, overlap=50. Single strategy in H1 (proposal).
- **Embedding — named (LumatRequest §1.12)**: OpenAI `text-embedding-3-small`, **1536 dims, $0.02/1M tokens**. Chat: OpenAI `gpt-4o-mini` (~$0.15/1M in, $0.60/1M out, reference — verify at openai.com/pricing at contract). Volume: 50 docs ≈ 250K tokens re-ingest ≈ **<$0.01 per full re-ingest**; ~50 conv/day ≈ 375K tokens ≈ **~$0.10/day (~$3/mo) chat** before guardrails. Provider/model/cost recorded per document (`cost_meta` in kb_documents, visible in panel — KB-1 scenario).
- **Storage**: `kb_chunks.embedding vector(1536)`, **HNSW** index (`vector_cosine_ops`, m=16, ef_construction=64).
- **Retrieval**: top_k=5, min cosine similarity **0.65** (both settings-configurable). Below threshold → unresolved path (CM-4). Query embedded with same model.
- **Manager ops** (KB-3/4): add → ingest; edit → new version + re-embed chunks; disable → excluded from retrieval (active=false). Restore = set `active_version` back (D8 — no re-embed). All ops via panel, audited, cost logged.

## Emergency + Handoff

- **Keyword engine** (`app/services/emergency.py`): regex list from `settings.emergency_keywords` (defaults: olor a gas, fuga, humo, incendio, chispa, explosión, monóxido, intoxicación, riesgo eléctrico, filtración severa + variants), compiled at load and on settings change (SS-2 immediate effect). Runs on every inbound text **before** LLM (EM-1).
- **Flow interrupt** (EM-2): emergency node abandons capture; bot sends Lumat-approved `settings.safety_instructions` (gas distributor + emergency contacts), states technician notified (EM-3); conversation → human; case escalated + emergency flag.
- **Notification** (EM-4): WhatsApp utility template `emergency_alert` to configured owner/technician number (customer phone, location when known, context) + email fallback via SMTP. **Ack**: owner replies with configured ack keyword (regex, recorded on case) or panel button on the case. Unacked >15 min → reminder email (max 2).
- **Handoff state model** (HH-1): `bot → human` (escalation trigger), `human → closed` (panel), `bot → closed` (resolved). Every transition → `conversation_events` row (event+cause). **Closed + new inbound message → new conversation** on same customer (no reopen complexity; history stays linked — CR-5). 24h window does not change state; it only gates outbound message cost.
- **Deriva bundle** (HH-2): on escalation — full message history, summary, customer data, captured fields → `cases` + panel view. Reply-from-panel explicitly NOT in H1 (HH-5: human answers via WhatsApp app on the same number; webhook keeps persisting during `human` state).

## Admin Panel

- **Auth** (AP-1): login form → bcrypt verify → signed-cookie session (Starlette SessionMiddleware, 12h expiry); `failed_logins`/`locked_until` on `users` (lock after 5 fails, 15 min); every login/failure → audit_log.
- **Roles** (AP-2): FastAPI dependency on every route; `operador`: clients, conversations, cases, notes. `admin`: + settings, cost view, KB manager. Server-side only — no client-side trust.
- **Views** (AP-3..8): dashboard (KPIs = SQL counts: contactos, motivos, derivados, solicitudes de visita, time window from settings) · clients (list/search by name/phone, ficha with history + notes) · conversations (read-only thread + media links) · cases (pending/escalated, state change, responsible assign → audited) · KB manager (admin: upload/edit/disable) · settings (admin: scope rules SS-1, keywords SS-2, tone/messages SS-5, spend limits SS-3, Meta pricing SS-4) · CSV export (stdlib `csv`, streaming, panel-visible fields — AP-7).

## Security & Hardening

**Server checklist** (SH-1..3 — executable, documented in `docs/hardening.md`): ufw 80/443/SSH only · SSH key-only + fail2ban · non-root deploy user · TLS Let's Encrypt on `agente.`+`panel.lumat.cl` with auto-renew (systemd timer) · secrets in server env vars only (`.env` gitignored; `infra/.env.example` committed) · Docker `--privileged` never, api fs read-only (`read_only: true`, tmpfs + `media/` writable volume) · internal docker network · daily `pg_dump` 03:00 → external `backups/` volume, retention 14d, weekly restore-verification to scratch DB (SH-3) · monitor cron every 5 min: `/health` uptime, bot-down (webhook POST probe), backup-age check → SMTP email alert · `audit_log` append-only (DB grants).

**Prompt injection** (SH-4, first-class acceptance):

| Layer | Design |
|---|---|
| Input-as-data | User text only fills the "user turn" slot; never concatenated into system prompt. System prompt = static versioned template + retrieved KB chunks |
| Delimiters | User input wrapped in `<user_input>` tags in the LLM call; KB content in `<kb>` tags |
| Detection | Pattern set ("ignore your instructions", "olvida tus instrucciones", "actúa como", "reveal", "otros clientes", "contraseña", "system prompt") → treated as data, logged, conversation escalated — never executed |
| Tool whitelist | Only 2 tools exist: KB retrieval and field capture, both bound to current conversation/customer_id (no cross-customer queries, no admin tools reachable from chat) |
| Never reveal | System prompt contains no secrets; KB is curated public content; responses forbid prices/guarantees outside KB |
| Escalation | Out-of-scope/manipulation → handoff, never execute |
| Audit | Every message + every tool call already persisted; injection events → audit_log + case flag |

## Cost Guardrails

- `messages.cost_llm` (tokens × rate) and `messages.cost_meta` (outbound msg; **Meta service-message pricing effective 2026-10-01** — unit cost in settings, default reference, verified with Meta at activation; communicated to client) written after each send/LLM call. Sums drive limits (D6).
- **Per-conversation limit** (default $1.50): at 80% → alert owner + conservative mode (shorten replies); at 100% → escalate conversation, no more LLM for it (SS-3).
- **Daily limit** (default $5): at 80% → alert; at 100% → block paid LLM calls, bot answers from fallback script (deterministic) and escalates (SS-3).
- Deterministic paths (emergency, ack, simple routing) never call the LLM → spend saved by design. Spend + limits visible in panel (SS-4).

## Testing Strategy

pytest baseline (greenfield, no runner yet — config.yaml `tdd: false`). Spec scenarios map 1:1 via `@pytest.mark.spec("WH-5")` markers; every Given/When/Then scenario becomes a test (spec → test traceability table in `tests/README.md`).

| Layer | What | Approach |
|---|---|---|
| Integration | Webhook: valid/invalid signature, 200-before-process, wamid dedup, retry storm, 131051/unsupported, sweep recovery | Test Postgres container (pgvector image, compose `test` profile) + `httpx` ASGI client |
| Integration | KB: ingest PDF/MD/CSV, chunk counts, embed+store, retrieval top-k/threshold, versioning/restore | Real pgvector; OpenAI mocked (`respx`) |
| Integration | Emergency: keyword hit/weak-hit, interrupt mid-capture, notification + ack | Mocked Meta send; assert audit + events |
| Integration | Handoff: state transitions, deriva bundle content, closed→new conversation | DB assertions |
| Functional | CM flows: first contact menu, repeat contact resume, capture skip, 2-failure escalation, KB miss → unresolved log; CR: auto-ficha, phone dedup (+E.164 variants), state transition rejection; AP: login/lockout, role matrix, CSV export, KPIs | FastAPI TestClient + seeded DB |
| Injection suite | SH-4 fixtures: "ignore your instructions…", admin-tool attempt, sensitive-data probe, delimiter breakouts, Spanish variants | Golden assertions: no tool call, escalated, logged |

## Deployment Plan (H1)

1. **Dev**: `docker compose up` (api, postgres+pgvector) on dev machine; Meta **test number** for development (free, 5 verified recipients — dev only).
2. **Prod provision** (Hostinger KVM 2): Ubuntu LTS → Docker + Compose → ufw → hardening checklist (SH-1) → non-root user.
3. **DNS** (client, week 1-2): `A agente.lumat.cl`, `A panel.lumat.cl` → VPS IP.
4. **Deploy**: clone repo → `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` → nginx + certbot TLS → `db/migrate.sh` → seed settings + admin user → smoke test (`/health`, webhook verify).
5. **Go-live**: point **prepago dedicated number** webhook at `https://agente.lumat.cl/webhook/whatsapp` → validate with Lumat → migrate to real number after approval (Meta checklist).
6. **Ops** (`docs/ops.md`): deploy/rollback (git tag + compose restart), backup restore drill, emergency ack flow, KB add/edit, settings change, monitoring alert triage, daily summary cron.

## File Changes

| File | Action | Description |
|---|---|---|
| `app/main.py`, `app/config.py`, `app/db.py`, `app/models.py` | Create | App factory, pydantic-settings env config, SQLAlchemy session, ORM models |
| `app/webhook/{router,verify,ingest}.py` | Create | GET verify, POST signature+persist+200, background schedule, sweep |
| `app/chat/{state,graph}.py`, `app/chat/nodes/*.py` | Create | ConversationState, graph builder, 9 nodes (receive, emergency_gate, handoff_gate, classify_intent, route, capture, kb_retrieve, respond, summary, emergency, handoff) |
| `app/services/{emergency,kb,customers,send,costs,audit}.py` | Create | Keyword engine; KB ingest/retrieve; customer/dedup; Meta send; cost calc; audit |
| `app/panel/` | Create | `routes/` (auth, clients, conversations, cases, kb, settings, export), `templates/`, `static/` |
| `db/migrations/*.sql`, `db/migrate.sh` | Create | 001_init.sql (all tables + HNSW), apply runner with schema_migrations |
| `infra/docker-compose.yml`, `docker-compose.prod.yml`, `nginx/`, `certbot/`, `backup.sh`, `restore-test.sh`, `monitor/*.sh`, `.env.example` | Create | Topology, TLS, backups, monitoring |
| `tests/{integration,functional,injection}/` | Create | Three suites per testing strategy |
| `docs/{hardening,ops}.md` | Create | Executed checklist + runbook |
| `openspec/config.yaml` | Modify | Refresh stale values (Hostinger/M1/software delivery) |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary in application code. The webhook is external HTTP input handled by signature verification, normalization, and parameterized SQL; monitoring/backup scripts are fixed-command ops scripts with no user-controlled arguments.

## Migration / Rollout

No migration (greenfield). Rollout = dev compose → prod VPS → prepago number → real number (phased, per Meta checklist). Rollback = `git revert` + container restart; data restore from daily backups.

## Open Questions

- [ ] Meta utility template `emergency_alert` approval timing (external; mitigation: email fallback already designed)
- [ ] Exact Meta service-message price for Chile post-2026-10-01 (settings default placeholder; verify at activation)
- [ ] KB document availability (client deadline 28-ago; FAQ mínimo seeded day 1)

## Ponytail Plan Review (applied — cuts)

1. `Section "Data Model"`: delete `emergency_rules` table → keywords live in `settings` KV (jsonb list). Config is KV, not relational.
2. `Section "Data Model"`: delete `spend_ledger` table → `cost_llm`/`cost_meta` columns on `messages` + SQL SUM. One write path, zero joins.
3. `Section "Architecture"`: delete worker container + broker → in-process BackgroundTasks + startup sweep (`ponytail:` ceiling = single-process; H4 event bus is the upgrade path).
4. `Section "Conversation Flow"`: delete LangGraph checkpointer → rebuild state from DB per message (D2).
5. `Section "Emergency"`: delete LLM secondary validation → deterministic hit = emergency, weak hit = human escalate (D4). Simpler, cheaper, safer.
6. `Section "KB"`: delete per-format chunkers → one `RecursiveCharacterTextSplitter` (already in dep tree) with CSV row-grouping.
7. `Section "Admin Panel"`: delete Excel export → CSV only (stdlib `csv`); AP-7 says "CSV or Excel".
8. `Section "Data Model"`: delete separate `handoff_transitions` table → `conversation_events` covers transitions + escalations (audit_log stays admin-only per SH-5).

net: -8 items cut from design.
