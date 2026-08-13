# LumatAgent — Operations & Meta Onboarding Checklist

> Change: `hito-1-setup-whatsapp` · Task: **T2.1** (ops, NOT code) · Updated: 2026-08-12
> Status: **BLOCKED on client action** — waiting on Meta credentials from Lumat (Max).
> This file is the T2.1 deliverable (onboarding notes structure). The full ops
> runbook (deploy/rollback, backup restore drill, monitoring triage, go-live
> record) lands in T6.5 — this checklist is the prerequisite that unblocks the
> live webhook.

---

## 1. Meta Cloud API Onboarding — Checklist (T2.1, BLOCKED)

**Why this is blocked**: T2.1 requires the client's Meta developer app, WABA
link, Phone Number ID, permanent token + 2-step PIN, and a public HTTPS
endpoint. None of these exist in the repo or in our control — they must come
from Lumat (Max) and Meta's approval process. **We do not fabricate
credentials or env values.** Until the items below are delivered, the live
webhook cannot be subscribed; development proceeds on the test number.

### 1.1 What we need from Lumat (client)

| # | Item | Status | Owner | Notes |
|---|------|--------|-------|-------|
| 1 | Meta Business Manager account (or dev access to existing) | ⬜ pending | Lumat (Max) | Container for app + WABA; see `docs/solicitud-al-cliente-lumat.md` §2.1 |
| 2 | WhatsApp Business API subscription (WABA link to the business) | ⬜ pending | Lumat | Requires business verification for stable use |
| 3 | Dedicated phone number for the bot (test number OK for dev) | ⬜ pending | Lumat | Meta **test number** for development (free, 5 verified recipients) |
| 4 | Business verification (Meta) | ⬜ pending | Lumat | Required for stable API + template messages |
| 5 | **Phone Number ID** | ⬜ pending | Lumat/dev | Shown in Meta App Dashboard after number is set up |
| 6 | **Permanent token** (long-lived system user token) + **2-step PIN** | ⬜ pending | Lumat/dev | Generated in Meta App Dashboard / System User |
| 7 | Utility template `emergency_alert` submitted for approval | ⬜ pending | dev | Prerequisite for EM-4 notifications; approval status logged here when known |
| 8 | Public HTTPS endpoint reachable from Meta (tunnel or early VPS) | ⬜ pending | dev + DNS (Lumat) | Meta webhooks reject non-HTTPS URLs; DNS `agente.lumat.cl` (client, week 1–2) |

### 1.2 Where credentials go (server env only — NEVER in the repo)

All Meta credentials are read from environment variables by
`app/config.py` (env-only, `env_file=None` — design SH-2). The committed
`infra/.env.example` documents the names with `change-me` placeholders; real
values live in the server environment / `infra/.env` (gitignored).

| Env var | What it holds | Source |
|---------|---------------|--------|
| `META_ACCESS_TOKEN` | Permanent token (item 6) | Meta App Dashboard → System User → Generate Token |
| `META_PHONE_NUMBER_ID` | Phone Number ID (item 5) | Meta App Dashboard → WhatsApp → API Setup |
| `APP_SECRET` | App secret (webhook HMAC) | Meta App Dashboard → App settings → Basic |
| `VERIFY_TOKEN` | Hub verify token we choose (any string, must match webhook config) | Our choice, set in Meta webhook config |

**Hard rules**:
- Never commit real tokens/IDs — repo carries placeholders only (`infra/.env.example`).
- The webhook is configured in Meta with the app secret + verify token; Meta
  calls `GET https://<public>/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=...`
  to subscribe to the `messages` field on the test number.

### 1.3 Acceptance (record results here when credentials arrive)

- [ ] Test number receives webhook POSTs (Meta → our endpoint, HMAC passes)
- [ ] `GET /webhook/whatsapp` verify handshake returns the challenge (WH-1 live)
- [ ] Template `emergency_alert` approval status recorded (EM-4 prerequisite)

**Blocked items to unblock**: 1.1 #1–#8. **This task stays `[ ]` in
tasks.md until the acceptance rows above can be verified with real
credentials.**

---

## 2. Ops Runbook (T6.5 — placeholder)

Deploy/rollback, backup restore drill, emergency ack flow, KB add/edit,
settings change, monitoring alert triage, daily summary cron, and the go-live
record will be documented here in T6.5. Not applicable in Batch 2.
