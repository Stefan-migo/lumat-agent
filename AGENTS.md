<!--
gentle-ai:persona
-->
## Rules

- Never add "Co-Authored-By" or AI attribution to commits. Use conventional commits only.
- This project runs on Pi through Gentle Shell. `gentle-ai` is the orchestrator and `gentle-engram`
  provides memory; this project keeps its own skills, not a persona pack.
- If `.rapsodia-code/prelude.md` exists when a session starts, read it before the first task: it
  holds scored Engram context, the Graphify report, and the project manifest summary.
- `rapso` prepares context; it never owns the session. `gentle-engram` opens the session, saves
  summaries, and captures discoveries.

## Runtime — Pi / Gentle Shell

| Resource | Location |
|---|---|
| This workflow contract | `AGENTS.md` — Pi reads it natively |
| Project skills | `.agents/skills/` |
| Project extensions | `.pi/extensions/` — loaded only after project trust is granted |
| Optional project MCP servers | `.pi/mcp.json` — read only after project trust is granted |
| Local ignored state | `.rapsodia-code/` (manifest, sessions, prelude) |

In a trusted project, `.pi/extensions/rapsodia-context.ts` refreshes `.rapsodia-code/prelude.md` in
the background on session start and points the first user run at it. Without project trust the
extension does not load, so run `rapso context` yourself when the prelude is stale; it only rewrites
the prelude, opening no session and launching no agent.

## Contextual Skill Loading (MANDATORY)

Pi discovers the project's skills in `.agents/skills/`. Load the one that matches the work instead of
carrying every rule in this file:

| Skill | Load it when |
|---|---|
| `rapso-session` | the conversation turns to analysis, decisions, brainstorming, or planning before ODD |
| `design-system` | building or reviewing UI |
| `component-adapter` | wiring a component to the project's data and API layer |
| `design-agent-lead` | coordinating a multi-part frontend change |
| `panel-section-analysis` | analysing or changing a panel section |

The retired Rapsodia persona, Ponytail pack and SDD pipeline are **not** part of this runtime. There
is no `rapso-persona` skill: this file plus the skills above carry what the project needs.

## Graphify — Mandatory Graph Check

Every agent that reads, designs, or writes code in this project MUST pass the
Graph Check before touching files (ODD 5-Step Execution Gate, Step 1):

1. The knowledge graph lives in `graphify-out/` (`graph.json` + `GRAPH_REPORT.md`).
   If it is missing or stale, build it FIRST with `graphify .` (or `graphify . --update`).
   A missing graph is a blocker — report `blocked`, never skip.
2. Before each task, run `graphify query "<area>"` and `graphify path <A> <B>`
   on the modules you will touch, and read `graphify-out/GRAPH_REPORT.md` for
   god nodes and communities.
3. Queries are mandatory on every task (step 2). The graph refresh with
   `graphify . --update` runs ONCE per work session, when the session closes — never after every
   batch or commit.
4. Record the graph nodes/edges consulted in every apply-progress, design, and
   exploration output.

### rapso-session — Planning Mode

A standalone skill for structured planning discussions. Load it when the conversation shifts to
analysis, decisions, brainstorming, or pre-ODD work.

- **Trigger**: `/skill:rapso-session` or a natural planning-mode conversation
- **Location**: `.agents/skills/rapso-session/SKILL.md`
- **Protocol**: session-init → discuss (auto-capture decisions/tradeoffs/risks to Engram) →
  session-close (consolidated report that seeds `odd/tasks/<feature>.md`)

## Test tiers (MANDATORY)

Backend verification is tiered instead of "always the full suite". `scripts/test.sh` is the
executable form of this policy; the costs below are measured on this repository (2026-10-23,
2822 collected tests).

| Tier | Command | Cost | What it catches |
|---|---|---|---|
| T0 gate | `bash scripts/test.sh gate` | ~7 s, no DB | broken import / collection: `--collect-only` imports every test and app module |
| T1 unit | `bash scripts/test.sh unit` | ~14 s, no DB | the contract of prompts, registry, routing, settings parsing |
| T0+T1 | `bash scripts/test.sh quick` | ~19 s | what an edit iteration must pass |
| T2 layer | `bash scripts/test.sh db tests/integration/<file>.py …` | per file | the database-backed behaviour you touched |
| T3 full | `bash scripts/test.sh full` | ~7 min | seams, cross-cutting shape drift, everything else |

Iterate with `quick` plus the focused test of the rule under RED/GREEN. Run `full` **only** at these
boundaries:

1. feature closure;
2. before opening a PR;
3. after merging `origin/main` into the branch;
4. whenever `bash scripts/test.sh shape` exits **3**.

One suite at a time per worktree: each worktree derives its own test database, and two concurrent
runs against the same one deadlock on the per-test `TRUNCATE`.

### Why `full` is not optional at those boundaries

Two documented escapes justify the rule, and both are cheap to cover without paying 7 minutes per
work unit:

- `odd/tasks/asistente-sdb.md` — a `NameError` from Slice 4 escaped a subset. Covered by T0, at ~7 s.
- Engram `odd/asistente-skills/tasks` — targeted runs missed two integration tests whose doubles
  needed the new `skills` shape. Covered by the shape rule below.

### Shape surfaces — `full` becomes mandatory

A shape change invalidates every targeted selection, so `scripts/test.sh shape` answers the question
mechanically instead of by memory. Its list lives in `scripts/test.sh`; keep both in step:

`app/models.py`, `app/config.py`, `app/panel/api/serializers.py`, `app/services/project_config.py`,
`tests/conftest.py`, `tests/*/conftest.py`, `tests/_testdb.py`, `tests/webhook_helpers.py`,
`agent/registry.yaml`, `agent/prompts/*`, `agent/personas/*`, `db/migrations/*`.

They are shape surfaces because the graph says so: `make_user()` (378 edges), `User` (199),
`Customer` (126), `Conversation` (124), `Project` (115) and `record_audit()` (113) are the god nodes
— that is `app/models.py` plus the harness fixture almost every suite imports.

For a committed range use a base ref: `bash scripts/test.sh shape origin/main`.

### What the tiers do not replace

- **TDD discipline.** RED before GREEN on the rule being implemented; the tier only decides how wide
  the verification sweep is.
- **The frontend gate.** If `web/` is touched: `npm ci` -> `npm run build` (tsc -b) -> `npm test`.
  `tsc -b` lives only inside `build`, and a green Vitest suite does not prove the tree type-checks.
- **`full` in CI.** `.github/workflows/tests.yml` runs the whole suite on every PR and every push to
  `main`. That is the authoritative gate and it stays.
- **The pre-merge integration check below.** Unchanged.

Never test with a lowered ceiling: the 120 s `pytest-timeout` and `timeout_method = "thread"` are the
diagnosis for the stall family documented in `odd/tasks/suite-truncate-stall.md`.

<!-- rapso:start -->
## ODD Worktrees

During ODD's `Classify` step, substantial work means two or more meaningful implementation steps or progress worth recovering. Code work is born in a sibling worktree (`../<Project>-odd-<slug>`, where `<Project>` is the main worktree's directory name) on branch `odd/<slug>`, not in main. Human consent is explicit and per-feature before invoking `rapso worktree create`; `--yes` is only the consequence of that approval, never a shortcut around it. The ODD task doc `odd/tasks/<feature>.md` is committed on the branch and reaches main through the PR, so it must never live inside a `gentle-ai` managed block.

### 5-Step Execution Gate (MANDATORY)
```
Step 1: GRAPH CHECK — query_graph before editing
Step 2: ATOMIC COMMIT — one concern per commit, <=5 files
Step 3: VERIFY — this project's gates are tiered (see "Test tiers" ABOVE this block, which is the
        authoritative copy): backend `bash scripts/test.sh quick` per change, `bash scripts/test.sh
        full` at the boundaries it names (needs the pgvector Postgres); panel `npm ci` -> `npm run
        build` (tsc -b) -> `npm test`. Report the exact command and its real output; never infer a
        pass from intent
Step 4: SPEC CHECK — the specs in odd/tasks/<feature>.md; /sdd-verify is retired
Step 5: FINALIZE — mem_save + `rapso close --message "<summary>"`
```
<!-- rapso:end -->

## Pre-merge integration check (MANDATORY discipline)

`main` is shared, and a PR can be green while still landing a broken tree. Two ways get
past the checks *running on that PR*:

1. **A semantic merge.** Git merges textually clean and GitHub reports `CLEAN`, while the
   combined tree does not compile — two branches adding the same import is the canonical
   case. `mergeable: CLEAN` says nothing about semantics.
2. **A stale green check.** If the base branch moves after the check ran, the tree that
   actually lands was never tested.

### What GitHub enforces (verified 2026-10-15 against the API)

`main` **does have branch protection**. An earlier version of this section claimed it did
not ("private, no GitHub Pro, so `gh pr merge` works with a red check") — that is **wrong
now**, and it was the most misleading line in this file, because it tells you the gate is
optional:

- **Required status checks**: `test` and `panel` (`.github/workflows/tests.yml`). `test`
  runs `uv run pytest tests/` against a real pgvector Postgres; `panel` runs `npm ci` →
  `npm run build` → `npm test`, so the `tsc -b` type check is a **required** gate, not a
  courtesy.
- **Require branches to be up to date before merging** (`strict: true`). A PR cannot merge
  while its head predates the current `main`, so bringing `origin/main` into the branch is
  forced — and that push re-runs the gate over the combined tree.
- **A pull request is required** (zero approving reviews); force-pushes and deletion of
  `main` are blocked.
- **`enforce_admins: false`** — a repository admin can still bypass all of it with
  `gh pr merge --admin`. That is the one remaining hole, and the reason the discipline
  below is not redundant.

Both failure modes above are therefore caught by CI rather than by memory: `strict` kills
the stale green check, and it is what forces the tested tree to be the combined one.

### What the author still does

Before merging any PR, the human — or the agent, on the owner's explicit authorization —
SHOULD:

- let the required checks finish on the branch head, and never reach for `--admin`;
- when another branch landed first, merge the current `origin/main` into the branch — now
  mandatory anyway, and it re-runs the gate;
- for a branch that touches a file another in-flight branch also touches, run the local
  integration over the merged tree before pushing: the frontend suite, `npm run build`,
  and the backend suite. The same three things `tests.yml` runs, only sooner and locally.

The frontend type check is not optional: `tsc -b` lives only inside `npm run build`, and a
green Vitest suite does **not** prove the tree type-checks.

This is deliberately **report-only and fail-closed**. Nothing here auto-merges, auto-fixes,
pushes, or edits the working tree: it produces evidence and stops. The merge decision stays
human.

## Reporting Rapsodia Defects

Rapsodia is a tool you are USING, not the project you are working on.

When you identify a failure that belongs to Rapsodia itself — not to this project, its
configuration, or its environment — say so, and **suggest** opening an issue at
https://github.com/Stefan-migo/rapsodia-code/issues with the evidence: what you ran, what happened,
and the smallest reproduction you have.

- Suggest only. Never open the issue, never run `gh`, and never write to the Rapsodia
  repository from a project workflow. The human decides.
- Only for an identified defect. Do not speculate, and do not suggest an issue for expected
  refusals, for this project's own bugs, or for environment and dependency failures.
- If you cannot tell whether the cause is Rapsodia, say that instead of filing.
