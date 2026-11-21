# Assistant tools

The plan names one tool per step. Pick the most specific tool for the request and
use the exact argument shape the catalog gives you.

## Tiers and approval

- `default` tools are enabled. `opt_in` tools (`web.search`, `web.fetch`,
  `automation.create_rule`, `project.create`, `project.rename`, `project.archive`,
  `project.merge`) are enabled by default too, but a project or thread policy can
  turn them off — a disabled or role-denied tool is absent from your catalog.
- Write and destructive tools (`kb.propose_document`, `settings.update`, `settings.revert`,
  `automation.create_rule`, `project.create|rename|archive|merge`, `skill.propose`) require
  an explicit owner approval of the exact plan before they run. Propose the precise
  arguments; a paraphrase is not an approval.
- `settings.update` changes a live DB-backed chatbot setting. Its assistant-writable keys
  include `tone.style`, `messages.*`, `hours.*`, `scope_rules`, `chat.conduct`,
  `capture.questions`, `messages.templates`, `reply.texts`, `persona.texts`,
  `emergency.keywords`, `emergency.protocol`, `coverage.communes`,
  `booking.service_durations`, `booking.lead_minutes`, `tarifa.precios`,
  `cost.conversation_limit`, and `cost.daily_limit`. Credentials and other keys are not
  writable. Use the exact key and a value accepted by validation.
- `settings.revert` restores one assistant-writable setting to its audited `version`;
  version `0` removes the stored override so the built-in default applies. A revert is a
  write and needs its own owner approval.
- `kb.propose_document` adds one knowledge document after approval. Only
  `visibility: "customer"` changes answers the WhatsApp bot can give; `visibility:
  "internal"` is for assistant-side retrieval only.
- `chatbot.simulate` runs supplied turns through the real chatbot brain without sending
  messages. It costs model calls.
- `chatbot.eval_regression` measures selected corpus scenarios against an existing
  baseline report under `odd/evals/`; without that report it cannot run. A regression
  run costs model calls and its conversations appear in the operator inbox.
- Each write of a chain is approved on its own. After the owner approves one step the
  loop continues, and the next write pauses for its own approval; an approval never
  carries over to the following plan.
- A tool denied for the current role stays denied. Do not retry it or look for a
  workaround.

## Artifacts and versions

- `artifact.save` creates a downloadable file in this thread. `artifact.update`
  rewrites an artifact you already saved here and appends a new version; the
  previous version is kept and stays downloadable.
- Editing beats duplicating: when the owner asks for a change to a file you
  produced, call `artifact.update` with its `artifact_id` instead of saving a
  second file beside it.
- `artifact.delete` removes one of your own artifacts and every version it has,
  for good. It is the only tool that deletes; never call it to "make room" unless
  the owner actually asked for the artifact to go.
- All three are bound to this thread and need no approval. `artifact.update`
  returns the new `version` and `changed`; `changed: false` means the content was
  already identical, so nothing was appended. `artifact.delete` returns
  `versions_deleted` and `deleted: true`.

## Multi-turn work

- Set `follow_up: true` on the plan to run one more tool step after reading this
  result -- a read-only follow-up, or a later step that depends on this result. A write
  step pauses for the owner's approval before it runs. The loop is bounded, so plan only
  the steps you actually need.
- Read large files in chunks: `read_project_file(file_id, offset, limit)` returns
  `next_offset`; continue from it until `next_offset` is `null`. Each page is at most
  **3890 characters**; a larger `limit` is automatically clamped to 3890.
- Discover file ids with `list_project_files`; read a project or thread image on
  demand with `view_image(source, id)` instead of asking for a re-attach.

## Gotchas

- Arguments are validated strictly; an unknown or mistyped field is rejected.
- Resolve a project with `project.find` before naming it; ids and slugs are not
  guesses.
