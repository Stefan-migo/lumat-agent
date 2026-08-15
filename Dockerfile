# LumatAgent production image (T7.1).
#
# The dev compose (infra/docker-compose.yml) bind-mounts the repo into the uv
# base image and runs `uv sync` at container start. Prod needs a
# self-contained image so the api can run with a read-only filesystem (SH-2):
# multi-stage build — deps are synced in the `build` stage, the runtime stage
# keeps only the venv + app code and runs as a non-root user.
#
# Used by infra/docker-compose.prod.yml (build context: repo root).

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
# Runtime deps only (--no-dev keeps pytest out); --no-install-project skips
# the hatchling wheel — the app is imported from /app directly.
RUN uv sync --frozen --no-dev --no-install-project

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# Non-root app user (SH-1: the api never runs as root; SH-2 read-only fs).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser
COPY --from=build /app/.venv /app/.venv
COPY app/ app/
COPY db/ db/
# Pre-create the media dir with appuser ownership so a fresh named volume at
# /app/media inherits writable perms (SH-2: media/ is the only writable path;
# without this, docker seeds the volume as root and media downloads fail).
RUN mkdir -p /app/media && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
