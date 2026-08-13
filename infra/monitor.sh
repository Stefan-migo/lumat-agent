#!/usr/bin/env bash
# 5-minute monitoring probe (SH-3): service uptime via the public /health,
# webhook signature-gate POST probe, and backup freshness. Any failed check
# exits 1 and sends an SMTP alert. Fixed commands only — no user-controlled
# arguments (threat matrix N/A).
#
# Cron entry (docs/hardening.md §8):
#   */5 * * * * /opt/lumat/infra/monitor.sh >> /var/log/lumat-monitor.log 2>&1
#
# SMTP alert uses curl (stdlib — no local MTA, no extra deps) with the
# credentials read from the SERVER environment (SH-2: secrets never in the
# repo): SMTP_HOST, SMTP_PORT (default 587), SMTP_FROM, SMTP_TO,
# SMTP_USER/SMTP_PASS (leave unset for an unauthenticated relay).
set -euo pipefail

HEALTH_URL="https://agente.lumat.cl/health"
WEBHOOK_URL="https://agente.lumat.cl/webhook/whatsapp"
BACKUP_MAX_AGE_SECONDS=93600  # 26 h — daily dump at 03:00, enough slack

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$INFRA_DIR")"
LOG_TAG="[$(date -u +%FT%TZ)]"

if docker volume inspect lumat_backups >/dev/null 2>&1; then
    BACKUPS_DIR="$(docker volume inspect -f '{{.Mountpoint}}' lumat_backups)"
else
    BACKUPS_DIR="$REPO_DIR/backups"
fi

alert() {
    : "${SMTP_HOST:?SMTP_HOST unset — cannot send monitoring alert}"
    : "${SMTP_FROM:?SMTP_FROM unset — cannot send monitoring alert}"
    : "${SMTP_TO:?SMTP_TO unset — cannot send monitoring alert}"
    local subject="$1" port="${SMTP_PORT:-587}"
    local body
    body="From: <${SMTP_FROM}>
To: <${SMTP_TO}>
Subject: [lumat] monitoring alert: ${subject}
Date: $(date -R)

Lumat monitoring failure on $(hostname) at $(date -u -Iseconds):
${subject}
"
    if [ -n "${SMTP_USER:-}" ]; then
        curl -fsS --max-time 15 --ssl-reqd --url "smtp://${SMTP_HOST}:${port}" \
            --mail-from "${SMTP_FROM}" --mail-rcpt "${SMTP_TO}" \
            --user "${SMTP_USER}:${SMTP_PASS}" --upload-file - <<<"$body"
    else
        curl -fsS --max-time 15 --ssl-reqd --url "smtp://${SMTP_HOST}:${port}" \
            --mail-from "${SMTP_FROM}" --mail-rcpt "${SMTP_TO}" --upload-file - <<<"$body"
    fi
}

failures=""

# 1. service uptime — public /health through nginx + TLS.
if curl -fsS --max-time 10 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "$LOG_TAG health=OK"
else
    failures="${failures}health=FAIL "
fi

# 2. webhook signature gate — an UNSIGNED POST must be rejected 403: proves
#    the endpoint is up AND the gate drops payloads (never persisted).
code="$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
    -X POST -H 'Content-Type: application/json' -d '{"probe":true}' \
    "$WEBHOOK_URL" 2>/dev/null || echo 000)"
if [ "$code" = "403" ]; then
    echo "$LOG_TAG webhook_probe=OK (unsigned POST rejected 403)"
else
    failures="${failures}webhook_probe=FAIL(HTTP $code) "
fi

# 3. backup freshness — the newest dump must be younger than 26 h.
newest="$(ls -1t "$BACKUPS_DIR"/lumat-*.sql.gz 2>/dev/null | head -1 || true)"
if [ -z "$newest" ]; then
    failures="${failures}backup_age=FAIL(no dump in $BACKUPS_DIR) "
else
    age="$(( $(date +%s) - $(stat -c %Y "$newest") ))"
    if [ "$age" -le "$BACKUP_MAX_AGE_SECONDS" ]; then
        echo "$LOG_TAG backup_age=OK ($(basename "$newest"), ${age}s old)"
    else
        failures="${failures}backup_age=FAIL(${age}s old) "
    fi
fi

if [ -n "$failures" ]; then
    echo "$LOG_TAG ALERT: ${failures}" >&2
    alert "$failures"
    exit 1
fi
exit 0
