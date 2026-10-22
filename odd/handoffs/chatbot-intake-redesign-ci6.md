# HANDOFF — chatbot-intake-redesign: continue with CI-6

Date: 2026-10-08. CI-5 merged (#530); feature worktree cleaned.

## Git state
- `main` = `37c88f58` (PR #530 merged). Main worktree: `/home/stefan/repos/lumat-agent`.
- No `odd/chatbot-intake-redesign` branch or worktree exists — cleaned after the slice.
- Slices shipped: CI-1 `#512`, CI-2 `#513`, CI-3a `#516`, CI-3b `#519`, CI-4 `#525`, CI-5 `#530`.

## What the feature is
ODD feature `chatbot-intake-redesign`: make the customer WhatsApp intake **organic** (Option A) +
controlled capture + **interruptible**. Measured target: happy path ~4–5 inbound turns (from ~10–11).
Task doc: `odd/tasks/chatbot-intake-redesign.md`.

## How to resume (new chat)
1. Read `odd/tasks/chatbot-intake-redesign.md` (in `main`) + this handoff + the Engram mirror.
2. Create the ODD worktree:
   `rapso worktree create chatbot-intake-redesign --root /home/stefan/repos/lumat-agent --yes`
3. Fresh worktree setup (no `.venv`):
   `uv sync` → `cp ../lumat-agent/infra/.env infra/.env` → `bash infra/test-db.sh up` (derived port **5830**).
4. Strict TDD. Runner: `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/`.
5. RDD (switch ON): after each work-unit commit run
   `gentle-ai review assess --cwd <worktree> --agent opencode --base-ref <last reviewed boundary> --committed-only --json`
   and run the returned transition only when `review_due` is true.
   - Known gotcha: `review start` / `review status` may fail at preflight with
     `immutable_review_transport_unsupported` (opencode alternately supported/unsupported — obs
     #5007/#5379). Retry the **exact** command a few times; the slot is reoffered and it succeeds.

## CI-6 scope (next) — owner tone pass on the copy (messages only)
The owner corrects the customer-facing copy during manual testing; **messages only, no flow or
behavior changes**. The golden-thread copy in the task doc (lines ~76–155) is the contract of intent;
CI-6 finalizes the exact wording.

### Where the copy lives
- `app/services/settings.py` — `MESSAGE_DEFAULTS` (greeting, farewell, emergency safety lines, contacts).
- `app/chat/nodes/receive.py` — `greeting()`, `EVIDENCE_ACK`.
- `app/chat/nodes/capture.py` — `CAPTURE_FIELDS` questions, `CONSENT_QUESTION`, `EVIDENCE_QUESTION`,
  `COMPLETION_REPLY`, skip words.
- `app/chat/nodes/handoff.py` — `HANDOFF_REPLY`.
- `app/chat/nodes/emergency.py` — safety protocol messages.
- `app/chat/nodes/booking.py`, `app/chat/nodes/manage.py` — slot offer / confirmation / cancel /
  reschedule copy.
- `scripts/kb_fidelity.py` consumes the greeting.

### Copy constraints (closed)
- **Neutral Chilean Spanish** (tú, no voseo); keep **"asistente virtual"** (`LumatRequest §1.3`).
- Artifacts / code / commits in English; the customer copy is the only Spanish artifact.

### Tests assert literal substrings — CI-6 must keep them or update the tests
CI-5 and the existing functional tests assert substrings of the copy. Changing these strings will
break tests, so update the assertion deliberately when the copy changes:
- `MESSAGE_DEFAULTS["greeting"]` (exact) and `"asistente virtual"`.
- `"¿Cuál es tu nombre?"` (`capture.py`), asserted present/absent in several tests.
- `"autorizas"` (consent question).
- `"correo"` / `"horario"` (capture resume after the pivot).
- `"1."` (numbered slot / manage offers), `"confirm"` (booking confirmation), `"horarios"` (reschedule).
- `"INSTRUCCIONES DE SEGURIDAD"` and `"No enciendas"` (emergency).
- `"asesor"` (handoff reply).

### Flow vs copy (do not conflate)
CI-5 revealed the code's actual flow differs from the golden-thread narration: the bot starts capture
immediately after the intent (there is no "¿Te parece?" confirmation turn, so the golden thread's
turn-3 "ya, sí" has no code equivalent), and the capture asks the first 2–3 still-missing fields (not
exactly "correo + horarios"). That is a **flow** difference, out of CI-6's copy-only scope — flag it
to the owner; do not "fix" it by editing copy.

### Pending wording ratification
- **Family 2 POSTVENTA:** the task doc example `"quedó con una fuga"` escalates as an emergency
  because a bare `fuga` is a strong safety keyword by design (`app/services/emergency.py`). The CI-5
  test uses `"fuga de agua"` (the benign qualifier) and pins the bare-leak escalation in its own test.
  Owner to ratify the wording (task doc note at Family 2).

## Decisions closed (do not re-discuss)
- Option A (organic intake). Interruptible capture = hard requirement.
- Customer copy: neutral Chilean Spanish (tú, no voseo); keep "asistente virtual".
- Media never a handoff trigger (CI-4); evidence = downloaded file + thread; explicit store deferred
  (`media-evidence-store`).
- Email mandatory for booking; consent explicit and separate (CI-3a).
- Emergency instant and deterministic.

## Gotchas (verified)
- Test DB per worktree; port from the worktree dir name (slug → **5830**); needs `infra/.env`.
- Fresh worktree needs `uv sync` BEFORE `test-db.sh up`.
- Known-flaky (deselect in the full suite; pass isolated):
  `tests/functional/test_seed_demo.py::test_demo_seed_populates_dashboard_windows_and_today`,
  `tests/integration/test_seed.py::test_seed_applies_cleanly_twice`.
- pytest prints NO final summary line — use the **exit code** (`EXIT=0`).
- Pre-merge discipline: merge the current `origin/main` into the branch before the PR and re-run the
  full suite over the merged tree (main moved 3× during CI-5).
- Repo has only `.github/workflows/tests.yml` (jobs `test` + `panel`); **no** issue-first / label
  enforcement, no PR template. PRs on `odd/...` branches; CI-5 used label `type:chore` (test-only),
  prior feature slices used `type:feature`.
- `agent/personas/classify.md` MUST stay byte-identical to `prompts.FALLBACKS["personas/classify.md"]`
  (`tests/unit/test_prompts.py::test_fallbacks_equal_agent_files`).
- **Worktree cleanup gotcha:** `rapso worktree cleanup <slug> --remote` removes the worktree and the
  local/remote branch but leaves the test DB container **and** network running. Stop them:
  `docker rm -f lumat-test-lumat-agent-odd-<slug>-db-test-1` and
  `docker network rm lumat-test-lumat-agent-odd-<slug>_default`.

## Key files
- `app/chat/graph.py` — routing, `_flow_start`, `_after_capture`, resume.
- `app/chat/nodes/{receive,classify_intent,capture,orchestrate,handoff_gate,handoff,booking,manage,respond,emergency}.py`.
- `app/chat/state.py` — `ConversationState` (`captured`, `extracted`, `capture_paused`).
- `app/services/settings.py` — `MESSAGE_DEFAULTS`, emergency keywords.
- `app/services/prompts.py`, `agent/personas/classify.md` — classifier prompt + FALLBACK mirror.
- `tests/functional/test_golden_threads.py` — CI-5 golden threads.
- `tests/functional/conftest.py` — `seed_customer_kb`, `seed_booking_availability`, `seed_future_appointment`.
- `tests/conftest.py` — `classify_result_for` (the shared classifier fake).
- `odd/tasks/chatbot-intake-redesign.md` — task doc.

## Engram references
- Feature tasks: `odd/chatbot-intake-redesign/tasks`.
- CI-5: delivery `odd/chatbot-intake-redesign/ci5-delivery`, review `.../ci5-review`, PR `.../ci5-pr`.
- CI-4 decision: `decision/media-evidence-store`.
- Related: `architecture/chatbot-thread-taxonomy`, `architecture/chatbot-capture-rigidity`,
  `decision/chatbot-intake-conversational`, `architecture/whatsapp-chatbot-flow`.
