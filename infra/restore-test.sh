#!/usr/bin/env bash
# Weekly backup restore drill (SH-3): newest dump -> scratch database
# `lumat_restore_test`, verify row counts, report. Fixed commands only — no
# user-controlled arguments (threat matrix N/A).
#
# Cron entry (docs/hardening.md §7):
#   0 4 * * 1 /opt/lumat/infra/restore-test.sh >> /var/log/lumat-backup.log 2>&1
set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$INFRA_DIR")"

COMPOSE_FILES=(-f "$INFRA_DIR/docker-compose.yml")
if [ -f "$INFRA_DIR/docker-compose.prod.yml" ]; then
    COMPOSE_FILES+=(-f "$INFRA_DIR/docker-compose.prod.yml")
fi

if docker volume inspect lumat_backups >/dev/null 2>&1; then
    BACKUPS_DIR="$(docker volume inspect -f '{{.Mountpoint}}' lumat_backups)"
else
    BACKUPS_DIR="$REPO_DIR/backups"
fi

NEWEST="$(ls -1t "$BACKUPS_DIR"/lumat-*.sql.gz 2>/dev/null | head -1 || true)"
if [ -z "$NEWEST" ]; then
    echo "restore FAIL: no backup found in $BACKUPS_DIR" >&2
    exit 1
fi

DB=postgres
SCRATCH=lumat_restore_test

docker compose --project-name lumat "${COMPOSE_FILES[@]}" exec -T db \
    psql -U lumat -d "$DB" -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS $SCRATCH" -c "CREATE DATABASE $SCRATCH" >/dev/null

gunzip -c "$NEWEST" | docker compose --project-name lumat "${COMPOSE_FILES[@]}" \
    exec -T db psql -U lumat -d "$SCRATCH" -v ON_ERROR_STOP=1 >/dev/null

CUSTOMERS="$(docker compose --project-name lumat "${COMPOSE_FILES[@]}" exec -T db \
    psql -U lumat -d "$SCRATCH" -Atc "SELECT count(*) FROM customers")"
MESSAGES="$(docker compose --project-name lumat "${COMPOSE_FILES[@]}" exec -T db \
    psql -U lumat -d "$SCRATCH" -Atc "SELECT count(*) FROM messages")"

echo "restore OK (lumat_restore_test, dump $(basename "$NEWEST"), customers=$CUSTOMERS messages=$MESSAGES)"
