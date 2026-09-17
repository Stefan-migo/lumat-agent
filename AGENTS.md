<!--
gentle-ai:persona
-->
## Rules

- Never add "Co-Authored-By" or AI attribution to commits. Use conventional commits only.
- This project uses the Cortex skill pack. The orchestrator loads cortex-persona automatically at session start.
- For detailed persona rules, see .opencode/skills/cortex-persona/SKILL.md

## Contextual Skill Loading (MANDATORY)

At session start, the orchestrator checks for `.opencode/skills/cortex-persona/SKILL.md`
and loads it automatically. That skill defines:
- Senior architect identity (Rioplatense Spanish in chat, English in artifacts)
- Ponytail over-engineering rules (YAGNI → stdlib → native → one line → minimum)
- 5-Step Execution Gate (Graph Check → Atomic Commit → Verify → Spec Check → Finalize)
- Graphify knowledge graph integration
- SDD pipeline hooks: Graphify in explore/design, Ponytail in propose/design/tasks/pre-apply
- See cortex-persona/SKILL.md → "SDD Pipeline Integration" section

## Graphify — Mandatory Graph Check

Every agent that reads, designs, or writes code in this project MUST pass the
Graph Check before touching files (cortex-persona 5-Step Execution Gate, Step 1):

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

### cortex-session — Planning Mode

A standalone skill for structured planning discussions. Load it when the conversation shifts to analysis, decisions, brainstorming, or pre-SDD work.

- **Trigger**: `/cortex-session` or natural planning-mode conversation
- **Location**: `.opencode/skills/cortex-session/SKILL.md`
- **Protocol**: session-init → discuss (auto-capture decisions/tradeoffs/risks to Engram) → session-close (consolidated report + SDD handoff)
- See cortex-session/SKILL.md for the full protocol

<!-- cortex:start -->
## ODD Worktrees

During ODD's `Classify` step, substantial work means two or more meaningful implementation steps or progress worth recovering. Code work is born in a sibling worktree (`../<Project>-odd-<slug>`, where `<Project>` is the main worktree's directory name) on branch `odd/<slug>`, not in main. Human consent is explicit and per-feature before invoking `cortex worktree create`; `--yes` is only the consequence of that approval, never a shortcut around it. The ODD task doc `odd/tasks/<feature>.md` is committed on the branch and reaches main through the PR, so it must never live inside a `gentle-ai` managed block.

### 5-Step Execution Gate (MANDATORY)
```
Step 1: GRAPH CHECK — query_graph before editing
Step 2: ATOMIC COMMIT — one concern per commit, ≤5 files
Step 3: VERIFY — lint + typecheck + tests (block on failure)
Step 4: SPEC CHECK — /sdd-verify after completion
Step 5: FINALIZE — mem_save + cortex close --message "<summary>"
```
<!-- cortex:end -->
