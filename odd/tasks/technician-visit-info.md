# ODD: technician-visit-info

## Objective

Make the technician's visit card tell the truth about what he is walking into. Three things, one
unit: shut the panel boundary the `tecnico` role can still reach, put the visit's safety state
(`emergency`, `priority`) on the agenda card, and make the address actionable with a map link.

The surface stays **read-only**. `design.md:9` excluded technician realtime/editing; this unit does
not reopen it. Nothing the technician can already see becomes editable, and no customer field that
`TECH-PRIVACY-1` protects becomes public.

## Problem

Source: the 2026-09-20 investigation (Engram #4455 design resolution, #4456 boundary finding, #4458
data inventory). All three findings were verified against the running stack, not inferred.

### P1 — The technician's own surface is the only link that does not know an emergency

The system already detects gas/electrical emergencies and reacts on four of five links:

| Link | Behaviour |
|---|---|
| Customer reply | Gets `emergency.safety_instructions` + `emergency.contacts` |
| Customer promise | Told "Un técnico de Lumat ha sido notificado" (`emergency.notify_message`) |
| Case row | `case.emergency = True`, `status = escalado`, `escalated_at` (`app/chat/nodes/emergency.py:82`) |
| External alert | `send_emergency_notification` to the configured owner/technician number (EM-4) |
| **Technician agenda** | **Nothing.** No signal at all |

`to_technician_appointment_dict` (`app/panel/api/serializers.py:208-226`) carries identity, service,
slot, timezone, customer contact, `status` and `case_summary` — but neither `emergency` nor
`priority`. Both columns exist and are populated by real flows. For a plumber dispatched to a gas
leak, "this is an emergency" is the single most important field on the card, and it is being
discarded at the last hop.

### P2 — The panel boundary is open to the `tecnico` role

`require_dashboard_user` (`app/panel/api/routes/dashboard.py:38-41`) correctly excludes `tecnico`.
It was applied to `/dashboard/today` — and to nothing else in the dashboard family. Verified live
with a real `tec-agenda` session cookie against `:8000`:

| Endpoint | Guard | Result |
|---|---|---|
| `/panel/api/technician/agenda` | `require_tecnico` | 200 (its own surface) |
| `/panel/api/dashboard/today` | `require_dashboard_user` | 403 |
| `/panel/api/cases` · `/conversations` · `/users` | `require_operator_json` / `require_admin_json` | 403 |
| `/panel/api/kpis` | `require_user_json` | **200** — business KPIs |
| `/panel/api/dashboard/summary` · `/trend` · `/drilldown` | `require_user_json` | **200** |

The concrete leak: `GET /dashboard/drilldown?metric=appointments&bucket_start=2026-09-19` returned
the **full panel serializer** to a technician —

```json
{"id":6,"service":"Revisión de calefont","customer_id":2,"case_id":2,"technician_id":4,
 "local_start":"2026-09-19T15:00:00","timezone":"America/Santiago","starts_at":"...",
 "ends_at":"...","duration_minutes":60,"status":"booked","history":[]}
```

`customer_id`, `case_id`, `technician_id`, `duration_minutes` and `history` are all outside the
`TECH-PRIVACY-1` allow-list. `metric=cases` uses `to_case_dict` and `metric=contacts` uses
`to_message_dict` — raw conversation messages. The dev database holds 0 inbound messages and 1 case,
so no real customer data leaked in practice, but the door is open to any valid technician credential.

### P3 — The address is not actionable

The technician has the address as dead text. He leaves the panel, opens a map, and retypes it.

There are **no coordinates anywhere in the schema**: verified via `information_schema`, no table has
lat/lng, region, city or country. The only geographic data is `customers.address` (free text) plus
`customers.comuna`. So the link cannot be a coordinate pin — it has to be an address search.

### Recorded but NOT in scope

- **`case.summary` is empty by default.** It is the only problem narrative the technician receives,
  and only the chat handoff path fills it (CM-5, `app/chat/nodes/summary.py` →
  `app/services/cases.py:106`). A visit booked by phone or by the operator arrives with no
  explanation at all. Real gap, different fix (data quality / operator flow), out of this unit.
- **The `info` tone gap in `Badge`.** Its own unit, carried in the standing handoff. This unit does
  not touch it and does not add a fifth tone.

## Scope

**In:**

- `openspec/specs/technician-agenda/spec.md` — amend `TECH-PRIVACY-1`.
- `openspec/specs/service-scheduling/spec.md` — amend `SS-TECH-2` (the second allow-list authority).
- `app/panel/api/routes/dashboard.py` — `/kpis` guard.
- `app/panel/api/routes/advanced_dashboard.py` — `summary`, `trend`, `drilldown` guards.
- `app/panel/api/serializers.py` — `to_technician_appointment_dict`.
- `tests/functional/test_api_technician.py` — allow-list assertions.
- `tests/functional/test_api_dashboard.py` (or the file that owns dashboard-role tests) — the four
  403s.
- `web/src/types.ts` — `TechnicianAppointment`.
- `web/src/components/pages/TechnicianAgenda.tsx` and its test.
- `web/src/components/primitives/primitives.css` — the card's new slots only.
- `web/src/stories/pages/_shared/mockData/technicianAgenda.ts` and the story test.
- `odd/tasks/technician-visit-info.md` — this record.

**Out:** `app/services/scheduling.py`, `app/services/cases.py`, `app/chat/**`,
`web/src/components/shared/toneMaps.ts`, `web/DESIGN_SYSTEM.md`,
`openspec/specs/panel-design-system/spec.md`, `web/src/components/pages/AgendaPage.tsx`,
`web/src/components/primitives/Badge.tsx`, any new dependency, any write path for the technician.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-technician-visit-info`
- Branch: `odd/technician-visit-info`
- Base: `f0338c1d` (main after PR #260)

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`). Backend runner:
  `uv run pytest tests/`. Frontend runner: `cd web && npm run test`. Observe RED before each source
  change; never invent RED evidence.
- UI copy stays neutral Chilean Spanish and reuses the labels already shipped in the panel.
- Token-only styling; no state is communicated by colour alone (`DESIGN_SYSTEM.md`).
- `emergency` is a boolean, not a status: it augments the visit, it does not replace `status`.
- Artifacts in English. Conventional commits, no AI attribution.
- No commits, no push, no PR unless the orchestrator authorizes it.

## Graph check

Graph freshness: `graphify-out/GRAPH_REPORT.md` was built from `0b9f3c2e`. HEAD at branch time is
`f0338c1d`; the three intervening commits touch only `scripts/kb_calibration.py`,
`tests/unit/test_kb_calibration.py` and two `odd/tasks/` records — none of them in this unit's
surface, so no mid-session rebuild is required (the incremental refresh runs once, at session close).

`graphify query "technician agenda technician allow-list serializer privacy"` returned the affected
nodes: `web/src/components/pages/TechnicianAgenda.tsx`, `app/panel/api/serializers.py`,
`app/models.py` (`Case`), `web/src/types.ts`, `shared/toneMaps.ts`, `Badge.tsx`,
`components/primitives/Button.tsx`, `hooks/useAsyncData.ts`, `AgendaPage.tsx`.

`graphify path "TechnicianAgenda.tsx" "serializers.py"` → **no directed path**. The frontend/backend
half of this contract is not connected in the graph at all; the link is the HTTP payload, which the
graph does not model. Recorded so the missing edge is not mistaken for a missing dependency.

**The graph check paid for itself:** it surfaced `SS-TECH-2 Read-Only Privacy Contract` in
`openspec/specs/service-scheduling/spec.md:49-61`, a **second** allow-list authority that the plan did
not know about. See D3.

## Decisions

- **D1 — The map link is one Google Maps `https` URL. No OS sniffing.**
  `https://www.google.com/maps/search/?api=1&query=<encoded>` opens Google Maps on Android (via App
  Links), on iOS (the app when installed, Safari otherwise) and in any laptop browser. Getting the
  literal OS default requires `geo:` on Android and `maps.apple.com` on iOS, which means user-agent
  sniffing and two code paths — for one link on one card. Rejected as the exact complexity this repo
  does not accept. Recorded so the limitation is a decision, not an oversight: on iPhone the link
  opens Google Maps rather than Apple Maps.
- **D2 — Reuse the existing tones; do not add a fifth.**
  `emergency` → `danger`. `priority === "alta"` → `warning`. Both map onto `BadgeTone` as it ships
  today. The pending `info`-tone unit stays separate and is not pulled in here.
- **D3 — `emergency` and `priority` are visit-safety fields, not "operational fields".**
  `SS-TECH-2` excludes "calendar sync, or operational fields", and its scenario asserts the serialized
  key set is *exactly* the allow-list. Both specs therefore have to be amended together and must say
  the same thing, or the change contradicts a spec it does not touch. The amendment states the
  boundary explicitly: operational fields are the panel's *workflow* state (`responsible_id`,
  `reminder_count`, `ack_by`, `notified_at`, `bundle`, `history`); `emergency` and `priority` are
  properties of the visit the technician is about to walk into. A technician who cannot see that a
  visit is an emergency cannot do his job safely.
- **D4 — No country or region is hardcoded in the UI.**
  The address is free text plus a comuna, with no region or country in the database. The query is
  `address, comuna` as-is. Appending a literal "Chile" would put a locale constant in a component;
  inventing a settings key for it is scope this unit does not need. Recorded as a known limit: an
  ambiguous address can match the wrong place.
- **D5 — The boundary closes with the guard the repo already has.**
  `require_user_json` → `require_dashboard_user` on the four routes. No new dependency, no policy
  layer, no per-route role matrix.

## Tasks

- [ ] **T1 — Spec amendments.** Amend `TECH-PRIVACY-1`
  (`openspec/specs/technician-agenda/spec.md`) and `SS-TECH-2`
  (`openspec/specs/service-scheduling/spec.md`) to admit `emergency` and `priority`, with the D3
  reasoning and the operational-vs-safety boundary written out. Both specs must leave the same
  allow-list. Update the existing scenarios that assert the exact key set.
- [ ] **T2 — RED/GREEN backend serializer.**
  - RED: `uv run pytest tests/functional/test_api_technician.py` — the exact-key-set assertion at
    line 46 fails with the extra items, and a new assertion for an emergency visit fails.
  - GREEN: `+ "emergency": case.emergency, + "priority": case.priority` in
    `to_technician_appointment_dict`. The test helper `_appointment` grows the parameters needed to
    build an emergency/high-priority visit. Every existing privacy denial stays asserted.
- [ ] **T3 — RED/GREEN boundary guard.**
  - RED: a new test proving a `tecnico` gets 403 on `/panel/api/kpis`,
    `/panel/api/dashboard/summary|trend|drilldown`; `admin`/`operador` keep 200.
  - GREEN: swap `require_user_json` for `require_dashboard_user` on the four routes.
    `dashboard.py` and `advanced_dashboard.py` must import it from the same module so there is one
    definition.
- [ ] **T4 — RED/GREEN types and fixtures.** `TechnicianAppointment` gains `emergency: boolean` and
  `priority: string | null`. RED: `npx tsc -b --noEmit` fails on every fixture missing the new
  required field. GREEN: page-test fixture, the `visit()` factory and the story mocks updated; the
  story roster includes at least one emergency visit and one `priority: "alta"` visit.
- [ ] **T5 — RED/GREEN card.** Tests first: an emergency visit is identifiable **by words**, not by
  colour alone; a high-priority visit likewise; the address renders as a link whose `href` is the
  Google Maps search URL with the address and comuna encoded. GREEN: `Badge` for the safety state,
  the address wrapped in an anchor, one `primitives.css` rule for the new slots.
- [ ] **T6 — Verification.** Backend functional layer + full suite on a quiet machine; frontend
  `npm run test`, `npx tsc -b --noEmit`, `npm run build`; browser check against this worktree's own
  API + Vite (the main worktree's `infra-api-1` mounts main, not this branch).

## Acceptance criteria

1. `GET /panel/api/technician/agenda` returns `emergency` and `priority` on every row and still never
   returns email, consent, `history`, messages, notes, calendar sync, `responsible_id`,
   `reminder_count`, `ack_by` or `bundle`.
2. The backend exact-key-set assertion names both new fields as approved, and still denies every
   protected field.
3. A `tecnico` receives 403 on `/kpis` and on `summary`, `trend`, `drilldown`; `admin` and `operador`
   keep 200 on all four.
4. An emergency visit and a high-priority visit are each distinguishable on the card **by text**, not
   by colour alone, and the distinction survives a greyscale rendering.
5. The customer address renders as a link to a Google Maps address search built from `address` and
   `comuna`; no coordinate is assumed and no country is hardcoded.
6. The technician surface remains read-only: no request that mutates state, no new endpoint, no
   editing affordance.
7. `uv run pytest tests/functional/test_api_technician.py` passes; `cd web && npm run test`,
   `cd web && npx tsc -b --noEmit` and `cd web && npm run build` pass.
8. Only the authorized files change.

## Checks

- `uv run pytest tests/functional/test_api_technician.py`
- `uv run pytest tests/` (breadth, on a quiet machine — the suite is load-sensitive)
- `cd web && npm run test`
- `cd web && npx tsc -b --noEmit`
- `cd web && npm run build`
- Browser check against this worktree's own API + Vite with the `tec-agenda` fixture (visits 5-8).

## Progress

- [x] Graph Check (Step 1) run and recorded above; it surfaced `SS-TECH-2`, the second spec.
- [x] Worktree created (`rapso worktree create technician-visit-info`), branch
      `odd/technician-visit-info` from `f0338c1d`.
- [x] Created this ODD record before the first source change.
- [x] T1 — Both privacy specifications now share the same allow-list, including `status`,
      `emergency`, and `priority`, and define the operational workflow boundary.
- [x] T2 — RED observed: two serializer failures (`Extra items in the right set: 'emergency'` /
      `'priority'` and `KeyError: 'emergency'`). GREEN: serializer and helper updated; focused
      technician tests **5 passed**.
- [x] T3 — RED observed: all four tecnico role checks returned 200 instead of 403. GREEN: the
      shared guard moved to `app/panel/api/deps.py`; dashboard functional tests passed.
- [x] T4 — RED observed: `npx tsc -b --noEmit` reported 7 fixture errors for missing `emergency`
      and `priority`. GREEN: types, page fixtures, and story roster updated; typecheck exit 0.
- [x] T5 — RED observed: two card tests failed (missing safety labels and map link). GREEN: safety
      badges and Google Maps address link added; focused page/story tests **25 passed**.
- [x] T6 — Focused backend, frontend tests, typecheck, and build passed. Full backend suite was
      attempted twice and timed out at 21% after 120s and 71% after 300s; it is partial evidence.
      Browser verification is pending because the live stack belongs to the main worktree and no
      isolated stack was started.
- [x] Correction round — Review found missing PEP8 spacing after the dashboard route, a vacuous
      phone-link assertion, and a comuna-only map link labelled as a missing address. Restored the
      spacing, asserted that no `tel:` href exists, and only render the map link when an address is
      present. RED for the address case observed: the test found an anchor to the comuna with text
      `Dirección no registrada`; GREEN focused page test **19 passed**. Sequential verification:
      focused backend **26 passed**, full backend **1010 passed, 2 warnings**, frontend **79 files /
      602 tests passed**, typecheck exit 0, build success.

## Size

`f0338c1d..working tree` is **163 changed lines over 13 tracked files** (+132 / −31) plus this
263-line task record. The package-lock file provisioned by the worktree setup remains untracked and
is not part of the unit.

Production is the small part: two serializer fields, one shared guard relocated and applied to four
routes, two safety badges, one map link, one CSS rule, two spec paragraphs. The rest is tests and
fixtures. Comfortably inside the 400-line review budget, and the pre-implementation forecast
(250–400 including the record) held. No split.

Outstanding at the time of writing: the browser check is still pending (see T6). Everything else is
green.
