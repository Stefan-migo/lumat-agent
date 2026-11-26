# Customer-aware booking offers
Align chatbot offers with customer appointment eligibility; preserve final reservation validation.
Branch: `odd/booking-customer-conflict` · Delivery: ask-on-risk, single slice forecast ~220 lines · Runner: `scripts/test.sh`.

## Specs
- **S1** — User: «ok entonces lo primero seria reproducir el caso exacto? lo pudes hacer?» and «ok vamos con eso». Turn the isolated reproduction into a regression: a previous appointment in a closed conversation must exclude overlapping new offers, without changing that appointment; an adjacent start remains valid.
- **S2** — Accepted scope: «Voy a convertir la reproducción en un test de regresión y corregir la coherencia entre oferta y reserva, sin tocar producción.» Filter customer conflicts before limiting offers and revalidate on confirmation. A customer conflict introduced after an offer must regenerate valid alternatives, not the same conflicting menu.
- **S3** — User worktree consent: «si procede». Preserve existing no-customer searches and rescheduling behavior. No production actions, deployment, Saturday intent redesign, preview changes, or automatic cancellation.

## Tasks
- **T1** — S1–S2 · inline · verified: regression RED (3 failures), customer-aware search and booking GREEN (3 cases) · commit: this work-unit commit.
- **T2** — S3 · inline · verified: quick, focused compatibility, full suite and independent verifier passed (risk item 3) · commit: this work-unit commit.
- **T3** — S1–S3 · inline · pending: native assessment/review as applicable, recovery evidence and coherent work-unit commit · commit pending.

## Log
- **L1** — Request sequence: «ok entonces lo primero seria reproducir el caso exacto? lo pudes hacer?» → «ok vamos con eso» → worktree authorization «si procede».
- **L2** — Baseline `69468cff8`. Previous isolated reproduction at deployed `2a129bb2` showed three selections of `1` returning the same menu; selecting `2` booked at the previous appointment end. Source paths are unchanged across these baselines.
- **L3** — Route inline: one coherent behavior, no parallel writer reason. Map delegated read-only because shared search also serves rescheduling. Reuse `_validate_interval`; optional customer identity defaults to None for existing consumers. Do not change rescheduling (it must allow overlap with its own prior interval).
- **L4** — Risk: item 3 (shared slot-search helpers used by booking, preview and rescheduling). Final reservation guards remain unchanged. Independent verifier follows feature checks.

- **L5** — RED observed: both graph booking cases fail (10:00 persists / same menu); service fails on unsupported customer keyword after correcting fixture to existing window semantics. GREEN: all three cases pass with real worktree PostgreSQL. No product text, guards, preview or manage changes.
- **L6** — Graph refreshed without LLM: 60,857 nodes / 87,091 edges. Path consulted: `slots_for_window → _search_slots → open_slots_for_assignment → open_slots`; shared appointment validation reused. Report re-clustering refused a smaller graph, leaving report metadata old; current AST graph and direct code used.

- **L7** — Checks observed: `bash scripts/test.sh quick` exit 0 (74s); `bash scripts/test.sh db tests/integration/test_chat_booking.py tests/integration/test_scheduling.py tests/integration/test_chat_manage.py tests/integration/test_configured_answers_availability.py` exit 0 (80 tests, 48s); `bash scripts/test.sh full` exit 0 (751s). Shape gate reports no shape surface touched; full still required at feature closure. Existing fastembed pooling warning recorded, no test failures.
- **L8** — Test runner agent ended before returning final result; parent recovered completed logs and explicit exit statuses. No suite was restarted. Independent verifier uses a fresh scratch copy and its own database; no concurrent suite targets the worktree DB.

- **L9** — Independent verifier PASS S1–S3 in fresh scratch PostgreSQL: six candidate cases passed; three baseline compatibility cases passed. Default direct/assigned/window/fallback outputs identical. Final reservation guards and reschedule self-overlap preserved. No blockers. Parent focal recheck passed all three regression cases.
- **L10** — Rollback: revert this work-unit commit; no migrations, configuration, stored-format changes or production operations. Native review remains pending user consent/assessment. Actual authored delta ~190 lines including this specification, within one slice.
