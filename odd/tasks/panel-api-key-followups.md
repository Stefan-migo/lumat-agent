# panel-api-key-followups — close the two non-blocking follow-ups of `panel-api-key-modelos`

Status: closed. Branch `odd/panel-api-key-followups`, base `main 6d7988b2`.
Worktree `/home/stefan/repos/lumat-agent-odd-panel-api-key-followups`.
Origin: `odd/tasks/panel-api-key-modelos.md` follow-ups **AK-17** and **AK-18 (R3-001)**.

## Objective

Close the two non-blocking follow-ups left after the `panel-api-key-modelos` work unit merged
(PRs #588/#589/#592). Both are backend-only.

## Why

- **AK-17** — the hard requirement test (`tests/integration/test_model_secrets.py`) asserts the
  contract of the `openai_client()` factory, not the real consumer paths. A future bypass (a node
  constructing an `OpenAI` client directly, or reading `settings.deepseek_api_key` instead of the
  resolver) would go undetected.
- **AK-18 (R3-001)** — a WARNING from the native review of PR1: the cache invalidation runs before
  the write transaction commits, so a same-process read can republish the stale key for up to the
  45s TTL.

## AK-18 — root cause (verified in code)

`app/panel/api/routes/settings.py` (POST and DELETE `/settings/model_api_key`) does:

```python
model_secrets.set_model_api_key(session, key, actor=..., updated_by=...)  # invalidates here
session.commit()
```

A `resolve_model_api_key()` that captures `_cache_generation` **after** the invalidation and reads
the DB **before** the commit reads the old committed row and publishes it (`_cache_expires_at = now
+ 45`). The generation guard does not cover this ordering, because the read starts after the bump.

## AK-18 — fix (the prescribed one, minimal code)

Move `invalidate_model_key_cache()` **out** of `set_model_api_key` / `clear_model_api_key` and call
it in the routes **after** `session.commit()`. With the invalidation after commit:

- a read that started before the invalidation sees a changed generation → it does not publish;
- a read after the invalidation reads the committed row.

The service write functions become pure DB + audit writers; cache lifecycle is the caller's,
documented in a docstring. The route is the only production caller (`grep` confirmed).

## AK-17 — consumer coverage

Add an integration test that drives the **real** consumer entries and asserts the outbound HTTP
`Authorization: Bearer <panel key>` header (proves the panel key, not the env fallback, is sent):

- **chatbot** — `app/chat/graph.py::run_internal_conversation` (the WhatsApp chat boundary,
  `openai_client()` with no provider).
- **assistant** — `app/chat/assistant/nodes.py::_assistant_client()` (the selector the assistant
  nodes use; `openai_client(assistant_chat_provider)`).

Interception: `respx` over `https://api.deepseek.com`, matching the existing repo pattern
(`tests/integration/conftest.py::mock_openai_chat`). Assert on `request.headers["authorization"]`.

Honest limitation to record in the test docstring: this covers the client-selection seams the
consumers use, not every call site inside every node. It catches a factory-level regression (the
bypass this follow-up targets).

## Constraints

- **TDD strict is ON** (`openspec/config.yaml`: `testing.strict_tdd: true`, runner
  `uv run pytest tests/`). RED → GREEN. Demonstrate the failing test first for AK-18.
- Test DB: `bash infra/test-db.sh up` + `eval "$(bash infra/test-db.sh env)"` (port 5656 in this
  worktree).
- Commit Conventional, **no AI attribution**. RDD is active (assess after the code is written).
- Tests use fake keys (`sk-test`); never a real key.
- **No frontend changes** in this unit.

## Tasks

- [x] **F1 — RED (AK-18).** A regression test proving the ordering bug: a resolve that runs between
  the invalidation and the commit must not leave the stale value cached after the commit. It MUST
  fail against the current code.
- [x] **F2 — AK-18 fix.** Remove `invalidate_model_key_cache()` from `set_model_api_key` /
  `clear_model_api_key` (document that the caller invalidates post-commit); add the post-commit
  `model_secrets.invalidate_model_key_cache()` call in both routes. F1 goes GREEN.
- [x] **F3 — AK-17 test.** New integration test driving the chatbot + assistant consumer entries and
  asserting the outbound `Authorization` header carries the panel key.
- [x] **F4 — GREEN + full suite.** Full backend suite green; `git diff --check` clean.
- [x] **F5 — Docs.** Update the parent `odd/tasks/panel-api-key-modelos.md` (Status → closed;
  AK-17/AK-18 → closed with evidence) and record the commit(s).

## Acceptance criteria

- F1 reproduces the AK-18 bug against the pre-fix code and passes after F2.
- The consumer test (F3) fails if the connection key is not the panel key (e.g. if the resolver is
  bypassed) — i.e. it asserts the auth header, not merely a returned object.
- Full backend suite green with the same exit-code discipline (the repo does not print a pytest
  summary line; verify by exit code and dot count).
- No frontend files touched.

## Checks

- `uv run pytest tests/` → green (exit 0).
- `git diff --check` → clean.

## Graph Check

Communities/nodes consulted: `set_model_api_key()`, `clear_model_api_key()`, `resolve_model_api_key()`,
`invalidate_model_key_cache()`, `session_scope()`, `settings_model_api_key()`,
`settings_model_api_key_clear()`, `openai_client()`, `run_internal_conversation()`, `_assistant_client()`.
Edges consulted: settings POST → model API key status; `run_internal_conversation()` → `openai_client()`.
No directed path was found from `model_secrets` to the settings route; route ownership of the
post-commit invalidation is therefore established in code rather than by an existing reverse edge.

## Evidence

- Commit `02328eb4f8be467899006f234b68891311226d23` — `fix(panel): invalidate the model key cache after the write commits`.
- Commit `COMMIT_2_SHA` — `test(panel): cover the real model-key consumers`.
- RED (pre-fix): `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_model_secrets.py::test_write_does_not_leave_a_read_during_commit_window_cached` → exit 1; failed at the post-commit assertion: `assert 'sk-env-test' == 'sk-new'`.
- GREEN (post-fix): `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_model_key_cache_ordering.py` → exit 0, 1 passed.
- Consumer/cache focused: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/integration/test_model_secrets.py tests/integration/test_model_key_cache_ordering.py` → exit 0, 3 passed.
- Full backend: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/` → exit 0, 2030 passed, 2 warnings (412.07s; output reached 100%).
- `git diff --check` → clean.
