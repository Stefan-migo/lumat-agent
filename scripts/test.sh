#!/usr/bin/env bash
# Test tiers — the project's executable test policy (see AGENTS.md → "Test tiers").
#
# Why tiers exist: the full suite is the only run that sees a broken import or a
# changed shared shape, but at ~2.8k tests it costs ~7 minutes. Tiering keeps
# that authority at the boundaries where only it can catch the failure, instead
# of paying for it once per work unit.
#
#   gate      T0  collection only — imports every test module and app module.
#                 No database, no environment file. Catches the NameError /
#                 import class that escapes a subset.
#   unit      T1  tests/unit — no database. The cheap layer (~14s).
#   quick     T0+T1: what an edit iteration is expected to pass.
#   focused   T1  exactly the tests of the rule under RED/GREEN.
#   db        T2  the database-backed layer for the surface you touched.
#   full      T3  the whole suite (~7min). Mandatory at the boundaries below.
#   shape     tells you whether `full` is mandatory: exits 3 when the diff
#                 touches a shape surface, 0 otherwise.
#
# Full suite is mandatory at: feature closure, before opening a PR, after
# merging origin/main into the branch, and whenever `shape` exits 3.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
TEST_DB="$ROOT_DIR/infra/test-db.sh"

usage() {
    cat >&2 <<'EOF'
Usage: scripts/test.sh <tier> [args...]

  gate                 collection only, no database (catches broken imports)
  unit                 tests/unit, no database
  quick                gate + unit — the per-edit iteration gate
  focused <path...>    exactly these tests (database env only if a path is
                       outside tests/unit)
  db <path...>         these tests, with the test database environment
  full [pytest args]   the whole suite
  shape [<git-ref>]    exit 3 when the diff against <git-ref> (default HEAD)
                       touches a shape surface, 0 otherwise
EOF
}

# Surfaces whose change invalidates every targeted selection: the models, the
# harness every test imports, the settings contract, the schema, the prompt
# shape the unit layer asserts, and the two serializer modules inside import
# cycles. Keep this list in step with AGENTS.md → "Test tiers".
matches_shape() {
    case "$1" in
        app/models.py \
        | app/config.py \
        | app/panel/api/serializers.py \
        | app/services/project_config.py \
        | tests/conftest.py \
        | tests/*/conftest.py \
        | tests/_testdb.py \
        | tests/webhook_helpers.py \
        | agent/registry.yaml \
        | agent/prompts/* \
        | agent/personas/* \
        | db/migrations/*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Export the isolated test-database environment for this worktree. Never source
# infra/.env directly: it exports DATABASE_URL for the compose `db` service and
# poisons the derived test URL.
with_test_db() {
    local exported
    if ! exported="$("$TEST_DB" env)"; then
        printf 'test database environment unavailable. Fix: cp ../lumat-agent/infra/.env infra/.env, then `infra/test-db.sh up`.\n' >&2
        return 1
    fi
    eval "$exported"
    "$@"
}

tier_gate() {
    "$PYTHON" -m pytest tests/ --collect-only -q
}

tier_unit() {
    "$PYTHON" -m pytest tests/unit -q
}

tier_focused() {
    if (($# == 0)); then
        printf 'focused needs at least one test path\n' >&2
        return 2
    fi
    local path needs_db=0
    for path in "$@"; do
        case "$path" in
            tests/unit/* | tests/unit) ;;
            *) needs_db=1 ;;
        esac
    done
    if ((needs_db)); then
        with_test_db "$PYTHON" -m pytest "$@" -q
    else
        "$PYTHON" -m pytest "$@" -q
    fi
}

tier_db() {
    if (($# == 0)); then
        printf 'db needs at least one test path\n' >&2
        return 2
    fi
    with_test_db "$PYTHON" -m pytest "$@" -q
}

tier_full() {
    with_test_db "$PYTHON" -m pytest tests/ -q "$@"
}

tier_shape() {
    local base="${1:-HEAD}" changed path hit=0
    # A typo'd ref must never read as "no shape surface": validate it first.
    if ! git -C "$ROOT_DIR" rev-parse --verify --quiet "$base" >/dev/null; then
        printf 'shape: unknown git revision: %s\n' "$base" >&2
        return 2
    fi
    changed="$(git -C "$ROOT_DIR" diff --name-only "$base")"
    changed+=$'\n'"$(git -C "$ROOT_DIR" ls-files --others --exclude-standard)"
    if [[ -z "${changed//[[:space:]]/}" ]]; then
        printf 'shape: no changes against %s -> full suite not required\n' "$base"
        return 0
    fi
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        if matches_shape "$path"; then
            printf 'shape: %s\n' "$path"
            hit=1
        fi
    done <<<"$changed"
    if ((hit)); then
        printf 'shape: a shape surface changed -> run `scripts/test.sh full`\n'
        return 3
    fi
    printf 'shape: no shape surface touched -> targeted tiers are safe\n'
}

command_name="${1:-}"
[[ -n "$command_name" ]] || { usage; exit 2; }
shift || true

case "$command_name" in
    gate) tier_gate "$@" ;;
    unit) tier_unit "$@" ;;
    quick)
        tier_gate
        tier_unit
        ;;
    focused) tier_focused "$@" ;;
    db) tier_db "$@" ;;
    full) tier_full "$@" ;;
    shape) tier_shape "$@" ;;
    -h | --help | help) usage ;;
    *)
        printf 'unknown tier: %s\n' "$command_name" >&2
        usage
        exit 2
        ;;
esac
