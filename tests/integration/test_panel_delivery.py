"""Static contracts for production delivery of the panel SPA.

These assertions exercise the image ownership and nginx location ordering
without requiring a running API or public DNS.
"""

from pathlib import Path

import yaml
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "infra" / "nginx" / "Dockerfile"
PANEL_CONF = REPO_ROOT / "infra" / "nginx" / "panel.lumat.cl.conf"
AGENT_CONF = REPO_ROOT / "infra" / "nginx" / "agente.lumat.cl.conf"
PROD_COMPOSE = REPO_ROOT / "infra" / "docker-compose.prod.yml"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


@pytest.fixture(autouse=True)
def clean_db():
    """Keep static delivery contracts independent from the test database."""
    yield


def test_nginx_image_owns_the_built_panel_artifact():
    content = DOCKERFILE.read_text()

    assert "FROM node:22.22.2-alpine AS build" in content
    assert "RUN npm ci" in content
    assert "RUN npm run build" in content
    assert "FROM nginx:1.27-alpine" in content
    assert "COPY infra/nginx/panel.lumat.cl.conf /etc/nginx/conf.d/" in content
    assert "COPY infra/nginx/agente.lumat.cl.conf /etc/nginx/conf.d/" in content
    assert "COPY infra/nginx/snippets/ /etc/nginx/conf.d/snippets/" in content
    assert "COPY --from=build /app/dist/ /usr/share/nginx/html/panel/app/" in content
    assert 'RUN rm /etc/nginx/conf.d/default.conf' in content
    assert "ENTRYPOINT" not in content
    assert "CMD" not in content


def test_dockerignore_keeps_nginx_sources_in_the_build_context():
    content = DOCKERIGNORE.read_text()

    assert "infra/*" in content
    assert "!infra/nginx/" in content
    assert "!infra/nginx/**" in content


def test_production_compose_builds_nginx_without_config_bind_mount():
    content = PROD_COMPOSE.read_text()
    nginx = content.split("  nginx:\n", 1)[1].split("\n  # One-shot", 1)[0]

    assert "build:" in nginx
    assert "context: .." in nginx
    assert "dockerfile: infra/nginx/Dockerfile" in nginx
    assert "image: lumat-nginx:prod" in nginx
    assert "./nginx:/etc/nginx/conf.d" not in nginx
    assert "certbot-webroot:/var/www/certbot:ro" in nginx
    assert "certbot-certs:/etc/letsencrypt:ro" in nginx
    assert "read_only: true" in nginx
    assert "- /var/cache/nginx" in nginx
    assert "- /var/run" in nginx


def test_panel_locations_preserve_backend_and_legacy_authority():
    content = PANEL_CONF.read_text()
    fallback = "location ^~ /panel/app/ {"
    fallback_index = content.index(fallback)
    legacy = "location /panel/ {"

    assert content.index("location = /panel/app") < fallback_index
    assert content.index("location = /panel/api") < fallback_index
    assert content.index("location ^~ /panel/api/") < fallback_index
    assert content.index("location = /panel/export") < fallback_index
    assert content.index("location ^~ /panel/export/") < fallback_index
    assert content.index("location = /panel/app/index.html") < fallback_index
    assert content.index("location ^~ /panel/app/assets/") < fallback_index
    assert content.index(legacy) > fallback_index
    assert "try_files $uri $uri/ /panel/app/index.html;" in content
    assert 'add_header Cache-Control "no-cache" always;' in content
    assert 'add_header Cache-Control "public, max-age=31536000, immutable" always;' in content
    assert "root /usr/share/nginx/html;" in content

    agent_content = AGENT_CONF.read_text()
    assert "/panel/app/" not in agent_content
    assert "try_files" not in agent_content


def test_compose_override_remains_valid_yaml():
    # The custom !reset/!override tags are Compose extensions; parsing the
    # source still catches accidental structural damage around the service.
    content = PROD_COMPOSE.read_text()
    for tag in ("!reset", "!override"):
        content = content.replace(tag, "")
    compose = yaml.safe_load(content)
    assert compose["services"]["nginx"]["build"]["dockerfile"] == "infra/nginx/Dockerfile"
