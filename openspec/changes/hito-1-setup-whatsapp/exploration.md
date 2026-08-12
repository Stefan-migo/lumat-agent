# Exploration: Hito 1 — Setup + WhatsApp operativo (LumatAgent)

> Change: `hito-1-setup-whatsapp` · Project: LumatAgent (client: Lumat, gasfitería, Chile)
> Phase: sdd-explore · Date: 2026-08-11
> Status: contract signed, Pago 1 received (11-ago-2026), kickoff 17-ago-2026
> Timeline: H1 = weeks 1-4 (17-ago → 13-sep) · 12 weeks construction + 5 weeks testing/rollout, acceptance ~16-dic-2026

---

## Current State

**There is NO source code.** The repository is documentation-only. Confirmed by inspection:

| Exists today | Detail |
|---|---|
| `LumatRequest.md` | Original functional request (M1 bot + M2 web + M3 servicios) — context only; M2 on standby by agreement |
| `Propuesta_Lumat_Entrega_1.pdf` | First proposal delivery (superseded by propuesta-final) |
| `.cortex-sessions/2026-08-07-reunion-cierre/propuesta-final-lumatagent.md` | **SIGNED proposal** — the authoritative contract scope (Hito 1 deliverables, architecture §3, server §4, WhatsApp §5, security §6) |
| `.cortex-sessions/2026-08-07-reunion-cierre/01-plan-hitos-detallado.md` | Detailed milestone plan, Hito 1 section |
| `.cortex-sessions/2026-08-07-reunion-cierre/02-requerimientos-servidor.md` | Server requirements (Hostinger KVM 2 recommended, hardening checklist, production readiness checklist) |
| `.cortex-sessions/2026-08-07-reunion-cierre/03-checklist-meta-api.md` | Meta Cloud API activation checklist (client + technical steps, test number vs prepago, 24h window, deleted messages) |
| `openspec/` | Existing OpenSpec structure with archived change `2026-07-20-lumat-propuesta-final` (proposal document lifecycle) and main spec `openspec/specs/lumat-propuesta-final/spec.md` |
| `.atl/skill-registry.md` | Skill registry (present, not needed — skills injected) |
| `.gitignore` | Only ignores `.atl/` — **no git repo initialized yet** (repo location pending per management plan) |

**Must be created from scratch:** application code (FastAPI), LangGraph flow, PostgreSQL schema + pgvector, Docker/Compose infra, webhook handler, admin panel, tests, CI-less project structure. Everything in H1 is greenfield.

### Stale context to flag (do not trust)

- **`openspec/config.yaml` is stale** (2026-07-20): says "Hetzner VPS + Next.js + 3 milestones (Bot IA, Website, Servicios), pre-code / cotización". Reality: **Hostinger KVM 2 (São Paulo) recommended as primary**, no Next.js in stack, **M1 only** (M2 web on standby), contract signed, software delivery starting. Should be updated at propose phase (explore does not modify).
- **Engram `sdd-init/lumat` (#1005) is stale**: same Hetzner/3-milestone/proposal-lifecycle framing. The management plan (11-ago) supersedes it: 4 SDD changes (one per hito), 12+5 week schedule, delivery_strategy `auto-chain`, review budget 400 lines.
- **No `graphify-out/`** — knowledge graph never built (docs-only repo). Graph Check skipped per launch instructions; consider building the graph on the first code commit (H1 apply phase).

---

## H1 Scope Decomposition

What H1 (`Setup + WhatsApp operativo`) actually entails, per the signed proposal + milestone plan + LumatRequest M1:

1. **Server setup & hardening** (proposal §4.3, §6.1; server reqs §2-5)
   - VPS Hostinger KVM 2 (2 vCPU / 8 GB / 100 GB NVMe, São Paulo) — Ubuntu LTS + Docker + Docker Compose
   - Firewall: only 80/443/SSH; SSH key-only + fail2ban; non-root app user
   - TLS via Let's Encrypt for `agente.lumat.cl` (API/webhooks) and `panel.lumat.cl` (panel)
   - Secrets in server env vars only; Docker without `--privileged`, read-only agent filesystem
   - Daily PostgreSQL backups to external volume + periodic restore verification; basic monitoring (uptime, bot down, backup failure); `audit_log` table
2. **PostgreSQL schema foundation** — customers, conversations, messages, cases, KB documents, audit_log, app settings/config, emergency keyword rules; pgvector extension for KB semantic search
3. **Meta WhatsApp Cloud API onboarding** (checklist §B) — developer app, WABA link, Phone Number ID, permanent token, 2-step PIN, utility templates, webhook subscription to `messages` events
4. **Webhook handling with dedup** — `GET /webhook/whatsapp` verify handshake; `POST` → verify `X-Hub-Signature-256`, respond `200` immediately, persist raw message, **dedup by wamid** to tolerate Meta retries (at-least-once delivery); gracefully ignore `unsupported`/error `131051` events
5. **Conversation manager** — per-conversation state machine (LangGraph), menu of categories (calefont, caldera, calefacción, solicitar visita, valores, postventa/garantía, emergencia, hablar con persona), progressive structured data capture (LumatRequest §1.5), intent classification, case classification by service/priority/status, summary generation
6. **Customer records** — auto-create ficha on first contact, recognize existing by phone number, no duplicate records, internal notes, states (nuevo/contactado/pendiente/agendado/en evaluación/finalizado/cancelado/postventa)
7. **Expert KB loading + KB manager** — documents Lumat provides (manuales de fabricantes, procedimientos, tarifario, FAQ, troubleshooting, códigos de error) ingested into pgvector with semantic search; admin panel to add/edit documents without code changes (LumatRequest §1.6)
8. **Configurable scope limits** — owner defines what the bot resolves alone vs always escalates; emergency keywords configurable (LumatRequest §1.12: "Permitir ajustar el tono, mensajes y reglas del bot")
9. **Emergency detection** — deterministic detection of emergency expressions (olor a gas, fuga, humo, incendio, chispa, explosión, monóxido, intoxicación, riesgo eléctrico, filtración severa); interrupt commercial flow, deliver Lumat-approved safety instructions, recommend emergency services/gas distributor contact, **immediate notification to owner/technician**
10. **Human handoff** — escalation with full history + summary (client must not repeat info); per-conversation state (`bot`/`human`/`closed` in DB); **scope boundary: H1 = deriva + historial + resumen + case visible in panel; full "bandeja humana" reply-from-panel is an H2 deliverable** (proposal Hito 2) — flag for propose to confirm this split
11. **Initial admin panel** — login for authorized users; clients list/search; conversation view; cases list (pendientes/derivados); KB manager; CSV/Excel export; basic KPIs (contactos, motivos, derivados, solicitudes de visita); admin/operador roles (LumatRequest §1.11)
12. **Tests** — integration, functional, and **prompt-injection** (proposal Hito 1 entregables; LumatRequest §1.14 acceptance)
13. **WhatsApp operational** — bot answering real customers within configured scope on the prepago number (dev on Meta test number meanwhile)

---

## Key Technical Questions / Risks to Resolve in Proposal

1. **KB ingestion approach for pgvector** — source document formats (PDF manuales, MD, CSV tarifario), chunking strategy, embedding provider + model + **costs** (LumatRequest §1.12 requires naming model/provider and costs), metadata/versioning, re-ingestion on update, retrieval strategy for the agent (top-k, threshold). Recommendation direction: simple chunk-and-embed pipeline, embeddings model TBD in design, `ponytail:` minimal.
2. **Emergency detection heuristics** — deterministic keyword/pattern layer (fast, safe, configurable) vs LLM classification. Safety-critical ⇒ deterministic gate first, LLM as secondary validation; false-positive → allow human check; escalation default. Configurable via panel (scope limits).
3. **Human-handoff state model** — states `bot`/`human`/`closed`; who owns the channel when human takes over (still same POST /messages endpoint — human handoff architecture already defined, mem #1341); summary generation timing; resume/return-to-bot semantics; interplay with Meta 24h window.
4. **Meta webhook reliability** — signature verification, immediate `200`, persist-before-process, dedup by wamid, retry storm handling, unsupported event (131051) filtering, rate limits (messages/s), media download handling for evidence photos (LumatRequest §1.5 evidencia).
5. **Prompt-injection mitigations** — input-as-data-not-instruction, system prompt isolation, injection attempt detection, tool whitelist by role, never reveal sensitive data (other clients, passwords, internal config), controlled escalation, full audit (proposal §6.2; LumatRequest §1.12 "responder únicamente con información autorizada").
6. **Server hardening checklist** — full executable checklist from `02-requerimientos-servidor.md` §7 ("listo para producción"), adapted to H1: firewall, SSH keys, fail2ban, Docker hardening, TLS, backups + restore test, monitoring, audit.
7. **Panel tech for H1 (minimal)** — proposal §4.2 says panel served by FastAPI; frontend approach undecided. Ponytail direction: minimal server-rendered or lightweight SPA, no PWA polish (that is H4). Defer heavy dashboarding to H2/H4.
8. **LangGraph in H1 vs H2** — H2 formally introduces the multi-agent orchestrator; contract stack is LangGraph-based. Starting H1 with a single-agent LangGraph graph avoids H2 rewrite; flag as design decision (Ponytail: single graph, no abstraction).
9. **Cost guardrails** — LumatRequest §1.12: consumption limits + cost alerts. H1 should include basic per-conversation/daily spend limits and alerting; pricing reality: service messages free until **1-oct-2026**, then charged (must communicate to client — already flagged in management plan risk).

---

## Client-side Dependencies (with deadlines)

| Dependency | Owner | Deadline | Notes |
|---|---|---|---|
| **Meta business verification** (Business Suite account, company verification via lumat.cl domain or legal docs, number registration) | Lumat | Start NOW (takes **weeks**; not under our control) | Dev proceeds with Meta test number meanwhile; production number only after verification |
| **SIM prepago dedicado** | Lumat | Before testing phase (~9-nov) | Number can't be active in WhatsApp app simultaneously — dedicated SIM documented (checklist §C) |
| **KB documents** (manuales, procedimientos, tarifario, FAQ) | Lumat | **28-ago** (management plan written deadline) | Start with FAQ mínimo + incremental loading via KB manager if late |
| **Backup human** for derived conversations during tests | Lumat | Testing phase | Responds from panel (H2) — during H1, human responds or acknowledges via agreed channel |
| DNS access to `lumat.cl` for subdomains (`agente.`, `panel.`) | Lumat | Early H1 (week 1-2) | Needed for TLS + webhook URL |

Management plan rule: client dependencies communicated in writing, 2 weeks in advance.

---

## Approach Options

1. **Greenfield monorepo — single repo, single VPS** *(recommended)*
   - One repo: `app/` (FastAPI + LangGraph + services), `infra/` (docker-compose, nginx, backup scripts), `tests/`, `docs/`. Prod = Hostinger VPS; dev = local Docker Compose. No separate staging VPS in H1 (Hetzner staging optional, only if budget/timing allows).
   - Pros: simplest ops surface for one person (20 h/wk), single source of truth, matches 1-change-per-hito delivery, staging can be added later without rework.
   - Cons: no isolated staging env in H1; changes go through tests + demo review instead.
   - Effort: Low infra overhead.

2. **Dual-environment (dev VPS + prod VPS) from day 1**
   - Hetzner or second Hostinger box as staging.
   - Pros: isolated staging, safer demos.
   - Cons: ~2× infra cost and maintenance for a solo operator at 20 h/wk; YAGNI for H1 volumes (decenas de conversaciones/día). Over-engineering per Ponytail.
   - Effort: Medium.

3. **Defer panel to H2** *(rejected)*
   - Pros: less H1 work.
   - Cons: contradicts signed proposal — H1 explicitly delivers "panel administrativo inicial: clientes, conversaciones, casos, exportación CSV" + KB manager. Not negotiable; only the panel's depth/tech is open.

**H1 must NOT include (belongs to H2-H4):** multi-agent orchestration + 5 sub-agents + role system + full human inbox (H2); calendar/scheduling/ICS (H3); notifications center + templates queue (H3); automations/event bus/deterministic worker (H4); PWA installability + push (H4); advanced dashboards/reports (H4); M2 website; M3 payments/catalog.

---

## Recommendation

Proceed to **propose** with: greenfield single-repo monorepo on Hostinger KVM 2 (production only, local Docker for dev); H1 built on a single-agent LangGraph graph (avoids H2 rewrite, honors contract stack); deterministic emergency/scope gate + LLM classification layered behind it; webhook with immediate `200` + wamid dedup + signature verification; prompt-injection hardening as a first-class test deliverable. Confirm with the client the handoff depth split (H1 = deriva + summary + case list; H2 = reply-from-panel inbox). Update stale `openspec/config.yaml` and `sdd-init/lumat` context during propose.

---

## Affected Areas (all to be CREATED — nothing to modify)

- `openspec/config.yaml` — stale (Hetzner/Next.js/3 milestones) → update in propose
- `app/` — FastAPI service: webhook router, conversation manager (LangGraph), customer/case/message services, KB ingestion + retrieval (pgvector), emergency detection, handoff state, settings/scope limits
- `app/panel/` — initial admin panel (clients, conversations, cases, KB manager, CSV export, login)
- `infra/` — docker-compose (api, worker, postgres+pgvector, panel), nginx/TLS, backup scripts, monitoring
- `db/` — schema migrations (customers, conversations, messages, cases, kb_documents, audit_log, settings)
- `tests/` — integration, functional, prompt-injection
- `docs/` — server hardening checklist applied, ops runbook
- Engram `sdd-init/lumat` (#1005) — stale project context, superseded by management plan memory (#1343)

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Meta business verification takes weeks (external) | **HIGH** | Start now; dev on Meta test number; tests on prepago SIM; production number only after verification |
| Prompt injection on open WhatsApp channel | **HIGH** | Layered defenses (input-as-data, tool whitelist, escalation, audit) + dedicated injection test suite as acceptance criterion |
| Emergency detection false negatives/positives (safety) | **MEDIUM** | Deterministic keyword layer + conservative default (escalate), configurable keywords, human ack |
| KB documents late (deadline 28-ago) | **MEDIUM** | FAQ mínimo from day 1; incremental loading via KB manager; no blocked path |
| Webhook reliability (retries, duplicates, signature) | **MEDIUM** | Immediate 200, persist-before-process, wamid dedup, signature verification |
| Capacity < 20 h/wk (solo, mid-time) | **MEDIUM** | Speed checkpoint week 2 (28-ago) per management plan; scope cuts via separate quotation |
| Meta service-message pricing from 1-oct-2026 | **LOW/MED** | Communicate to client; volume low; budgets in cost guardrails |
| Stale OpenSpec/Engram context misleads later phases | **LOW** | Update config.yaml + sdd-init context in propose phase |

---

## Ready for Proposal

**Yes.** The orchestrator should tell the user: H1 is fully greenfield (no code exists), scoped as 13 workstreams across server → Meta onboarding → conversational core → KB → panel → tests; the two open decisions for propose are (a) handoff depth split H1-vs-H2 and (b) panel tech depth; client dependencies (Meta verification, SIM, KB by 28-ago, DNS) are communicated and tracked; next step is `sdd-propose`.
