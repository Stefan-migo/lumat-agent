#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
TESTDB="$ROOT_DIR/tests/_testdb.py"

command_name="${1:-}"
if [[ -z "$command_name" ]]; then
    printf 'Usage: %s {up|down|env|port|project}\n' "$0" >&2
    exit 2
fi

case "$command_name" in
    port|project)
        exec "$PYTHON" "$TESTDB" "$command_name"
        ;;
    env)
        exec "$PYTHON" "$TESTDB" env
        ;;
    up|down)
        if [[ ! -f "$ROOT_DIR/infra/.env" ]]; then
            printf 'Missing %s. Copy it with: cp ../lumat-agent/infra/.env infra/.env\n' \
                "$ROOT_DIR/infra/.env" >&2
            exit 1
        fi
        port="$($PYTHON "$TESTDB" port)"
        project="$($PYTHON "$TESTDB" project)"
        export TEST_DB_PORT="$port"
        compose=(
            docker compose
            --env-file "$ROOT_DIR/infra/.env"
            -p "$project"
            -f "$ROOT_DIR/infra/docker-compose.yml"
            --profile test
        )
        if [[ "$command_name" == up ]]; then
            exec "${compose[@]}" up -d db-test
        fi
        exec "${compose[@]}" down -v
        ;;
    *)
        printf 'Unknown command: %s\nUsage: %s {up|down|env|port|project}\n' \
            "$command_name" "$0" >&2
        exit 2
        ;;
esac
