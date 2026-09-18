---
description: Bootstrap Rapsodia skill pack in a project — links skills, registers them, adds Graphify MCP, creates AGENTS.md
agent: gentle-orchestrator
---

## rapso-init

Bootstraps the Rapsodia skill pack into the current project.

**Note**: The global orchestrator prompt ships no Rapsodia-specific hook. This command links the Rapsodia skills into `.opencode/skills/`, so they appear in the session's skill list, and writes an `AGENTS.md` that declares the persona and the contextual skill-loading check.

### What the orchestrator does

1. **Check prerequisites**: opencode + engram installed.
2. **Delegate to sub-agent** with bash access to run `rapso-init.sh`:
   - Links `rapso-persona` + `rapso-session` + `ponytail-*` skills to `.opencode/skills/`
   - Builds Graphify knowledge graph (`graphify-out/`)
   - Adds Graphify MCP server to `.opencode/opencode.json`
   - Creates `AGENTS.md` with persona reference
   - Writes skill registry to `.atl/skill-registry.md`
   - Adds `.atl/` to `.gitignore`
   - Installs `/rapso-init` command in project
3. After completion, suggest running `/sdd-init`.

### Notes

- `rapso-init.sh` is the single entry point.
- **Idempotent**: safe to run multiple times. Already-installed skills and config are skipped.
- Requires: graphify, gentle-ai

### What changed (v2 → v3)

| Before | After |
|--------|-------|
| Solo symlink skills | Links skills + registers them in skill registry |
| No MCP config | Adds Graphify MCP to `.opencode/opencode.json` |
| No AGENTS.md | Creates AGENTS.md with persona reference |
| No .gitignore update | Adds `.atl/` to `.gitignore` |
| Manual Ponytail trigger | Ponytail skills linked into the project; the rules live in the persona and apply at ODD's Implement step |
