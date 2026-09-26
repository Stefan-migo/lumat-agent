<!--
gentle-ai:persona
-->
## Rules

- Never add "Co-Authored-By" or AI attribution to commits. Use conventional commits only.
- This project uses the Rapsodia skill pack. The orchestrator loads rapso-persona automatically at session start.
- For detailed persona rules, see .opencode/skills/rapso-persona/SKILL.md

## Contextual Skill Loading (MANDATORY)

At session start, the orchestrator checks for `.opencode/skills/rapso-persona/SKILL.md`
and loads it automatically. That skill defines:
- Senior architect identity (Rioplatense Spanish in chat, English in artifacts)
- Ponytail over-engineering rules (YAGNI → stdlib → native → one line → minimum)
- 5-Step Execution Gate (Graph Check → Atomic Commit → Verify → Spec Check → Finalize)
- Graphify knowledge graph integration
- SDD pipeline hooks: Graphify in explore/design, Ponytail in propose/design/tasks/pre-apply
- See rapso-persona/SKILL.md → "SDD Pipeline Integration" section

## Graphify — Mandatory Graph Check

Every agent that reads, designs, or writes code in this project MUST pass the
Graph Check before touching files (rapso-persona 5-Step Execution Gate, Step 1):

1. The knowledge graph lives in `graphify-out/` (`graph.json` + `GRAPH_REPORT.md`).
   If it is missing or stale, build it FIRST with the `/graphify` skill
   (`graphify <project-root>` or `graphify <project-root> --update`). A missing
   graph is a blocker — report `blocked`, never skip.
2. Before each task, run `graphify query "<area>"` and `graphify path <A> <B>`
   on the modules you will touch, and read `graphify-out/GRAPH_REPORT.md` for
   god nodes and communities.
3. Queries are mandatory on every task (step 2). The graph refresh with
   `graphify <project-root> --update` runs ONCE per work session, when the
   session closes — never after every batch or commit.
4. Record the graph nodes/edges consulted in every apply-progress, design, and
   exploration output.

### rapso-session — Planning Mode

A standalone skill for structured planning discussions. Load it when the conversation shifts to analysis, decisions, brainstorming, or pre-SDD work.

- **Trigger**: `/rapso-session` or natural planning-mode conversation
- **Location**: `.opencode/skills/rapso-session/SKILL.md`
- **Protocol**: session-init → discuss (auto-capture decisions/tradeoffs/risks to Engram) → session-close (consolidated report + SDD handoff)
- See rapso-session/SKILL.md for the full protocol

<!-- rapso:start -->
## ODD Worktrees

During ODD's `Classify` step, substantial work means two or more meaningful implementation steps or progress worth recovering. Code work is born in a sibling worktree (`../<Project>-odd-<slug>`, where `<Project>` is the main worktree's directory name) on branch `odd/<slug>`, not in main. Human consent is explicit and per-feature before invoking `rapso worktree create`; `--yes` is only the consequence of that approval, never a shortcut around it. The ODD task doc `odd/tasks/<feature>.md` is committed on the branch and reaches main through the PR, so it must never live inside a `gentle-ai` managed block.

### 5-Step Execution Gate (MANDATORY)
```
Step 1: GRAPH CHECK — query_graph before editing
Step 2: ATOMIC COMMIT — one concern per commit, ≤5 files
Step 3: VERIFY — lint + typecheck + tests (block on failure)
Step 4: SPEC CHECK — /sdd-verify after completion
Step 5: FINALIZE — mem_save + rapso close --message "<summary>"
```
<!-- rapso:end -->

## Pre-merge integration check (MANDATORY discipline)

`main` is shared, and a PR can be green while still landing a broken tree. Two ways get
past the checks we have:

1. **A semantic merge.** Git merges textually clean and GitHub reports `CLEAN`, while the
   combined tree does not compile — two branches adding the same import is the canonical
   case. `mergeable: CLEAN` says nothing about semantics.
2. **A stale green check.** If the base branch moves after the check ran, the tree that
   actually lands was never tested.

Before merging any PR, the human — or the agent, on the owner's explicit authorization —
MUST:

- ensure the branch contains the current head of the base branch; merging `origin/main`
  into the branch is enough, and it forces a fresh CI run over the real tree;
- for a branch that touches a file another in-flight branch also touches, run the local
  integration over the merged tree before pushing: the frontend suite, `npm run build`,
  and the backend suite.

The frontend type check is not optional: in this repository `tsc -b` lives only inside
`npm run build`, and a green Vitest suite does **not** prove the tree type-checks.

This is deliberately **report-only and fail-closed**. Nothing here auto-merges, auto-fixes,
pushes, or edits the working tree: it produces evidence and stops. The merge decision stays
human.

**Limitation, stated honestly.** This repository has no branch protection (private, no
GitHub Pro), so no check can block a merge — `gh pr merge` works with a red check. The
discipline above is evidence, not enforcement. Enforcement would need branch protection or
a local hook, and a hook is bypassable and does not cover GitHub's merge.

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
