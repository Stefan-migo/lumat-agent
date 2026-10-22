# HANDOFF — chatbot-intake-redesign: continue with CI-4

Date: 2026-10-08. Feature worktree cleaned; CI-1..CI-3 are merged to `main`.

## Git state
- `main` = `35261ee1` (PR #519 merged). Main worktree: `/home/stefan/repos/lumat-agent`.
- No `odd/chatbot-intake-redesign` branch or worktree exists — cleaned after each slice.
- Slices shipped: CI-1 `#512`, CI-2 `#513`, CI-3a `#516`, CI-3b `#519`.

## What the feature is
ODD feature `chatbot-intake-redesign`: make the customer WhatsApp intake **organic** (Option A) +
controlled capture + **interruptible**. Measured target: happy path ~4–5 inbound turns (from ~10–11).
Task doc: `odd/tasks/chatbot-intake-redesign.md`.

## How to resume (new chat)
1. Read `odd/tasks/chatbot-intake-redesign.md` (in `main`) + this handoff + the Engram mirror.
2. Create the ODD worktree:
   `rapso worktree create chatbot-intake-redesign --root /home/stefan/repos/lumat-agent --yes`
3. Fresh worktree setup (it has no `.venv`):
   `uv sync` → `cp ../lumat-agent/infra/.env infra/.env` → `bash infra/test-db.sh up` (derived port **5830**).
4. Strict TDD is active. Runner: `uv run pytest tests/`. Export the DB env per shell:
   `eval "$(bash infra/test-db.sh env)"`.
5. RDD (switch is ON): after each work-unit commit run
   `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <main head> --committed-only --json`
   and run the returned transition only when `review_due` is true.

## CI-4 scope (next) — media as evidence (photo/audio for the technician)
- `handoff_gate` MUST **stop routing media to a human** while the capture is active; media is stored
  as **case evidence** instead. Keep the triggers that MUST still fire: persona, complaint, injection,
  emergency.
- Add the **optional** ask: "¿tienes algo más para pasarle al técnico? (una foto, un audio…)" — never
  a mandatory capture field.
- Owner decision (2026-10-08): keep an evidence ask as an **optional technician reference**, never a
  mandatory field.
- Note: `app/chat/nodes/capture.py` still has `evidence` in `CAPTURE_FIELDS` (asked as a text field
  with a skip). CI-4 changes how media/evidence is handled.

Then **CI-5** (one golden-thread functional test per family: booking / KB / escalation / hidden) and
**CI-6** (owner tone pass on the copy).

## Decisions closed (do not re-discuss)
- Option A. Interruptible capture = hard requirement.
- Customer-facing copy: **neutral Chilean Spanish** (tú, no voseo); keep "asistente virtual"
  (`LumatRequest §1.3`).
- Photo/audio: **optional**, technician reference only; never a mandatory field.
- **Email mandatory** for booking; **consent explicit and separate**, before booking (CI-3a).
- Emergency stays instant and deterministic.

## Gotchas (verified this session)
- Test DB per worktree; port derived from the worktree directory name (this slug → **5830**); needs
  `infra/.env`.
- Fresh worktree needs `uv sync` BEFORE `test-db.sh up` (the script uses `.venv/bin/python`).
- Known-flaky (deselect in the full suite; they pass isolated):
  `tests/functional/test_seed_demo.py::test_demo_seed_populates_dashboard_windows_and_today`,
  `tests/integration/test_seed.py::test_seed_applies_cleanly_twice`.
- **Pre-merge discipline**: merge the current `origin/main` into the branch before opening the PR;
  `main` moved several times in this session. If the merge touches `app/models.py` or migrations,
  re-run the full suite over the merged tree (semantic-merge risk).
- The repo has only `.github/workflows/tests.yml` (jobs `test` + `panel`); there is NO issue-first or
  label enforcement. PRs merged with label `type:feature`, no linked issue.
- `agent/personas/classify.md` MUST stay byte-identical to `prompts.FALLBACKS["personas/classify.md"]`
  (proven by `tests/unit/test_prompts.py::test_fallbacks_equal_agent_files`).
- CI-3b model: `_pending` is now a **list** (the batch of asked fields); `consent` is the sentinel
  string; `state.extracted` carries the classifier's extracted fields.

## Key files
- `app/chat/graph.py` — `_flow_start`, `_after_capture`, `_after_research_triage`, routing.
- `app/chat/nodes/capture.py` — grouped asks, `_merge_extracted`, `CONSENT_QUESTION`,
  `EXTRACTABLE_FIELDS`, `MAX_ASKS`.
- `app/chat/nodes/classify_intent.py` — classification + `_extracted`.
- `app/chat/nodes/orchestrate.py` — `_dispatch` (mid-capture routing).
- `app/chat/nodes/handoff_gate.py` — deterministic triggers (**CI-4 target**).
- `app/chat/state.py` — `ConversationState` (`captured`, `extracted`, `capture_paused`).
- `agent/personas/classify.md`, `app/services/prompts.py` — classifier prompt + FALLBACK mirror.
- `tests/conftest.py`, `tests/integration/conftest.py` — `classify_result_for` mock mirror.
- `odd/tasks/chatbot-intake-redesign.md` — task doc.

## Engram references
- Feature tasks: topic `odd/chatbot-intake-redesign/tasks`.
- Related: `architecture/chatbot-thread-taxonomy`, `architecture/chatbot-capture-rigidity`,
  `decision/chatbot-intake-conversational`, `architecture/whatsapp-chatbot-flow`.
