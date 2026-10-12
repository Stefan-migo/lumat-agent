# chatbot-visit-duration

## Objective

Replace the chatbot's hardcoded 60-minute visit duration with a **per-service** duration, resolved
from the case's classified `service` through an existing-settings map, falling back to 60.

## Problem

`app/chat/nodes/booking.py:20-21` fixes `SERVICE = "Visita técnica"` and `DURATION_MINUTES = 60`, and
uses 60 in both the slot search (`:61`, `open_slots_for_assignment`) and the booking commit (`:138`,
`scheduling.book`). The chatbot never uses the case's classified `service` to pick a duration. The
panel already sends a free duration (create/reschedule), and `scheduling.open_slots_for_assignment()`
/ `scheduling.book()` already accept `duration_minutes`, so the plumbing exists — only the chatbot
engine hardcodes it.

The original design (`odd/tasks/agenda-agente-whatsapp.md:57`) left both the service label and the
duration "adjustable later"; this unit delivers the duration half.

## Why

A calefont diagnosis and a caldera repair are not the same length. Booked slots are computed from the
duration, so a wrong duration produces wrong availability and overlapping visits.

## Scope

- **In:** `app/services/settings.py` (default key + resolver), `app/chat/nodes/booking.py` (use the
  resolver over `case.service` in both the offer and the commit),
  `openspec/specs/service-scheduling/spec.md` (SS-1 amendment), and the unit/integration tests.
- **Out:** a service catalog / M3 scope (`openspec/config.yaml` places it in M3 and forbids expanding
  M3 without an explicit request); any panel UI (the Settings surface is section-based, not a free KV
  editor — the map is configured via seed/DB); the appointment `service` label (stays
  `Visita técnica`); asking the customer; `scheduling.py` (no change — it already takes a duration).

## Decision (owner, 2026-10-12)

Option A — minimal, non-M3. A `booking.service_durations` map in the existing settings. The chatbot
resolves the duration from the case's classified `service`; unknown/unset → **60**. Panel unchanged.
The map starts **empty** (no invented durations); the owner configures values via seed/DB.

## Constraints

- Strict TDD is ON (`openspec/config.yaml:38`), runner `uv run pytest tests/`. RED before GREEN.
- One concern per commit, ≤5 files, Conventional Commits, **no `Co-Authored-By` and no AI attribution**.
- English artifacts; neutral Chilean Spanish for any user-facing copy.
- The fallback of 60 preserves today's behavior exactly when the map is empty.
- Do NOT change `SERVICE` or `scheduling.*` signatures; do NOT touch the panel.

## Delivery strategy

- Forecast: resolver + tests ≈ 90; booking change ≈ 20; spec ≈ 25; this record ≈ 120.
  **~255 authored lines — under the ~400 review budget** → single PR.
- `delivery_strategy`: `ask-on-risk`; `chain_strategy`: n/a (single PR expected).

## Work units (stable IDs)

### S1 — Settings resolver (TDD)
- [ ] RED: unit test for `get_service_duration(session, service, default=60)` — mapped value returned;
      unknown service → 60; `None`/empty → 60; malformed/`<= 0` stored value → 60; normalization
      (case + accents) matches a mapped key.
- [ ] `SETTINGS_DEFAULTS["booking.service_durations"] = {}` and `get_service_duration()` in
      `app/services/settings.py` (normalize keys and lookup; non-positive/non-int → fallback).
- [ ] GREEN: unit test passes.

### S2 — Booking uses the resolver (TDD)
- [ ] RED: integration test in `tests/integration/test_chat_booking.py` — a case with a classified
      `service` and a `booking.service_durations` map books an appointment whose `duration_minutes`
      equals the mapped value; empty map books 60.
- [ ] `app/chat/nodes/booking.py`: resolve the duration from `case.service` in `_new_offer`
      (slot search) and in `booking()` (commit). Remove the standalone `DURATION_MINUTES` constant or
      keep it as the named fallback only.
- [ ] GREEN: integration test passes.

### S3 — Spec + close
- [ ] Amend `openspec/specs/service-scheduling/spec.md` SS-1: the appointment duration is resolved
      per service via `booking.service_durations`, falling back to 60 when unset.
- [ ] Record evidence (commits, focused pytest result) in the Progress section.

## Authorized scope

Work **only** in `/home/stefan/repos/lumat-agent-odd-chatbot-visit-duration` on branch
`odd/chatbot-visit-duration`. Do not modify the main worktree or another worktree.

## Acceptance criteria

- With an empty map, the chatbot behaves exactly as today (books 60) — zero behavior change.
- With a configured map, both the offered slots and the booked appointment use the resolved duration.
- Existing booking/scheduling tests stay green; no panel or `scheduling.*` regression.

## Checks

- Focused: `uv run pytest tests/unit/test_settings.py tests/integration/test_chat_booking.py -q`
  (via the isolated test DB: `infra/test-db.sh up` + `eval "$(infra/test-db.sh env)"`).
- Full applicable backend suite before close: `uv run pytest tests/ -q`.

## Graph nodes consulted (Step 1)

- Query `appointment booking duration minutes per service slot search open_slots_for_assignment
  service catalog` → `open_slots_for_assignment()` (`app/services/scheduling.py:227`), `book()`
  (`app/services/scheduling.py:274`), `booking()` (`app/chat/nodes/booking.py:90`),
  `test_open_slots_defaults_step_to_duration_and_respects_limit()`
  (`tests/unit/test_scheduling_unit.py:73`), `get_settings()` (`app/config.py:116`),
  `session_scope()` (`app/db.py:27`), `slotFormat()` (`web/src/components/shared/agendaTime.ts`).
- Query `new inbound after closed conversation ... get_or_create_conversation` → confirmed the
  scheduling/booking communities are disjoint from the panel sections (no panel edge affected).
- Communities: `scheduling.py`, `booking.py`. God nodes (GRAPH_REPORT): `Conversation` (134 edges),
  `Message` (124), `Case` (123) — `Case.service` is the input this unit reads.
- A narrow read-only mapper produced the initial map; every decisive line was re-verified by the
  orchestrator against the working tree.

## Progress

- Created 2026-10-12. Worktree `../lumat-agent-odd-chatbot-visit-duration`, branch
  `odd/chatbot-visit-duration`, base `main` = `8063a050`.
- **S1** (`b981226e`): `SETTINGS_DEFAULTS["booking.service_durations"] = {}` + `get_service_duration()`
  (normalized lookup, non-positive/non-int → fallback). Strict-TDD RED: `ImportError: cannot import name
  'get_service_duration'`; GREEN: `5 passed`.
- **S2** (`2c1c8a25`): `booking.py` resolves the duration from `case.service` in `_new_offer` (slot
  search) and `booking()` (commit); `DURATION_MINUTES` → `DEFAULT_DURATION_MINUTES` (fallback). RED: a
  mapped `Caldera: 90` case booked 60; GREEN: mapped case + empty-map fallback `2 passed`.
- **S3** (`7f6d8bc5`): SS-1 amended with the per-service resolution + fallback scenarios.
- Task record commit `d9af7f55`.
- **Verification:** focused `13 passed`; full backend suite `uv run pytest tests/ -q` → **1922 passed,
  exit 0** (warnings: unawaited `_publish_all` in `test_startup_sweep_reprocesses_received`; fastembed
  pooling notice). Parent spot check re-ran the focused suite: `13 passed`.
- **Native assessment:** `risk: medium` (`executable_change`, `booking.py`), 227 changed lines, 6 paths,
  **`review_due: false` (`under_budget`)**. No review started.
- Not done (owner's decision): push, PR, merge.
