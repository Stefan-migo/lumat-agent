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
>
> The block below is written for a **root** shell: `sudo -u deploy …` is how root
> runs a step as the deploy user. If your session already **is** `deploy`, drop the
> prefix — `sudo -u deploy git …` fails with «user deploy is not allowed to execute
> … as deploy», because `deploy`'s sudoers entry only allows `/usr/bin/systemctl`
> and `/usr/bin/docker` (`docs/hardening.md` §3). Drop `sudo` for `git` and for
> `docker` alike: `deploy` is in the `docker` group. Measured on the `v2026.11.20`
> deploy, which spent its first attempt on exactly this.

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

> **Two things the 2026-11-27 deploy had to learn the hard way.** First, every `docker compose` call in prod needs `GIT_SHA` exported, not only the `up`: the file interpolates `services.api.build.args.GIT_SHA`, so even `up -d --no-deps nginx` refuses with `required variable GIT_SHA is missing a value`. Second, `docker build -f infra/nginx/Dockerfile -t lumat-nginx:prod .` followed by `up -d --build` did **not** recreate nginx — it kept the previous container (`Up 6 hours`) while the tag pointed at a new image id, so the release would have gone live on the previous nginx image. Compare `docker inspect lumat-nginx-1 --format '{{.Image}}'` with `docker image inspect lumat-nginx:prod --format '{{.Id}}'`; when they differ run `up -d --force-recreate --no-deps nginx` and then `nginx -t` **inside the new container** (the earlier test only proves the old one). Record the previous image id before recreating: it is the rollback reference.

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

> The `VERIFY_TOKEN` for the verify handshake must come from the **server's**
> `infra/.env`. A local copy belongs to the dev stack and returns `403` — which
> is exactly what a wrong token returns, so the smoke cannot tell a stale local
> token from a real webhook regression. Read it on the host:
> `set -a; . /opt/lumat/infra/.env; set +a` before the `curl`.

> **The panel smoke runs against `panel.lumat.cl`, never `agente.lumat.cl`.** On the bot host,
> `location /panel/` proxies to the api (`infra/nginx/agente.lumat.cl.conf:79`) and the api serves no
> SPA, so `/panel/app/` there answers **404** by design — which reads exactly like a broken release.
> The 2026-11-24 deploy spent a diagnosis on it. The SPA lives in the panel vhost:
> `curl -s -o /dev/null -w "%{http_code}" --resolve "panel.lumat.cl:443:127.0.0.1" https://panel.lumat.cl/panel/app/`.
>
> **Any deploy script fed to the host over `ssh … 'bash -s' < script.sh` needs `</dev/null` on every
> `docker exec` and `docker compose exec`.** Those attach stdin by default, drain the rest of the script
> and leave the shell exiting **0** with the work half done. This was already recorded in §3 on
> 2026-11-19 and it was still paid three times on 2026-11-24 — the pre-deploy dump, the in-image probe
> and the KB queries each truncated while looking like a success — because the warning lived only in the
> change log and not here, where the deploy is actually run.

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
  `curl -fsS https://agente.lumat.cl/health` and the webhook verification probe
  from §2.1. **Do not run `monitor.sh` as `deploy` on a deploy:** its
  `backup_age` probe is root-only and reads a volume `deploy` cannot see, so it
  reports a false negative **and sends a real SMTP alert** for it — measured
  again on 2026-11-26 on `v2026.11.21`, after the same lesson was written into
  the `v2026.11.20` row of §2.9 instead of here. Run its two useful probes by
  hand and record them: `health=OK` and an unsigned webhook POST → `403`. Run
  `sudo -u deploy /opt/lumat/infra/monitor.sh` as root when you actually want
  the freshness check, and treat exit 0 as the acceptance condition there.
- [ ] Confirm the deployed KB matches `docs/kb` (§2.5): run the seed in report
  mode against the release and require `kb · consistente con docs/kb`. A release
  whose documents drifted ships prose that contradicts the configuration.
- [ ] Send a **document larger than 1 MB** from a conversation thread (a PDF is
  the natural case) and confirm it arrives. This is the check that would have
  caught the 1 MB nginx ceiling in §2.1.3, which silently rejected every operator
  upload from the release until 2026-11-09.

Record the tag, timestamp, operator, and any failed check in the release record
(§2.9). These panel checks require the VPS DNS, TLS certificates, and valid
panel credentials; they are not reproducible in the local repository test
environment.

### 2.1.3 Panel upload limits (nginx + api)

The panel's uploads — conversation media (image, video, audio, document), voice
notes and assistant attachments — POST through `location ^~ /panel/api/` in
`infra/nginx/panel.lumat.cl.conf`. **nginx defaults `client_max_body_size` to
1 MB and it is not inherited from anywhere else in this stack**, so that location
carries an explicit `client_max_body_size 100m`.

The api validates again, per type, in `MEDIA_SIZE_LIMITS`
(`app/services/conversations.py`): image 5 MB, video and audio 16 MB, document
100 MB (Meta's own document ceiling). Two consequences worth knowing:

- A file above 100 MB is refused by **nginx with a plain 413**, before auth and
  before any audit row exists. The SPA maps that status to "El archivo supera el
  límite de subida del panel (100 MB)"; if the message ever reads as raw HTML, the
  SPA is older than the api.
- A file between nginx's ceiling and the api's per-type limit is refused by the
  api with a 422 carrying the exact limit (`document file exceeds the 100 MB
  limit`), and the operator sees that text.

Measured 2026-11-09 on production: a 2 MB POST returned `413` after nginx
uploaded ~130 KB, a 200-byte POST returned `401` (reached the api). The only
document delivered before the fix was 121 KB; the operator's attempt never
reached the api and left no trace in `audit_log`.

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
# Call `python`, NOT `uv run`: the deployed image mounts a read-only rootfs and
# `uv run` dies with "failed to write to file /app/uv.lock: Read-only file system"
# (measured on the v2026.11.10 deploy, 2026-11-18) before the script even starts.
cd /opt/lumat && sudo -u deploy docker compose --project-name lumat \
  -f infra/docker-compose.yml -f infra/docker-compose.prod.yml \
  exec api python scripts/seed_kb_docs.py

# Apply: create missing documents, re-version drifted ones, repair lost routing.
cd /opt/lumat && sudo -u deploy docker compose --project-name lumat \
  -f infra/docker-compose.yml -f infra/docker-compose.prod.yml \
  exec api python scripts/seed_kb_docs.py --apply --force
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

**Do not delete the documents and re-upload them either.** Measured on
2026-10-29: `POST /panel/kb` writes no `source_meta.source_id`, so every chunk of
the new version loses topic routing and the bot answers "No tengo ese dato" with
the text in the document. The loss is worse than it looks, because the seed
reports `consistente con docs/kb` and says nothing: `inspect_kb` only lists a
document under `unrouted` when the stored title equals the H1 of the file, so
renaming on the way in (`Lumat Cobertura y Horarios` instead of `Cobertura y
horarios de Lumat`) hides the problem. The version history is gone as well. The
supported path is the two commands above: edit `docs/kb/*.md`, then run the seed
with `--apply --force`. If titles were already changed, set them back to the
file H1s first (`UPDATE kb_documents SET title=...`) and the seed repairs the
routing metadata in place — no re-embed, no new version.

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

### 2.8.3 Panel web push (VAPID)

Web push is optional and never replaces the email/WhatsApp fallback, but when the
operator turns it on from the panel it has to work. Production ran from
`v2026.10.2` (the release that added panel push) until `2026-11-04` with **zero
VAPID keys**: `/opt/lumat/infra/.env` had none, `push_subscriptions` held 0 rows,
and `GET /panel/api/push/config` answered `{"public_key": null}`. The panel read
that as "this browser does not support push", so an operator on current Chrome
was told the browser was the problem. It never was.

Three values live in `infra/.env` (server only, never in the repo, §1.2):

| Key | Value |
|---|---|
| `VAPID_PUBLIC_KEY` | base64url of the uncompressed EC point (87 chars, starts with `B`) — this is what the browser gets as `applicationServerKey` |
| `VAPID_PRIVATE_KEY` | base64url of the **PKCS8 DER**, one single line (184 chars, no PEM header) |
| `VAPID_SUBJECT` | a `mailto:` contact the push service can reach, e.g. `mailto:contacto@lumat.cl` |

Generate them inside the running container, so the key pair never touches a
laptop, and print only the public half:

```bash
docker exec lumat-api-1 python - <<'PY'
import base64
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01
v = Vapid01(); v.generate_keys()
der = v.private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
pub = v.public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)
print("VAPID_PRIVATE_KEY=" + base64.urlsafe_b64encode(der).decode().rstrip("="))
print("VAPID_PUBLIC_KEY=" + base64.urlsafe_b64encode(pub).decode().rstrip("="))
PY
```

The private key must be **written into `infra/.env` without passing through this
command's stdout** (redirect it straight into the file, or paste it in a shell
that does not echo), and `infra/.env` keeps mode `600`.

The api service declares its environment explicitly in `infra/docker-compose.yml`,
so the three keys are forwarded there by name. Adding them only to `.env` is not
enough — that is the second half of this incident. After editing, recreate **only**
api and verify:

```bash
cd /opt/lumat && GIT_SHA=$(git rev-parse HEAD) docker compose --project-name lumat \
  -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d api
docker exec lumat-api-1 sh -lc 'printenv | cut -d= -f1 | grep VAPID'   # three names, no values
cd /opt/lumat && GIT_SHA=$(git rev-parse HEAD) docker compose --project-name lumat \
  -f infra/docker-compose.yml -f infra/docker-compose.prod.yml exec -T api \
  python -c "from app.config import get_settings as g; print(bool(g().vapid_public_key), bool(g().vapid_private_key))"
```

Expected: `True True`. Then the operator opens the panel, presses **Activar
notificaciones**, accepts the browser prompt, and `push_subscriptions` gains one
row per device. A row appearing is the end-to-end proof; the panel saying "Push
activado" without a row means the save route failed, not the browser.

Rotating the keys invalidates every existing subscription: the browsers keep a
subscription bound to the old `applicationServerKey`, and `push_subscriptions`
keeps rows that can no longer receive anything. Delete those rows (or ask each
operator to reactivate) as part of a rotation; do not leave them to be counted as
deliveries.

### 2.8.4 Audio transcription sweep cron

The audio sweep runs outside the webhook path and processes only recent inbound
audio while `transcription.enabled` is true (the default is false). Install it
under **`deploy`'s own crontab** with the append form, alongside the other
containerized jobs:

```bash
( crontab -l 2>/dev/null; echo '*/5 * * * * /usr/bin/docker exec lumat-api-1 python -m app.ops.transcribe >> /home/deploy/lumat-transcribe.log 2>&1' ) | crontab -
crontab -l
```

Verification: `crontab -l` shows the entry, and
`/home/deploy/lumat-transcribe.log` gains one `Processed N audio message(s)`
line per run (or `Transcription disabled; processed 0 audio message(s)` while
the flag is off). The interval matches the notification and automation sweeps;
the bounded batch keeps each run finite.

### 2.8.5 Follow-up sweep cron

The follow-up sweep detects conversations whose newest message is inbound and
older than `followup.idle_hours`, and commitments still pending past their due
date. Detection is always on and records one `conversation_events` row per fact;
**sending** requires `followup.idle_enabled` (default false), a
`followup.idle_template_name` that the owner has had approved by Meta, and a
thread that was never followed up before. With the flag off this job writes
nothing to a customer.

```bash
( crontab -l 2>/dev/null; echo '*/5 * * * * /usr/bin/docker exec lumat-api-1 python -m app.ops.followup >> /home/deploy/lumat-followup.log 2>&1' ) | crontab -
crontab -l
```

Verification: `crontab -l` shows the entry, and
`/home/deploy/lumat-followup.log` gains one line per run with the number of facts
recorded. While the flag is off the count can be non-zero — that is the detector
working, not a message sent. A template name without Meta's approval fails at
send time and is logged; nothing else in the sweep is affected.

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
| `v2026.10.10` | `d040b7c6` | 2026-10-29 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.10","commit":"d040b7c6"}`; panel `/panel/app/` → 200; `nginx -t` inside the compose network → syntax ok; schema stayed at **058**, the `db/migrate.sh` re-run skipped every migration (`migrations up to date`); `db/seed.sh` → 0 inserted, 41 already present, `admin` not overwritten; the new deterministic answers were probed **inside the deployed image** against real configuration: `que comunas cubren?` → the seven configured communes, `cual es el horario de atencion?` → "Las visitas se agendan según la disponibilidad de los técnicos." (the 24/7 window is not announced as business hours), `cuanto dura la mantencion de calefont?` → `None` (map still empty, so the question kept its KB path), `la garantia cubre algo?` → `None` (no hijack). **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (no panel credentials in this session; root-only false negative, §3). | `v2026.10.9` (`605ea491`) | Carries slice B of `agenda-config-fuente` (#725, #726) plus #728. Pre-deploy dump as `deploy` (`/tmp/lumat-pre-v2026.10.10-20261029T140515Z.sql.gz`, 752942 B, `gzip -t` verified). **Recorded here because this table is its only trace:** afterwards the owner updated the customer KB by deleting the four documents in the panel and re-uploading the files, which is NOT a supported path — the panel route writes no `source_meta.source_id`, so all 280 chunks lost topic routing, and the invented titles (`Lumat Cobertura y Horarios`, `Lumat Garantia pagos`, `Lumat Identidad`, `Lumat Servicios`) kept the seed from reporting it (`unrouted` requires the stored title to equal the file H1). Repair: `UPDATE kb_documents SET title=...` to the four repository H1s (psql, **no `audit_log` row**), then `seed_kb_docs.py --apply --force` → `creados 0 · actualizados 0 · reparados 4`, same 280 chunks and fingerprint `baa03df47194` (metadata rewrite, no re-embed, no new version). Verified with a live probe: 3 of 3 topic questions returned chunks from exactly the right document and the near miss returned 0. The version history of the four documents was lost with the deletion and cannot be recovered. The same day the owner configured `booking.service_durations` from the panel (four services at 60 minutes, `settings.change` audited); the first save carried `Mantención de  calefont` with a double space, which answered nothing, and was corrected in the panel at 14:47Z. |
| `v2026.10.11` | `046a1254` | 2026-10-29 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.11","commit":"046a1254"}`; panel `/panel/app/` → 200; `nginx -t` inside the compose network → syntax ok; schema stayed at **058**, `db/migrate.sh` re-run skipped every migration; `db/seed.sh` → 0 inserted, 41 already present, `admin` not overwritten; **the four duration answers verified inside the deployed image**: `Visita técnica`, `Mantención de calefont`, `Mantención de caldera` and `Lavado de red` all answer "dura 1 hora" from `booking.service_durations`, and the topic-routing probe still returns 3 of 3 with the near miss rejected. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** (same two reasons as above). | `v2026.10.10` (`d040b7c6`) | Carries #730 (service-duration names with stray whitespace: matching folds spacing and the write-time validator stores the name collapsed). No migrations, no settings change, no data change: only the api image moved. Pre-deploy dump as `deploy` (`/tmp/lumat-pre-v2026.10.11-20261029T151332Z.sql.gz`, 741569 B, `gzip -t` verified). Rollback is code-only (§2.2). |
| `v2026.10.12` | `24b60d77` | 2026-10-29 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.12","commit":"24b60d77"}`; webhook verify handshake on `/webhook/whatsapp` echoed `123` (200); `nginx -t` inside the compose network → syntax ok; schema stayed at **058** (`max(version)` = `058_message_media`), the `db/migrate.sh` re-run skipped 057 and 058 (`migrations up to date`); `db/seed.sh` → 0 inserted, 41 already present, `admin` not overwritten. **The verification this tag exists for:** the new `scripts/probe_assistant_tools.py` was run **three times** inside the deployed image (`--role admin --owner-id 5 --proyecto test-del-agente`) and all three were identical — **21 ok · 0 error · 1 skipped · 11 requires-approval**. `conversations.search` and `dashboard.summary` are `ok` on every run, which is the point: both failed on `v2026.10.11` with a cold-import cycle, and `dashboard.summary` failed *intermittently* because it depended on import order, so a single green run would not have proved anything. `web.search` is `ok` too (real Brave result), after `BRAVE_SEARCH_API_KEY` was provisioned during this session (§below); the only `skipped` is `view_image`, because no image exists in that project or thread. `monitor.sh` as `deploy` → health=OK, webhook_probe=OK, `backup_age=FAIL` — the documented permission false negative of §3, not an outage: the `lumat_backups` volume holds **16 dumps**, the newest `lumat-20261029T030001Z.sql.gz`. **Not run: the authenticated `/panel/api/kpis` and the headless-Chrome render** (no panel credentials in this session). | `v2026.10.11` (`046a1254`) | Carries #733 (the turn no longer presents harness memory as the turn's tool evidence), #734 (cold-import cycle in `app/services/conversations.py`, `assistant.capabilities` reporting the effective catalog, and the panel package init no longer assembling all 20 routers on import — the class behind a second, order-dependent cycle in `app/services/dashboard.py`), #735 (the tool probe and its registry-tied coverage test) and, because the release cuts from `main`, #736/#737 (`odd/asistente-memoria-captura`) from another actor. **No migrations** in `23d1d29f..v2026.10.12`, so no data was at risk and the rollback is code-only (§2.2). **No pre-deploy dump was taken** — recorded plainly rather than implied; a post-deploy one exists instead: `/tmp/lumat-post-v2026.10.12-20261029T214804Z.sql.gz`, 514985 B, `gzip -t` verified. Two operational notes: (1) `BRAVE_SEARCH_API_KEY` was added to `/opt/lumat/infra/.env` during this session — that file was already `600 deploy:deploy` and gitignored — and `web.search` went from `skipped` to `ok`, i.e. it is verified by effect, not by presence; the key was removed from the local `infra/.env`, whose permissions were tightened from `755` to `600`; (2) the release PR #739 was blocked as `BEHIND` after #736/#737 landed mid-release, so `origin/main` was merged into the release branch and CI re-ran on the combined tree before the merge. The alert path of §3 is still undeliverable (`SMTP_HOST=change-me-smtp-host`), unchanged by this release. |
| `v2026.10.13` | `5ec2573e` | 2026-10-30 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.13","commit":"5ec2573e"}`; webhook verify handshake echoed `123` (200); `nginx -t` inside the compose network → syntax ok; schema **058 → 060** — migrations 059 and 060 applied on the api start, and the explicit `db/migrate.sh` re-run skipped all three (`migrations up to date`, `max(version)` = `060_capture_ack_plain`); the live `memories_visibility_scope_coherence` now accepts `scope='user'` with `visibility='global'`; `reply.texts.capture_ack` reads `Entiendo. `, so the guarded rewrite applied; `db/seed.sh` → 0 inserted, 41 already present, `admin` not overwritten; panel `/panel/app/` → 200 with `manifest.webmanifest`, `sw.js` and the hashed `index-C9e8w9XF.js` all 200. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` as `deploy`** — the monitor exits 6 with health=OK and webhook_probe=OK but `backup_age=FAIL`, the known root-only false negative (§3), and its alert cannot be delivered because `notify.smtp_host` is still `change-me-smtp-host`. | `v2026.10.12` (`24b60d77`) | Two migrations: `059_memory_user_scope` (widens the `memories` visibility/scope CHECK; a superset, so the previous code works against it) and `060_capture_ack_plain` (guarded UPDATE of `reply.texts.capture_ack`). Rollback is code-only (§2.2) and leaves both applied. Pre-deploy dump as `deploy` (`/home/deploy/lumat-predeploy-20261030T114349Z.sql.gz`, 521623 B, `gzip -t` verified) because `infra/backup.sh` needs root. Carries the per-user, cross-project memory axis with its audit screen, the capture-ack text fix, four clock-dependent scheduling tests pinned to a business hour, and three chatbot-realism branches (#740, #741, #743) merged while the release was cut — described in the changelog from their commit subjects rather than re-verified. This release added two checks beyond the runbook: `max(schema_migrations.version) = 060_capture_ack_plain` and the live coherence constraint accepting `scope='user'`, both because an unapplied migration fails silently at runtime and no HTTP smoke would see it. |
| `v2026.10.14` | `84f0a7bc` | 2026-10-31 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.10.14","commit":"84f0a7bc"}`; webhook verify handshake echoed `123` (200); `nginx -t` inside the compose network → syntax ok; schema **060 → 062** — migrations 061 and 062 applied on the api start and the explicit `db/migrate.sh` re-run skipped all of them (`migrations up to date`); both verified by effect in the prod DB, not by the runner's output: `assistant_artifacts.root_id` and `.version` exist, and `appointments.technician_id` + `project_files.owner_id` report `nullable=YES`; `db/seed.sh` → 0 inserted, 41 already present, `admin` not overwritten; panel shell, a client-side deep link below `/panel/app/`, the hashed `index-kKu_n5ju.js`, `manifest.webmanifest` and `sw.js` → 200; the KB reports `consistente con docs/kb` (4 documents, 156 chunks, fingerprint `baa03df47194`); `monitor.sh` as `deploy` → health=OK, webhook_probe=OK, `backup_age=FAIL`, which is the known root-only false negative (§3) — the underlying fact was verified instead: the `lumat_backups` volume holds 16 dumps and the newest is `lumat-20261031T030002Z.sql.gz`, 20 h old at deploy time. **Not run: the authenticated `/panel/api/kpis`, `panel/export/cases.csv` (302 to login, needs a session), the headless-Chrome render and the PWA install/offline check** — the owner's browser actions. | `v2026.10.13` (`5ec2573e`) | The 16 PRs since `v2026.10.13` (#748–#761): the assistant panel rebuild, the conversation evaluator fallback, overdue visits, the assistant context sidebar, the in-panel file viewer, append-only artifact **revisions (061)**, the pre-release polish with hard artifact and user deletion **(062)**, and the audio + action-toast + conversation-redesign release itself. **The api image now carries `ffmpeg`** (audio remux, `app/services/audio_format.py`), so the image is larger and its build got slower — that is the only delivery-environment change in this tag. **No pre-deploy dump was taken**: `deploy` has no passwordless sudo for `infra/backup.sh`; the automated 03:00 UTC dump (`lumat-20261031T030002Z.sql.gz`) predates the deploy by 20 h and is the snapshot this release relies on. Rollback is code-only for the 062 relaxation (§2.2 keeps 061 in place). |
| `v2026.11.1` | `846481e9` | 2026-11-04 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.1","commit":"846481e9"}`; webhook verify handshake echoed `12345` (200) and a wrong token → 403; `nginx -t` inside the running nginx container → syntax ok; **no migrations**: the explicit `db/migrate.sh` re-run skipped every one (`migrations up to date`, `max(version)` still `062_user_nullable_refs`), exactly as preflighted (`git diff v2026.10.14..main -- db/migrations/` empty); `db/seed.sh` → 1 inserted, 41 already present, `admin` not overwritten; panel `/panel/app/` → 200 with `manifest.webmanifest` and `sw.js` under `/panel/app/` (both 200) — the root paths `/manifest.webmanifest` and `/sw.js` answer **404 by design**, because the SPA base is `/panel/app/` (`web/vite.config.ts`, `infra/nginx/panel.lumat.cl.conf`), so the root-path checks in the older records no longer apply; verified by effect inside the image, not by the tag name: `app.chat.slot_window.slot_label` exists, `booking._asks_another_visit("quiero agendar otra visita")` → `True`, `closure_gate.is_farewell("no, eso seria todo gracias")` → `True`, and `messages.smalltalk_decline` is in `MESSAGE_DEFAULTS`. **Open observation:** the api logs `ERROR: ASGI callable returned without completing handshake` every ~8 s. The panel WS route (`app/panel/api/routes/realtime.py:64`) depends on `realtime_user` and raises before `accept()` for an unauthenticated client, so a retrying tab without a valid session produces exactly that line; this deployment's nginx stdout carries no `/panel/` access entries at all, so it could not be attributed from logs, and the authenticated WS was **not** verified. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render and `monitor.sh` as `deploy`** (the known root-only `backup_age=FAIL` false negative, §3). | `v2026.10.14` (`84f0a7bc`) | Code-only: 16 commits, 0 migrations, so nothing in the data is at risk and the rollback is code-only (§2.2). Pre-deploy dump taken as `deploy`: `/home/deploy/lumat-predeploy-20261104T143308Z.sql.gz`, 550989 B, `gzip -t` verified. Carries the four harness-driven chat fixes: the coverage gate tolerating a punctuation mark or one typo (#763), the agenda release that stops repeating the recap, understands a requested hour and prints the weekday (#764), the farewell that closes the conversation plus the refusal that is no longer thanked (#765), and the guard that stops re-offering slots once a visit is booked (#766). The two month-dependent price tests (#763) are what had `main` red since 1 November; CI was green again on every merge and on the release PR #767. |
| `v2026.11.2` | `fbada88b` | 2026-11-04 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.2","commit":"fbada88b"}`; webhook verify handshake echoed `123` (200); `nginx -t` inside the running nginx container → syntax ok; **no migrations**: `db/migrate.sh` → `skip 062_user_nullable_refs (already applied)` / `migrations up to date`, `max(version)` still `062_user_nullable_refs`; `db/seed.sh` → 0 inserted, 42 already present, `admin` not overwritten; panel `/panel/app/`, `/panel/app/manifest.webmanifest` and `/panel/app/sw.js` → 200. **The check this release exists for — VAPID — passed**: `printenv` inside `lumat-api-1` lists `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT`, and `app.config.get_settings()` reports `public set: True`, `private set: True`, subject `mailto:contacto@lumat.cl`, public key 87 chars. `push_subscriptions` is still 0 because no operator has activated push on a device yet — that row is the end-to-end proof and it is the owner's to produce. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render, and `monitor.sh` meaningfully** (see the incidents column). | `v2026.11.1` (`846481e9`) | Code-only: 0 migrations, so no data is at risk and rollback is a code revert (§2.2). Pre-deploy dump taken as `deploy`: `/home/deploy/lumat-predeploy-20261104T182845Z.sql.gz`, 555524 B, `gzip -t` verified. Carries #769 (the conversation that never closed, the push message that blamed the browser, the un-designed overdue-visits band, and the design-system wiring) and #770 (the CalVer bump). **Two runbook traps measured in this deploy**: (1) `docker compose … exec -T` inside an `ssh 'bash -s' <<EOF` script consumes the script itself from stdin and truncates the remote run mid-way — every `exec -T` needs `< /dev/null`; (2) `docker cp` into `lumat-api-1` fails with `container rootfs is marked read-only`, so a verification script goes in with `docker exec -i lumat-api-1 python -` instead. **Open observations**: (a) `monitor.sh` as `deploy` reports `backup_age=FAIL(no dump …)`, the documented root-only false negative (§3) — but the volume's newest dump is `lumat-20261021T030001Z.sql.gz`, so run as root the 26 h freshness check fails too: dumps have not been produced since 2026-10-21; (b) the stale `uv.lock` stash entry in the main worktree is unrelated to this deploy. |
| `v2026.11.3` | `d221b9e5` | 2026-11-06 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.3","commit":"d221b9e5"}`; webhook verify handshake echoed `123`; `nginx -t` inside the running container → syntax ok; **no migrations**: `db/migrate.sh` → `skip 062_user_nullable_refs (already applied)` / `migrations up to date`; `db/seed.sh` → 0 inserted, 42 already present, `admin` not overwritten; panel `/panel/app/`, `manifest.webmanifest` and `sw.js` → 200. **Verified inside the deployed image, not by the tag name**: `grep -c` finds 4 references to `iter_delivery_statuses`/`apply_delivery_statuses` in `app/webhook/ingest.py` and 4 to `equipment_ack` in `app/chat/nodes/capture.py`, and `from app.webhook.ingest import apply_delivery_statuses, iter_delivery_statuses` imports cleanly. **Not run: the authenticated `/panel/api/kpis`, the headless-Chrome render and a real outbound media send** — the last one is the check this release exists for and it needs an operator to send audio from the panel. `monitor.sh` as `deploy` still reports the known root-only `backup_age=FAIL` false negative. | `v2026.11.2` (`fbada88b`) | Code-only: 0 migrations, rollback is a code revert (§2.2). Pre-deploy dump as `deploy`: `/home/deploy/lumat-predeploy-20261106T002306Z.sql.gz`, 563839 B, `gzip -t` verified. Carries #772 (one acknowledgement in the diagnosis question), #773 (Meta delivery statuses applied to the message row) and #775 (the CI `test` job budget, below). **CI, recorded because it blocked three merges the same day**: the `test` job was cancelled three times inside `sudo apt-get install ffmpeg` — the job carried `timeout-minutes: 10` for `uv sync`, the install and the suite while `panel` had 15 — and every rerun then passed in ~5 min. #775 raises it to 15 and installs ffmpeg only when the image lacks it; measured after the change, that step went from minutes to **19 s** and the job to 5m43s. |
| `v2026.11.4` | `6c03ae3e` | 2026-11-06 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.4","commit":"6c03ae3e"}`; `nginx -t` ok; **no migrations**; `db/migrate.sh` skipped 062 / `migrations up to date`; `db/seed.sh` admin not overwritten. **Verified inside the deployed container**: `normalize_audio` on a generated fragmented MP4 returns `audio/ogg`, `opus`, in a new file. **Not run: a real outbound audio**, which still failed after this release — the container fix was necessary and not sufficient. | `v2026.11.3` (`d221b9e5`) | Code-only. Pre-deploy dump `lumat-predeploy-20261106T014639Z.sql.gz`, 567284 B, `gzip -t` verified. Carries #777: audio through Ogg/Opus and the cached media id cleared on failure in both paths. **Recorded honestly**: this deploy's premise (the container was the audio cause) turned out to be incomplete; the files it produced were still rejected by Meta. |
| `v2026.11.5` | `4696215d` | 2026-11-06 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.5","commit":"4696215d"}`; `nginx -t` ok; `migrations up to date`. **Verified inside the deployed container**: `_delivery_error` on Meta's real 131053 payload returns `131053: Media upload error — Audio file uploaded with mimetype as audio/ogg; codecs=opus, however on processing it is of type application/octet-stream. Please choose a different file.` instead of the repeated `Media upload error`. Diagnostic release: it changes no behaviour, only what a failure tells the operator. | `v2026.11.4` (`6c03ae3e`) | Code-only. Pre-deploy dump `lumat-predeploy-20261106T022726Z.sql.gz`, 570533 B, `gzip -t` verified. Carries #779 only. |
| `v2026.11.6` | `227cd10a` | 2026-11-06 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.6","commit":"227cd10a"}`; `nginx -t` ok; **no migrations**: `migrations up to date`. **The check this release exists for, measured inside the deployed container**: `normalize_audio` on a generated fragmented MP4 returns `audio/ogg`, `opus`, `start_time=0.000000`, in a new file, leaving no `.wav` behind. **One audio sent from the panel after this deploy reached the customer's WhatsApp**, confirmed by the owner on 2026-11-06 — the end-to-end proof, and the reason the release exists. | `v2026.11.5` (`4696215d`) | Code-only: 0 migrations, rollback is a code revert (§2.2). Pre-deploy dump `lumat-predeploy-20261106T101927Z.sql.gz`, 579429 B, `gzip -t` verified. Carries #781 (audio through PCM) and the three CI changes #782/#784/#785. **CI, recorded because it blocked the release for hours**: the `test` job was cancelled or timed out three times inside its ffmpeg install — neither `ubuntu-latest` nor `ubuntu-24.04` shipped ffmpeg on those runners, and the mirror moved at ~50 KB/s for ~60 MB. Caching `/var/cache/apt/archives` never saved (`tar` hit the root-owned `lock`/`partial` entries, exit 2), so every run started cold; #785 caches `~/.cache/apt-ffmpeg` and copies the `.deb` files back before installing. GitHub caches are branch-scoped, so only a `main` cache is shared with other branches. |
| `v2026.11.7` | `802ab53c` | 2026-11-06 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.7","commit":"802ab53c"}`; webhook verify handshake echoed `12345` (200); `nginx -t` inside the compose network → syntax ok; schema **062 → 063** — `063_artifact_outputs` applied, verified by effect (`project_files.source_artifact_root_id` and index `uq_project_files_source_artifact` both present), and the `db/migrate.sh` re-run skipped it (`migrations up to date`); `db/seed.sh` idempotent (0 inserted, 42 already present, `admin` not overwritten); authenticated `/panel/api/kpis` → `contacts 8, derived 2`, `/panel/api/notifications` returns rows and `/panel/api/push-config` returns the VAPID public key; panel `/panel/app/`, `manifest.webmanifest` and `sw.js` → 200; **the sweep cron is installed and documented**: `*/5 * * * * docker exec lumat-api-1 python -m app.ops.sweep`. **Not run: the headless-Chrome render, the PWA install/offline pass and the CSV export** (§2.1.2 items that need a browser). `monitor.sh` as `deploy` printed `health=OK`, `webhook_probe=OK` and the documented root-only `backup_age=FAIL` false negative. | `v2026.11.6` (`227cd10a`) | Migration 063 is additive (a nullable column plus a partial unique index), so a code-only rollback to `v2026.11.6` is safe and leaves both in place — nothing in the older code reads them. Pre-deploy dump `/home/deploy/lumat-predeploy-20261106T140636Z.sql.gz`, 580351 B, `gzip -t` verified. |
| `v2026.11.9` | `c1e490bd` | 2026-11-13 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.9","commit":"c1e490bd"}`; webhook verify handshake echoed `123` (200); `nginx -t` inside the compose network → syntax ok; schema **063 → 067** — `064_conversation_turn_count`, `065_case_ficha`, `066_commitments` and `067_message_transcript` applied by the container's startup chain, verified by effect (`schema_migrations` max `067`, table `commitments` present with 0 rows, `messages.transcript`/`transcript_at`/`transcript_attempts` present), and the `db/migrate.sh` re-run skipped all four (`migrations up to date`); `db/seed.sh` → 8 settings inserted, 42 already present, `admin` not overwritten; **the audio path verified inside the image**, which is what `v2026.11.8` got wrong: `ffprobe 5.1.9`, `av 18.1.0`, and a real ogg transcribed through `transcribe_path`; `transcription.enabled = true` and the transcribe cron installed, and a real customer voice note (message 501) came out as «Y, ¿dónde voy a escuchar uno?» after the counter it had burnt during the broken window was reset. Pre-deploy dump `/home/deploy/lumat-predeploy-20261113T125607Z.sql.gz`, 585K. `monitor.sh` as `deploy`: `health=OK`, `webhook_probe=OK`, documented root-only `backup_age=FAIL`. **Not run: the §2.1.2 browser checklist, the CSV export and the KB consistency seed.** | `v2026.11.7` (`802ab53c`) | `v2026.11.8` shipped a broken pair (`faster-whisper 1.2.1` with `av 19.0.2`, which removed the `metadata_errors` keyword): the sweep downloaded the model and failed on every audio. `v2026.11.9` pins `av<19`. The four migrations are additive, so a code-only rollback to `v2026.11.7` is safe and leaves them in place — the older code never reads those columns. |
| `v2026.11.10` | `0bd6e8f1` | 2026-11-18 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.10","commit":"0bd6e8f1"}`; webhook verify handshake echoed `123` (200); `nginx -t` inside the compose network → syntax ok; schema stayed at **068** — `068_customer_address_validation` applied by the container's startup chain and the explicit `db/migrate.sh` re-run skipped every migration (`migrations up to date`); `db/seed.sh` → 1 setting inserted, 50 already present, `admin` not overwritten; panel `/panel/app/`, `manifest.webmanifest`, `sw.js` and the hashed `index-CNQBaWTH.js` → 200; **the KB had to be re-versioned and was**: the read-only report returned exit 1 naming `lumat-servicios` as different from `docs/kb`, `python scripts/seed_kb_docs.py --apply --force` reported `creados 0 · actualizados 1 · reparados 0 · sin cambios 3` (156 → 167 chunks), and the report afterwards returned **exit 0** (`kb · consistente con docs/kb`); the gas guard was verified **by effect inside the deployed image** — `_gas_manipulation_instruction` returns True for «revisa que la llave de gas esté abierta» and «abre el gas», and False for the accepted residuals («cierra la llave azul del calefont», «prueba con un fósforo si hay fuga de gas») and for the legitimate emergency advice control; `reply.texts` carries 35 keys including `capture_quote_ack` and `validate_reply_texts` accepts a round-trip of the merged catalogue; api logs since the recreate carry **no real errors** (the 16 `WebSocket /panel/ws` 401s are unauthenticated probes, pre-existing). Pre-deploy dump `/home/deploy/lumat-predeploy-20261118T155042Z.sql.gz`, 609095 B, `gzip -t` verified. `monitor.sh` as `deploy`: `health=OK`, `webhook_probe=OK`, documented root-only `backup_age=FAIL` (exit 1). **Not run: the authenticated §2.1.2 browser checklist items, the CSV export, and `monitor.sh` as root.** | `v2026.11.9` (`c1e490bd`) | The 22 PRs since `v2026.11.9`: the gas guard and the service-KB scope, the capture acknowledgements (maintenance and evaluation/quote), the reschedule handoff, deterministic coverage answers, the address validation against the official street index, the post-emergency silence, the conversation evaluator's honest corpus plus its first judge baseline (35/42, zero gate failures), and the mobile Clientes/Conversaciones lists (#838). Two runbook corrections came out of this deploy: `uv run python scripts/seed_kb_docs.py` **cannot run in the deployed image** (`failed to write to file /app/uv.lock: Read-only file system`) — call `python scripts/seed_kb_docs.py` there, fixed in §2.5 — and any release that touches `docs/kb/*.md` must run `--apply --force` before go-live, which this one did. Rollback is code-only and leaves `068` in place (additive). |
| `v2026.11.11` | `db51adaa` | 2026-11-19 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.11","commit":"db51adaa"}`; webhook verify handshake echoed `123` (200); `nginx -t` **inside the compose network** → syntax ok; compose config validated with the stamped `GIT_SHA`; schema **068 → 069** — `069_panel_sessions` applied by the container's startup chain (no explicit line in that log, so it was read: `schema_migrations` max = `069_panel_sessions` at `2026-11-19 21:52:22Z`, and `panel_sessions` carries its 9 columns), then the explicit `db/migrate.sh` re-run skipped every migration (`migrations up to date`); `db/seed.sh` → 1 setting inserted, 51 already present, `admin` not overwritten; panel `/panel/app/`, `manifest.webmanifest`, `sw.js` and the hashed `index-ComvhQQU.js` → 200; the read-only KB report returned **exit 0** (`kb · 4 documentos customer · 167 chunks · fingerprint 34670f5b3d75`, `kb · consistente con docs/kb`), so no forced re-seed was needed; the release's product change was verified **by effect inside the deployed image** — `_reduced` (12 references) and `is_confusion_only` are in `/app/app/chat/nodes/receive.py` and `MESSAGE_DEFAULTS["confusion"]` reads «Perdón, me expliqué mal…»; `docker logs lumat-api-1` since the recreate carry **0** error/traceback lines (the 1 `WebSocket /panel/ws` probe is the pre-existing unauthenticated noise); `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, documented root-only `backup_age=FAIL`. **Not run: the authenticated §2.1.2 browser items, the CSV export, the >1 MB document upload, and `monitor.sh` as root.** | `v2026.11.10` (`0bd6e8f1`) | The 54 commits / 78 files since `v2026.11.10` (`+4912/−149`): the greeting read the way WhatsApp writes it plus the deterministic repair for a customer who did not understand the bot (#846), the agenda that respects the customer's schedule (#845), the revocable per-device panel session (#844), the mobile viewport fix (#843), the closed service catalogue and the tariff/scope corrections (#842), and the chat approval decision for `project.create`/`project.find` (#841). Pre-deploy dump taken as `deploy` (`docker exec lumat-db-1 pg_dump` piped through `gzip`, `/home/deploy/lumat-predeploy-20261119T185408Z.sql.gz`, 657451 B, `gzip -t` verified; prod held the 4 customers and the KB at 167 chunks). `069_panel_sessions` is additive and must not be rolled back (§2.2), so the rollback is code-only. The release also repaired a lock drift the previous release left: `uv.lock` still carried `lumatagent 2026.11.9` while `pyproject.toml` said `2026.11.10`, which `uv sync --frozen` in CI is exactly the step that would have caught. Cutting the tag took `db51adaa` (the merge commit of PR #847), and `pyproject.toml` on it reads `2026.11.11`. |
| `v2026.11.12` | `98f440de` | 2026-11-19 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.12","commit":"98f440de"}`; webhook verify handshake on `/webhook/whatsapp` echoed `123` (200, with the **server's** `VERIFY_TOKEN`); `nginx -t` inside the compose network → syntax ok; schema stayed at **069_panel_sessions**, the `db/migrate.sh` re-run skipped every migration (`migrations up to date`); `db/seed.sh` → 0 inserted, 52 already present, `admin` not overwritten; panel `/panel/app/`, a client-side deep link below it, `manifest.webmanifest`, `sw.js` and the hashed `index-DSNu5iT_.css` / `index-qzuJQoOJ.js` → 200; **the release's product change was verified by effect in the served bundle**: the CSS a phone downloads carries all four mobile rules — `.settings-tabs>.tabs>.tabs__panel>.tabs--vertical{grid-template-columns:minmax(0,1fr)`, `.settings-conduct__table-wrap{position:relative`, `.settings-page .card__copy{flex:1 1 12rem`, `.settings-hours-editor__table{display:block`; unauthenticated `/panel/api/kpis` → 401 and `/panel/export/clients.csv` → 302, so auth still fails closed; `monitor.sh` as `deploy` → health=OK, webhook_probe=OK, `backup_age=FAIL`, the documented root-only false negative (§3) verified instead through the volume: 16 dumps, newest `lumat-20261119T030001Z.sql.gz`. **Not run: the authenticated §2.1.2 browser items** (login, CSV export, a >1 MB document upload, PWA install and offline reload) — they stay the owner's action from a real browser. | `v2026.11.11` (`db51adaa`) | Frontend-only: the Configuración section was unusable on a phone (#848) — a hidden section rail that still claimed its 13rem grid track, card headers that squeezed the title to one word per line, a document 620px wide from out-of-flow labels, and an unreachable end-time field in Horarios y avisos. No migrations, no contract change, no backend change: the api image was rebuilt only for the version stamp, so the rollback is code-only (§2.2). Pre-deploy dump taken as `deploy` (`/home/deploy/lumat-predeploy-20261120T020353Z.sql.gz`, 661326 B, `gzip -t` verified; prod held 4 customers / 42 conversations / 679 messages / 22 appointments / 34 cases / 5 KB documents / 57 settings / 1251 audit rows). **Recorded because it is the reason this tag exists:** `v2026.11.11` was tagged at 16:04 and the fix merged at 18:58, so that release shipped five hours before the panel mobile fix existed. The check for the next release: `git merge-base --is-ancestor <fix-merge> <tag>` before declaring a fix released. |
| `v2026.11.13` | `3796477f` | 2026-11-21 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.13","commit":"3796477f"}` (read from outside the host, so TLS and DNS are exercised too); webhook verify handshake on `/webhook/whatsapp` echoed `123` (200, with the **server's** `VERIFY_TOKEN`); unsigned webhook POST rejected 403 (`infra/monitor.sh`); `nginx -t` inside the compose network → syntax ok; schema stayed at **069_panel_sessions** — the release carries no migration, and the explicit `db/migrate.sh` re-run skipped every migration (`migrations up to date`); `db/seed.sh` → 0 settings inserted, 52 already present, `admin` not overwritten; panel `/panel/app/` → 200 and the PWA files are fetched where the SPA actually serves them, `/panel/app/manifest.webmanifest` and `/panel/app/sw.js` → 200 (their root paths are 404 by the deliberate narrowing in `a8b5670c2`, not a regression: `git diff v2026.11.12 v2026.11.13 -- infra/` is empty); unauthenticated `/panel/api/kpis` → 401 and `/panel/export/clients.csv` → 302, so auth still fails closed; the KB read-only report returned **exit 0** (`kb · 4 documentos customer · 167 chunks · fingerprint 34670f5b3d75`, `kb · consistente con docs/kb`); **the release was verified by effect inside the deployed image** — `_asks_about_availability` and `_prose_availability` are present in `/app/app/chat/nodes/capture.py`, `handoff_booking_change_ack` reads its approved sentence in `/app/app/services/settings.py`, and `chat_simulation.py` + `chat_regression.py` exist; `docker logs lumat-api-1 --since 30m` carries **0** error/traceback lines; data unchanged across the deploy (4 customers / 42 conversations / 679 messages / 22 appointments / 34 cases / 5 KB documents / 57 settings). `infra/monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, documented root-only `backup_age=FAIL`, verified instead through the volume (newest `lumat-20261121T030001Z.sql.gz`). **Not run: the authenticated §2.1.2 browser items** (login, CSV export, a >1 MB document upload, PWA install and offline reload). | `v2026.11.12` (`98f440de`) | The 21 commits / 52 files since `v2026.11.12` (`+4062/−74`): the panel assistant can finally write the levers the bot reads every turn — `kb.propose_document`, the remaining writable settings, `chatbot.simulate` over the real brain, `chatbot.eval_regression` against a named baseline and `settings.revert` over the audited history, all behind the exact-approval path (#853); and the chat brain reads the turn instead of running its capture ritual — a greeting or a courtesy with a pending batch continues the capture without spending a classifier call, an explicit date change leaves capture instead of exhausting a field into `handoff_campo_sin_respuesta`, a question about availability keeps the day it proposes while its acknowledgement says preference rather than booked visit, and a bare franja after a weekday survives window resolution (#854, corpus 36/42 → 38/42 with the rubric judge and zero gate failures). Pre-deploy dump taken as `deploy` (`docker exec pg_dump` piped through `gzip`, `/home/deploy/lumat-predeploy-20261121T145542Z.sql.gz`, 661327 B, `gzip -t` verified). No migrations: the rollback is code-only to `v2026.11.12`.
| `v2026.11.14` | `b536f94f` | 2026-11-22 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.14","commit":"b536f94f"}` (read from outside the host); **schema `069_panel_sessions` → `071_simulation_isolation`** — the first schema movement since `069`: `070_session_safety` (merged by another session and never deployed) and `071_simulation_isolation` both applied by the container's startup chain, and the explicit `db/migrate.sh` re-run skipped every migration (`skip 071_simulation_isolation (already applied)` / `migrations up to date`); `db/seed.sh` → 1 setting inserted, 52 already present, `admin` not overwritten; `nginx -t` inside the compose network → syntax ok; panel `/panel/app/` → 200 and `/panel/app/manifest.webmanifest` → 200, unauthenticated `/panel/api/kpis` → 401; the KB read-only report returned **exit 0** (`kb · 4 documentos customer · 168 chunks · fingerprint 34670f5b3d75`, `kb · consistente con docs/kb`; the table holds 6 documents because two are `internal`, including the one the panel assistant proposed); **the release verified by effect in both places** — in the database, `conversations.simulated` and `cases.simulated` exist as `boolean NOT NULL DEFAULT false` with 0 flagged rows, and `get_simulation_enabled()` inside the container returns **False**; inside the deployed image, `not_simulated_expr` (2 references), `_SCHEDULE_QUESTION` (2) and `_asks_about_availability` (2) are present and both `070`/`071` migration files ship in `/app/db/migrations/`; `docker logs lumat-api-1 --since 15m` carries **0** error/traceback lines; data unchanged across the deploy (4 customers / 42 conversations / 679 messages / 22 appointments / 34 cases / 6 KB documents / 58 settings / 11 open cases). Pre-deploy dump `/home/deploy/lumat-predeploy-20261122T215924Z.sql.gz` (768581 B, `gzip -t` verified). **Not run: the authenticated §2.1.2 browser items** (login, CSV export, a >1 MB document upload, PWA install and offline reload). | `v2026.11.13` (`3796477f`) | The 4 PRs since `v2026.11.13`, all from the review of two simulated production conversations: a question outranks the capture step with or without a pending batch and the schedule vocabulary recognises how customers ask for a time (#858, corpus 43 scenarios); migration `071` flags what a simulation writes and one shared predicate keeps simulated rows out of the case list, the panel queries and the daily summary, with `chatbot.simulate` disabled by default (#859); and the booking fixture that failed every UTC Sunday now uses the product's own day rule (#860, test-only). `070_session_safety` also lands here. Both new migrations are additive and forward-only, so the rollback is code-only to `v2026.11.13`. Already cleaned before this deploy: the simulated rows a run left on 2026-11-21 were deleted in production (see §3, 2026-11-22). |
| `v2026.11.15` | `7a565d86` | 2026-11-23 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.15","commit":"7a565d86"}` (version and commit match the tag); webhook verify on `/webhook/whatsapp` echoed `12345` and a wrong token returned `403`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — the explicit `db/migrate.sh` re-run skipped `070`/`071` and reported `migrations up to date`, `max(version)` stays `071_simulation_isolation`; `db/seed.sh` → 0 settings inserted, 53 already present, `admin` not overwritten; panel `/panel/app/`, `manifest.webmanifest`, `sw.js` and a deep link below `/panel/app/` → 200, unauthenticated `/panel/api/projects` and `/panel/api/projects/{slug}/deletion-impact` → **401** (the new routes exist and demand a session, they are not 404); the KB read-only report → `kb · 4 documentos customer · 168 chunks · fingerprint 34670f5b3d75`, **consistente con docs/kb** (the same fingerprint the shipped eval baseline stamps); **verified by effect in both places** — in the deployed SPA bundle (`index-DM8e2jgE.js`): `Mover contexto y archivos`, `Eliminar proyecto`, `Filtrar por estado` and the `deletion-impact` path present; inside the deployed image: `version = "2026.11.15"`, `odd/evals/conv-eval-baseline.json` ships (23.639 B), `projects.deletion_impact`/`delete_project`/`move_files` exist and `_validated_bytes` carries the `%PDF-` guard; `docker compose logs --since 20m api` carries **0** error/traceback lines; `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, `ALERT: backup_age=FAIL` (the root-only false negative of §3, exit 1). Pre-deploy dump `/home/deploy/lumat-predeploy-20261123T203951Z.sql.gz` (777317 B, `gzip -t` verified). **Not run: the authenticated §2.1.2 browser items** (login, `/panel/api/kpis`, CSV export, a >1 MB document upload, PWA install and offline reload) — no panel credentials in this session. | `v2026.11.14` (`b536f94f`) | The 2 PRs since `v2026.11.14`, both from the E2E testing of the assistant in production: #864 stops publishing the `.bak` copy of every rewritten project file into `/outputs`, refuses text written into a binary-declared artifact (the corrupt PDF: 3.507 B of markdown served as `application/pdf`), passes the thread attachment ids to the turn so `view_image` resolves, matches the conversation summary in `conversations.search`, and ships a reference eval baseline (`odd/evals/conv-eval-baseline.json`, tag `baseline`) inside both api images; #865 adds real project management to the panel — irreversible delete behind an impact preview that is the same census the delete removes, move of files and folders between projects, archive/reactivate, and a rebuilt `Administrar proyectos`. No migrations, so the rollback is code-only. Cleaned in production before the tag: the two visible `.bak.md` files and the corrupt PDF were deleted with the app's own `delete_project_file` (audit 1512-1514). |
| `v2026.11.16` | `5bd2edb7` | 2026-11-24 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.16","commit":"5bd2edb7"}`; webhook verify echoed `12345`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — `db/migrate.sh` skipped `071` and reported `migrations up to date`; `db/seed.sh` → **2 settings inserted** (the configurable return greeting of #869), 53 already present, `admin` not overwritten; panel `/panel/app/`, `manifest.webmanifest` and `sw.js` → 200; the KB report → `consistente con docs/kb`; `docker compose logs --since 10m api` carries **0** error/traceback lines; **the reason this tag exists, verified by effect on the real rows**: inside the deployed image, `_planner_messages` for a turn carrying thread attachment 7 emits `[attachment id="7" filename="_.jpeg" kind="image"]` in the plan prompt **and** `execute_tool("view_image", {"source":"thread","id":7})` against thread 62 returned `completed` with `{'image': {'source': 'thread', 'id': 7, 'filename': '_.jpeg', 'mime': 'image/jpeg'}}` — the exact call that returned `thread image not found` four times on 2026-11-23 21:55-21:57 UTC; `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, `ALERT: backup_age=FAIL` (the root-only false negative of §3, exit 1). Pre-deploy dump `/home/deploy/lumat-predeploy-20261123T235909Z.sql.gz` (469077 B, `gzip -t` verified). **Not run: the authenticated §2.1.2 browser items** (no panel credentials in this session); the owner's own panel turn on that thread is the end-to-end confirmation. | `v2026.11.15` (`7a565d86`) | Patch over `v2026.11.15`: `view_image` still failed after it, because that fix put the attachment ids where the responder reads them instead of where the planner decides (#870). Two cuts from other sessions merged into `main` first and travel here because a tag is cut from `main`: the water valve guard for a calefont question (#868) and the mid-thread greeting that no longer restarts the introduction (#869, which is where the 2 seeded settings come from). No migrations, so the rollback is code-only. |
| `v2026.11.17` | `f5cefe45` | 2026-11-24 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.17","commit":"f5cefe45"}`; webhook verify echoed `12345`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — `db/migrate.sh` reported `migrations up to date`; `db/seed.sh` → 0 inserted, 55 already present, `admin` not overwritten; panel `/panel/app/` and `manifest.webmanifest` → 200; the KB report → `consistente con docs/kb`; `docker compose logs --since 5m api` carries **0** error/traceback lines; **verified by effect inside the deployed image** (this is the reason the tag exists): the evidence budget reads **12.000** with a **9.800**-character page, two 5.000-character pages of the same file render **both halves** (10.202 characters) where 5.500 used to evict the first, `_tool_step_limit()` returns **8**, a chain that names a write stops with `write_pending_after_reads` instead of asking for another read, and `assemble_context` puts the `attachment` before the `history` with the header `[adjunto id="9" filename="informe.pdf" caracteres=17]`; `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, `ALERT: backup_age=FAIL` (the root-only false negative of §3, exit 1). Pre-deploy dump `/home/deploy/lumat-predeploy-20261124T*.sql.gz` (502872 B, `gzip -t` verified). **Not run: the authenticated §2.1.2 browser items**; the owner's own panel turn is the end-to-end confirmation. | `v2026.11.16` (`5bd2edb7`) | Patch over `v2026.11.16` with #874: the evidence box kept the newest tool result and evicted the older one, so reading the second page of a 5,899-byte project file made the first half vanish (page 1 alone rendered 4,063 characters; pages 1+2 rendered 2,323 with page 1 gone). The planner then re-read the half it had lost until the step budget ended the turn — six `read_project_file` and zero `project_file.update`, five turns in a row. Reads of one file are now one evidence block, the budget is 12.000, the last step of a write request cannot be another read, a third read of the same file id is refused, the prompt asks for two pages per turn, the step cap is a setting (8), attachments outrank the thread history, and every step audits an argument digest instead of its content. No migrations, so the rollback is code-only. |
| `v2026.11.18` | `f9795b1b` | 2026-11-24 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.18","commit":"f9795b1b"}`; webhook verify echoed `12345` and a wrong token returned `403`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — `db/migrate.sh` skipped `069`/`070`/`071` and reported `migrations up to date`, so the schema stays at `071_simulation_isolation`; `db/seed.sh` → 0 settings inserted, 55 already present, `admin` not overwritten; **the KB had to be re-versioned and was**: the read-only report returned exit 1 naming `lumat-cobertura-horarios`, `python scripts/seed_kb_docs.py --apply --force` reported `creados 0 · actualizados 1 · reparados 0 · sin cambios 3` (34 → 37 chunks, fingerprint `99a2bbabbeb1`), and the report afterwards returned **exit 0** (`kb · consistente con docs/kb`); the SPA was checked on the **panel host** — `panel.lumat.cl/panel/app/`, `manifest.webmanifest`, `sw.js`, the deep link `/panel/app/settings` and the hashed bundle `index-B46MHUxc.js` → 200, and that bundle carries the two new availability reply keys; unauthenticated `/panel/api/kpis` → **401**; **verified by effect inside the deployed image**: evidence budget **12.000** with a **9.800**-character page and `_DETAIL_EVIDENCE_SHARE` 0.85, `LLM_TIMEOUT_SECONDS` 60 with `LLM_MAX_RETRIES` **1** (worst case 120 s, under the 180 s guard), `_release_before_provider_call` present and referenced from `nodes.py`, `assistant.evidence_truncated` present in the shipped module, `_cut_with_marker` returning the dropped count, and `availability_reply` + `_one_slot_per_day` present with `get_reply_texts` returning both new keys («Tengo disponibilidad el {{dias}}…», «El {{dia}} tengo estas horas libres: {{horas}}…»); in the database, `kb_documents` 48 carries the new availability policy and **no** document carries the old one, and `audit_log` holds 0 `assistant.evidence_truncated` rows because nobody has used the panel since the deploy; `docker compose logs --since 15m api` carries **0** error/traceback lines; `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, `ALERT: backup_age=FAIL` (the documented root-only false negative, exit 1). Pre-deploy dump `/home/deploy/lumat-predeploy-20261124T195024Z.sql.gz` (504917 B, `gzip -t` verified, 42 `CREATE TABLE`). **Not run: the authenticated §2.1.2 browser items** (no panel credentials). Two runbook corrections came out of this deploy, both applied to §2.1 below. | `v2026.11.17` (`f5cefe45`) | The four PRs since `v2026.11.17`: availability is answered from the technician agenda with the customer KB realigned to that policy (#880, which is why the KB had to be re-seeded); the panel turn stops dying at three minutes on the database idle guard, because `60 s × 3 SDK attempts` was exactly the 180 s guard, and a failed turn now records its reason (#878); every evidence projection that drops or cuts content records one `assistant.evidence_truncated` row, the measurement the next file-read budget decision depends on (#879); and the conversation evaluator's harness relaxes its own session instead of the database guard, seeds its configured window and keeps the session option inside the harness process, with both 2026-11-24 baselines recorded as explicitly not comparable (#877). No migrations, so the rollback is code-only. |
| `v2026.11.20` | `2a129bb2` | 2026-11-26 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.20","commit":"2a129bb2"}`; webhook verify echoed `12345` (200) and a wrong token → `403`; an unsigned POST → `403`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — `db/migrate.sh` skipped `070` and `071` and reported `migrations up to date`, so the schema stays at `071_simulation_isolation`; `db/seed.sh` → 0 settings inserted, 55 already present, `admin` not overwritten; **the KB did not change and did not need reseeding** (no `docs/kb` file moved since `v2026.11.19`); the SPA was checked on the **panel host** — `/panel/app/`, `manifest.webmanifest`, `sw.js` and the deep link `/panel/app/settings` → 200, unauthenticated `/panel/api/kpis` → **401**; **verified by effect inside the deployed image**: `av` → `18.1.1` (the yanked 18.1.0 is gone) and `REPLY_TEXT_DEFAULTS["handoff_ruptura"]` is present with the reason mapping to it; the api logs since the recreate carry **no application error** (0 matching lines); backup freshness read directly from the `lumat_backups` volume — 16 dumps, newest `lumat-20261126T030001Z.sql.gz` at 03:00Z. **Not run: `monitor.sh`** — it sends an SMTP alert on the documented `backup_age` root-only false negative, so its two probes were run by hand instead (health=OK, unsigned POST → 403) — **and the authenticated §2.1.2 browser items** (no panel credentials in this session). | `v2026.11.19` (`055ce902`) | The eight PRs since `v2026.11.19`: a declared relationship break now escalates to a person with its own approved text instead of offering a capture (#889), four conversation fixes (#887 `slot_window` «próximo»/am-pm, #888 the bare acknowledgement, #890 coverage and price before capture, #894 a farewell closing with a capture pending), `av` 18.1.1 (#892), the evaluation harness seeding production's capture redaction (#891) and the merged-tree baseline (#895). Both images were rebuilt — api for `av`, nginx for the SPA carrying the new `reply.texts` slot — and the deploy was split in two stages so a build failure could not touch the running service. Pre-deploy dump `/home/deploy/lumat-predeploy-20261126T142431Z.sql.gz` (525268 B, `gzip -t` verified); prod held 4 customers / 44 conversations / 732 messages / 23 appointments / 36 cases / 60 settings / 5 KB documents before the deploy and the same after. No migrations, so the rollback is code-only (§2.2). |
| `v2026.11.19` | `055ce902` | 2026-11-25 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.19","commit":"055ce902"}`; webhook verification echoed `12345` (200) and a wrong token → `403`; an unsigned POST → `403`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — `db/migrate.sh` skipped `071` and reported `migrations up to date`, so the schema stays at `071_simulation_isolation`; `db/seed.sh` → 0 settings inserted, 55 already present, `admin` not overwritten; **the KB did not change and did not need reseeding**: the read-only report returned exit 0 (`kb · 4 documentos customer · 37 chunks · fingerprint 99a2bbabbeb1`, `kb drift · tolerados: 0 hallazgos (0 claves) · nuevos: 0`, `kb · consistente con docs/kb`), which is what a release that touches no `docs/kb` file must show; the SPA was checked on the **panel host** — `/panel/app/`, `manifest.webmanifest`, `sw.js` and the deep link `/panel/app/settings` → 200, unauthenticated `/panel/api/kpis` → **401**; **verified by effect inside the deployed image**: `phrasing._FIELD_IDENTIFIERS` = `['address','availability','equipment','equipment_type','failure','name']`, `validate('¿name?')` and `validate('¿equipment?')` → `False`, while `validate('¿Cuál es tu nombre?')` and `validate('¿En qué comuna estás?')` → `True` (the gate does not reject Spanish), `window_label(SlotWindow(day=2026-11-28))` → `el sábado 28/11` and the same window with `with_date=False` → `el sábado`, and `reply.texts.capture_availability_hold` still renders `{{disponibilidad}}`; the api logs since the recreate carry **no application error** (the single `error` line is compose's own `GIT_SHA` interpolation warning on an ad-hoc `logs` call); `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, `ALERT: backup_age=FAIL` (the documented root-only false negative, exit 1). Pre-deploy dump `/home/deploy/lumat-predeploy-20261125T023810Z.sql.gz` (515974 B, `gzip -t` verified); prod held 4 customers / 43 conversations / 704 messages / 23 appointments / 35 cases / 60 settings / 5 KB documents before the deploy and the same after. **Not run: the authenticated §2.1.2 browser items** (no panel credentials in this session). | `v2026.11.18` (`f9795b1b`) | The two PRs since `v2026.11.18`: **#884** keeps the raw capture field names away from the customer — production runs `chat.conduct.redaccion = "llm"`, so the rewrite path was live and it reached the customer as «¿name?»/«¿equipment?»; the fix is a deterministic `validate` rejection of the identifier plus a rewrite that no longer receives `Campos pendientes: ['name']`. **#883** seals the capture redaction the conversation evaluator measured (`Redacción de captura: llm · …`), because two runs that put different words in the customer's mouth shared one seal, and stops the capture acknowledgement from pinning a calendar date («Sobre tu horario: el sábado» instead of «el sábado 28/11», which the corpus judge read as a promise). No migrations, so the rollback is code-only. |
| `v2026.11.21` | `03eeecbf` | 2026-11-26 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.21","commit":"03eeecbf"}`; webhook verify echoed `12345` (200) and a wrong token → `403`; `nginx -t` inside the compose network → syntax ok; **no schema movement** — `db/migrate.sh` skipped `069`, `070` and `071` and reported `migrations up to date`, so the schema stays at `071_simulation_isolation`; `db/seed.sh` → 0 settings inserted, 55 already present, `admin` not overwritten; the KB was checked in report mode inside the image → `kb · 4 documentos customer · 37 chunks · fingerprint 99a2bbabbeb1`, `kb drift … 0 hallazgos`, `kb · consistente con docs/kb`, exit 0, so no reseed was needed; the SPA was checked on the **panel host** — `/panel/app/`, `/panel/app/manifest.webmanifest`, `/panel/app/sw.js` and the deep link `/panel/app/conversaciones` → 200, unauthenticated `/panel/api/kpis` → **401**; **verified by effect inside the deployed image**: `_HOURS_VOCABULARY` present in `app/chat/nodes/configured_answers.py` (4 references), `availability_preview_day_none` in `app/services/settings.py` (2) and in `configured_answers.py` (1), `day_selection` in `app/chat/nodes/orchestrate.py` (4), and the customer filter still threaded in `app/chat/nodes/booking.py`; the api logs since the recreate carry **no application error** (0 matching lines); backup freshness read directly from the `lumat_backups` volume — 16 dumps, newest `lumat-20261126T030001Z.sql.gz` at 03:00Z. `monitor.sh` as `deploy` → `health=OK`, `webhook_probe=OK`, documented root-only `backup_age=FAIL` (exit 1), **and it sent the SMTP alert it is designed to send** — see the incident column. **Not run: the authenticated §2.1.2 browser items** (no panel credentials in this session). | `v2026.11.20` (`2a129bb2`) | The two chatbot fixes merged since `v2026.11.20`: #899 keeps the day the bot just offered as the customer's selection (acceptance stored as a preference, the later offer restricted to that day, a day question answered from the real agenda, and a day with no slots answered from configuration instead of the generic policy sentence) and #898 removes a previous appointment of the same customer from the booking offer by applying customer eligibility before the limit and before assigning a technician. Both images were rebuilt, api for the code and nginx for the SPA. Pre-deploy dump `/home/deploy/lumat-predeploy-20261126T210536Z.sql.gz` (525270 B, `gzip -t` verified); prod held 4 customers / 44 conversations / 732 messages at schema `071` before the deploy. No migrations, so the rollback is code-only (§2.2). The release also repairs the `uv.lock` drift the previous release left (`2026.11.19` while `pyproject.toml` said `2026.11.20`); `uv lock --check` is clean again. **Incident:** `monitor.sh` was run as `deploy` because §2.1.2's checklist still asked for it, and it sent one SMTP alert for the root-only `backup_age` false negative; the checklist line is corrected in this same change. |
| `v2026.11.22` | `13ab42f9` | 2026-11-27 | agent-assisted SSH as `deploy` (authorized by the owner) | `/health` → `{"status":"ok","version":"2026.11.22","commit":"13ab42f9"}` (read from outside the host, so TLS and DNS are exercised too); webhook verify echoed `12345` (200, with the **server's** `VERIFY_TOKEN`) and a wrong token → `403`; **no schema movement** — the explicit `db/migrate.sh` skipped `069`, `070` and `071` and reported `migrations up to date`, so the schema stays at `071_simulation_isolation`; `db/seed.sh` → 0 settings inserted, 55 already present, `admin` not overwritten; pre-deploy dump `/home/deploy/lumat-predeploy-20261127T032259Z.sql.gz` (529935 B, `gzip -t` verified, 42 `CREATE TABLE`); **the first `up -d --build` recreated `api` but not `nginx`**, so nginx was recreated explicitly with `--force-recreate --no-deps` and `nginx -t` re-run **inside the new container** → syntax ok, with the previous image `sha256:5812655d…` kept on disk as the rollback reference; the panel smoke ran on the **panel host** with `--resolve` — `/panel/app/`, `manifest.webmanifest`, `sw.js` and the deep link `/panel/app/settings` → 200, and unauthenticated `/panel/api/kpis` → **401**; **verified by effect inside the deployed image**: `MAX_REBUILD_ROUNDS` 4 next to `MAX_INVALID_REPLIES` 1, `_continuation_offer`, `_week_ahead_window`, `_rebuild` and `_franja_of` present, `resolve_window("Puede ser para la proxima semana? Lunes quizas en la manana?")` → `la mañana del lunes 30/11` while a bare «proxima semana» resolves to no window at all, which is exactly the case the node's own week-ahead rule covers; the KB report inside the image → `kb · consistente con docs/kb`; `docker logs --since 25m api` → **0** error/traceback lines; `infra/monitor.sh` was **not** run — its `backup_age` probe is root-only and firing it sends a real SMTP alert for a condition already recorded as a false negative — and the authenticated §2.1.2 browser items were not run either (no panel credentials in this session). | `v2026.11.21` (`03eeecbf`) | Neither stumble was a production fault: the nginx recreation gap left the release serving the previous nginx image, and the `GIT_SHA` interpolation refusal aborted one `up` before it touched anything. Both corrections are now in §2.1. |

### 2.9.1 Artifacts: what the revision chain costs

Every edit of an artifact appends a full copy of the file (migration 061), and nothing is purged. That
is deliberate: a revision is the record of what the file said, and deleting one would break the
download path a message already wrote. The cost is disk, so measure it before choosing a retention
policy instead of guessing:

```sql
SELECT thread_id,
       count(*)                        AS revisions,
       count(DISTINCT root_id)         AS artifacts,
       pg_size_pretty(sum(size)::bigint) AS bytes
FROM assistant_artifacts
GROUP BY thread_id
ORDER BY sum(size) DESC
LIMIT 20;
```

Run it as the `app` role (it is a plain `SELECT` on `assistant_artifacts`, already granted) or as the
admin role from `infra/.env`. `size` is the stored blob's byte count, so `sum(size)` is the real
on-disk weight of the chain plus whatever the filesystem rounds up. A thread whose `revisions` is
close to `artifacts` has never been edited; a large `revisions / artifacts` ratio on a heavy thread is
the signal that a retention policy is worth designing.

### 2.10 Spec part-status convention

The convention is one `Status:` line inside each existing spec. There is no
parallel artifact, so the status cannot drift from the spec.

- `released-in-prod` — deployed and running in production.
- `contract-complete` — implemented and verified in the repository, not yet deployed.
- `in-flux` — still being changed, not stable.
- `deferred` — deliberately postponed.

Applying this line to existing specs retroactively or only to future work is
still an open decision and is not part of this runbook.

### 2.11 Database idle-transaction guard

The database aborts a transaction that sits idle for **180 s**
(`idle_in_transaction_session_timeout`). Migration `070_session_safety.sql` sets
it as a database-level default, so it applies to every role that connects — the
app pool, the admin role, an operator's `psql` — and survives a rebuilt volume.

It exists because of the 2026-11-21 incident (§3): an assistant turn kept a
transaction open while waiting on external I/O, held its row locks for sixteen
minutes, and every writer queued behind it until the SQLAlchemy pool (5 + 10)
was gone and the whole panel answered 500. Nothing in the database could abort
that transaction, because the value was `0`.

The guard is a net, not a timeout budget: the application must not hold a
transaction across external I/O at all. A transaction idle for three minutes is
pathological by construction, and aborting it costs one failed turn with its
retry action instead of a wedged service.

Verify it from a **new** session (a session opened before the setting ran keeps
the old value — that is what a pool recycle is for):

```bash
docker exec lumat-db-1 sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -U lumat -d lumat -X -c \
  "SELECT current_setting('\''idle_in_transaction_session_timeout'\'')"'
# 3min
```

To recycle pooled app connections so they inherit it, terminate only the ones
that are not in a request, plus any read-only `idle in transaction` leftover
whose only locks are `AccessShareLock`:

```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = 'lumat' AND usename = 'app' AND state IN ('idle', 'idle in transaction');
```

`pool_pre_ping` reconnects them on the next checkout. A rollback is
`ALTER DATABASE lumat RESET idle_in_transaction_session_timeout;`.

The connection pool is sized by the environment, not by code
(`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`, `DB_POOL_TIMEOUT=10`,
`DB_POOL_RECYCLE=1800`; see `infra/.env.example`). The 2026-11-21 incident took
the API down with SQLAlchemy's 5 + 10 and a 30 s checkout wait, and widening it
meant editing code — which is the wrong dependency at three in the morning. Keep
`pool_size + max_overflow` well inside the database's `max_connections` (100);
`db_pool_recycle` is what eventually hands a long-lived connection the current
database defaults above.

---

## 3. Runbook incident + change record

### Incidents

| Date | Incident | Resolution | Operator |
|------|----------|------------|----------|
| 2026-09-22 | The backup/monitor tooling is non-functional on the VPS. `infra/backup.sh` fails as `deploy` (`Permission denied` writing to the root-owned `lumat_backups` mountpoint), so the volume existed but was empty; `infra/restore-test.sh` cannot read that path either; `infra/monitor.sh` reports `backup_age=FAIL` for the same reason and cannot send alerts (`SMTP_HOST` unset — it does not load `infra/.env`); and no backup/restore/monitor crons are installed (only `lumat-certbot-renew.timer` exists). `lumat-certbot-renew.service` has been failing since 2026-09-21 on its `nginx -s reload` post step; the certificate expires 2026-12-07. | Unresolved. The `v2026.09.2` deploy proceeded only after a pre-deploy dump was taken by an alternative route (docker `pg_dump` piped into a root container writing the `lumat_backups` volume) and restore-verified into a scratch database. The scripts and the crons must be fixed and armed under root before go-live. | agent-assisted |

| 2026-09-23 | The §2.1.2 smoke command `sudo -u deploy /opt/lumat/infra/monitor.sh` can never exit 0. `infra/monitor.sh:40` resolves the `lumat_backups` volume mountpoint, which is root-owned and unreadable by `deploy`, so `ls` finds no dump, `backup_age=FAIL` is reported and the run exits 6. Observed during the `v2026.09.4` deploy. The same script run by root's cron is green: `/var/log/lumat-monitor.log` has a five-minute entry since 2026-09-22 with zero ALERT lines. | Not a production fault — a permission false negative in the documented smoke command, the same class as the `nginx -t` standalone note in §2.1. Recorded so the next deploy does not read it as an outage. The check should be run as root, or replaced in §2.1.2 by reading the cron log; the command is left as-is here because its correct root form could not be exercised from a `deploy` session. | agent-assisted |
| 2026-09-23 | The monitoring alert path cannot deliver. `/opt/lumat/infra/.env` on the VPS still carries the placeholder `SMTP_HOST=change-me-smtp-host`, so on any failed check `monitor.sh` dies with `curl: (6) Could not resolve host: change-me-smtp-host`. Observed live during the `v2026.09.4` deploy, when the deploy-run monitor tried to alert on the false negative above. No real alert has ever been sent: the cron log shows zero ALERT lines since 2026-09-22. | Unresolved — it needs the owner's real SMTP host and credentials in the server environment; the repository cannot supply them and inventing one would be worse than the gap. This qualifies the 2026-09-22 incident row above: the `infra/.env` loading fix does work, but the value it loads is still a placeholder, so "alerts can actually be sent" is not yet true. | agent-assisted |
| 2026-10-30 | The 2026-09-23 undeliverable alert path — and, behind it, every outbound email: `mail.lumat.cl` never offers `SMTP AUTH` to the VPS IP, which is what S9 of WU-E recorded. | **Resolved.** Outbound email now goes through **Resend** as the SMTP relay. Panel (`notify.smtp_*`): `smtp.resend.com`, port `587`, `starttls`, user `resend`, `from=notificaciones@lumat.cl`, API key in the encrypted `smtp_password` panel secret. `monitor.sh`: `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASS` in `/opt/lumat/infra/.env` (`600`), which the script loads itself, so no container was recreated. The domain was verified in Resend with `TXT resend._domainkey.lumat.cl` and the `CNAME`s `rsend`/`send`; the root SPF record was deliberately left untouched and still holds exactly one `v=spf1`. **Verified by effect, not by presence:** `notification_operations` id 13 → `status=sent`, `attempts=1`, `delivered_at 2026-10-30T14:27:13Z`, with audit `notification.operation_sent`; a direct `alert()` run of `monitor.sh` delivered to `SMTP_TO`; and a full `monitor.sh` run printed `health=OK`, `webhook_probe=OK`, `ALERT: backup_age=FAIL` and exited 1 — the documented permission false negative of §3, reached without dying in the alert path, which is the whole point. | agent-assisted |
| 2026-09-23 | The assistant could not answer in production for the whole `v2026.09.1`–`v2026.09.4` window. The prod image never shipped `agent/`, so `app/agent_registry.py:223` resolved `/app/agent/registry.yaml` to nothing and `load_registry()` raised `registry file not found` on every turn; the panel answered with the raw error plus "No se pudo procesar el mensaje". Not a boot failure — `build_graph()` runs per message (`app/chat/graph.py:300`) — and invisible to the deploy smoke, which has no assistant-turn probe. `prompts.load()` masked the same missing tree on its own path by silently serving its literal `FALLBACKS`. | Fixed in `v2026.09.5` (`COPY agent/ agent/` in the prod `Dockerfile`, plus a regression test asserting the image ships every repo-root path the runtime resolves). **Forward-only: there is no known-good tag to roll back to on this path**, because the prod Dockerfile never contained `agent/`. Still open: the smoke needs an assistant-turn probe (§2.1), and the first real conversation after this deploy is the outstanding end-to-end confirmation. | agent-assisted |
| 2026-11-21 | The panel answered 500 on every endpoint that touches the database. One assistant turn (thread 55, run `7b589166…`, stage `planning`) kept a transaction `idle in transaction` for sixteen minutes while it waited on external I/O, holding RowShare/RowExclusive locks on `internal_chat_threads`, `internal_chat_messages`, `assistant_artifacts`, `audit_log`, `project_files`, `projects` and `users`. `pg_blocking_pids()` showed a six-deep chain of waiters behind it; the waiters exhausted the pool (5 + 10) and every request raised `QueuePool limit of size 5 overflow 10 reached, connection timed out`. The application's own failure path then deadlocked trying to mark the operator's message as failed, so nothing self-healed; the operator could not fix it from the panel, which was the surface that was down. The database had no guard at all (`idle_in_transaction_session_timeout = 0`, `statement_timeout = 0`, `lock_timeout = 0`). | **Resolved by effect.** One `SELECT pg_terminate_backend(4016327)` on the lock holder released everything: pool back to 7 connections, the message recorded `failed` with `El agente no pudo procesar este mensaje. Reinténtalo.`, a fresh run completed in the same thread, `/health` 200 and `/panel/api/*` 401 instead of 500. The residual fixes are the `pool-safety` unit: migration `070` (the 180 s guard, §2.11, applied to production the same day), no transaction held across external I/O, a configurable pool, and a failure path that survives a deadlock. | agent-assisted |

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
| 2026-10-29 | Deploys of `v2026.10.10` (`d040b7c6`) and `v2026.10.11` (`046a1254`), the two releases after `v2026.10.9`. `v2026.10.10` carries slice B of **`agenda-config-fuente`**: coverage, opening-hours and service-duration questions are answered from `coverage.communes`, `hours.schedule` and `booking.service_durations` ahead of the KB path (`configured_answers.py`), and the customer KB stops restating those values — `docs/kb/drift-baseline.json` is now empty, so `scripts/kb_doc_drift.py` fails on any new restatement. A 24/7 window is no longer announced as business hours: production's `hours.schedule` (every day `00:00–23:59`) is how "no restriction" is expressed, and the technicians' agenda is what bounds the calendar, so the answer says availability decides (#728). `v2026.10.11` carries #730, the whitespace defect measured the same day. **Two operational lessons recorded here:** (1) the customer KB must not be updated by deleting and re-uploading documents in the panel — the panel route writes no `source_meta.source_id`, every chunk loses topic routing, and invented titles make the loss invisible to the seed; the path is editing `docs/kb/*.md` and running `seed_kb_docs.py --apply --force`; (2) a configured service name is matched as a phrase against the customer's message, so a stray double space silences the answer while the other services keep working. | agent-assisted |
| 2026-10-30 | Deploy of `v2026.10.13` (`5ec2573e`), the PRs since `v2026.10.12`: the **per-user, cross-project memory axis** with its "Memorias sobre ti" audit screen and `GET`/`DELETE` API (404 for a foreign id), the capture-ack text fix, four scheduling tests pinned to a business hour, and three chatbot-realism branches merged mid-release. Two migrations applied (schema 058 → 060) and the explicit re-run proved idempotent; seed idempotent; panel shell, manifest, `sw.js` and the hashed asset at 200. Two checks beyond the runbook were added to §2.1's smoke for this case: the applied schema version and the live coherence constraint. Pre-deploy dump taken as `deploy` because `infra/backup.sh` needs root. Rollback is code-only: 059 is a superset and 060's reverse UPDATE is documented in its file. | agent-assisted |
| 2026-10-30 | Outbound email fixed in production without a release: the app and the monitoring alert path moved from cPanel SMTP (which refuses AUTH from the VPS) to **Resend**. Panel settings changed from the UI (§Correo) and `monitor.sh` credentials loaded into `/opt/lumat/infra/.env`; no code and no container change, because the panel reads its SMTP config from the database and the monitor reads the `.env` directly. The DNS records Resend asked for were the current three — a `TXT` DKIM under `resend._domainkey` plus the `CNAME`s `rsend` and `send` — not the MX+TXT pair the older documentation describes; the root `v=spf1` record was left alone and still holds exactly one entry. Sandbox behaviour worth remembering: before a domain is verified Resend only delivers to the account's own address (`rapsodiaitinerante@gmail.com`) and requires `onboarding@resend.dev` as the sender, so a real-sender send fails with `550 domain is not verified` while the credentials are already fine — `535` is the credential error, `550` is the DNS one. Verified by effect through `notification_operations` id 13 (`sent`) and a real `monitor.sh` alert. | agent-assisted |
| 2026-11-04 | Deploy of `v2026.11.1` (`846481e9`), the four chat fixes measured in the local harness: the coverage gate that rejected a covered commune for a trailing period or one misspelling, the capture questions that repeated the whole recap every turn, the requested hour ("después de las 17") that was never understood, and the farewell that looped on "Con gusto" instead of closing the conversation; plus the guard that stops `booking` from re-offering slots once a visit is booked. **No migrations** (schema stays at `062_user_nullable_refs`), so the rollback to `v2026.10.14` is code-only; pre-deploy dump verified with `gzip -t`. Two corrections to the documented smoke: the panel's manifest and service worker live under `/panel/app/` (the root paths 404 by design), and the api's unauthenticated panel-WS attempts surface as `ASGI callable returned without completing handshake` every ~8 s, which is the auth guard doing its job rather than an outage. | agent-assisted |
| 2026-11-04 | Deploy of `v2026.11.2` (`fbada88b`), the two PRs since `v2026.11.1`: **#769** closes the conversation on a repeated refusal and on a farewell with a temporal qualifier, names the real reason web push cannot be enabled instead of blaming the browser, forwards the VAPID keys to the `api` container, designs the overdue-visits band, and points agents at `web/DESIGN_SYSTEM.md` with a structural check that fails on a list container without classes; **#770** is the CalVer bump. Code-only: no migrations (schema stays at `062_user_nullable_refs`), api and nginx images rebuilt with the `GIT_SHA` stamp, seed idempotent. The VAPID keys were already written into `/opt/lumat/infra/.env` on 2026-11-04 (backup `infra/.env.bak-20261104T162254Z`, mode 600, pair verified by signing a VAPID header) and this is the release that makes the container see them: `printenv` lists all three and `get_settings()` returns both halves. `docs/ops.md` §2.8.3 documents generation, storage, verification and rotation. **Recorded, not fixed**: dumps in `lumat_backups` stop at 2026-10-21, so the backup freshness check would fail from root as well. | agent-assisted |
| 2026-11-06 | Deploy of `v2026.11.3` (`d221b9e5`): **#772** stops the first diagnosis question greeting twice and naming the appliance twice, by making the equipment sentence the acknowledgement instead of an extra prefix over the configurable one; **#773** applies Meta's delivery callbacks, which the ingestion filter used to drop before anything could read them — `failed` now sets `delivery_status`, writes the reason from `errors[]` and audits it, `delivered`/`read` write `delivered_at`, and a late `sent` never walks a `failed` row back; **#775** gives the CI `test` job the same 15-minute budget as `panel` and skips the ffmpeg install when the runner image already has it. Code-only: no migrations (schema stays at `062_user_nullable_refs`). **The audio question is now measurable, not answered**: the next outbound media Meta rejects will show its error code in the panel instead of looking delivered, and that code decides whether forcing ogg/opus is the fix. **Open, unchanged**: dumps in `lumat_backups` still stop at 2026-10-21. | agent-assisted |
| 2026-11-06 | Deploy of `v2026.11.4` (`6c03ae3e`): #777 sends audio as Ogg/Opus and clears the cached media id on failure. **The premise was incomplete**: valid Ogg/Opus produced from the browser recording was still rejected by Meta, and only the next release's diagnostic output (11.5) showed why. Recorded because a release whose premise turns out wrong is part of the history, not something to drop. | agent-assisted |
| 2026-11-06 | Deploy of `v2026.11.5` (`4696215d`): #779 surfaces `error_data.details`, the only field where Meta names a cause. Diagnostic only. With it, the failing audio read `on processing it is of type application/octet-stream`, which redirected the investigation from the container to the conversion. | agent-assisted |
| 2026-11-06 | Deploy of `v2026.11.6` (`227cd10a`): #781 converts audio through PCM. The cause was measured against production, not reasoned: a browser recording has a negative start time (encoder delay), encoding it straight into libopus produced a file every local tool reads as valid — same duration, loudness, page count and end-of-stream flag as a working file — and Meta answered 131053 every time, while the same recording through an intermediate WAV was accepted every time with the sends interleaved. The sample-copy path is gone. **Also**: #782 pins the CI runner, #784/#785 make the ffmpeg install cacheable in a directory the runner owns. Code-only, no migrations. | agent-assisted |
| 2026-11-06 | Deploy of `v2026.11.7` (`802ab53c`): the panel-polish thread header and voice-note player, the designed notifications surface with an immediate read state, cost-alert push and panel visibility for exhausted notification operations, and the assistant artifact outputs with migration 063. The release record carries the first verified answer to an open operational question: **the `*/5` sweep cron is installed**, so the push outbox drains on its own and not only at API boot. | agent-assisted |
| 2026-11-13 | Deploy of `v2026.11.9` (`c1e490bd`): the ten defects from the WhatsApp corpus analysis (D1-D10) — the deterministic case ficha and case lineage, who decides the spending, the attached question, the quote step, the multi-topic classifier, commitments with due dates, local audio transcription, follow-up detection — plus panel stickers and `ffmpeg`/`libgomp1` in the api image. Two releases: `v2026.11.8` was cut and deployed first and carried a broken dependency pair that only the deployed container could see, so `v2026.11.9` pinned `av<19` within the hour. | agent-assisted |
| 2026-11-18 | Deploy of `v2026.11.10` (`0bd6e8f1`): the answer path stops instructing gas manipulation (deterministic guard plus the event in the thread) and the service KB now names what Lumat does not repair; capture acknowledges the service the customer asked for — maintenance, and now an evaluation with a quote — once; a reschedule with no upcoming visit hands off with a cause; coverage questions answer deterministically; a voice note reporting a leak gets the safety protocol. Plus the address validation against the official street index, the conversation evaluator's corrected corpus and its first judge baseline (35/42, zero gate failures), and the mobile Clientes/Conversaciones lists. The KB re-version was the only data write of the deploy (156 → 167 chunks). | agent-assisted |
| 2026-11-19 | Deploy of `v2026.11.11` (`db51adaa`), the 54 commits since `v2026.11.10`: the bot reads a greeting the way WhatsApp writes it (`Holaa`, `holaaa`, `buenaaas`) instead of promising help the customer never asked for, and a customer who says they did not understand the bot gets a deterministic repair (`messages.confusion`, editable in the panel) instead of the complaint mirrored back and one `unknown_intent` charged against them (#846); the agenda respects the customer's schedule (#845); the panel session is remembered per device and revocable (#844); the mobile viewport no longer zooms on focus (#843); the service catalogue is closed and a catalogue service without a published tariff is no longer denied (#842); the chat approval decision reaches `project.create`/`project.find` (#841). Only data change: `069_panel_sessions` (additive, forward-only). The release also repaired the `uv.lock` drift the previous release left behind. | agent-assisted |
| 2026-11-22 | Deploy of `v2026.11.14` (`b536f94f`), the review of two simulated production conversations: una pregunta de disponibilidad vuelve a ser una pregunta — «¿Qué días tienen disponibles?» y «¿Tienen hora disponible esta semana?» reciben la respuesta de horarios en vez de la pregunta de diagnóstico (#858); las simulaciones del panel dejan de dejar casos abiertos, conversaciones y un cliente sintético en la operación (#859, migración `071`); y el fixture de booking que fallaba todo domingo UTC queda arreglado (#860). Con este deploy entra también `070_session_safety`: primer movimiento de esquema desde `069`. | agent-assisted |
| 2026-11-23 | Deploy of `v2026.11.15` (`7a565d86`), the two cuts from the E2E testing of the assistant: el asistente deja de publicar una copia `.bak` de cada archivo de proyecto que reescribe, un artefacto declarado binario rechaza contenido de texto (el PDF corrupto), `view_image` recibe los ids de los adjuntos del hilo, `conversations.search` busca en el resumen y `chatbot.eval_regression` tiene un baseline versionado dentro de la imagen (#864); y el panel gana borrado definitivo de proyectos con vista previa, mover archivos y carpetas, archivar/reactivar y `Administrar proyectos` reconstruida (#865). Sin movimiento de esquema. | agent-assisted |
| 2026-11-24 | Deploy of `v2026.11.16` (`5bd2edb7`), patch para que `view_image` funcione: el prompt del planner lleva el inventario de adjuntos del hilo con `id`, nombre y tipo (#870), junto con el guard de la llave de agua en una pregunta de calefont (#868) y el saludo de medio hilo que ya no reinicia la presentación (#869). Sin movimiento de esquema. Verificado por efecto sobre las filas reales: el prompt del plan cita el adjunto 7 del hilo 62 y `view_image` lo resuelve. | agent-assisted |
| 2026-11-24 | Deploy of `v2026.11.17` (`f5cefe45`), el arreglo del planner: la caja de evidencia expulsaba una página del archivo con la siguiente, así que la cadena de lecturas nunca podía tener el documento que debía reescribir y el turno cerraba prometiendo escribir «el próximo turno». Ahora las lecturas de un mismo archivo son un bloque, el presupuesto es 12.000 caracteres, el último paso de un turno de escritura se reserva, la tercera lectura del mismo archivo se rechaza, el prompt pide dos páginas por turno, el tope de pasos es un setting (8), los adjuntos van antes que la historia y cada paso audita un digest de sus argumentos (#874). Sin movimiento de esquema. | agent-assisted |
| 2026-11-22 | Data cleanup in production: the two simulated conversations a `chatbot.simulate` run left on 2026-11-21 were removed, with the reserved synthetic customer and everything hanging from them — `messages` 682-693 (12), `conversation_events` 355-362 (8), `cases` 35 and 36 (2, both `abierto`), `conversations` 43 and 44 (2), `customers` 5 (1, `phone_e164 +56900000000`). Ordered by foreign key inside one transaction with `ON_ERROR_STOP=1` and no `CASCADE`. Pre-cleanup dump `/home/deploy/lumat-prelimpieza-20261122T195518Z.sql.gz` (769310 B, `gzip -t` verified). Measured before: 4 customers / 42 + 2 conversations / 679 + 12 messages / 354 + 8 events / 34 + 2 cases / 13 open cases. After: **4 customers / 42 conversations / 679 messages / 354 events / 34 cases / 11 open cases**, zero orphan messages, zero orphan cases, zero simulated rows left — i.e. exactly the counts the `v2026.11.13` deploy recorded as its pre-deploy state, so the cleanup removed the simulation and nothing else. `/health` after → `2026.11.13` / `3796477f`, api, nginx and db `healthy`. Why it mattered: those two cases were counted by `app/ops/daily_summary.py` (`list_open_cases`), so the 07:00 digest would have reported two invented cases. The permanent fix ships as migration `071_simulation_isolation` plus the refusal-by-default guard (PR #859), which is in `main` and not yet deployed. | agent-assisted |
| 2026-11-21 | Deploy of `v2026.11.13` (`3796477f`), two PRs since `v2026.11.12`: el asistente del panel puede escribir el comportamiento del bot con aprobación exacta — propone documentos de KB, escribe los settings que antes sólo leía, simula conversaciones sobre el cerebro real, corre la regresión contra una baseline nombrada y revierte un cambio con el historial auditado (#853); y el cerebro del chat lee el turno en vez de ejecutar su ritual de captura — un saludo o una cortesía con datos pendientes retoma la captura, un pedido explícito de cambio de fecha sale de la captura, una pregunta de disponibilidad conserva el día que propone y su confirmación dice preferencia y no visita agendada (#854, corpus 36/42 → 38/42). Sin migraciones: rollback code-only. | agent-assisted |
| 2026-11-19 | Deploy of `v2026.11.12` (`98f440de`), one PR since `v2026.11.11`: la sección Configuración vuelve a ser usable en celular — tarjetas de ancho completo en lugar de una franja de 208px, encabezado legible, sin documento de 620px, y las tablas de horarios y de captura apiladas en un bloque por fila con sus etiquetas visibles (#848). Frontend-only: la imagen api se reconstruyó por el sello de versión y no corrió ninguna migración. Se cortó porque `v2026.11.11` quedó tagueado 2h54m antes de que el fix se mergeara. | agent-assisted |
| 2026-11-19 | Runbook correction, measured on the `v2026.11.11` deploy: a remote script fed to `bash -s` **stops after the first `docker compose exec`**, because `exec` consumes the script's stdin and every following line is lost with no error. Observed twice: the `nginx -t` / migrate / seed / schema steps of the first pass vanished and the run was re-collected explicitly. Fix, proven on the server: give every `exec` its own `< /dev/null`, or run the steps one command per session. The same deploy proved a second trap: any compose command that resolves the build section (`logs`, `config`, `up`) fails with `error while interpolating services.api.build.args.GIT_SHA` unless `GIT_SHA=$(git rev-parse --short HEAD)` is exported, because `infra/docker-compose.prod.yml:30` requires it (`${GIT_SHA:?…}`). `exec` alone does not resolve it. | agent-assisted |
| 2026-11-21 | Production DB guard applied during the 2026-11-21 incident: `idle_in_transaction_session_timeout = 180s` as a database-level default (`ALTER DATABASE` by hand, then codified as migration `070_session_safety.sql` so a rebuilt database cannot silently lose it). Pooled app connections were recycled (`pg_terminate_backend` on `idle` and on a read-only `idle in transaction` leftover) so live sessions inherit it — verified `3min` on the connections serving requests next. Documented in §2.11 and recorded in §3. | agent-assisted |
| 2026-11-24 | Deploy of `v2026.11.18` (`f9795b1b`), the four PRs since `v2026.11.17`. La disponibilidad se responde desde la agenda del técnico —días con cupo para una pregunta general, horas sólo cuando el cliente nombra el día— y la KB del cliente se alineó a esa política, así que este deploy **re-sembró la KB**: `actualizados 1`, 34 → 37 chunks, fingerprint `99a2bbabbeb1`, reporte posterior en exit 0. El turno del panel deja de morir a los tres minutos: la transacción se libera antes de cada llamada al proveedor y el tope de reintentos deja el peor caso en 120 s contra los 180 s del guard de la base, con la razón del fallo registrada. Cada proyección de evidencia que descarta contenido deja una fila `assistant.evidence_truncated`, que es la medición que decide el próximo presupuesto de lectura. Sin movimiento de esquema (sigue en `071_simulation_isolation`); rollback sólo de código. Una corrección de runbook nueva salió de acá: el smoke del panel va contra `panel.lumat.cl` (`agente.lumat.cl` proxyá `/panel/` al api y devuelve 404 por diseño, y este deploy gastó un diagnóstico en esa falsa alarma), ahora anotada en §2.1. La otra trampa de este deploy —todo script alimentado por stdin necesita `</dev/null` en cada `docker exec`, porque si no drena el resto y sale 0— ya estaba registrada el 2026-11-19 y se pagó igual tres veces hoy, así que quedó también en §2.1. | agent-assisted |
| 2026-11-25 | Deploy of `v2026.11.19` (`055ce902`), the two PRs since `v2026.11.18`. The capture question no longer shows the customer the internal field name (#884): with production's `chat.conduct.redaccion = "llm"` the rewrite received `Campos pendientes: ['name']` and echoed it, so the guard now rejects a draft carrying a field identifier and the rewrite only learns how many questions to keep; `comuna` and `email` stay out of the guard because they are the customer's own words. The conversation evaluator's report now declares the capture redaction it measured, and the capture acknowledgement stops pinning a date (#883). Also recorded: the release candidate's native review could not be collected — `gentle_review_capture` rejected the binding its own STATUS kept reoffering (four representations, no mutation), so the lineage `review-46135af21c1c2b04` stayed in `reviewing` and the deploy proceeded on the owner's explicit authorization, since a review never authorizes delivery. | agent-assisted SSH as `deploy` (authorized by the owner) |
| 2026-11-26 | Deploy of `v2026.11.20` (`2a129bb2`), the eight PRs since `v2026.11.19`. A customer who declares the working relationship is over — or who already hired someone else — reaches a person before the model answers, with a text of its own that the owner approved, instead of a greeting and an offer to take their data (#889). Four conversation defects closed: «próximo martes» no longer resolves to that same Tuesday and `am`/`pm` are a twelve-hour clock (#887); a bare «Eso!» answering the bot is no longer recorded as a misunderstanding (#888); coverage and price are answered on the opening turn and the capture resumes in the same turn without re-asking what the customer already gave (#890); and a farewell closes even with a capture batch pending (#894), which the 2026-11-25b baseline caught as a regression of #890. `av` moves to 18.1.1 because 18.1.0 was yanked. Two **runbook corrections** came out of this deploy: (1) §2.1 now states that its `sudo -u deploy …` form is for a root shell, and that a session already in as `deploy` must drop the prefix — `deploy`'s sudoers allows only `systemctl` and `docker`, so `sudo -u deploy git …` is refused, which cost this deploy its first attempt; (2) `monitor.sh` is not run on a deploy that has nothing to check about backups, because its `backup_age` probe is root-only and firing it sends an SMTP alert for a condition that is already documented as a false negative — the two probes it does cover were run by hand and are recorded in §2.9. | agent-assisted SSH as `deploy` (authorized by the owner) |
| 2026-11-26 | Deploy of `v2026.11.21` (`03eeecbf`), the two chatbot fixes since `v2026.11.20`: #899 keeps the day the bot just offered as the customer's selection — acceptance stored as a preference, the later offer restricted to that day, a day question answered from the real agenda, and a day with no slots answered from configuration instead of the generic policy sentence — and #898 removes a previous appointment of the same customer from the booking offer. No migrations (schema stays at `071`), the KB did not move, and the release also repairs the `uv.lock` version drift the previous release left. **Runbook defect repeated and corrected:** §2.1.2 ordered `monitor.sh` as `deploy` with exit 0 as the acceptance condition while §2.9 documented that the `backup_age` probe is root-only; running it sent a real SMTP alert for a false negative. The checklist now forbids that call and names the two probes to run by hand. | agent-assisted SSH as `deploy` (authorized by the owner) |
| 2026-11-27 | Deploy of `v2026.11.22` (`13ab42f9`), the single PR since `v2026.11.21`. Rescheduling stopped rejecting the customer's own answer: a day and/or franja («¿Puede ser para la próxima semana? Lunes quizás en la mañana?»), a relative week with no day, and a rejection of the menu («ninguno me sirve, necesito otro día») each rebuild the offer from the real agenda instead of spending the single clarification and handing off — «la próxima semana» keeps the day and franja of the visit being moved, seven days forward, and a rejection advances one day; the pre-LLM gate and the node now agree on what counts as a valid answer (#902). Code-only release: no migration, no configuration change, no new reply-text key. **Two runbook corrections came out of it, both now in §2.1:** every prod `docker compose` call needs `GIT_SHA` exported, because the file interpolates `services.api.build.args.GIT_SHA` and even `up -d --no-deps nginx` refuses without it — that aborted one attempt before it touched anything; and `docker build -t lumat-nginx:prod` plus `up -d --build` did **not** recreate nginx, so the container was recreated explicitly and `nginx -t` re-run inside the new one. | agent-assisted SSH as `deploy` (authorized by the owner) |
