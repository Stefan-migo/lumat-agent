# LumatAgent — certbot (Let's Encrypt) + renewal (T7.1)

Reverse proxy and TLS run in containers (see `infra/docker-compose.prod.yml`):
nginx terminates TLS on 80/443 and proxies the api; the `certbot` compose
service issues and renews certificates through the **webroot** challenge into
the `certbot-certs` volume that nginx mounts read-only. Renewal is driven by a
host systemd timer (`lumat-certbot-renew.{service,timer}` in this directory).

Hostnames — a single certificate with two SANs (`certbot -d agente.lumat.cl
-d panel.lumat.cl`), DNS `A` records must point at the VPS (client, week 1–2):

- `agente.lumat.cl` — bot API (webhook + health + panel)
- `panel.lumat.cl` — admin panel

## 1. First issuance (VPS, after DNS propagates)

```bash
cd /opt/lumat
# `--project-name lumat` is REQUIRED on every compose command in this file:
# without it Compose derives the project name from the `infra/` directory, so
# the certbot container mounts `infra_certbot-certs` / `infra_certbot-webroot`
# instead of the `lumat_*` volumes nginx actually reads. `run` also needs
# `GIT_SHA` exported, because the prod override guards
# `services.api.build.args.GIT_SHA` with `${GIT_SHA:?}` and `run` interpolates
# the whole file even for a service that does not build.
GIT_SHA=$(git rev-parse --short HEAD) docker compose --project-name lumat \
  --profile certbot -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot \
  -d agente.lumat.cl -d panel.lumat.cl \
  --email ops@lumat.cl --agree-tos --no-eff-email
```

Then reload nginx so it picks up the `live/` symlinks:

```bash
docker compose --project-name lumat -f infra/docker-compose.yml -f infra/docker-compose.prod.yml exec nginx nginx -s reload
```

Verify: `curl -sI https://agente.lumat.cl/health` → `200`;
`curl -sI http://agente.lumat.cl/health` → `301` (redirect to HTTPS).

## 2. Renewal — systemd timer (VPS)

The certbot service default command is `renew --webroot -w /var/www/certbot`.
A systemd timer checks twice daily and reloads nginx after each run (reload is
harmless when nothing renewed):

```bash
sudo cp infra/certbot/lumat-certbot-renew.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lumat-certbot-renew.timer
systemctl list-timers | grep lumat-certbot
```

Manual dry run:

```bash
cd /opt/lumat
GIT_SHA=$(git rev-parse --short HEAD) docker compose --project-name lumat \
  --profile certbot -f infra/docker-compose.yml \
  -f infra/docker-compose.prod.yml run --rm certbot renew \
  --webroot -w /var/www/certbot --dry-run
```

> Pass `renew` its full command, not just `--dry-run`: overriding the service
> command with a bare `renew --dry-run` drops the webroot arguments.

Expected: `Congratulations, all simulated renewals succeeded`.

## 3. Local rehearsal without public DNS (T7.1 VM)

Let's Encrypt cannot issue without a public `A` record, so the rehearsal VM
uses a **self-signed certificate** placed at the *same* live paths the nginx
confs read — `/etc/letsencrypt/live/agente.lumat.cl/{fullchain,privkey}.pem`
inside the `certbot-certs` volume — with both hostnames as SANs. The nginx
server blocks are byte-for-byte the same as the VPS, which is exactly the
point of the rehearsal: the TLS config is validated locally, and only the
cert source changes on the real VPS (commands in §1–§2).

## 4. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| nginx `502` on /health | api container not healthy yet — `docker compose ps`; healthcheck `start_period` covers migrations |
| `certbot` container exits non-zero | DNS not pointing at the VPS, or port 80 blocked by the firewall — see `docs/hardening.md` §1 |
| nginx serves an old cert | run `docker compose --project-name lumat exec nginx nginx -s reload` (the renew timer does this automatically) |
| Renewal exits 0 but the served cert keeps aging | the command omitted `--project-name lumat`, so certbot renewed into `infra_certbot-certs` while nginx reads `lumat_certbot-certs` — compare `docker volume ls` against the volumes `lumat-nginx-1` mounts, and check `docker compose --project-name lumat --profile certbot ... run --rm certbot certificates` finds the lineage |
