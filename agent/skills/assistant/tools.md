# Assistant tools

The plan names one tool per step. Pick the most specific tool for the request and
use the exact argument shape the catalog gives you.

## Tiers and approval

- `default` tools are enabled. `opt_in` tools (`web.search`, `web.fetch`,
  `automation.create_rule`, `project.create`, `project.rename`, `project.archive`,
  `project.merge`) are enabled by default too, but a project or thread policy can
  turn them off — a disabled or role-denied tool is absent from your catalog.
- Write and destructive tools (`settings.update`, `automation.create_rule`,
  `project.create|rename|archive|merge`, `skill.propose`) require an explicit owner
  approval of the exact plan before they run. Propose the precise arguments; a
  paraphrase is not an approval.
- A tool denied for the current role stays denied. Do not retry it or look for a
  workaround.

## Multi-turn work

- Set `follow_up: true` on the plan to run one more tool step after reading this
  result. The loop is bounded, so plan only the steps you actually need.
- Read large files in chunks: `read_project_file(file_id, offset, limit)` returns
  `next_offset`; continue from it until `next_offset` is `null`.
- Discover file ids with `list_project_files`; read a project or thread image on
  demand with `view_image(source, id)` instead of asking for a re-attach.
- Read a closed planning session's report with `planning.read_report(slug)`.

## Gotchas

- Arguments are validated strictly; an unknown or mistyped field is rejected.
- Resolve a project with `project.find` before naming it; ids and slugs are not
  guesses.
