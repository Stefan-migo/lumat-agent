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
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
# Validate the nginx config INSIDE the compose network. The standalone form
# (`docker run --rm lumat-nginx:prod nginx -t`) can NEVER pass: the server blocks
# proxy to the `api` service name, which does not resolve off the compose
# network, so nginx exits with `host not found in upstream "api"` — a false
# negative that says nothing about the config.
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T nginx nginx -t
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
- [ ] After deploying this worker fix, reload once (or clear site data) in any
  browser stranded by the old worker; the page that would re-register the
  worker is the page that never renders, and the fixed worker then stays current.
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
- [ ] Confirm the deployed KB matches `docs/kb` (§2.5): run the seed in report
  mode against the release and require `kb · consistente con docs/kb`. A release
  whose documents drifted ships prose that contradicts the configuration.

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
sudo -u deploy env GIT_SHA="$GIT_SHA" docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml up -d --build
sudo -u deploy docker compose --project-name lumat -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml exec -T nginx nginx -t
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

**Where the customer KB comes from.** The customer-facing knowledge base is
`docs/kb/*.md` in the repository, seeded into the database by
`scripts/seed_kb_docs.py`. Production therefore has two copies of the same text
(the file and the `kb_documents` row) and they drift silently: a deployed
release can answer with prose that contradicts the settings the rest of the bot
obeys. Treat the file as the source and the row as a cache.

```bash
# On the server (or in the local harness container). Report only: no writes.
cd /opt/lumat && sudo -u deploy docker compose --project-name lumat \
  -f infra/docker-compose.yml -f infra/docker-compose.prod.yml \
  exec api uv run python scripts/seed_kb_docs.py

# Apply: create missing documents, re-version drifted ones, repair lost routing.
cd /opt/lumat && sudo -u deploy docker compose --project-name lumat \
  -f infra/docker-compose.yml -f infra/docker-compose.prod.yml \
  exec api uv run python scripts/seed_kb_docs.py --apply --force
```

Read the exit code, never the prose alone: `0` means consistent, `1` means the
report found something to fix. `--force` authorizes both writes that change a
stored document — a new version for drifted content, and an in-place rewrite of
routing metadata (`source_meta.source_id`) for a document whose text already
matches. The second is why a re-seeded document can go from answering to saying
"No tengo ese dato": topic routing filters on that key, and without it the turn
falls back to the similarity threshold.

Do not hand-edit a seeded document in the panel KB manager. The panel takes the
same path (`kb.update_document`, which now inherits the routing metadata), but
the next seed run sees the row as drifted from the file and re-versions it back:
the edit is lost and the incident costs an hour to reconstruct. Document a new
fact by editing `docs/kb/*.md` and committing it.

**Values belong to the settings, not to the prose.** Prices
(`tarifa.precios`), covered communes (`coverage.communes`), opening hours
(`hours.schedule`) and service durations (`booking.service_durations`) are
configured in the panel and are read by the deterministic nodes
(`app/chat/nodes/configured_answers.py` for coverage, hours and durations;
`respond.tariff_price_reply` for prices). Prices were migrated out of the KB
first; `odd/agenda-config-fuente` finished the job for the other three, so the
customer documents now hold the **policy** (an advisor coordinates Sundays,
holidays and out-of-hours visits, what each service includes, emergencies) and
no configured value.

`scripts/kb_doc_drift.py` is the control, and its baseline
(`docs/kb/drift-baseline.json`) is now **empty**, which is what "tolerance zero"
means: any restatement is a new finding and the command exits 1. When you add a
service duration or a commune in the panel, do not write it into a KB document —
the answer already comes from the setting. A value the configuration does not
hold is never invented: an empty window, or a service with no configured
duration, keeps the KB path for that question.

Other documents (internal visibility, project uploads) still go through the
panel route `POST /panel/kb`; every ingest writes an `audit_log` row
(`kb.document_ingest`, actor + action + timestamp — SH-5) and both the panel and
the seed path record a metadata repair as `kb.document_metadata`.

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

**Opening hours are two decisions on one window.** `hours.schedule` is the only
source of truth for when a visit can be booked: `open_slots_for_assignment`
offers nothing outside it, and a visit has to fit entirely before closing (a
60-minute service is not offered at 17:30 when the window closes at 18:00). An
empty schedule means "no restriction" and is what every deployment ships with.

Silencing the chat outside those hours is a **separate, opt-in switch**:
`hours.closure_enabled`, `false` by default. With it off the bot answers at any
hour and only the booking offers respect the window; with it on, a message
outside the window gets `messages.out_of_hours` and no conversation runs.

**The panel cannot flip it, on purpose.** The panel sets values, never a switch
(`tests/functional/test_invariant_contract.py`), and this one changes whether
customers get an answer at all. It is an operator action, here:

```bash
# turn the out-of-hours closure on (default is off). Back it up first.
docker exec lumat-db-1 psql -U lumat -d lumat -c \
  "SELECT value FROM settings WHERE key='hours.closure_enabled';"
docker exec lumat-db-1 psql -U lumat -d lumat -c \
  "INSERT INTO settings (key, value) VALUES ('hours.closure_enabled', 'true'::jsonb)
   ON CONFLICT (key) DO UPDATE SET value = 'true'::jsonb;"
```

A psql write bypasses the `settings.change` audit that the panel route records:
note the change and its reason in the release record (§2.9). The panel still
SHOWS the current state in `GET /panel/api/settings` under `hours.closure_enabled`.

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

> Digest content is built by `app.ops.daily_summary.build_digest` and delivered
> to the admin by the `admin_daily_summary` / `admin_weekly_summary` automation
> recipes via the worker tick. The `.venv`-based standalone form above is the
> original draft and is **not** used (no host `.venv` exists); delivery happens
> through the worker cron installed in §2.8.2 (A1).

### 2.8.1 Appointment reminder sweep cron

Run the durable notification sweep every five minutes so reminders due between
API process starts are delivered. Install it under **`deploy`'s own crontab**
(the app runs in the container; deploys create no host virtualenv) with the
append form — never a replace:

```bash
( crontab -l 2>/dev/null; echo '*/5 * * * * /usr/bin/docker exec lumat-api-1 python -m app.ops.sweep >> /home/deploy/lumat-sweep.log 2>&1' ) | crontab -
crontab -l
```

> The entry this section first documented — `cd /opt/lumat && .venv/bin/python
> -m app.ops.sweep >> /var/log/lumat-sweep.log` — could never have run. Three
> reasons, all confirmed on the VPS on 2026-09-29: (1) deploys are containerized
> (§2.1) and **no host `.venv` exists**, so `.venv/bin/python` is not a path; (2)
> `/var/log` is root-only and `deploy` has no passwordless sudo, so the redirect
> fails before the command executes — a cron that looks installed and silently
> does nothing; (3) `docker compose … exec` is not a substitute either, because
> the prod compose files **require `GIT_SHA`** for every invocation, so a bare
> `docker compose` call in cron aborts on interpolation. `docker exec lumat-api-1`
> sidesteps all three.

Verification: `crontab -l` shows the entry, and `/home/deploy/lumat-sweep.log`
gains one `Delivered N notification operation(s)` line per run.

### 2.8.2 Automation worker cron (A1)

The worker tick runs `app.ops.worker.run_cycle`, which evaluates the time-offset
and calendar-summary automation recipes (`evaluate_time_triggers`) and drains the
`domain_events` outbox. Without it, the **time- and calendar-driven** recipes
never fire in production, and the daily/weekly admin digests (§2.8) are never
delivered. Event-driven recipes do not depend on this cron — they are evaluated
by the api pipeline. Install it under **`deploy`'s own crontab** with the append
form — never a replace, and never `docker compose … exec` (§2.8.1):

```bash
( crontab -l 2>/dev/null; echo '*/5 * * * * /usr/bin/docker exec lumat-api-1 python -m app.ops.worker >> /home/deploy/lumat-worker.log 2>&1' ) | crontab -
crontab -l
```

Verification: `crontab -l` shows the entry, and `/home/deploy/lumat-worker.log`
gains one `worker cycle: processed=… pending=… failed=… leased=…` line per run
(the summary line was added to `main()` in `v2026.10.2`; earlier images emitted
nothing). The runner requires the deployed image to carry both
`app/ops/worker.py` and `app/services/time_triggers.py` — the latter first shipped
in `v2026.10.2`, so on `v2026.10.1` and earlier this cron is a no-op for the
time/calendar recipes.

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

| `v2026.09.3` | `77961c29` | 2026-09-23 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.09.3","commit":"77961c29"}`; WhatsApp end-to-end verified. **The §2.1.2 panel SPA smoke was skipped and `monitor.sh` was not run**, so no panel result was ever recorded. | `v2026.09.2` (`cfbefcbd`) | Row backfilled 2026-09-23 from the session record (it was deployed without a record). Skipping the panel smoke is what let the blank-screen defect reach production: the first case with no service made the panel blank (`motivos: [[null, 1]]`), fixed in `v2026.09.4`. |
| `v2026.09.4` | `12ccfd43` | 2026-09-23 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.09.4","commit":"12ccfd43"}`; webhook handshake echoed `12345` over `VERIFY_TOKEN` (200); authenticated `/panel/api/kpis` → `motivos=[["sin clasificar",1]]`, no null service; shell, hashed css/js, `manifest.webmanifest` and `sw.js` → 200; a deep link below `/panel/app/` → 200 shell; `export/clients.csv` → `text/csv`; headless Chrome: the authenticated shell renders (`#root` populated, zero uncaught exceptions), and an offline reload serves the shell while `/panel/api/` fails closed rather than from cache; `Page.getAppManifest` + `getInstallabilityErrors` → no errors. Root's `monitor.sh` cron → health=OK, webhook_probe=OK, backup_age=OK (`lumat-20260923T030002Z.sql.gz`). | `v2026.09.3` (`77961c29`) | No migrations (`migrations up to date`); `db/seed.sh` idempotent (4 settings inserted, 18 already present, `admin` not overwritten). The first full §2.1.2 panel smoke since `v2026.09.2`. `monitor.sh` run as `deploy` exits 6 on a `backup_age=FAIL` permission false negative, and its alert cannot be delivered — see §3. |
| `v2026.09.5` | `5fcde80b` | 2026-09-23 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.09.5","commit":"5fcde80b"}`; webhook verify handshake echoed `12345`; `nginx -t` inside the compose network → syntax ok; `db/migrate.sh` re-run → `migrations up to date`; `db/seed.sh` → 0 inserted, 22 already present, `admin` not overwritten; the assistant configuration loads **inside the deployed image** (`load_assistant_config()` → persona 1194 chars, prompts `classify`/`plan`/`respond`, 22 tools); authenticated `GET /panel/api/assistant/capabilities` → 200, 22 tools; api logs clean since the recreate. **Not run in this deploy: the §2.1.2 panel SPA checklist, `monitor.sh`, and a live assistant conversation turn** — see the incident row below. | none exists on this path — see the incident row below | The first deploy of the window that ships `agent/`. `v2026.09.1`–`v2026.09.4` fail identically on the assistant path, so this release is forward-only. The outstanding end-to-end confirmation is one real assistant turn, which the owner runs from the panel. |
| `v2026.09.6` | `665e92b0` | 2026-09-25 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.09.6","commit":"665e92b0"}`; webhook verify handshake echoed `12345` (200); `nginx -t` inside the compose network → syntax ok; `db/migrate.sh` re-run → every migration skipped, `migrations up to date`; `db/seed.sh` → 0 inserted, 22 already present, `admin` not overwritten; the assistant configuration loads **inside the deployed image** (registry with 5 sub-agents; `load_assistant_config()` → persona 1599 chars, prompts `classify`/`plan`/`respond`, 23 tools) and authenticated `GET /panel/api/assistant/capabilities` → 200 with 23 tools; api logs clean since the recreate; the full §2.1.2 panel checklist passed on `panel.lumat.cl` (login, shell, front-end deep link, hashed shell assets, `GET /panel/api/kpis` → `motivos=[["sin clasificar",2]]`, `panel/export/clients.csv` → `text/csv`, headless-Chrome authenticated render showing the new **Conversaciones** section with zero uncaught exceptions, offline reload serving the shell while `/panel/api/` fails closed). **Not run: `monitor.sh` as `deploy`** (root-only, known false negative, §3) **and a live assistant conversation turn**, which stays the owner's action from the panel. | `v2026.09.5` (`5fcde80b`) | First release cut from a green `main`: the merge of #355 had left `main` red on a time-dependent out-of-hours test that fails inside the last minute of a UTC day, fixed in PR #356 before the tag. No migrations — the schema was already at 031 since `v2026.09.5`, so the rollback is code-only (§2.2) and no data was at risk; no pre-deploy dump was taken because `deploy` has no passwordless sudo and `infra/backup.sh` needs root. The panel root `favicon.ico` still 404s (cosmetic). |
| `v2026.09.7` | `3dcae195` | 2026-09-29 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.09.7","commit":"3dcae195"}`; webhook verify echoed `12345` (200); schema 031 → 038 — 7 migrations applied (032–038) and the explicit `db/migrate.sh` re-run reported `migrations up to date`; `db/seed.sh` → 3 settings inserted, 22 already present, `admin` not overwritten; panel shell, a client-side deep link, `manifest.webmanifest`, `sw.js` and one hashed asset → 200; the sweep cron was installed under `deploy`'s crontab and **observed firing on its own**. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.09.6` (`665e92b0`) | First deploy carrying `agenda-agente-whatsapp` S1–S5. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 387K, gzip-verified) because `infra/backup.sh` needs root; the DB held 2 customers / 48 messages. The sweep cron had never been installed (`deploy` had no crontab at all) and §2.8.1's documented entry could never have run — corrected there. |
| `v2026.10.1` | `d9609621` | 2026-10-09 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.1","commit":"d9609621"}`; webhook verify echoed `12345` (200); `nginx -t` inside the compose network → syntax ok; schema 038 → 046 — 8 migrations (039–046) applied on the api start and the explicit `db/migrate.sh` re-run reported `migrations up to date`; `db/seed.sh` → 0 inserted, 25 already present, `admin` not overwritten; panel shell, a client-side deep link, `manifest.webmanifest` and `sw.js` → 200. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.09.7` (`3dcae195`) | Catch-up of 125 PRs / 864 commits since `v2026.09.7`: project-scoped Asistente Lumat (A1–A6), the panel redesigns (Conversaciones, Clientes, Configuración, Agenda, Dashboard, Usuarios, shell/design system), the KB redesign, the chatbot intake redesign (CI-1–CI-5), panel notifications, the automation recipe catalog (Slice 1) and post-visit follow-ups. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 387K, gzip-verified) because `infra/backup.sh` needs root. |
| `v2026.10.2` | `668bcba1` | 2026-10-13 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.2","commit":"668bcba1"}`; webhook verify echoed `12345` (200); `nginx -t` inside the compose network → syntax ok; schema 046 → 049 — 3 migrations (047–049) applied on the api start and the explicit `db/migrate.sh` re-run reported `migrations up to date`; `db/seed.sh` → 1 setting inserted, 25 already present, `admin` not overwritten; panel shell, `manifest.webmanifest` and `sw.js` → 200; verified inside the deployed image that `app.services.time_triggers` and `app.ops.worker.run_cycle` import. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.1` (`d9609621`) | Carries the automation **time-offset and calendar recipes** (they need the worker tick) plus the A1 worker-cron prerequisite: the image now ships `app/services/time_triggers.py` and `worker.main()` logs a summary line, so the runner is verifiable. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 3.4 MB, gzip-verified) because `infra/backup.sh` needs root. The **A1 worker cron was installed under `deploy`'s crontab (§2.8.2) and observed firing on its own** (14:10 UTC tick); its first manual run drained 25 pending `domain_events` (0 failed). No `automation_installations` existed at deploy time, so no recipe was exercised end to end. |
| `v2026.10.3` | `dd6476bc` | 2026-10-13 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.3","commit":"dd6476bc"}`; webhook verify echoed `12345` (200); `nginx -t` inside the compose network → syntax ok; no new migrations (`migrations up to date`, schema at 049); `db/seed.sh` → 0 inserted, 26 already present, `admin` not overwritten; panel shell, `manifest.webmanifest`, `sw.js` and the SPA's hashed `index-CeQVdqYV.js` → 200. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.2` (`668bcba1`) | Frontend-only release: the Asistente Lumat **phone layout** (PR #577) — mobile control header, navigation/project/thread-detail sheets, phone composer. No backend or migration changes; the api image was rebuilt only for the version stamp, so the rollback is code-only (§2.2). Pre-deploy dump taken as `deploy` (3.47 MB, gzip-verified). The A1 worker cron (§2.8.2) keeps running across the api recreate. |
| `v2026.10.4` | `c6142845` | 2026-10-14 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.4","commit":"c6142845"}`; webhook verify echoed `12345` (200) and a wrong token returned 403; `nginx -t` inside the compose network → syntax ok; schema 049 → 053 — 4 migrations (050–053) applied on the api start and the explicit `db/migrate.sh` re-run reported `migrations up to date`; `db/seed.sh` → 2 settings inserted, 26 already present, `admin` not overwritten; panel shell, `manifest.webmanifest` and `sw.js` → 200. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.3` (`dd6476bc`) | Carries the panel-configurable **model API key** (encrypted store, hot resolution, admin API + Settings UI), the **Tukulpan memory** handoff slices, the chatbot **preset message catalog**, read-only chatbot metrics, the panel KB/user/case CRUD controls, and the WhatsApp conversation + first-turn greeting fixes. First release with the `panel_secrets` schema (migration 053). Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 3.4 MB, gzip-verified). The A1 worker cron (§2.8.2) keeps running across the api recreate. |
| `v2026.10.5` | `267146e2` | 2026-10-17 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.5","commit":"267146e2"}`; webhook verify echoed `12345` (200) and a wrong token → 403; `nginx -t` inside the compose network → syntax ok; schema **053 → 057** — 4 migrations (054–057) applied on the api start and the explicit `db/migrate.sh` re-run skipped all of them (`migrations up to date`); `db/seed.sh` → 5 settings inserted, 28 already present, `admin` not overwritten; panel shell, `manifest.webmanifest` and `sw.js` → 200; the deployed bundle carries the new **Correo** settings tab (`index-CsgkTgNX.js` contains `Servidor SMTP`, `Guardar correo`, `Guardar contraseña`) and the five `notify.smtp_*` settings exist with defaults. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.4` (`c6142845`) | Carries the WU-E **configurable SMTP email** and its Correo tab, the **technician field workflow** (quick actions, cooldown, visit close, office semaphore, customer phone dropped from the technician contract), **Meta template delivery** for automation recipes plus reminder/follow-up in the recipe engine and recipe uninstall, the assistant **config layer** (project-scoped personality/response/memory/KB/skills/agents/planning, opt-in tools on by default), assistant **write chaining** (re-enter after an approved write, fresh approval per step, terminal rejection, chain timeline), **project folders**, chatbot metrics/inspection/settings-write tooling, and the role-scoped panel shell. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 423K, gzip-verified; prod holds 3 customers / 13 cases / 153 messages, and its KB is down to the 2 global documents after the owner deleted 29 on 2026-10-14, audited as `kb.document_delete`). The A1 worker cron (§2.8.2) keeps running across the api recreate. |
| `v2026.10.6` | `0a0de247` | 2026-10-22 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.6","commit":"0a0de247"}`; verified inside the deployed image that `version` is `2026.10.6` and that `is_explicit_human_request` and `retrieve_chunks` are present; explicit `db/migrate.sh` re-run → `migrations up to date`; api healthy. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in that session; root-only false negative, §3). | `v2026.10.5` (`267146e2`) | Row backfilled on 2026-10-27 from the session record, because this deploy was made **without a §2.9 row**: no pre-deploy dump, seed output or panel result was recorded. Carried the 16 PRs since `v2026.10.5` — the chatbot retrieval fix for service queries, the message-catalog slot documentation and the `chatbot-config-model` T19 slices. No migrations (`git diff v2026.10.5..v2026.10.6 -- db/` is empty), so the rollback was code-only (§2.2). |
| `v2026.10.7` | `e884dcf5` | 2026-10-27 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.7","commit":"e884dcf5"}`; webhook verify handshake echoed `12345` (200) and a wrong token returned 403; `nginx -t` inside the compose network → syntax ok; schema **057 → 058** — `058_message_media` applied on the api start, the explicit `db/migrate.sh` re-run skipped every migration (`migrations up to date`) and the seven media columns (`stored_path`, `content_type`, `filename`, `size_bytes`, `caption`, `media_attempts`, `meta_media_id`) exist on `messages`; `db/seed.sh` → 10 settings inserted, 30 already present, `admin` not overwritten; panel shell, `manifest.webmanifest`, `sw.js` and the hashed `index-ChAMrEME.js` → 200; api logs since the recreate carry 0 error/traceback lines; inside the deployed image `app.chat.phrasing` and `app.chat.human_request` import and both operator media routes are registered (`/conversations/{id}/media`, `/conversations/{id}/messages/{mid}/media`). **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.6` (`0a0de247`) | The 42 PRs / 301 commits since `v2026.10.6`: the conversation evaluator, WhatsApp media in the human thread (migration 058), the Configuración super-sections and their redesigns, and the chatbot conversation fixes. Cut through PR #706 (`test` 4m58s + `panel` 2m52s green, GitGuardian pass) with the tag **before** the deploy; the tagged tree `2300de2f` is identical to the tested cut tree. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 737K, gzip-verified; prod held 4 customers / 17 cases / 253 messages / 21 conversations / 636 `audit_log` rows). `chat.conduct` is deliberately absent from `settings`: it is read with `default={}`, not a seeded key. Migration 058 is additive and must not be rolled back (§2.2) even though it is the only schema change. |
| `v2026.10.8` | `45bf8d55` | 2026-10-28 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.8","commit":"45bf8d55"}`; webhook verify handshake on the documented route (`/webhook/whatsapp`) echoed `12345`; `nginx -t` inside the container → syntax ok; schema stayed at **058** (no new migration) and the explicit `db/migrate.sh` re-run — with the admin `DATABASE_URL` the runbook uses — skipped every migration (`migrations up to date`); `db/seed.sh` → 1 setting inserted, 40 already present, `admin` not overwritten; panel shell, `manifest.webmanifest` and `sw.js` → 200; the knowledge base was realigned and re-checked from inside the deployed image: `seed_kb_docs.py` reported `consistente con docs/kb`, listed the 4 documents that had lost topic routing, and `--apply --force` reported `creados 0 · actualizados 0 · reparados 4` with the same 296 chunks and the same fingerprint before and after (metadata repair, no re-embed, no new version). **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.7` (`e884dcf5`) | The 13 PRs since `v2026.10.7`: the booking preference (day and franja), the assistant panel changes and the planning retirement, KB topic routing surviving a re-version, the drift control plus the release check that can finally run in the deployed image, and the business window that narrows offers. **Two records worth keeping:** (1) the four customer documents were renamed to their repository headings with `UPDATE kb_documents SET title=...` — a psql write, so it left **no `audit_log` row**; this table is its only record; (2) the post-deploy probe `retrieve(..., source_ids=[...])` returned **0 chunks while the filter matched 2**, because pgvector's HNSW scan returns `hnsw.ef_search` neighbours before the `WHERE` applies and one 258-chunk document dominated the neighbourhood; `enable_indexscan = off` returned the 2 rows. Fixed in `v2026.10.9` (PR #721), not in this tag. Pre-deploy dump as `deploy` (`lumat-predeploy-20261028T193429Z.sql.gz`, 735K, `gzip -t` verified; prod held 4 customers / 22 conversations / 279 messages / 11 appointments / 18 cases). |
| `v2026.10.9` | `605ea491` | 2026-10-28 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.9","commit":"605ea491"}`; webhook verify on the documented route echoed `12345`; `nginx -t` inside the container → syntax ok; schema stayed at **058**, the `db/migrate.sh` re-run skipped every migration (`migrations up to date`); panel shell, `manifest.webmanifest` and `sw.js` → 200; api healthy 11s after the recreate. **The verification this tag exists for:** the topic-filtered retrieval probe that returned 0 on `v2026.10.8` now returns **2 of 2** matching chunks — `retrieve(..., source_ids=[...])` → 2 and `retrieve_for_queries` (the path the chat uses) → 2 — and the KB seed report still reads `consistente con docs/kb` with the same 296 chunks and fingerprint `49563716dcce`. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.8` (`45bf8d55`) | Patch over `v2026.10.8` carrying PR #721 (the filtered retrieval fix) and PR #722 (the `v2026.10.8` release record). No migrations, no settings changes, no data change: the api image is the only thing that moved, and nginx was left running because this commit does not touch the SPA. Pre-deploy dump as `deploy` (`lumat-predeploy-20261028T202116Z.sql.gz`, 736K, `gzip -t` verified). Rollback is code-only (§2.2). |

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

| 2026-09-23 | The §2.1.2 smoke command `sudo -u deploy /opt/lumat/infra/monitor.sh` can never exit 0. `infra/monitor.sh:40` resolves the `lumat_backups` volume mountpoint, which is root-owned and unreadable by `deploy`, so `ls` finds no dump, `backup_age=FAIL` is reported and the run exits 6. Observed during the `v2026.09.4` deploy. The same script run by root's cron is green: `/var/log/lumat-monitor.log` has a five-minute entry since 2026-09-22 with zero ALERT lines. | Not a production fault — a permission false negative in the documented smoke command, the same class as the `nginx -t` standalone note in §2.1. Recorded so the next deploy does not read it as an outage. The check should be run as root, or replaced in §2.1.2 by reading the cron log; the command is left as-is here because its correct root form could not be exercised from a `deploy` session. | agent-assisted |
| 2026-09-23 | The monitoring alert path cannot deliver. `/opt/lumat/infra/.env` on the VPS still carries the placeholder `SMTP_HOST=change-me-smtp-host`, so on any failed check `monitor.sh` dies with `curl: (6) Could not resolve host: change-me-smtp-host`. Observed live during the `v2026.09.4` deploy, when the deploy-run monitor tried to alert on the false negative above. No real alert has ever been sent: the cron log shows zero ALERT lines since 2026-09-22. | Unresolved — it needs the owner's real SMTP host and credentials in the server environment; the repository cannot supply them and inventing one would be worse than the gap. This qualifies the 2026-09-22 incident row above: the `infra/.env` loading fix does work, but the value it loads is still a placeholder, so "alerts can actually be sent" is not yet true. | agent-assisted |
| 2026-09-23 | The assistant could not answer in production for the whole `v2026.09.1`–`v2026.09.4` window. The prod image never shipped `agent/`, so `app/agent_registry.py:223` resolved `/app/agent/registry.yaml` to nothing and `load_registry()` raised `registry file not found` on every turn; the panel answered with the raw error plus "No se pudo procesar el mensaje". Not a boot failure — `build_graph()` runs per message (`app/chat/graph.py:300`) — and invisible to the deploy smoke, which has no assistant-turn probe. `prompts.load()` masked the same missing tree on its own path by silently serving its literal `FALLBACKS`. | Fixed in `v2026.09.5` (`COPY agent/ agent/` in the prod `Dockerfile`, plus a regression test asserting the image ships every repo-root path the runtime resolves). **Forward-only: there is no known-good tag to roll back to on this path**, because the prod Dockerfile never contained `agent/`. Still open: the smoke needs an assistant-turn probe (§2.1), and the first real conversation after this deploy is the outstanding end-to-end confirmation. | agent-assisted |

### Change log

| Date | Change | Operator |
|------|--------|----------|
| 2026-08-16 | T7.2 — §2.1 deploy flow updated (`--project-name lumat`, containerized migrate/seed via `docker compose exec api`); §2.1.1 rehearsal record (clean-deploy simulation on the local VM, smoke outputs, rehearsal-caught bugs, VPS-only remainder) | dev |
| 2026-09-21 | CalVer release rule; tag-before-deploy; `GIT_SHA` build stamp; per-deploy release record; spec part-status convention; repaired incident-record references | dev |
| 2026-09-22 | Catch-up deploy of `v2026.09.2` (`cfbefcbd`) to the VPS: checkout of the tag, `GIT_SHA` stamped build, api + nginx images rebuilt, 11 migrations applied (schema 018 → 029), explicit `db/migrate.sh` re-run proved idempotent, `db/seed.sh` idempotent (4 settings inserted, 14 already present, admin not overwritten), `/health` reports the tag version and the deployed commit, webhook verify handshake echoes the challenge, panel SPA served over TLS. Pre-deploy dump restore-verified. | agent-assisted |
| 2026-09-22 | Repaired the two continuity mechanisms the deploy pre-flight found dead, on the VPS: root's backup/restore/monitor crontab installed (it had never existed), `monitor.sh` run with `infra/.env` loaded so alerts can actually be sent, and the certbot renewal unit corrected (`--project-name lumat` + `git safe.directory`). Verified: `backup OK` + `restore OK`, monitor exit 0 with all three checks green, unit `result: success`, and `certbot renew --dry-run` reporting `all simulated renewals succeeded` for both SANs. The same defects are fixed in this repo (§2.1, `infra/certbot/`, `infra/monitor.sh`, `docs/hardening.md` §7) so a re-provision cannot reproduce them. | agent-assisted |
| 2026-09-23 | Deploy of `v2026.09.4` (`12ccfd43`): the fix for the panel blank screen — a case with no service published `NULL` in the KPI `motivos`, the dashboard threw on it, and with no SPA error boundary one field blanked the whole panel. No migrations; seed idempotent. §2.1.2 was run in full for the first time since `v2026.09.2` (HTTP surfaces, authenticated API, headless-Chrome render, offline shell, PWA installability), the `v2026.09.3` release-record row was backfilled, and the monitor's deploy-run false negative plus the undeliverable alert path were recorded in §3. | agent-assisted |
| 2026-09-23 | Deploy of `v2026.09.5` (`5fcde80b`): the prod image now ships `agent/`, fixing the assistant outage that broke every turn across `v2026.09.1`–`v2026.09.4`. api + nginx images rebuilt with the `GIT_SHA` stamp; api recreated and healthy. Verified inside the container that the registry and the full assistant configuration load, and over HTTP that the authenticated capabilities endpoint returns 22 tools. No migrations; seed idempotent. The §2.1.2 panel checklist, `monitor.sh`, and a live conversation turn were **not** run in this deploy and are recorded as outstanding in §2.9. | agent-assisted |
| 2026-09-25 | Deploy of `v2026.09.6` (`665e92b0`), the 301 commits `main` held over `v2026.09.5`: the Conversaciones redesign, the Agenda alignment, the page-frame action guard, the 200% text-zoom reflow fix and `assistant-web-fetch` reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; no migrations (schema already at 031); seed idempotent. The full §2.1.2 panel checklist ran and passed, including the headless-Chrome authenticated render and the offline shell; the assistant was verified inside the deployed image and over the authenticated capabilities endpoint. `main` was red when this release started: the merge of #355 had tripped a time-dependent out-of-hours test, fixed in PR #356 and merged before the tag. | agent-assisted |
| 2026-09-29 | Deploy of `v2026.09.7` (`3dcae195`), the first release carrying the `agenda-agente-whatsapp` unit end to end (S1–S5: autonomous booking, cancel/reschedule from WhatsApp, the 24 h reminder, and the post-service follow-up). api + nginx images rebuilt with the `GIT_SHA` stamp; 7 migrations applied (schema 031 → 038), the explicit re-run proved idempotent, seed idempotent. The §2.1.2 checklist ran for its HTTP surfaces (shell, deep link, manifest, `sw.js`, hashed asset) but **not** the authenticated API call or the headless-Chrome render. §2.8.1's cron entry was corrected — it could never have run — and the sweep cron was installed under `deploy`'s crontab for the first time and observed firing. | agent-assisted |
| 2026-10-09 | Deploy of `v2026.10.1` (`d9609621`), the catch-up of 125 PRs / 864 commits since `v2026.09.7`: project-scoped Asistente Lumat (A1–A6), the panel redesigns (Conversaciones, Clientes, Configuración, Agenda, Dashboard, Usuarios, shell/design system), the KB redesign, the chatbot intake redesign (CI-1–CI-5), panel notifications, the automation recipe catalog (Slice 1) and post-visit follow-ups reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; 8 migrations applied (schema 038 → 046), the explicit re-run proved idempotent, seed idempotent. The §2.1.2 checklist ran for its HTTP surfaces (shell, deep link, manifest, `sw.js`) but **not** the authenticated API call or the headless-Chrome render. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 387K, gzip-verified). | agent-assisted |
| 2026-10-13 | Deploy of `v2026.10.2` (`668bcba1`), the 231 commits since `v2026.10.1`: the automation catalog's time-offset and calendar recipes, the Asistente Lumat redesign, per-technician Agenda schedules, panel web push, the Conversaciones queue change, and the worker-cron logging line reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; 3 migrations applied (schema 046 → 049), the explicit re-run proved idempotent, seed idempotent. The §2.1.2 checklist ran for its HTTP surfaces (shell, manifest, `sw.js`) but **not** the authenticated API call or the headless-Chrome render. Pre-deploy dump taken as `deploy` (3.4 MB, gzip-verified). The **A1 worker cron was installed (§2.8.2) and observed firing on its own**; its first manual run drained 25 pending `domain_events`. | agent-assisted |
| 2026-10-13 | Deploy of `v2026.10.3` (`dd6476bc`), the 34 commits of the Asistente Lumat **mobile redesign** (PR #577) since `v2026.10.2`: the phone control header, the navigation/project/thread-detail bottom sheets, and the phone composer and empty state reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; no migrations (schema at 049), the explicit re-run confirmed `migrations up to date`, seed idempotent. The §2.1.2 checklist ran for its HTTP surfaces (shell, manifest, `sw.js`, hashed asset) but **not** the authenticated API call or the headless-Chrome render. Pre-deploy dump taken as `deploy` (3.47 MB, gzip-verified). | agent-assisted |
| 2026-10-14 | Deploy of `v2026.10.4` (`c6142845`), the 16 PRs since `v2026.10.3`: the panel-configurable **model API key** (AES-256-GCM encrypted store, hot resolution, admin API and Settings UI), the **Tukulpan memory** handoff slices, the chatbot **preset message catalog**, read-only chatbot metrics, guarded KB/user deletion and reversible closed-case archiving, and the WhatsApp conversation + first-turn greeting fixes reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; 4 migrations applied (schema 049 → 053), the explicit re-run proved idempotent, seed idempotent. The §2.1.2 checklist ran for its HTTP surfaces (shell, manifest, `sw.js`) but **not** the authenticated API call or the headless-Chrome render. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 3.4 MB, gzip-verified). | agent-assisted |
| 2026-10-17 | Deploy of `v2026.10.5` (`267146e2`), the 42 PRs since `v2026.10.4`: configurable **SMTP email** with its Correo tab (WU-E), the **technician field workflow** (WU1–WU8: quick actions, resend cooldown, visit close, office semaphore, privacy-scoped contract), **Meta template delivery** for automation recipes with reminders/follow-ups moved into the recipe engine and recipe uninstall, the assistant **config layer** (project-scoped personality/response/memory/KB/skills/agents/planning, opt-in tools on by default), assistant **write chaining** (approved writes re-enter the graph, fresh approval per step, terminal rejection, chain timeline), **project folders**, chatbot metrics/inspection/settings-write tooling, and the role-scoped panel shell reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; 4 migrations applied (schema 053 → 057), the explicit re-run proved idempotent, seed inserted the five `notify.smtp_*` defaults. The §2.1.2 checklist ran for its HTTP surfaces (shell, manifest, `sw.js`) plus a bundle check proving the Correo tab ships, but **not** the authenticated API call or the headless-Chrome render. Pre-deploy dump taken as `deploy` (423K, gzip-verified; the DB's KB holds 2 global documents because the owner deleted 29 on 2026-10-14). | agent-assisted |
| 2026-10-22 | Deploy of `v2026.10.6` (`0a0de247`), the 16 PRs since `v2026.10.5`: the chatbot retrieval fix for service queries, the message-catalog slot documentation and the `chatbot-config-model` T19 slices reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; no migrations (schema already at 057), the explicit re-run confirmed `migrations up to date`. Verified inside the deployed image that the version stamp is `2026.10.6` and that `is_explicit_human_request` and `retrieve_chunks` are present. **Recorded on 2026-10-27**: this deploy shipped with **no §2.9 row and no pre-deploy dump**, so its seed output and panel result were never captured; the row was backfilled from the session record rather than inferred. | agent-assisted |
| 2026-10-27 | Deploy of `v2026.10.7` (`e884dcf5`), the 42 PRs / 301 commits since `v2026.10.6`: the **conversation evaluator** (corpus, runner, deterministic gates plus a rubric judge), **WhatsApp media in the human conversation thread** in both directions with recording and playback, the **Configuración super-sections** (Chatbot / Operación / Integraciones / Costos) with the Agente, Persona, Conducta, Mensajes and Operación redesigns, the capture phrasing switch in the panel, and the **chatbot conversation fixes** (greeting and courtesy as understood turns, one human-request detector, rephrase → two paths → derivation, validated capture with a real consent decision, prices from the tariff, schedule questions mid-capture) reach production. api + nginx images rebuilt with the `GIT_SHA` stamp; migration 058 applied (schema 057 → 058), the explicit re-run proved idempotent, seed inserted 10 defaults. The §2.1.2 checklist ran for its HTTP surfaces (shell, manifest, `sw.js`, hashed asset) but **not** the authenticated API call or the headless-Chrome render. Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump`, 737K, gzip-verified). The missing `v2026.10.6` row was backfilled in the same change. | agent-assisted |
| 2026-10-28 | Deploy of `v2026.10.8` (`45bf8d55`), the 13 PRs since `v2026.10.7`: **booking preference** (the offer respects the day and franja a customer asks for, and rescheduling follows it), the **assistant panel** work (tabs that survive navigation, background runs with an alert, reattach on open) with the **planning feature retired**, **KB topic routing surviving a re-version** (a re-seeded or panel-edited document kept losing `source_meta` and answered "no tengo ese dato" with its own text on screen), the **KB drift control** with its baseline plus the release check that can run inside the deployed image, and the **business window** that narrows offers to what the business sells while out-of-hours closure became an opt-in switch. The customer KB was realigned in production: four titles set to their repository headings (psql, no `audit_log`) and `--apply --force` repaired the topic metadata of all four documents with no re-embed and no new version. The deploy's own verification found that pgvector's HNSW scan starves a filtered search (2 matching rows, 0 returned, 2 with the index disabled); fixed in `v2026.10.9` (PR #721). | agent-assisted |
| 2026-10-28 | Deploy of `v2026.10.9` (`605ea491`), a patch over `v2026.10.8`: the **filtered KB retrieval fix** (PR #721 — the topic search returns the rows its filter matches instead of whatever the HNSW candidate window left behind) plus the **`v2026.10.8` release record** (PR #722). Only the api image moved; nginx stayed up because the SPA did not change. The verification the tag exists for ran in production: the probe that returned **0** chunks with 2 matching rows on `v2026.10.8` now returns **2 of 2**, both through `retrieve` and through `retrieve_for_queries` (the path the chat uses), and the KB seed report remains `consistente con docs/kb` with the same 296 chunks and fingerprint. Pre-deploy dump 736K, `gzip -t` verified; schema unchanged at 058. | agent-assisted |
