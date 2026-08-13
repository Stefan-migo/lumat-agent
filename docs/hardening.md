# LumatAgent — Server Hardening Checklist (SH-1..SH-3)

> Change: `hito-1-setup-whatsapp` · Task: **T6.4** · Executed on the H1 VPS during **T7.1**
> Target: Hostinger KVM 2 — Ubuntu LTS (São Paulo), Docker + Compose
> Hosts: `agente.lumat.cl` (bot API) · `panel.lumat.cl` (admin panel)
> How to use: run every block as `root` (sections 1–4) or `deploy` (5–9) on the
> production server; paste the real output under each block; tick the box with
> date + initials when the expected output matches. The go-live record in
> `docs/ops.md` §10 links to this executed checklist.

| # | Check | SH req | Status |
|---|-------|--------|--------|
| 1 | Firewall: 80/443/SSH only | SH-1 | ⬜ |
| 2 | SSH key-only + fail2ban | SH-1 | ⬜ |
| 3 | Non-root deploy user | SH-1 | ⬜ |
| 4 | TLS + auto-renew | SH-1 | ⬜ |
| 5 | Container hardening (read-only fs) | SH-2 | ⬜ |
| 6 | Secrets env-only | SH-2 | ⬜ |
| 7 | Backups: schedule + retention | SH-3 | ⬜ |
| 8 | Monitoring: checks + alert | SH-3 | ⬜ |
| 9 | Audit grants append-only | SH-5 | ⬜ |

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

- [ ] **SH-1 firewall verified — date/initials:**

```bash
# pasted real output here:
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

- [ ] **SH-1 SSH verified — date/initials:**

```bash
# pasted real output here:
```

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

- [ ] **SH-1 non-root user verified — date/initials:**

```bash
# pasted real output here:
```

---

## 4. TLS — Let's Encrypt + auto-renew (SH-1)

Prerequisite: DNS `A` records for `agente.lumat.cl` and `panel.lumat.cl`
pointing at the VPS IP (client, week 1–2).

```bash
apt install -y nginx certbot python3-certbot-nginx
certbot --nginx -d agente.lumat.cl -d panel.lumat.cl
systemctl list-timers | grep certbot
certbot renew --dry-run
```

Expected: `Successfully received certificate` for both domains; the
`certbot.timer` shows `next elapse` (twice-daily renewal check); the dry-run
ends with `Congratulations, all simulated renewals succeeded`.

Verify: `curl -sI https://agente.lumat.cl/health` returns `200`; plain HTTP
redirects to HTTPS (`curl -sI http://agente.lumat.cl/health` → `301`).

- [ ] **SH-1 TLS verified — date/initials:**

```bash
# pasted real output here:
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

Verify against the running container (replace `api` with the actual name):

```bash
docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' lumat-api        # true
docker inspect --format '{{.HostConfig.Privileged}}' lumat-api            # false
docker inspect --format '{{.HostConfig.SecurityOpt}}' lumat-api           # [no-new-privileges:true]
docker inspect --format '{{.HostConfig.CapDrop}}' lumat-api               # [ALL]
grep -n privileged infra/docker-compose.prod.yml || echo "no --privileged flag"
```

Write probe (must FAIL — SH-2 "write outside the writable volume is denied"):

```bash
docker exec lumat-api touch /root/probe.txt
```

Expected: `touch: cannot touch '/root/probe.txt': Read-only file system`.

- [ ] **SH-2 read-only fs verified — date/initials:**

```bash
# pasted real output here:
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
docker exec lumat-api printenv | grep -E 'OPENAI_API_KEY|META_ACCESS_TOKEN|APP_SECRET'
# 4. nothing secret baked into the image:
docker history --no-trunc lumat-api | grep -iE 'secret|token|sk-' || echo "clean"
```

Expected: `git grep` prints nothing (or `clean`); `git check-ignore` prints
`infra/.env`; `printenv` shows the variables; `docker history` shows no
secret material.

- [ ] **SH-2 secrets env-only verified — date/initials:**

```bash
# pasted real output here:
```

---

## 7. Backups — daily pg_dump, 14-day retention (SH-3)

`infra/backup.sh` (T6.6) dumps the `lumat` database to the `backups/` volume
every day at 03:00 and deletes dumps older than 14 days. Install the cron
entry on the server:

```bash
crontab -l 2>/dev/null; cat > /tmp/cron <<'EOF'
0 3 * * * /opt/lumat/infra/backup.sh >> /var/log/lumat-backup.log 2>&1
EOF
crontab /tmp/cron && rm /tmp/cron
crontab -l | grep backup.sh
```

Verify:

```bash
# dumps exist and are non-empty:
ls -lh /var/lib/docker/volumes/lumat_backups/_data/ | tail -5
# retention: nothing older than 14 days
find /var/lib/docker/volumes/lumat_backups/_data/ -name '*.sql.gz' -mtime +14 | wc -l   # 0
# restore drill (weekly, T6.6): see docs/ops.md §3 for the full drill
sudo -u deploy /opt/lumat/infra/restore-test.sh
```

Expected: one dump per day, gzipped, > 0 bytes; the `-mtime +14` count is 0;
`restore-test.sh` exits 0 and prints `restore OK`.

- [ ] **SH-3 backups verified — date/initials:**

```bash
# pasted real output here:
```

---

## 8. Monitoring — /health + webhook probe + backup age (SH-3)

`infra/monitor.sh` (T6.6) runs every 5 minutes: checks the `/health` endpoint
(service uptime), POSTs a webhook probe (bot/external API path), and verifies
the newest backup is fresh; on any failure it sends an SMTP alert. Install:

```bash
crontab -l 2>/dev/null | grep -q monitor.sh || (crontab -l 2>/dev/null; cat > /tmp/cron <<'EOF'
*/5 * * * * /opt/lumat/infra/monitor.sh >> /var/log/lumat-monitor.log 2>&1
EOF
crontab /tmp/cron && rm /tmp/cron)
crontab -l | grep monitor.sh
```

Verify — healthy run exits 0 and prints OK lines:

```bash
sudo -u deploy /opt/lumat/infra/monitor.sh; echo "exit=$?"
tail -5 /var/log/lumat-monitor.log
```

Expected: `health=OK`, `webhook_probe=OK`, `backup_age=OK` (or the equivalent
lines), `exit=0`. **Alert drill**: stop the api container for 60 s — the next
5-min run must exit non-zero and the SMTP alert must arrive; restart the
container (`docker compose up -d`).

- [ ] **SH-3 monitoring verified — date/initials:**

```bash
# pasted real output here:
```

---

## 9. Audit log — append-only, admin-read (SH-5)

The `app` DB role must have INSERT + SELECT only on `audit_log` (no
UPDATE/DELETE/TRUNCATE/REFERENCES) — enforced by `db/migrations/001_init.sql`
and re-verified here:

```bash
docker exec lumat-db psql -U lumat -d lumat -Atc \
  "SELECT grantee || ':' || privilege_type FROM information_schema.role_table_grants
   WHERE table_name='audit_log' ORDER BY 1;"
```

Expected output — the only rows are INSERT/SELECT for the `app` role (and
superuser privileges for the admin role):

```
app:INSERT
app:SELECT
```

Verify a write other than INSERT is rejected:

```bash
docker exec lumat-db psql -U lumat -d lumat -c \
  "DELETE FROM audit_log;"    # ERROR: permission denied for table audit_log
```

Expected: `ERROR: permission denied for table audit_log` (or
`ERROR: must be owner of table audit_log` under the app role).

- [ ] **SH-5 audit grants verified — date/initials:**

```bash
# pasted real output here:
```

---

## Execution record

| Date | Executor | Sections verified | Notes / deviations |
|------|----------|------------------|--------------------|
|      |          |                  |                    |

> If any check does NOT match its expected output, STOP and fix it before
> go-live (T7.3). Record the deviation above, then re-run the failed block.
