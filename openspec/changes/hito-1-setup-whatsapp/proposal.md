# Proposal: H1 — Setup + WhatsApp operativo (LumatAgent)

> Change: `hito-1-setup-whatsapp` · Project: LumatAgent (client: Lumat, gasfitería, Chile)
> Phase: sdd-propose · Date: 2026-08-11 · Status: contract signed, Pago 1 received, kickoff 17-ago-2026
> Artifact language: English (technical) · Client-facing docs (Spanish) are a separate deliverable, NOT part of this change

## Intent

Deliver Hito 1 of the signed proposal (2026-08-07): a secure server plus a WhatsApp bot operating with real Lumat customers. The bot must be a gasfitería expert from day 1 (answers within configured scope using Lumat's KB), manages customer records, detects emergencies, escalates to humans with history+summary, all hardened against prompt injection. **Fully greenfield** — no source code exists; everything is created.

## Scope

### In Scope (13 workstreams)

1. **Server setup & hardening** — Hostinger KVM 2 (São Paulo), Ubuntu LTS + Docker Compose; firewall 80/443/SSH only; SSH key-only + fail2ban; non-root app user; TLS (Let's Encrypt) for `agente.` + `panel.lumat.cl`; secrets in server env vars; read-only agent fs; daily Postgres backups + restore verification; basic monitoring (uptime, bot down, backup fail); `audit_log`
2. **PostgreSQL schema + pgvector** — customers, conversations, messages, cases, kb_documents, audit_log, settings, emergency rules
3. **Meta Cloud API onboarding** — developer app, WABA link, Phone Number ID, permanent token, 2-step PIN, utility templates, webhook subscribe to `messages`
4. **Webhook handling + dedup** — GET verify handshake; POST: verify `X-Hub-Signature-256`, reply `200` immediately, persist raw, dedup by wamid; ignore `unsupported`/`131051`
5. **Conversation manager** — single-agent LangGraph state machine; 8-category menu (LumatRequest §1.4); progressive structured data capture (§1.5); intent classification; case classification (service/priority/status); summary generation
6. **Customer records** — auto-ficha on first contact, recognize by phone, no duplicates, internal notes, states (nuevo→postventa)
7. **Expert KB + KB manager** — Lumat docs ingested to pgvector (semantic retrieval); panel add/edit without code
8. **Configurable scope limits** — owner defines bot-resolves vs always-escalate; emergency keywords configurable (§1.12)
9. **Emergency detection** — deterministic keyword layer (gas, fuga, humo, incendio, chispa, monóxido…); interrupts commercial flow; Lumat-approved safety instructions; immediate owner/technician notification
10. **Human handoff** — deriva + history + summary + case visible in panel; per-conversation state `bot`/`human`/`closed`
11. **Initial admin panel** — login; clients list/search; conversation view; cases (pending/escalated); KB manager; CSV export; basic KPIs; admin/operador roles
12. **Tests** — integration, functional, prompt-injection suite (H1 acceptance deliverable)
13. **WhatsApp operational** — live on prepago number; dev on Meta test number meanwhile

### Out of Scope (H2–H4 / M2–M3)

- H2: multi-agent orchestration + 5 sub-agents, role system, full human inbox (reply-from-panel), agent scaffolds
- H3: calendar/ICS, visit scheduling, notifications center, template queue
- H4: automations/event bus, deterministic worker, PWA installability + push, chat-with-agent, advanced dashboards, notifications polish
- M2 website; M3 payments/catalog/agenda. No staging VPS in H1 (YAGNI at ~tens conversations/day).

## Open Decisions (recommendations — orchestrator confirms with client)

| Decision | Recommendation | Rationale |
|---|---|---|
| **a. Handoff depth split** | H1 = deriva + history + summary + case in panel; **reply-from-panel inbox = H2** | Signed proposal places "bandeja humana" in Hito 2 §2; H1 only promises deriva+historial+resumen. Respecting it keeps H1 shippable in 4 weeks and avoids building an inbox twice. |
| **b. Panel tech depth** | Minimal: login + clients + conversations + cases + KB manager + CSV + basic KPIs | Proposal §4.2 = panel served by FastAPI; PWA/dashboards are H4. Ponytail: server-rendered or lightweight, no chart lib, no PWA polish. |

## Capabilities (contract with sdd-spec)

| New capability | Covers (→ `openspec/specs/<name>/spec.md`) |
|---|---|
| `whatsapp-webhook` | Verify handshake, signature check, 200-first, persist-before-process, wamid dedup, unsupported-event filtering |
| `conversation-manager` | LangGraph flow, menu, progressive data capture, intent + case classification, summary, unresolved-response logging |
| `customer-records` | Ficha lifecycle, phone-based dedup, states, notes, history linkage |
| `knowledge-base` | Ingestion (chunking + embeddings), pgvector retrieval, KB manager, versioning |
| `emergency-detection` | Deterministic rules, flow interrupt, safety instructions, owner/technician alert |
| `human-handoff` | State model bot/human/closed, deriva with history+summary, case visibility |
| `admin-panel` | Auth, roles (admin/operador), clients/conversations/cases views, KB manager, CSV export, basic KPIs |
| `settings-scope-limits` | Configurable bot-vs-escalate rules, emergency keywords, cost guardrails (spend limits + alerts) |
| `security-hardening` | Server checklist, prompt-injection mitigations, `audit_log` (quién, qué, cuándo) |

**Modified capabilities:** None — greenfield. (`lumat-propuesta-final` spec is prior document lifecycle, unaffected.)

## Approach

- **Greenfield single-repo monorepo**: `app/` (FastAPI + LangGraph + services), `app/panel/`, `db/` (migrations), `infra/` (compose, nginx/TLS, backup, monitoring), `tests/`, `docs/`. Prod = Hostinger KVM 2; dev = local Docker Compose.
- **Single-agent LangGraph graph in H1** — honors contract stack, avoids H2 rewrite (orchestrator conversion later).
- **Deterministic emergency/scope gate first**; LLM classification layered *behind* it (safety-critical ⇒ deterministic wins, escalate on ambiguity).
- **Webhook: 200-first + wamid dedup + signature verification** (at-least-once tolerance).
- **Prompt-injection hardening as first-class test deliverable** (input-as-data, tool whitelist, never reveal sensitive data, controlled escalation, audit).
- Ponytail cuts: no staging VPS, no message broker, no observability stack (basic cron alerts), provider embedding API (no self-hosted models), single chunk strategy in H1.

## Key Technical Decisions → confirm in design

| Area | Decision needed in design |
|---|---|
| KB ingestion | Chunking strategy, embedding **provider + model + costs** (LumatRequest §1.12 mandates naming), retrieval top-k/threshold, re-ingestion on update |
| Emergency heuristics | Deterministic-first keyword set + LLM secondary validation; default = escalate; panel-configurable |
| Handoff state model | `bot`/`human`/`closed` transitions, summary timing, resume-to-bot semantics, 24h-window interplay |
| Webhook reliability | Retry-storm handling, rate limits, media download (evidence photos §1.5) |
| Prompt injection | Input sanitization, system-prompt isolation, tool whitelist by role, injection test suite |
| Server hardening | Executable "listo para producción" checklist (02-requerimientos §7) |
| Cost guardrails | Per-conversation/daily spend limits + alerts; **Meta charges service messages from 1-oct-2026** (communicate to client) |
| LangGraph in H1 | **Use it** (single graph) — avoids H2 rewrite; contract stack |

## Affected Areas (all created — nothing modified)

| Area | Impact | Description |
|---|---|---|
| `app/` | New | FastAPI service: webhook router, conversation manager, services |
| `app/panel/` | New | Initial admin panel |
| `db/` | New | Schema migrations (customers, conversations, messages, cases, kb, audit, settings) |
| `infra/` | New | docker-compose, nginx/TLS, backups, monitoring |
| `tests/` | New | Integration, functional, prompt-injection |
| `docs/` | New | Hardening checklist applied, ops runbook |
| `openspec/config.yaml` | Modified | Refresh stale values (Hostinger/M1/software delivery) |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Meta business verification takes weeks (external) | High | Start NOW; dev on Meta test number; prepago SIM for tests; prod number only after verification |
| Prompt injection on open WhatsApp channel | High | Layered defenses + injection test suite as acceptance criterion |
| Emergency false +/- (safety) | Med | Deterministic layer, conservative escalate default, configurable keywords, human ack |
| KB docs late (deadline 28-ago) | Med | FAQ mínimo from day 1; incremental loading via KB manager |
| Webhook reliability (retries, dupes, signature) | Med | 200-first, persist-before-process, wamid dedup, signature verification |
| Capacity < 20 h/wk (solo) | Med | Speed checkpoint week 2 (28-ago); scope cuts via separate quote |
| Meta service-message pricing from 1-oct-2026 | Low/Med | Communicate to client; volume low; cost guardrails |

## Rollback Plan

- Greenfield ⇒ no prior behavior to break. Revert = `git revert` of commits; containers stop/restart independently; daily Postgres backups to external volume with periodic restore verification.
- Webhook misbehavior ⇒ keep traffic on Meta test number; production/prepago number stays unlinked until verified.
- config.yaml refresh is data-only; revert restores prior values.

## Dependencies (client-side, tracked in writing ≥2 weeks ahead)

| Dependency | Owner | Deadline |
|---|---|---|
| Meta business verification + number registration | Lumat | Start NOW (weeks) |
| SIM prepago dedicado | Lumat | ~9-nov (testing phase) |
| KB documents (manuales, procedimientos, tarifario, FAQ) | Lumat | 28-ago |
| DNS access `lumat.cl` → `agente.` + `panel.` subdomains | Lumat | Week 1-2 |
| Backup human for derived conversations | Lumat | Testing phase |

## Success Criteria (H1 acceptance, signed proposal §2)

- [ ] Bot answers real WhatsApp queries within configured scope
- [ ] Creates/updates customer records; no duplicate fichas
- [ ] Detects emergencies and notifies owner/technician immediately
- [ ] Escalates to human with history + summary (client repeats nothing)
- [ ] Panel shows conversations + KB management
- [ ] CSV export works; data under Lumat control
- [ ] Prompt-injection test suite passes
- [ ] Client validates behavior with real test cases
