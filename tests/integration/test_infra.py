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
PROD_COMPOSE = REPO_ROOT / "infra" / "docker-compose.prod.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
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


def test_prod_api_build_wires_deployed_identity():
    compose_text = PROD_COMPOSE.read_text().replace("!reset", "").replace("!override", "")
    compose = yaml.safe_load(compose_text)
    build_args = compose["services"]["api"]["build"]["args"]
    assert "GIT_SHA" in build_args

    dockerfile = DOCKERFILE.read_text()
    assert "ARG GIT_SHA=unknown" in dockerfile
    assert "COPY pyproject.toml ./" in dockerfile


def test_prod_image_ships_every_repo_path_the_runtime_resolves():
    """odd/prod-image-agent-dir: the image copied app/ and db/, but not agent/.

    The runtime resolves these paths relative to the image root:

    - `app/agent_registry.py:223` -> `parents[1] / "agent" / "registry.yaml"`
    - `app/services/prompts.py:30` -> `parents[2] / "agent"`
    - `app/config.py:19` -> `parents[1] / "pyproject.toml"`

    `agent/` was the missing one, so `load_registry()` raised
    `registry file not found: /app/agent/registry.yaml` on the first assistant
    turn and the panel answered with the raw error. The registry has no fallback
    (unlike `prompts.load()`, which silently serves its literal FALLBACKS), so a
    missing `agent/` is a hard failure of every assistant turn.
    """
    dockerfile = DOCKERFILE.read_text()
    for copy in ("COPY pyproject.toml ./", "COPY agent/ agent/", "COPY db/ db/"):
        assert copy in dockerfile, (
            f"the prod image must ship {copy!r}: the runtime resolves that path "
            f"relative to the image root"
        )


def test_prod_api_service_has_a_writable_embedder_cache():
    """odd/prod-embedder-cache: the prod api runs read_only, so the local embedding
    model needs an explicit writable cache. `volumes: !override` silently drops
    anything the base compose declares, which is how prod lost it in the first place.
    """
    compose_text = PROD_COMPOSE.read_text().replace("!reset", "").replace("!override", "")
    compose = yaml.safe_load(compose_text)
    api = compose["services"]["api"]

    mounts = [str(m) for m in api.get("volumes", [])]
    cache_mount = next((m for m in mounts if "/home/appuser/.cache" in m), None)
    assert cache_mount is not None, (
        f"prod api must mount a writable embedder cache, got: {mounts}"
    )
    # Source and writability matter, not just the path: `other:/home/appuser/.cache:ro`
    # satisfies a substring check and still fails exactly like the original bug.
    assert cache_mount.startswith("embed-cache:/home/appuser/.cache"), (
        f"the cache mount must come from the embed-cache volume, got: {cache_mount}"
    )
    assert ":ro" not in cache_mount, f"the cache mount must be writable, got: {cache_mount}"
    assert "embed-cache" in compose.get("volumes", {}), (
        "compose must declare the embed-cache volume"
    )

    env = api.get("environment", {})
    assert env.get("HF_HOME") == "/home/appuser/.cache/huggingface", (
        "prod api must point HF_HOME at the mounted volume (hf_hub's xet cache lives there)"
    )
    assert env.get("FASTEMBED_CACHE_PATH") == "/home/appuser/.cache/fastembed", (
        "prod api must point FASTEMBED_CACHE_PATH at the mounted volume"
    )
    # fastembed's decompress_to_cache rmtree's any cache_dir containing "tmp"
    # (model_management.py:315-316), so neither path may live under /tmp.
    for name in ("HF_HOME", "FASTEMBED_CACHE_PATH"):
        assert "tmp" not in env[name], f"{name} must not live under a 'tmp' path"

    dockerfile = DOCKERFILE.read_text()
    assert "/home/appuser/.cache" in dockerfile, (
        "Dockerfile must pre-create the cache dir so the named volume is appuser-writable"
    )

    assert api.get("read_only") is True, "the read-only hardening must stay"
    assert not api.get("ports"), "prod api must not publish host ports"


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
