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

# `port` and `project` are pure derivation. `up` and `env` need the dev
# credentials, which are declared once in infra/.env.
require_env_file() {
    if [[ ! -f "$ROOT_DIR/infra/.env" ]]; then
        printf 'Missing %s. Copy it with: cp ../lumat-agent/infra/.env infra/.env\n' \
            "$ROOT_DIR/infra/.env" >&2
        exit 1
    fi
}

# Read one KEY=value out of infra/.env WITHOUT sourcing it. Sourcing would export
# DATABASE_URL (which points at the compose `db` service, host `db`) and poison
# the derived test URL. Only the superuser password of `db-test` is needed here;
# tests/_testdb.py refuses to invent it.
env_file_value() {
    sed -n "s/^$1=//p" "$ROOT_DIR/infra/.env" | tail -n 1 | sed 's/^"\(.*\)"$/\1/'
}

case "$command_name" in
    port|project)
        exec "$PYTHON" "$TESTDB" "$command_name"
        ;;
    env)
        require_env_file
        TEST_POSTGRES_PASSWORD="$(env_file_value TEST_POSTGRES_PASSWORD)"
        export TEST_POSTGRES_PASSWORD
        exec "$PYTHON" "$TESTDB" env
        ;;
    up|down)
        if [[ "$command_name" == up ]]; then
            require_env_file
        fi
        if [[ -f "$ROOT_DIR/infra/.env" ]]; then
            TEST_POSTGRES_PASSWORD="$(env_file_value TEST_POSTGRES_PASSWORD)"
            export TEST_POSTGRES_PASSWORD
        else
            export POSTGRES_PASSWORD=teardown-placeholder
            export APP_SECRET=teardown-placeholder
            export VERIFY_TOKEN=teardown-placeholder
            export DATABASE_URL=postgresql://teardown-placeholder
            export META_ACCESS_TOKEN=teardown-placeholder
            export META_PHONE_NUMBER_ID=teardown-placeholder
            export PANEL_SESSION_SECRET=teardown-placeholder
        fi
        port="$($PYTHON "$TESTDB" port)"
        project="$($PYTHON "$TESTDB" project)"
        export TEST_DB_PORT="$port"
        compose=(docker compose)
        if [[ -f "$ROOT_DIR/infra/.env" ]]; then
            compose+=(--env-file "$ROOT_DIR/infra/.env")
        fi
        compose+=(-p "$project" -f "$ROOT_DIR/infra/docker-compose.yml" --profile test)
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
