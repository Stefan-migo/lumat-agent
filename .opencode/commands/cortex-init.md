---
description: Bootstrap Cortex skill pack in a project — links skills, registers them, adds Graphify MCP, creates AGENTS.md
agent: gentle-orchestrator
---

## cortex-init

Bootstraps the Cortex skill pack into the current project.

**Note**: The global orchestrator prompt already includes the Cortex auto-load and Ponytail review workflow integration. This command configures the project so those integrations work.

### What the orchestrator does

1. **Check prerequisites**: opencode + engram installed.
2. **Delegate to sub-agent** with bash access to run `cortex-init.sh`:
   - Links `cortex-persona` + `ponytail-*` skills to `.opencode/skills/`
   - Builds Graphify knowledge graph (`graphify-out/`)
   - Adds Graphify MCP server to `.opencode/opencode.json`
   - Creates `AGENTS.md` with persona reference
   - Writes skill registry to `.atl/skill-registry.md`
   - Adds `.atl/` to `.gitignore`
   - Installs `/cortex-init` command in project
3. After completion, suggest running `/sdd-init`.

### Notes

- `cortex-init.sh` is the single entry point — lives at `/home/stefan/Cortex/cortex-init.sh`
- **Idempotent**: safe to run multiple times. Already-installed skills and config are skipped.
- Requires: graphify, gentle-ai

### What changed (v2 → v3)

| Before | After |
|--------|-------|
| Solo symlink skills | Links skills + registers them in skill registry |
| No MCP config | Adds Graphify MCP to `.opencode/opencode.json` |
| No AGENTS.md | Creates AGENTS.md with persona reference |
| No .gitignore update | Adds `.atl/` to `.gitignore` |
| Manual Ponytail trigger | Orchestrator auto-runs ponytail-review after sdd-apply |
