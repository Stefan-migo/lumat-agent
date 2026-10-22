# HANDOFF — chatbot-intake-redesign: continue with CI-5

Date: 2026-10-08. CI-4 merged; feature worktree cleaned.

## Git state
- `main` = `3894b3f3` (PR #525 merged). Main worktree: `/home/stefan/repos/lumat-agent`.
- No `odd/chatbot-intake-redesign` branch or worktree exists — cleaned after the slice.
- Slices shipped: CI-1 `#512`, CI-2 `#513`, CI-3a `#516`, CI-3b `#519`, CI-4 `#525`.

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
4. Strict TDD is active. Runner: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`.
5. RDD (switch is ON): after each work-unit commit run
   `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <main head> --committed-only --json`
   and run the returned transition only when `review_due` is true.

## CI-5 scope (next) — one golden-thread functional test per family
The task doc's "Golden threads (acceptance contract)" (task doc lines ~76–155) defines four families;
write **one functional test per family** covering the contract:
- **Family 1 — Book a visit** (`calefont`, `caldera`, `calefaccion`, `solicitar_visita`): the full happy
  path, including **turn 4** — the pivot "…¿Cuánto cuesta la visita?" is answered AND the agenda resumes.
- **Family 2 — Resolve alone (KB)**: VALORES + POSTVENTA / GARANTÍA.
- **Family 3 — Always escalate to human**: EMERGENCIA + HABLAR CON UNA PERSONA.
- **Family 4 — Threads the menu does not show**: CONSULTA, CANCELAR VISITA, REAGENDAR VISITA.
UI copy below the golden threads is the contract of intent; the exact wording is finalized in CI-6.

Then **CI-6** (owner tone pass on the copy; messages only).

## Decisions closed (do not re-discuss)
- Option A (organic intake). Interruptible capture = hard requirement.
- Customer-facing copy: **neutral Chilean Spanish** (tú, no voseo); keep "asistente virtual"
  (`LumatRequest §1.3`).
- Media (photo/audio): **never a handoff trigger** (owner Option B, CI-4). Evidence = the already-downloaded
  file + the conversation thread (Option A); the explicit media/evidence store is deferred to the debt
  phase (`media-evidence-store`).
- **Email mandatory** for booking; **consent explicit and separate**, before booking (CI-3a).
- Emergency stays instant and deterministic.

## Gotchas (verified)
- Test DB per worktree; port derived from the worktree directory name (this slug → **5830**); needs
  `infra/.env`.
- Fresh worktree needs `uv sync` BEFORE `test-db.sh up` (the script uses `.venv/bin/python`).
- Known-flaky (deselect in the full suite; they pass isolated):
  `tests/functional/test_seed_demo.py::test_demo_seed_populates_dashboard_windows_and_today`,
  `tests/integration/test_seed.py::test_seed_applies_cleanly_twice`.
- **This repo's pytest prints NO final summary line** (only progress dots). Use the **exit code** as the
  pass signal (`EXIT=0`).
- **Pre-merge discipline**: merge the current `origin/main` into the branch before opening/merging the PR
  and re-run the full suite over the merged tree (main moved twice during CI-4; CI-4 merged `d4e6b82f`).
- The repo has only `.github/workflows/tests.yml` (jobs `test` + `panel`); there is **NO** issue-first or
  label enforcement. PRs merge with label `type:feature`, no linked issue, on an `odd/...` branch (which
  does NOT match the branch-pr skill's `feat/...` regex — that is fine here).
- `agent/personas/classify.md` MUST stay byte-identical to `prompts.FALLBACKS["personas/classify.md"]`
  (proven by `tests/unit/test_prompts.py::test_fallbacks_equal_agent_files`).
- CI-3b model: `_pending` is now a **list** (the batch of asked fields); `consent` is a sentinel string;
  `state.extracted` carries the classifier's extracted fields.
- CI-4 model: media never escalates; `is_media_evidence(message)` = media `msg_type` + no text; `receive`
  acks media-only turns; `capture` resumes the agenda on a media turn without attributing it; `evidence`
  is NOT in `CAPTURE_FIELDS`; `EVIDENCE_QUESTION` is appended once to the last mandatory batch.

## Key files
- `app/chat/graph.py` — `_flow_start`, `_after_capture`, `_after_research_triage`, routing.
- `app/chat/nodes/capture.py` — grouped asks, `_merge_extracted`, `CONSENT_QUESTION`, `EVIDENCE_QUESTION`,
  `MAX_ASKS`, media-evidence resume.
- `app/chat/nodes/handoff_gate.py` — deterministic triggers (persona/complaint; media is NOT one),
  `is_media_evidence`, `MEDIA_EVIDENCE_TYPES`.
- `app/chat/nodes/receive.py` — greeting + `EVIDENCE_ACK`.
- `app/chat/nodes/classify_intent.py` — classification + `_extracted`.
- `app/chat/nodes/orchestrate.py` — `_dispatch` (mid-capture routing).
- `app/chat/state.py` — `ConversationState` (`captured`, `extracted`, `capture_paused`).
- `agent/personas/classify.md`, `app/services/prompts.py` — classifier prompt + FALLBACK mirror.
- `tests/functional/test_conversation_flows.py`, `tests/integration/test_chat_capture.py`,
  `tests/integration/test_handoff.py` — existing coverage to extend for CI-5.
- `odd/tasks/chatbot-intake-redesign.md` — task doc.

## Engram references
- Feature tasks: topic `odd/chatbot-intake-redesign/tasks`.
- CI-4 decision: `decision/media-evidence-store`.
- CI-4 delivery: `odd/chatbot-intake-redesign/ci4-delivery`.
- Related: `architecture/chatbot-thread-taxonomy`, `architecture/chatbot-capture-rigidity`,
  `decision/chatbot-intake-conversational`, `architecture/whatsapp-chatbot-flow`.
