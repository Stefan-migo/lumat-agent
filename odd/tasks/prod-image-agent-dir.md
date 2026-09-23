# The prod image does not ship agent/, so every assistant turn fails

Feature id: `prod-image-agent-dir`
Branch: `odd/prod-image-agent-dir`

## Objective

The production api image contains the `agent/` tree, so the assistant can load its
declarative registry and prompt files instead of raising on the first turn.

## Problem

Observed on the VPS (2026-09-23), testing the `v2026.09.4` deploy from the panel:

```
registry file not found: /app/agent/registry.yaml
No se pudo procesar el mensaje
```

`Dockerfile:29-32` copies `--from=build /app/.venv`, `pyproject.toml`, `app/` and `db/`.
It never copied `agent/`. The runtime resolves that tree from the image root:

- `app/agent_registry.py:223` -> `Path(__file__).resolve().parents[1] / "agent" / "registry.yaml"`
  (`/app/agent/registry.yaml` in the image)
- `app/services/prompts.py:30` -> `Path(__file__).resolve().parents[2] / "agent"`

Three facts explain why this reached production and stayed invisible:

1. **The failure is not at boot.** `build_graph()` runs per message
   (`app/chat/graph.py:300`), and `get_registry()` is first called inside it. The
   container starts, `/health` is 200, the webhook handshake works — the image is only
   broken once somebody actually talks to the assistant.
2. **The registry has no fallback.** `prompts.load()` degrades silently to its literal
   `FALLBACKS` when a file is missing (`app/services/prompts.py:113-120`); the registry
   raises. So the same missing directory produced a hard failure on one path and a
   silent, undeclared behaviour change on the other.
3. **The deploy smoke never exercises a turn.** `docs/ops.md` §2.1/§2.1.2 check `/health`,
   the webhook verification probe, `monitor.sh`, and the SPA shell/assets/worker. No step
   sends a message to the assistant.

The gap is not a regression of `v2026.09.4`: the prod Dockerfile dates from `310204bf`
(2026-08-15) and never copied `agent/`, while the assistant path has read the registry at
runtime since `a7abba4b` (2026-09-10). All four tags (`v2026.09.1` .. `v2026.09.4`) are
built from that image. **There is no known-good tag to roll back to on this path** — the
fix is forward-only.

## Scope

### T1 — ship `agent/` in the prod image, with a regression test

- `Dockerfile`: `COPY agent/ agent/`, between `app/` and `db/`, with a comment naming the
  two runtime resolution sites — the omission was easy to make precisely because nothing
  in the file said `agent/` was runtime config rather than dev noise.
- `tests/integration/test_infra.py`:
  `test_prod_image_ships_every_repo_path_the_runtime_resolves` asserts the image ships all
  three repo-root paths the runtime resolves (`pyproject.toml`, `agent/`, `db/`), so the
  next omission of the same class fails a test instead of production.

### Out of scope (do not expand)

- `prompts.load()`'s silent fallback. It is why the missing tree was invisible on that
  path, but changing its behaviour is its own decision with its own blast radius.
- The deploy smoke. Adding an assistant-turn probe to `docs/ops.md` §2.1 is the durable
  guard against this class, and it belongs with the deploy documentation, not here.
- `infra/docker-compose.prod.yml`. The prod api has no repo bind mount by design.

## Verification

- `eval "$(bash infra/test-db.sh env)" && uv run --frozen pytest tests/integration/test_infra.py -q`
  -> **12 passed**.
- **Teeth (observed):** removing `COPY agent/ agent/` from the Dockerfile -> FAILED
  (`the prod image must ship 'COPY agent/ agent/'`); restored -> passed.
- Static confirmation that no fourth path is missing: every root-relative read under
  `app/` is `pyproject.toml` (`app/config.py:19`), `agent/`
  (`app/agent_registry.py:223`, `app/services/prompts.py:30`) or the configured
  `media_dir` (a runtime volume). All three are covered by the test.
- **Not verified here:** the image was not built locally. Container-level confirmation is
  the tagged deploy plus an assistant turn in the smoke.

## Follow-ups

- Add an assistant-turn probe to `docs/ops.md` §2.1 (or at minimum
  `GET /panel/api/assistant/capabilities`, which calls `get_registry()` and fails the same
  way). This is the check whose absence let `v2026.09.4` go live with an assistant that
  could not answer.
- Decide whether `prompts.load()` should keep degrading silently or fail fast like the
  registry.
- `docs/ops.md` §2.1 shows `git commit -m "release: 2026.09.3"`; the actual history uses
  `chore(release): cut v<calver>`. The doc example drifted.
