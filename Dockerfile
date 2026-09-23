# LumatAgent production image (T7.1).
#
# The dev compose (infra/docker-compose.yml) bind-mounts the repo into the uv
# base image and runs `uv sync` at container start. Prod needs a
# self-contained image so the api can run with a read-only filesystem (SH-2):
# multi-stage build — deps are synced in the `build` stage, the runtime stage
# keeps only the venv + app code and runs as a non-root user.
#
# The runtime also carries pyproject.toml for the version source, and receives
# the deployed commit SHA as a build argument from infra/docker-compose.prod.yml.

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
# Runtime deps only (--no-dev keeps pytest out); --no-install-project skips
# the hatchling wheel — the app is imported from /app directly.
RUN uv sync --frozen --no-dev --no-install-project

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Non-root app user (SH-1: the api never runs as root; SH-2 read-only fs).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser
COPY --from=build /app/.venv /app/.venv
COPY pyproject.toml ./
COPY app/ app/
# agent/ is runtime config, not build noise: app/agent_registry.py resolves
# `../agent/registry.yaml` and app/services/prompts.py resolves `../agent` at
# runtime. Without it the registry load raises and prompts silently fall back.
COPY agent/ agent/
COPY db/ db/
# Pre-create the writable mount points with appuser ownership so a fresh named
# volume at either path inherits writable perms: /app/media (SH-2 — WhatsApp
# media) and /home/appuser/.cache (odd/prod-embedder-cache — the local embedding
# model cache). Without this, docker seeds the volume as root and writes fail.
RUN mkdir -p /app/media /home/appuser/.cache && chown -R appuser:appuser /app /home/appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
