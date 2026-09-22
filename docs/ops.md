# LumatAgent — Operations & Meta Onboarding Checklist

> Change: `panel-spa-delivery` · Tasks: **3.1–3.2** · Updated: 2026-09-21
> Status: **BLOCKED on client action** — waiting on Meta credentials from Lumat (Max).
> This file is the T2.1 deliverable (onboarding notes structure). The full ops
> runbook (deploy/rollback, backup restore drill, monitoring triage, release
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
> the VPS, deploy user `deploy`, containers `lumat-api-1` / `lumat-db-1` (compose `--project-name lumat` names), volumes
> `lumat_db` / `lumat_media` / `lumat_backups` (names from
> `infra/docker-compose.yml`; prod override `infra/docker-compose.prod.yml`).
> All commands run as `deploy` unless marked `sudo`.

### 2.1 Deploy — git tag + compose restart

The release version is CalVer `YYYY.MM.N`; `N` increments within the month, and
the annotated tag is `v` + that version. Create the tag **before** the deploy on
the exact commit being deployed; that makes the rollback point real. The single
version source is `pyproject.toml [project] version`. The same string reaches the
tag, image, `/health`, and changelog entry.

Release prep, when the release needs a new number — set `[project] version` in
`pyproject.toml` to the new CalVer, then tag that exact commit:

```bash
cd /opt/lumat
sudo -u deploy git fetch origin main
sudo -u deploy git checkout main
# edit pyproject.toml: [project] version = "2026.09.3"  (the tag must match it)
sudo -u deploy git add pyproject.toml
sudo -u deploy git commit -m "release: 2026.09.3"
sudo -u deploy git push origin main
sudo -u deploy git tag -a v2026.09.3 -m "Release v2026.09.3"
sudo -u deploy git push origin v2026.09.3
```

> `--project-name lumat` is REQUIRED: with `-f infra/...` compose would derive
> the project name from the `infra/` directory, producing `infra-api-1` /
> `infra_db` instead of the documented `lumat-*` names every other command and
> volume path assumes.

```bash
cd /opt/lumat
sudo -u deploy git fetch origin main
sudo -u deploy git checkout <tag>            # e.g. v2026.09.2
# The api image stamps the deployed commit and prod compose refuses to build
# without it. Read it as `deploy`, the repo owner: an admin shell in a repo owned
# by another user hits Git's dubious-ownership refusal.
GIT_SHA="$(sudo -u deploy git rev-parse --short HEAD)"
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml config >/tmp/lumat-compose-config.yml
sudo -u deploy docker build -f infra/nginx/Dockerfile -t lumat-nginx:prod .
sudo -u deploy docker run --rm lumat-nginx:prod nginx -t
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
# Migrate runs automatically inside the api container before uvicorn (compose
# command chain); re-run it explicitly to prove/refresh idempotence:
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api sh -c \
  'DATABASE_URL=postgresql://lumat:$POSTGRES_PASSWORD@db:5432/lumat db/migrate.sh'
# Seed settings defaults + initial admin (T7.2; idempotent, first seed wins):
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api db/seed.sh
```

`db/migrate.sh` and `db/seed.sh` are containerized on purpose: the api image
carries the venv, `DATABASE_URL`/`APP_DB_PASSWORD`/`PANEL_ADMIN_*` come from
`infra/.env` through the compose environment (SH-2 — no secrets on the CLI),
and the admin password is consumed at seed time only (bcrypt hash stored).

Smoke (each deploy, before go-live):

```bash
curl -fsS https://agente.lumat.cl/health                      # {"status":"ok",...}
curl -fsS "https://agente.lumat.cl/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=<VERIFY_TOKEN>&hub.challenge=123"   # echo 123
sudo -u deploy /opt/lumat/infra/monitor.sh && echo monitor=OK
```

Expected: `/health` returns 200 and `{"status":"ok","version":"<calver>","commit":"<short sha>"}`;
the version matches the tag (without `v`) and the commit matches the deployed
commit; the verify handshake echoes the challenge; monitor exits 0. If any
smoke fails → roll back (§2.2).

### 2.1.2 Panel SPA release smoke checklist

Run this checklist against `https://panel.lumat.cl` after the tagged compose
deploy. Browser checks are authenticated with the normal panel account; do not
put credentials or session cookies in the repository or shell history.

- [ ] Open `https://panel.lumat.cl/panel/app/`; submit valid credentials and
  confirm the authenticated shell loads under `/panel/app/`.
- [ ] Open a client-side deep link directly below `/panel/app/` and confirm it
  returns the SPA shell rather than a 404.
- [ ] In browser DevTools Network, confirm the shell, manifest, worker, brand
  icons, and at least one hashed `/panel/app/assets/` file return `200`.
- [ ] Confirm the browser offers PWA installation over HTTPS; install it and
  load the previously visited `/panel/app/` shell once with the network
  disabled. The offline shell must load, while authenticated `/panel/api/`
  requests must not be served from the service-worker cache.
- [ ] From the authenticated panel, export clients or cases and confirm
  `/panel/export/clients.csv` or `/panel/export/cases.csv` returns a CSV
  download, not `index.html`.
- [ ] Run the agent checks and record green results:
  `curl -fsS https://agente.lumat.cl/health`, the webhook verification probe
  from §2.1, and `sudo -u deploy /opt/lumat/infra/monitor.sh` (exit 0).

Record the tag, timestamp, operator, and any failed check in the release record
(§2.9). These panel checks require the VPS DNS, TLS certificates, and valid
panel credentials; they are not reproducible in the local repository test
environment.

### 2.1.1 T7.2 deploy rehearsal record — rehearsal complete, VPS pending

Executed 2026-08-15/16 on the local Ubuntu 24.04 KVM rehearsal VM
(`lumat-rehearsal`; Docker 29 + Compose v2.40, hardened stack §1–§9 already
executed per `docs/hardening.md`). Simulated a clean deploy: fresh clone of
`main` from a local git bundle into `/opt/lumat` (fresh db volume), exact
commands below. **Rehearsal complete — the same steps run on the Hostinger VPS
at go-live; nothing below touched a VPS.**

```bash
# 1. fresh clone (bundle -> /opt/lumat, branch main, HEAD 96d16817)
sudo -u deploy git clone /tmp/lumat-main.bundle /opt/lumat
sudo -u deploy git -C /opt/lumat checkout main
# 2. full prod stack (api runs migrate before uvicorn):
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
#    -> lumat-db-1 / lumat-api-1 / lumat-nginx-1 all healthy
# 3. migrate twice (idempotence proof):
#    run 1 (container start): created role app; applying 001_init..007_case_created_at; migrations up to date
#    run 2 (explicit):        skip 001_init..007 (already applied); migrations up to date
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api sh -c \
  'DATABASE_URL=postgresql://lumat:$POSTGRES_PASSWORD@db:5432/lumat db/migrate.sh'
# 4. seed twice (idempotence proof):
#    run 1: settings: 14 inserted, 0 already present
#           admin: created admin user 'admin'
#    run 2: settings: 0 inserted, 14 already present
#           admin: user 'admin' already exists — not overwritten
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api db/seed.sh
```

Smoke outputs (recorded):

> The endpoint now also reports the commit; the recorded output below is what the endpoint returned at the time.

```
$ curl -fsS https://agente.lumat.cl/health
{"status":"ok","version":"0.1.0"}
$ curl -fsS "https://agente.lumat.cl/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=dummy-vm-verify-token&hub.challenge=9876543210"
9876543210            # challenge echoed (WH-1); wrong token -> 403
$ sudo /opt/lumat/infra/monitor.sh; echo "monitor exit=$?"
[2026-08-16T00:15:46Z] health=OK
[2026-08-16T00:15:46Z] webhook_probe=OK (unsigned POST rejected 403)
[2026-08-16T00:15:46Z] backup_age=OK (lumat-20260816T001541Z.sql.gz, 6s old)
monitor exit=0
$ sudo crontab -l        # backup + restore + monitor armed under root
*/5 * * * * /opt/lumat/infra/monitor.sh >> /var/log/lumat-monitor.log 2>&1
0 3 * * * /opt/lumat/infra/backup.sh >> /var/log/lumat-backup.log 2>&1
0 4 * * 1 /opt/lumat/infra/restore-test.sh >> /var/log/lumat-backup.log 2>&1
$ systemctl list-timers | grep lumat-certbot      # renew timer armed (03:17/15:17)
```

Bonus (not in the canonical smoke): the seeded admin logged into the panel
end-to-end — `POST /panel/login` (admin / env-supplied password) → 302 to
`/panel/` → dashboard 200; wrong password rejected.

Rehearsal-caught bugs fixed in this batch:
- **Deploy scripts were mode 100644 in the git index** — a fresh clone drops
  working-tree chmods, so the api container failed with `db/migrate.sh:
  Permission denied`. Fixed with `git update-index --chmod=+x` on
  `db/{migrate,seed}.sh` + `infra/{backup,monitor,restore-test}.sh`; regression
  test added (`test_deploy_scripts_tracked_as_executable`).
- **`docs/hardening.md` §8 cron command replaced (not appended) the crontab**
  — `(crontab -l; echo X | crontab -)` wipes §7's backup/restore entries.
  Fixed to `(crontab -l; echo X) | crontab -`; VM crontab rebuilt with all
  three entries active.

**Remains VPS-only (cannot run locally — no public DNS/LE):** real Let's
Encrypt issuance for `agente.` + `panel.lumat.cl`, `certbot renew --dry-run`,
SMTP alert delivery (monitor failure path), and all real credentials
(`infra/.env` on the server). See `docs/hardening.md` §4/§8 + §2.9 release
record.

### 2.2 Rollback — previous tag + compose restart

```bash
cd /opt/lumat
sudo -u deploy git checkout <previous-tag>   # the last known-good tag
GIT_SHA="$(sudo -u deploy git rev-parse --short HEAD)"
sudo -u deploy docker build -f infra/nginx/Dockerfile -t lumat-nginx:prod .
sudo -u deploy docker run --rm lumat-nginx:prod nginx -t
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T api sh -c \
  'DATABASE_URL=postgresql://lumat:$POSTGRES_PASSWORD@db:5432/lumat db/migrate.sh'
```

The checkout and rebuild restore the nginx image, embedded SPA bytes, routing,
and legacy `/panel/` proxy behavior from the known-good tag. This is a code and
static-artifact rollback only: never roll back database data or an already-run
schema migration. Re-run §2.1.2 and record the incident in §3.

**Rule: never roll back a schema migration that already ran** (the app
migrates forward only). If the bad release included a migration, roll back
code to the previous tag, then run the forward migration manually via
`db/migrate.sh` before restarting the api — data is never reverted, only code.
Record the incident in the runbook log (§3).

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
docker exec lumat-db-1 sh -c 'gunzip -c < /backups/'"$(basename "$DUMP")" \
  '| psql -U lumat -d lumat_restore_test'
docker exec lumat-db-1 psql -U lumat -d lumat_restore_test -Atc \
  'SELECT count(*) FROM customers;'          # matches production count
docker exec lumat-db-1 psql -U lumat -c 'DROP DATABASE lumat_restore_test;'
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
docker exec lumat-db-1 psql -U lumat -d lumat -c \
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
docker exec lumat-db-1 psql -U lumat -d lumat -c \
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
incident + resolution in §3.

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

### 2.9 Release record

One row per deploy; it is the evidence that the tagged release is in production.

Production ran untagged from 2026-09-08 until `v2026.09.1` was created
retroactively on 2026-09-20, and the previous one-time form of this record was
never filled in. The baseline row is therefore the first recorded entry: its
smoke results and operator were never recorded, and they are left unknown rather
than inferred.

| Deploy tag | Commit | Date | Operator | Smoke (`/health` version + commit, webhook verify, monitor) | Rollback tag | Incidents |
|------------|--------|------|----------|------------------------------------------------------------|--------------|-----------|
| `v2026.09.1` | `10165a6d` | 2026-09-08 | not recorded (tag created 2026-09-20) | not recorded | — (first tag) | — |
| `v2026.09.2` | `cfbefcbd` | 2026-09-22 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.09.2","commit":"cfbefcbd"}`; webhook verify echoed the challenge; panel shell + manifest + `sw.js` + a hashed asset → 200; `monitor.sh` → health=OK, webhook_probe=OK, **backup_age=FAIL** (§3) | `v2026.09.1` (`10165a6d`) | Catch-up deploy: 11 migrations applied (schema 018 → 029), explicit re-run proved idempotent, seed idempotent. Pre-deploy dump taken by an alternative route and restore-verified, because §2.1's `backup.sh` cannot run as `deploy` (§3). The `nginx -t` step in §2.1 fails when run standalone and only passes inside the compose network. |

### 2.10 Spec part-status convention

The convention is one `Status:` line inside each existing spec. There is no
parallel artifact, so the status cannot drift from the spec.

- `released-in-prod` — deployed and running in production.
- `contract-complete` — implemented and verified in the repository, not yet deployed.
- `in-flux` — still being changed, not stable.
- `deferred` — deliberately postponed.

Applying this line to existing specs retroactively or only to future work is
still an open decision and is not part of this runbook.

---

## 3. Runbook incident + change record

### Incidents

| Date | Incident | Resolution | Operator |
|------|----------|------------|----------|
| 2026-09-22 | The backup/monitor tooling is non-functional on the VPS. `infra/backup.sh` fails as `deploy` (`Permission denied` writing to the root-owned `lumat_backups` mountpoint), so the volume existed but was empty; `infra/restore-test.sh` cannot read that path either; `infra/monitor.sh` reports `backup_age=FAIL` for the same reason and cannot send alerts (`SMTP_HOST` unset — it does not load `infra/.env`); and no backup/restore/monitor crons are installed (only `lumat-certbot-renew.timer` exists). `lumat-certbot-renew.service` has been failing since 2026-09-21 on its `nginx -s reload` post step; the certificate expires 2026-12-07. | Unresolved. The `v2026.09.2` deploy proceeded only after a pre-deploy dump was taken by an alternative route (docker `pg_dump` piped into a root container writing the `lumat_backups` volume) and restore-verified into a scratch database. The scripts and the crons must be fixed and armed under root before go-live. | agent-assisted |

### Change log

| Date | Change | Operator |
|------|--------|----------|
| 2026-08-16 | T7.2 — §2.1 deploy flow updated (`--project-name lumat`, containerized migrate/seed via `docker compose exec api`); §2.1.1 rehearsal record (clean-deploy simulation on the local VM, smoke outputs, rehearsal-caught bugs, VPS-only remainder) | dev |
| 2026-09-21 | CalVer release rule; tag-before-deploy; `GIT_SHA` build stamp; per-deploy release record; spec part-status convention; repaired incident-record references | dev |
| 2026-09-22 | Catch-up deploy of `v2026.09.2` (`cfbefcbd`) to the VPS: checkout of the tag, `GIT_SHA` stamped build, api + nginx images rebuilt, 11 migrations applied (schema 018 → 029), explicit `db/migrate.sh` re-run proved idempotent, `db/seed.sh` idempotent (4 settings inserted, 14 already present, admin not overwritten), `/health` reports the tag version and the deployed commit, webhook verify handshake echoes the challenge, panel SPA served over TLS. Pre-deploy dump restore-verified. | agent-assisted |
