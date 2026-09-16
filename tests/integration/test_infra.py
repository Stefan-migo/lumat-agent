"""T1.3 integration tests — local dev env (compose + .env.example, SH-2).

Static checks that don't require a running Docker daemon:

- infra/docker-compose.yml defines `api` + `db` (pgvector) services and the
  db/media/backups volumes (design deployment step 1)
- infra/.env.example documents ALL required env names as placeholders
  (secrets never in repo — SH-2), with no real credential values
- .gitignore keeps `.env`, `media/` and `backups/` out of the repo

The runtime acceptance (docker compose up -> api /health OK, pgvector ready,
migrate.sh in container) is verified live in the apply harness.
"""

from pathlib import Path
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / "infra" / "docker-compose.yml"
ENV_EXAMPLE = REPO_ROOT / "infra" / ".env.example"
GITIGNORE = REPO_ROOT / ".gitignore"

# Scripts invoked directly by the deploy path (compose container command,
# cron entries, ops.md) — the git index MUST carry the +x bit.
EXECUTABLE_SCRIPTS = (
    REPO_ROOT / "db" / "migrate.sh",
    REPO_ROOT / "db" / "seed.sh",
    REPO_ROOT / "infra" / "backup.sh",
    REPO_ROOT / "infra" / "monitor.sh",
    REPO_ROOT / "infra" / "restore-test.sh",
)

REQUIRED_ENV_NAMES = {
    "APP_SECRET",
    "VERIFY_TOKEN",
    "DATABASE_URL",
    "CHAT_PROVIDER",
    "DEEPSEEK_API_KEY",
    "OPENROUTER_API_KEY",
    "CHAT_MODEL",
    "EMBED_MODEL",
    "EMBED_DIMS",
    "META_ACCESS_TOKEN",
    "META_PHONE_NUMBER_ID",
    "POSTGRES_PASSWORD",
}

# values that look like real credentials — .env.example must not contain them
SECRET_PATTERNS = ("sk-", "sha256:", "AKIA", "ghp_", "xoxb-")
# documented non-secret dev defaults (not credentials)
ALLOWED_PLAIN_VALUES = {
    "app",
    "lumat",
    "deepseek",  # CHAT_PROVIDER default
    "deepseek-chat",  # CHAT_MODEL default
    "deepseek-flash",  # ASSISTANT_CHAT_MODEL default
    "384",  # EMBED_DIMS default
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # EMBED_MODEL default
}


def _load_compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


def test_compose_file_exists():
    assert COMPOSE.exists(), "infra/docker-compose.yml missing"
    assert COMPOSE.read_text().strip(), "infra/docker-compose.yml empty"


def test_compose_defines_api_and_db_services():
    compose = _load_compose()
    services = compose.get("services", {})
    assert "api" in services, "compose missing api service"
    assert "db" in services, "compose missing db service"


def test_db_service_uses_pgvector_image():
    compose = _load_compose()
    db = compose["services"]["db"]
    assert "pgvector" in db["image"], "db image must be pgvector"
    assert "POSTGRES_PASSWORD" in db.get("environment", {}).get("POSTGRES_PASSWORD", "").__str__() or \
        db.get("environment", {}).get("POSTGRES_PASSWORD"), "db must receive POSTGRES_PASSWORD"


def test_compose_declares_db_media_backups_volumes():
    compose = _load_compose()
    volumes = compose.get("volumes", {})
    for name in ("db", "media", "backups"):
        assert name in volumes, f"compose missing volume: {name}"


def test_api_service_wires_health_endpoint_port():
    compose = _load_compose()
    api = compose["services"]["api"]
    ports = api.get("ports", [])
    assert any("8000" in p for p in ports), "api must expose port 8000"


def test_env_example_exists_and_has_required_names():
    assert ENV_EXAMPLE.exists(), "infra/.env.example missing"
    content = ENV_EXAMPLE.read_text()
    for name in REQUIRED_ENV_NAMES:
        assert name in content, f".env.example missing env name: {name}"


def test_env_example_has_no_real_secrets():
    """SH-2: secrets never in repo — .env.example carries placeholders only."""
    content = ENV_EXAMPLE.read_text()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert "=" in line, f".env.example line has no '=': {line!r}"
        _key, _, value = line.partition("=")
        assert value.strip(), f".env.example key {_key!r} has empty value"
        assert not any(p in value for p in SECRET_PATTERNS), (
            f".env.example {_key!r} looks like a real secret: {value!r}"
        )
        # placeholder convention: documented token or explicit dev default
        # (e.g. APP_DB_PASSWORD=app for the local role), never a live credential
        assert (
            "change-me" in value
            or "your-" in value
            or value in ALLOWED_PLAIN_VALUES
            # DATABASE_URL embeds the same documented dev role (app:app)
            or "app:app@" in value
        ), (
            f".env.example {_key!r} value is not an obvious placeholder: {value!r}"
        )


def test_gitignore_covers_secrets_and_runtime_data():
    content = GITIGNORE.read_text()
    assert ".env" in content, ".gitignore must ignore .env (SH-2)"
    assert "media/" in content, ".gitignore must ignore media/"
    assert "backups/" in content, ".gitignore must ignore backups/"
    assert "!infra/.env.example" in content, ".gitignore must whitelist .env.example"


def test_deploy_scripts_tracked_as_executable():
    """Deploy scripts must be executable IN THE GIT INDEX (100755), not just in
    the working tree: a fresh clone/bundle drops working-tree chmods, and a
    100644 index breaks the api container (`db/migrate.sh: Permission denied`
    in the compose command) and the cron jobs. Caught by the T7.2 clean-deploy
    rehearsal on a fresh clone."""
    for script in EXECUTABLE_SCRIPTS:
        assert script.exists(), f"missing deploy script: {script}"
        relative = script.relative_to(REPO_ROOT)
        staged = subprocess.run(
            ["git", "ls-files", "--stage", "--", str(relative)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()[0]
        assert staged == "100755", (
            f"{relative} is mode {staged} in the git index; run "
            f"`git update-index --chmod=+x {relative}`"
        )
