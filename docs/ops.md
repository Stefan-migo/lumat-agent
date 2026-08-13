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

## 2. Ops Runbook (T6.5)

> Real paths below assume the deploy layout: repo cloned to `/opt/lumat` on
> the VPS, deploy user `deploy`, containers `lumat-api` / `lumat-db`, volumes
> `lumat_db` / `lumat_media` / `lumat_backups` (names from
> `infra/docker-compose.yml`; prod override `infra/docker-compose.prod.yml`).
> All commands run as `deploy` unless marked `sudo`.

### 2.1 Deploy — git tag + compose restart

Every deploy is a tagged release; the tag is the rollback point (§2.2).

```bash
cd /opt/lumat
sudo -u deploy git fetch origin main
sudo -u deploy git checkout <tag>            # e.g. v1.4.0
sudo -u deploy docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
sudo -u deploy bash db/migrate.sh            # idempotent; run BEFORE the api picks up new code
```

Smoke (each deploy, before go-live):

```bash
curl -fsS https://agente.lumat.cl/health                      # {"status":"ok",...}
curl -fsS "https://agente.lumat.cl/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<VERIFY_TOKEN>&hub.challenge=123"   # echo 123
sudo -u deploy /opt/lumat/infra/monitor.sh && echo monitor=OK
```

Expected: `/health` returns 200; the verify handshake echoes the challenge;
monitor exits 0. If any smoke fails → roll back (§2.2).

### 2.2 Rollback — previous tag + compose restart

```bash
cd /opt/lumat
sudo -u deploy git checkout <previous-tag>   # the last known-good tag
sudo -u deploy docker compose -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
sudo -u deploy bash db/migrate.sh            # safe: migrations are idempotent, never destructive
```

**Rule: never roll back a schema migration that already ran** (the app
migrates forward only). If the bad release included a migration, roll back
code to the previous tag, then run the forward migration manually via
`db/migrate.sh` before restarting the api — data is never reverted, only code.
Record the incident in the runbook log (§10).

### 2.3 Backup restore drill (weekly, automated + manual)

`infra/restore-test.sh` restores the newest dump into a scratch database
(`lumat_restore_test`) and reports `restore OK`. Run it at least weekly
(cron entry installed in §7 of `docs/hardening.md`):

```bash
sudo -u deploy /opt/lumat/infra/restore-test.sh
```

Expected output: `restore OK (lumat_restore_test, dump <file>, rows <n>)`.

Manual drill (quarterly, operator): pick yesterday's dump and restore to a
scratch DB, verify row counts, drop the scratch DB:

```bash
DUMP=$(ls -t /var/lib/docker/volumes/lumat_backups/_data/*.sql.gz | head -1)
docker exec lumat-db sh -c 'gunzip -c < /backups/'"$(basename "$DUMP")" \
  '| psql -U lumat -d lumat_restore_test'
docker exec lumat-db psql -U lumat -d lumat_restore_test -Atc \
  'SELECT count(*) FROM customers;'          # matches production count
docker exec lumat-db psql -U lumat -c 'DROP DATABASE lumat_restore_test;'
```

### 2.4 Emergency ack flow

Emergency case → customer receives the `emergency_alert` template (or email
fallback) → the bot keeps listening for an ack keyword ("ok", "sí", "gracias"
— EM-4). The operador watches the panel cases view (AP-5):

1. Case marked `escalado` with `emergency=true` appears in the panel.
2. If the customer acks, the case is acknowledged automatically and the
   reminder emails stop (`acknowledge_emergency_if_ack`, audited).
3. If NOT acked, `send_pending_emergency_reminders` re-alerts on every sweep
   until ack or manual close (documented interval in `app/services/notify.py`).

Operator actions:

```bash
# view pending emergency cases (panel UI, or psql for triage):
docker exec lumat-db psql -U lumat -d lumat -c \
  "SELECT id, customer_id, status, escalated_at FROM cases WHERE status='escalado' ORDER BY escalated_at;"
```

Close/acknowledge manually from the panel cases view (state change → `closed`,
recorded in `conversation_events` + `audit_log`). If the customer texts
"emergencia"/"incendio" again, the conversation is still in `human` state
(HH-5) — alert the on-call human directly (phone), the bot does not run.

### 2.5 KB add/edit

Add a document (KB-1; panel route `POST /panel/kb` or service):

```bash
# via the panel: KB manager (T5.4) — title + content + source url; ingest chunks immediately
# via CLI on the server (same path the panel calls):
cd /opt/lumat && .venv/bin/python - <<'EOF'
from app.db import SessionLocal
from app.services import kb
with SessionLocal() as s:
    kb.ingest_document(s, title="FAQ revision anual", content="La revision anual de calefont cubre...", source_url="https://lumat.cl/faq")
    s.commit()
EOF
```

Every ingest writes an `audit_log` row (`kb.document_ingest`, actor + action +
timestamp — SH-5) and replaces the previous version's chunks for the same
title (chunk churn is handled by `ingest_document`, KB-1). Edit = re-ingest
with the same title; delete = panel KB manager (removes chunks + audit).

Verify retrieval answers the new content (chat test or `/panel/kb` list).

### 2.6 Settings change

Settings are KV in the `settings` table (panel Settings view, T5.4):
scope rules (`scope_rules`), keywords, cost limits, KPI window. Changes are
audited (`settings.change`, before/after values — SH-5).

```bash
# via the panel (recommended), or psql for a fast change:
docker exec lumat-db psql -U lumat -d lumat -c \
  "UPDATE settings SET value='{\"calefont\": \"always_escalate\"}'::jsonb WHERE key='scope_rules';"
```

The api reads settings per request (`get_setting` cache — T4.1); no restart
needed. **Rule**: verify the JSON is valid before saving — an invalid
`scope_rules` value makes the classification path fall back to the default
(marked in logs).

### 2.7 Monitoring alert triage

`infra/monitor.sh` (every 5 min) sends an SMTP alert when a check fails.
Triage table:

| Alert | Meaning | First action |
|-------|---------|--------------|
| `health=FAIL` | api down / 5xx | `docker compose ps` → `docker compose logs --tail 50 api` → restart (§2.1) |
| `webhook_probe=FAIL` | Meta→webhook path broken | verify signature config + `VERIFY_TOKEN`/`APP_SECRET`; check `docker compose logs --tail 50 api \| grep -i webhook` |
| `backup_age=FAIL` | no fresh dump | run `infra/backup.sh` manually; check `/var/log/lumat-backup.log`; verify `db-test`/prod DB is up |

After fixing, run `sudo -u deploy /opt/lumat/infra/monitor.sh` → exit 0
clears the alert (next 5-min run re-alerts if still failing). Log every
incident + resolution in §10.

### 2.8 Daily summary cron

Operational digest (open cases, unresolved questions, cost spend, backup
status) delivered daily. Install with cron (adjust the hour; 07:00):

```bash
crontab -l 2>/dev/null | grep -q summary || (crontab -l 2>/dev/null; cat > /tmp/cron <<'EOF'
0 7 * * * cd /opt/lumat && .venv/bin/python -m app.ops.daily_summary >> /var/log/lumat-summary.log 2>&1
EOF
crontab /tmp/cron && rm /tmp/cron)
```

> `app.ops.daily_summary` is a thin script over existing services
> (`list_open_cases`, `list_unresolved_questions`, cost sums) that emails the
> digest via the same SMTP path as `monitor.sh`. Add it in T7.2 alongside the
> seed if not present; the cron entry above is the ops contract.

### 2.9 Go-live record

Fill this out at T7.3 (after the prepago number webhook is live and Meta
validation passes). It is the evidence the change is in production.

| Item | Value | Date/initials |
|------|-------|---------------|
| Deploy tag (git) | `v1.x.x` | |
| Production URL (webhook) | `https://agente.lumat.cl/webhook/whatsapp` | |
| Meta number (prepago dedicated) | +56 … | |
| Meta validation status | ⬜ pending / ✅ approved | |
| Hardening checklist | `docs/hardening.md` — all 9 ticks | |
| Backup cron verified | `crontab -l \| grep backup.sh` | |
| Monitor cron verified | `crontab -l \| grep monitor.sh` | |
| First real customer conversation | case id: | |
| Rollback tag (known-good) | `v1.(x-1).y` | |

---

## 3. Runbook change log

| Date | Change | Operator |
|------|--------|----------|
| 2026-08-13 | T6.5 — full runbook written (sections 2.1–2.9); Meta onboarding checklist (section 1) unchanged | dev |
