# LumatAgent — Server Hardening Checklist (SH-1..SH-3)

> Change: `hito-1-setup-whatsapp` · Task: **T6.4** (doc) / **T7.1** (execution) · Date: 2026-08-15
> Target: Hostinger KVM 2 — Ubuntu LTS (São Paulo), Docker + Compose
> Hosts: `agente.lumat.cl` (bot API) · `panel.lumat.cl` (admin panel)
> How to use: run every block as `root` (sections 1–4) or `deploy` (5–9) on the
> production server; paste the real output under each block; tick the box with
> date + initials when the expected output matches. The go-live record in
> `docs/ops.md` §2.9 links to this executed checklist.
>
> **T7.1 execution note (2026-08-15)**: all 9 sections were executed and
> recorded against a **local Ubuntu Server 24.04 rehearsal VM** (libvirt/KVM,
> same Docker+Compose+ufw+fail2ban setup as the VPS) BEFORE provisioning any
> Hostinger VPS. Deviations vs the VPS, all documented per-section:
> - §4 TLS uses a **self-signed cert at the same live paths** (no public DNS
>   locally) — the nginx server blocks are identical; Let's Encrypt real
>   issuance + `certbot renew --dry-run` run on the VPS at T7.2.
> - §7/§8 backup/monitor crons run under **root's crontab** (the docker volume
>   host path `/var/lib/docker/volumes/…` is root-only; the api *container*
>   still runs non-root — §5).
> - SMTP alert delivery (§8) is VPS-only (no relay locally); the failure path
>   and env guard were verified in T6.6.

| # | Check | SH req | Status |
|---|-------|--------|--------|
| 1 | Firewall: 80/443/SSH only | SH-1 | ✅ 2026-08-15 (VM) |
| 2 | SSH key-only + fail2ban | SH-1 | ✅ 2026-08-15 (VM) |
| 3 | Non-root deploy user | SH-1 | ✅ 2026-08-15 (VM) |
| 4 | TLS + auto-renew | SH-1 | ✅ 2026-08-15 (VM, self-signed; LE on VPS) |
| 5 | Container hardening (read-only fs) | SH-2 | ✅ 2026-08-15 (VM) |
| 6 | Secrets env-only | SH-2 | ✅ 2026-08-15 (VM) |
| 7 | Backups: schedule + retention | SH-3 | ✅ 2026-08-15 (VM) |
| 8 | Monitoring: checks + alert | SH-3 | ✅ 2026-08-15 (VM) |
| 9 | Audit grants append-only | SH-5 | ✅ 2026-08-15 (VM) |

---

## 1. Firewall — only 80/443/SSH (SH-1)

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp    # HTTP  -> nginx (redirects to HTTPS)
ufw allow 443/tcp   # HTTPS -> nginx
ufw allow 22/tcp    # SSH  -> adjust if you moved the SSH port
ufw enable
ufw status verbose
```

Expected output (last command):

```
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
```

Verify: a probe from outside to any other port (e.g. `nc -vz <server-ip> 5432`)
times out / is filtered — connection is dropped (SH-1 "Firewall blocks
unexpected port").

- [x] **SH-1 firewall verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), deny (routed)
To                         Action      From
--                         ------      ----
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
22/tcp                     ALLOW IN    Anywhere
```

---

## 2. SSH — key-only, root login via key, fail2ban (SH-1)

```bash
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd
sshd -T | grep -Ei 'passwordauthentication|permitrootlogin'
```

Expected output:

```
passwordauthentication no
permitrootlogin prohibit-password
```

fail2ban (brute-force ban after 5 failures / 1 h):

```bash
apt install -y fail2ban
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
port = ssh
maxretry = 5
bantime = 1h
EOF
systemctl enable --now fail2ban
fail2ban-client status sshd
```

Expected output (last command): `Status for the jail: sshd` with
`Currently banned: 0`.

Verify: log out and back in with your key only; a password login attempt is
rejected before any prompt.

- [x] **SH-1 SSH verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ sudo sshd -T | grep -Ei 'passwordauthentication|permitrootlogin'
permitrootlogin without-password
passwordauthentication no
$ sudo fail2ban-client status sshd
Status for the jail: sshd
|- Filter
|  |- Currently failed:  0
|  |- Total failed:      0
`- Actions
   |- Currently banned:  0
   |- Total banned:      0
   `- Banned IP list:
```

> Ubuntu 24.04 prints `permitrootlogin without-password` for the configured
> `prohibit-password` (same semantics: key-only root login).

---

## 3. Non-root deploy user (SH-1)

```bash
adduser --disabled-password --gecos "" deploy
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
# deploy needs docker group + passwordless sudo for compose/service commands only:
usermod -aG docker deploy
echo 'deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl, /usr/bin/docker' > /etc/sudoers.d/deploy
chmod 440 /etc/sudoers.d/deploy
```

Expected: `sudo -u deploy whoami` → `deploy`; `ssh deploy@<server>` works
with the key and lands in `/home/deploy`. The API never runs as root:
compose runs under the `deploy` user and the api container runs its own
non-root user (see section 5).

- [x] **SH-1 non-root user verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ sudo -u deploy whoami
deploy
$ getent group docker
docker:x:112:ubuntu,deploy
```

---

## 4. TLS — Let's Encrypt + auto-renew (SH-1)

Prerequisite: DNS `A` records for `agente.lumat.cl` and `panel.lumat.cl`
pointing at the VPS IP (client, week 1–2).

TLS runs in containers (T7.1, `infra/docker-compose.prod.yml`): nginx
terminates TLS, the `certbot` service issues/renews via the webroot challenge
into the `certbot-certs` volume. First issuance on the VPS:

```bash
cd /opt/lumat
docker compose --profile certbot -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot \
  -d agente.lumat.cl -d panel.lumat.cl \
  --email ops@lumat.cl --agree-tos --no-eff-email
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml exec nginx nginx -s reload
```

Auto-renewal — systemd timer (files shipped in `infra/certbot/`):

```bash
sudo cp infra/certbot/lumat-certbot-renew.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lumat-certbot-renew.timer
systemctl list-timers | grep lumat-certbot
docker compose --profile certbot -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml run --rm certbot renew --dry-run
```

Expected: `Successfully received certificate` for both domains; the
`lumat-certbot-renew.timer` shows `next elapse` (twice-daily renewal check); the
dry-run ends with `Congratulations, all simulated renewals succeeded`.

Verify: `curl -sI https://agente.lumat.cl/health` returns `200`; plain HTTP
redirects to HTTPS (`curl -sI http://agente.lumat.cl/health` → `301`).

**Local rehearsal (no public DNS → Let's Encrypt cannot issue)**: a
self-signed certificate with both hostnames as SANs was placed at the SAME
live paths the nginx confs read (`/etc/letsencrypt/live/agente.lumat.cl/…`,
inside the `certbot-certs` volume) and the same cert was added to the system
CA store so `curl`/`monitor.sh` validate the stack end-to-end. The nginx
server blocks are byte-for-byte the VPS config (see `infra/certbot/README.md`
§3). Real issuance + `renew --dry-run` run on the VPS at T7.2.

- [x] **SH-1 TLS verified — 2026-08-15 (VM, self-signed; LE issuance pending VPS):**

```bash
# rehearse on the VM: /etc/hosts (agente.lumat.cl, panel.lumat.cl -> 127.0.0.1),
# self-signed SAN cert in lumat_certbot-certs volume + CA trust, stack up:
$ curl -s https://agente.lumat.cl/health
{"status":"ok","version":"0.1.0"}
$ curl -sI http://agente.lumat.cl/health | head -1
HTTP/1.1 301 Moved Permanently
$ echo | openssl s_client -connect agente.lumat.cl:443 -servername agente.lumat.cl 2>/dev/null | grep Protocol
    Protocol  : TLSv1.3
$ sudo systemctl list-timers | grep lumat-certbot
Sun 2026-08-16 03:21:19 UTC  4h 3min -  -  lumat-certbot-renew.timer  lumat-certbot-renew.service
```

---

## 5. Container hardening — read-only fs, no privileged (SH-2)

`infra/docker-compose.prod.yml` (created in T7.1) MUST declare for the api
service (the WhatsApp-facing surface):

```yaml
api:
  read_only: true            # agent filesystem is read-only (SH-2)
  tmpfs:
    - /tmp                   # only /tmp writable (transient)
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  volumes:
    - media:/app/media       # WhatsApp media downloads (writable volume)
  # NO "privileged: true" anywhere in the file
```

Verify against the running container (compose names them `lumat-api-1`):

```bash
docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' lumat-api-1        # true
docker inspect --format '{{.HostConfig.Privileged}}' lumat-api-1            # false
docker inspect --format '{{.HostConfig.SecurityOpt}}' lumat-api-1           # [no-new-privileges:true]
docker inspect --format '{{.HostConfig.CapDrop}}' lumat-api-1               # [ALL]
docker exec lumat-api-1 whoami                                             # appuser (non-root)
grep -n privileged infra/docker-compose.prod.yml || echo "no --privileged flag"
```

Write probe (must FAIL — SH-2 "write outside the writable volume is denied"):

```bash
docker exec lumat-api-1 touch /root/probe.txt
```

Expected: `touch: cannot touch '/root/probe.txt': Permission denied` (the api
runs as the non-root `appuser`, so even `/root` is unreachable; `/app` — the
image fs — fails with `Read-only file system`). The only writable paths are
`/tmp` (tmpfs) and `/app/media` (the `media` volume — verified by a
write-and-clean probe; the Dockerfile pre-creates `/app/media` as `appuser`
so a fresh volume inherits writable ownership).

- [x] **SH-2 read-only fs verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' lumat-api-1
true
$ docker inspect --format '{{.HostConfig.Privileged}}' lumat-api-1
false
$ docker inspect --format '{{.HostConfig.SecurityOpt}}' lumat-api-1
[no-new-privileges:true]
$ docker inspect --format '{{.HostConfig.CapDrop}}' lumat-api-1
[ALL]
$ docker exec lumat-api-1 whoami
appuser
$ grep -n privileged infra/docker-compose.prod.yml || echo "no --privileged flag"
no --privileged flag in compose
$ docker exec lumat-api-1 touch /root/probe.txt
touch: cannot touch '/root/probe.txt': Permission denied
$ docker exec lumat-api-1 touch /app/probe.txt
touch: cannot touch '/app/probe.txt': Read-only file system
$ docker exec lumat-api-1 touch /app/media/probe.txt && echo "media write OK"
media write OK
```

---

## 6. Secrets — env-only, never in the repo (SH-2)

The app reads every secret from the environment (`app/config.py`,
`env_file=None` — design SH-2). Real values live in the server environment /
`infra/.env` (gitignored); the repo carries only `infra/.env.example` with
`change-me` placeholders.

```bash
# 1. repo is clean of real secrets (no sk- keys, no Meta tokens, no change-me leaks):
git grep -nE 'sk-[A-Za-z0-9]{20}|EAAG[A-Za-z0-9]{20}' || echo "clean"
# 2. infra/.env is gitignored:
git check-ignore infra/.env          # -> infra/.env
# 3. the running container has the secrets in ENV, not in code/image layers:
docker exec lumat-api-1 printenv | grep -E 'OPENAI_API_KEY|META_ACCESS_TOKEN|APP_SECRET'
# 4. nothing secret baked into the image:
docker history --no-trunc lumat-api:prod | grep -iE 'secret|token|sk-' || echo "clean"
```

Expected: `git grep` prints nothing (or `clean`); `git check-ignore` prints
`infra/.env`; `printenv` shows the variables; `docker history` shows no
secret material.

- [x] **SH-2 secrets env-only verified — 2026-08-15 (VM):**

```bash
# pasted real output here (rehearsal snapshot repo, dummy env values):
$ git grep -nE 'sk-[A-Za-z0-9]{20}|EAAG[A-Za-z0-9]{20}' || echo "clean"
clean
$ git check-ignore infra/.env
infra/.env
$ docker exec lumat-api-1 printenv | grep -E 'OPENAI_API_KEY|META_ACCESS_TOKEN|APP_SECRET' | sed 's/=.*/=<set>/'
META_ACCESS_TOKEN=<set>
OPENAI_API_KEY=<set>
APP_SECRET=<set>
$ docker history --no-trunc lumat-api:prod | grep -iE 'secret|token|sk-' || echo "clean"
clean
```

---

## 7. Backups — daily pg_dump, 14-day retention (SH-3)

`infra/backup.sh` (T6.6) dumps the `lumat` database to the `backups/` volume
every day at 03:00 and deletes dumps older than 14 days. Install the cron
entry on the server — **under ROOT's crontab** (T7.1 note: the docker volume
host path `/var/lib/docker/volumes/…` is root-only; the api *container* still
runs non-root, this is host-level ops):

```bash
sudo crontab -l 2>/dev/null; cat > /tmp/cron <<'EOF'
0 3 * * * /opt/lumat/infra/backup.sh >> /var/log/lumat-backup.log 2>&1
0 4 * * 1 /opt/lumat/infra/restore-test.sh >> /var/log/lumat-backup.log 2>&1
EOF
sudo crontab /tmp/cron && rm /tmp/cron
sudo crontab -l | grep -E 'backup|restore'
```

Verify (as root — the volume path is root-only):

```bash
# dumps exist and are non-empty:
sudo ls -lh /var/lib/docker/volumes/lumat_backups/_data/ | tail -5
# retention: nothing older than 14 days
sudo find /var/lib/docker/volumes/lumat_backups/_data/ -name '*.sql.gz' -mtime +14 | wc -l   # 0
# restore drill (weekly, T6.6): see docs/ops.md §2.3 for the full drill
sudo /opt/lumat/infra/restore-test.sh
```

Expected: one dump per day, gzipped, > 0 bytes; the `-mtime +14` count is 0;
`restore-test.sh` exits 0 and prints `restore OK`.

- [x] **SH-3 backups verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ sudo /opt/lumat/infra/backup.sh
backup OK: /var/lib/docker/volumes/lumat_backups/_data/lumat-20260815T231553Z.sql.gz (4.0K)
$ sudo find /var/lib/docker/volumes/lumat_backups/_data/ -name '*.sql.gz' -mtime +14 | wc -l
0
$ sudo /opt/lumat/infra/restore-test.sh
restore OK (lumat_restore_test, dump lumat-20260815T231553Z.sql.gz, customers=0 messages=0)
$ sudo crontab -l | grep -E 'backup|restore'
0 3 * * * /opt/lumat/infra/backup.sh >> /var/log/lumat-backup.log 2>&1
0 4 * * 1 /opt/lumat/infra/restore-test.sh >> /var/log/lumat-backup.log 2>&1
```

---

## 8. Monitoring — /health + webhook probe + backup age (SH-3)

`infra/monitor.sh` (T6.6) runs every 5 minutes: checks the `/health` endpoint
(service uptime), POSTs a webhook probe (bot/external API path), and verifies
the newest backup is fresh; on any failure it sends an SMTP alert. Install —
also under **root's crontab** (reads the root-only volume path; see §7):

```bash
sudo crontab -l 2>/dev/null | grep -q monitor.sh || { (sudo crontab -l 2>/dev/null; echo "*/5 * * * * /opt/lumat/infra/monitor.sh >> /var/log/lumat-monitor.log 2>&1") | sudo crontab -; }
sudo crontab -l | grep monitor.sh
```

> The `(crontab -l; echo X) | crontab -` form APPENDS to the existing crontab.
> Do not write `(crontab -l; echo X | crontab -)` — the pipe binds only to the
> echo and REPLACES the whole crontab, wiping §7's backup/restore entries
> (rehearsal-caught, T7.2).

> On the VPS, export the SMTP credentials for the cron job: put `SMTP_HOST`,
> `SMTP_PORT`, `SMTP_FROM`, `SMTP_TO`, `SMTP_USER`, `SMTP_PASS` in
> `/etc/environment` (read by cron via pam_env) — values never in the repo
> (SH-2; `infra/.env.example` documents the names).

Verify — healthy run exits 0 and prints OK lines:

```bash
sudo /opt/lumat/infra/monitor.sh; echo "exit=$?"
tail -5 /var/log/lumat-monitor.log
```

Expected: `health=OK`, `webhook_probe=OK`, `backup_age=OK` (or the equivalent
lines), `exit=0`. **Alert drill**: stop the api container for 60 s — the next
5-min run must exit non-zero and the SMTP alert must arrive; restart the
container (`docker start lumat-api-1`).

- [x] **SH-3 monitoring verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ sudo /opt/lumat/infra/monitor.sh; echo "exit=$?"
[2026-08-15T23:16:07Z] health=OK
[2026-08-15T23:16:07Z] webhook_probe=OK (unsigned POST rejected 403)
[2026-08-15T23:16:07Z] backup_age=OK (lumat-20260815T231553Z.sql.gz, 14s old)
exit=0
# alert drill (api stopped):
[2026-08-15T23:16:23Z] ALERT: health=FAIL webhook_probe=FAIL(HTTP 000000)
/opt/lumat/infra/monitor.sh: line 34: SMTP_HOST: SMTP_HOST unset — cannot send monitoring alert
# drill exit=1; api restarted -> healthy. SMTP delivery verified on the VPS at T7.2
# (failure path + env guard verified in T6.6).
```

---

## 9. Audit log — append-only, admin-read (SH-5)

The `app` DB role must have INSERT + SELECT only on `audit_log` (no
UPDATE/DELETE/TRUNCATE/REFERENCES) — enforced by `db/migrations/001_init.sql`
and re-verified here:

```bash
docker exec lumat-db-1 psql -U lumat -d lumat -Atc \
  "SELECT grantee || ':' || privilege_type FROM information_schema.role_table_grants
   WHERE table_name='audit_log' ORDER BY 1;"
```

Expected output — the only rows for the `app` role are INSERT/SELECT (plus
the admin role's full privileges):

```
app:INSERT
app:SELECT
```

Verify a write other than INSERT is rejected:

```bash
docker exec lumat-db-1 psql -U app -d lumat -c \
  "DELETE FROM audit_log;"    # ERROR: permission denied for table audit_log
```

Expected: `ERROR: permission denied for table audit_log` (or
`ERROR: must be owner of table audit_log` under the app role).

- [x] **SH-5 audit grants verified — 2026-08-15 (VM):**

```bash
# pasted real output here:
$ docker exec lumat-db-1 psql -U lumat -d lumat -Atc "SELECT grantee || ':' || privilege_type FROM information_schema.role_table_grants WHERE table_name='audit_log' ORDER BY 1;"
app:INSERT
app:SELECT
lumat:DELETE
lumat:INSERT
lumat:REFERENCES
lumat:SELECT
lumat:TRIGGER
lumat:TRUNCATE
lumat:UPDATE
$ docker exec lumat-db-1 psql -U app -d lumat -c "DELETE FROM audit_log;"
ERROR:  permission denied for table audit_log
$ docker exec lumat-db-1 psql -U app -d lumat -c "UPDATE audit_log SET action='x';"
ERROR:  permission denied for table audit_log
$ docker exec lumat-db-1 psql -U app -d lumat -Atc "INSERT INTO audit_log (actor, action, entity) VALUES ('rehearsal','probe','audit_log') RETURNING id;"
1
```

---

## Execution record

| Date | Executor | Sections verified | Notes / deviations |
|------|----------|------------------|--------------------|
| 2026-08-15 | dev (T7.1) | 1–9 on local Ubuntu 24.04 rehearsal VM (libvirt/KVM, Docker 29 + Compose v2.40, ufw, fail2ban) | §4 self-signed cert at the LE live paths (no public DNS locally); §7/§8 crons under root (volume path root-only; api container stays non-root); §8 SMTP delivery VPS-only (env guard verified); VPS re-run of the full checklist + real LE issuance + `certbot renew --dry-run` at T7.2 go-live |
| 2026-08-16 | dev (T7.2) | §7/§8 re-verified during the clean-deploy rehearsal (fresh clone into `/opt/lumat`, db volume wiped, full stack + migrate + seed + smoke; record in `docs/ops.md` §2.1.1) | §8 cron command fixed (append not replace — see note above); §1–§6/§9 unchanged, still valid on the same VM; real LE issuance + `certbot renew --dry-run` + SMTP delivery remain VPS-only |
|      |          |                  |                    |

> If any check does NOT match its expected output, STOP and fix it before
> go-live (T7.3). Record the deviation above, then re-run the failed block.
