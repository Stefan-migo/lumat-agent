#!/usr/bin/env bash
# Daily PostgreSQL backup (SH-3): pg_dump the lumat DB into the compose
# `backups` volume, 14-day retention. Fixed commands only — no user-controlled
# arguments (threat matrix N/A).
#
# Cron entry (docs/hardening.md §7):
#   0 3 * * * /opt/lumat/infra/backup.sh >> /var/log/lumat-backup.log 2>&1
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$INFRA_DIR")"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Compose invocation: base file + prod override when present (created in T7.1).
# `--project-name lumat` pins the resource names (lumat-db, lumat_backups)
# regardless of the checkout directory name.
COMPOSE_FILES=(-f "$INFRA_DIR/docker-compose.yml")
if [ -f "$INFRA_DIR/docker-compose.prod.yml" ]; then
    COMPOSE_FILES+=(-f "$INFRA_DIR/docker-compose.prod.yml")
fi

# Backups live in the compose `backups` volume; fall back to <repo>/backups
# when the stack has never been brought up (dev machine, volume absent).
if docker volume inspect lumat_backups >/dev/null 2>&1; then
    BACKUPS_DIR="$(docker volume inspect -f '{{.Mountpoint}}' lumat_backups)"
else
    BACKUPS_DIR="$REPO_DIR/backups"
    mkdir -p "$BACKUPS_DIR"
fi

OUT_FILE="$BACKUPS_DIR/lumat-$STAMP.sql.gz"

docker compose --project-name lumat "${COMPOSE_FILES[@]}" exec -T db \
    pg_dump -U lumat -d lumat | gzip > "$OUT_FILE"

# 14-day retention (SH-3): anything older than 14 days is deleted.
find "$BACKUPS_DIR" -name 'lumat-*.sql.gz' -mtime +14 -delete

echo "backup OK: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
