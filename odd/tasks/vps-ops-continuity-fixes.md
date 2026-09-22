# ODD: vps-ops-continuity-fixes

## Objective

Make the repository's production-continuity tooling describe and implement what actually works, so a
re-provision of the VPS cannot reproduce the two silent failures found on 2026-09-22: no database
backups, and a certificate renewal that had never renewed anything.

This is a **repo-side** change. The server was already repaired by hand the same day; every file here
now matches the artefact that was verified live on the host.

## Problem (verified on the VPS, 2026-09-22)

The `v2026.09.2` catch-up deploy pre-flight exposed two mechanisms that were dead while the system
looked healthy — containers up, TLS valid, `/health` returning 200, no alert ever fired.

1. **No backups had ever run.** `root` had **no crontab at all** (`no crontab for root`), so
   `infra/backup.sh`, `infra/restore-test.sh` and `infra/monitor.sh` were never scheduled. The
   `lumat_backups` volume existed but was empty, and `lumat_restore_test` had never been created.
   The scripts are written for **root's** crontab because the volume host path
   `/var/lib/docker/volumes/…` is root-only: run as `deploy` they die with `Permission denied` on the
   mountpoint, which is why the volume looked "created but never filled".

2. **The certificate renewal had never renewed the served certificate.**
   `infra/certbot/lumat-certbot-renew.service` omitted `--project-name lumat` on both commands.
   Without it Compose derives the project name from the `infra/` directory, so the container mounted
   `infra_certbot-certs` / `infra_certbot-webroot` instead of the `lumat_certbot-certs` volume nginx
   reads. `infra_certbot-certs` contained only `renewal-hooks/` — no `live/`, no `archive/` — so
   `renew` found no lineage, exited 0, and the unit's `ExecStartPost` then failed on
   `services.api.build.args.GIT_SHA: required variable GIT_SHA is missing a value`. The unit showed
   `failed`; the certificate nginx served (`notAfter=Dec 7 12:45:24 2026 GMT`) was never touched.

Two further defects surfaced while repairing the above:

3. **`monitor.sh` cannot alert on its own.** It reads `SMTP_HOST`/`SMTP_FROM`/`SMTP_TO` from the
   environment, and nothing provided them in a cron context, so every check could pass while every
   alert died on `SMTP_HOST unset`. A monitor that cannot alert is a false sense of safety.

4. **Two runbook steps cannot execute as written.** `docs/ops.md` §2.1/§2.2 run
   `docker run --rm lumat-nginx:prod nginx -t`, which can never pass: the server blocks proxy to the
   `api` service name, which does not resolve off the compose network (`host not found in upstream
   "api"`). The step had never been a real check. Separately, `docs/hardening.md` §7 installs the
   backup crontab with `sudo crontab /tmp/cron`, which **replaces** root's crontab — the exact trap
   §8 documents for the append form.

## Root cause, in one line

Both silent failures are the same shape: a command that "succeeds" (exit 0) while doing nothing,
because a scope was resolved differently than the author assumed — a crontab that was never
installed, and a Compose project name derived from a directory.

## What changed

| File | Change |
|---|---|
| `infra/certbot/lumat-certbot-renew.service` | `--project-name lumat` on the compose command; `ExecStart` resolves the SHA with `git -c safe.directory=/opt/lumat` (the unit runs as root while the checkout belongs to `deploy` — `detected dubious ownership` otherwise); `ExecStartPost` reloads nginx with a direct `docker exec lumat-nginx-1`, so that step needs neither project-name resolution nor `GIT_SHA` (see the review outcome below). |
| `infra/certbot/README.md` | The documented commands carry `--project-name lumat` and the `GIT_SHA` export; the dry-run passes `renew` its full command (a bare `renew --dry-run` drops the webroot arguments); troubleshooting row for "renewal exits 0 but the cert keeps aging". |
| `infra/monitor.sh` | Loads `infra/.env` when present, so the alert path has credentials without depending on how the cron was written. |
| `docs/ops.md` | §2.1/§2.2 validate nginx **inside** the compose network after `up -d` instead of a standalone `nginx -t` that can never pass; change-log entry. |
| `docs/hardening.md` | §7 installs root's crontab by merging instead of replacing it. |

## Authorized scope

`infra/certbot/**`, `infra/monitor.sh`, `docs/ops.md`, `docs/hardening.md`, this work-unit record.

## Out of scope

- `infra/backup.sh` and `infra/restore-test.sh` keep requiring root; making them root-free (writing
  and reading the volume through a container) is a larger design change and is not needed while the
  documented cron runs under root.
- arming the outbox worker (`app/ops/worker.py` has no runner in production).
- Adding `ASSISTANT_CHAT_PROVIDER` / `ASSISTANT_CHAT_MODEL` to the server's `infra/.env`; today the
  compose defaults (`deepseek` / `deepseek-chat`) apply. That is a product decision, not a defect.

## Verification

Verified live on the VPS the same day, with the corrected artefacts (the deploy-host equivalents of
the files above):

- `backup OK … (16K)` and `restore OK (lumat_restore_test, dump lumat-20260922T155300Z.sql.gz,
  customers=0 messages=0)` — a real restore into a scratch database, not just a file copy.
- `monitor.sh` with `infra/.env` loaded: `health=OK`, `webhook_probe=OK`, `backup_age=OK`, `exit=0`.
- Unit after the fix: `result: success`, `ExecStart` and `ExecStartPost` both `status=0/SUCCESS`
  (the reload had been failing since 2026-09-21).
- `certbot renew … --dry-run`: `Processing /etc/letsencrypt/renewal/agente.lumat.cl.conf` →
  `Simulating renewal of an existing certificate for agente.lumat.cl and panel.lumat.cl` →
  `Congratulations, all simulated renewals succeeded`. Finding that renewal config inside the
  `lumat_certbot-certs` store is the proof that the project-name fix points certbot at the volume
  nginx reads.
- `infra_certbot-certs` / `infra_certbot-webroot` (created by the defect) removed.

In the repository the change is docs + shell/systemd only: `bash -n infra/monitor.sh` for syntax, and
a line-by-line diff against the artefacts verified on the host.

## Review outcome (native 4R) and the `ExecStartPost` change

The first candidate was reviewed by the native 4R flow (lineage `review-d3330565ffc2346b`) and closed
**`escalated`**, not `approved`: the reliability lens raised `R3-certbot-env` (CRITICAL,
`causal_disposition: unknown`) against `infra/certbot/lumat-certbot-renew.service`, claiming that
`ExecStartPost` invokes Compose without `GIT_SHA` and could therefore fail, leaving the reload broken.

Measured on the host, the claim does not hold as written. The exact `ExecStartPost` of that candidate
reported `(code=exited, status=0/SUCCESS)`; the same command run by hand as `deploy` returned 0; and
the same command **without** `--project-name` is the one that fails on the `${GIT_SHA:?}` guard. The
discriminator is the project name, which the candidate already passed. The lens cannot execute
commands — it reasons statically over the frozen patch, which is why its conclusion was plausible
from the diff and wrong about the behaviour.

The change was made anyway, for the part the measurement does not answer: the **asymmetry was real
and unexplained** — why should one line need `GIT_SHA` and the other not? — and this step's failure
path is silent. Nothing alerts on a failed systemd unit, so a broken reload would leave nginx
serving a certificate that expires with no warning: the same class of silent failure this work unit
exists to remove. `ExecStartPost` now goes straight to the running container
(`/usr/bin/docker exec lumat-nginx-1 nginx -s reload`), verified `exit 0` on the host, and no longer
depends on Compose interpolation at all.

## Progress

- [x] Root causes identified with host evidence (`chage`, `docker volume ls`, `systemctl show`, the
      unit journal, `openssl s_client` against the live certificate).
- [x] Server repaired and verified (crontab, unit, monitor, dry-run, cleanup).
- [x] The same defects corrected in the repository.
- [x] Verified: `bash -n` on the touched script, and the repo files match the live-verified artefacts.
- [x] Native 4R review run and resolved: escalated on `R3-certbot-env`, the claim disproved by host
      execution, and `ExecStartPost` hardened anyway against the silent-failure path it pointed at.
