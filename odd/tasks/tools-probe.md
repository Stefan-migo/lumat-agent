# ODD: Repeatable assistant tool probe

- Branch: `odd/tools-probe`
- Base: `origin/main` (`23d1d29f`)
- Origin: “luego no hay certeza de que esten todos los tools realmente funcionando.”

## Specs

- **S1.** Execute each read-only assistant tool through `execute_tool` with valid minimal arguments and report one row per tool: name, tier, status (`ok` / `error` / `skipped`), elapsed milliseconds, and a bounded output summary. Exit 0 when every attempted tool succeeds, 1 otherwise.
- **S2.** Never execute write tools. Report them as `requires-approval` to state clearly what the probe did not prove.
- **S3.** Give every live `TOOL_REGISTRY` entry either an argument fixture or a named skip reason. A unit test fails if the registry gains a tool without coverage.
- **S4.** Use the app's environment settings, including `DATABASE_URL`, and accept `--role`, `--proyecto`, and `--project-id`. Support `--json` for machine-readable output alongside the human table.
- **S5.** Never expose customer PII. Summaries contain counts and field names, never row values. The probe is intended for production read-only use.

## Tasks

- [ ] Implement registry-complete argument fixtures, outcome summaries, and CLI report. (S1, S2, S3, S4, S5) — commit: `<pending>`
- [ ] Add unit coverage enforcing fixture-or-named-skip completeness against the live registry. (S3) — commit: `<pending>`
- [ ] Verify local probe behavior and test tiers. (S1, S2, S3, S4, S5) — commit: `<pending>`

## Log

- L1. luego no hay certeza de que esten todos los tools realmente funcionando.
- L2. `uv run pytest tests/unit/test_probe_tool_fixtures.py` — RED: collection failed because `scripts.probe_assistant_tools` did not yet exist; GREEN: 1 passed after adding the fixture/skip table. One intermediate GREEN attempt exposed overlapping fixture/skip entries; removing fixtures for the named skips made the contract pass.
- L3. Graph consulted: `TOOL_REGISTRY`, `execute_tool`, and the tool registry community; Graphify found no directed path from `TOOL_REGISTRY` to `execute_tool`. The base graph was `23d1d29f`.
- L4. `eval "$(bash infra/test-db.sh env)" && uv run python scripts/probe_assistant_tools.py --role admin --proyecto default` — report printed one row for each of 33 tools; exit 1 because `conversations.search` returned an error. Empty local DB caused the documented entity skips; writes reported `requires-approval`; `web.search` skipped because `BRAVE_SEARCH_API_KEY` was absent.
- L5. `bash scripts/test.sh quick` — collection and all unit tests passed, including `test_probe_tool_fixtures.py`.

### L5 — First production run (read-only, `lumat-api-1`, `v2026.10.11`)

Invocation: `--role admin --owner-id 5 --proyecto test-del-agente --reveal-errors`, script copied into the
running container, no writes executed. Result: **19 ok · 1 error · 2 skipped · 11 requires-approval**.

- **error** — `conversations.search`: `cannot import name 'assign' from partially initialized module
  'app.services.conversations'`. The cold-import cycle of `odd/tasks/harness-tool-truth.md` S1, still live in
  production because that fix is not deployed yet.
- **skipped** — `web.search`: `missing BRAVE_SEARCH_API_KEY` in production, so the tool cannot work there at
  all. A deployment finding, not a code defect.
- **skipped** — `view_image`: no image exists in that project or thread; nothing to view.
- **requires-approval** — the 11 write tools, never executed by the probe by design.

Two probe pitfalls found and fixed during this run, both of which had produced false failures:

1. The probe initially ran against the **test database** because its env was borrowed from `test-db.sh`.
   Every read returned `rows=0` and entity-shaped tools reported `no ... rows`, which reads like broken tools
   and is not. The probe now states that `DATABASE_URL` must be the application database.
2. `--owner-id` matters: thread 39 belongs to user 5, so resolving "the first active user" (id 1) made
   `memory.read`, `memory.search` and `list_project_files` fail with `project 'test-del-agente' is not an
   active project`. That was the probe asking as the wrong owner, not a product defect. `--owner-id` and
   `--thread-id` are now explicit flags.

`--reveal-errors` is what made all of this diagnosable, and it is safe: exception messages and validation
reasons only, never row values. It stays off by default and was used here only because the summaries withhold
detail by contract (S5).
