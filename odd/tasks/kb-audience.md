# ODD: kb-audience

## Objective

Give the KB a real per-document audience — `customer` or `internal` — enforced where retrieval
happens, so the customer-facing chatbot can never read a document meant only for Lumat, and make
that audience visible and editable in the panel.

## Problem

The KB has no audience control at all, and the surface that talks to the **public** reads the whole
active corpus. Verified against the source:

- **No visibility field.** `app/models.py:403-422` — `KbDocument` has `active` (on/off) and nothing
  else that expresses who may read it.
- **The declared mechanism is deliberately unwired.** `agent/registry.yaml:10-14` says only
  `research_triage` has runtime wiring; `app/agent_registry.py:3-7` states the module "does NOT
  enforce tools, KB scope, or memory scope beyond data declaration". A `*_scope` that looks enforced
  and is not is worse than none: it manufactures false confidence.
- **Every real consumer reads everything.** `app/chat/nodes/respond.py:130-133` (the customer
  chatbot), `app/chat/subgraphs/research_triage.py:91-98` (customer chat, topic-scoped only), and
  `app/chat/assistant/tools/registry.py:212-213` (the Lumat assistant) all call `kb.retrieve`
  without any audience filter.
- **The upload path cannot express it either.** `app/panel/api/routes/kb.py:113-131` accepts only
  `title` and `file`; `ingest_document` is called with no metadata, so `kb_chunks.source_meta` is
  `NULL` (apart from the injected `chunk_index`, `app/services/kb.py:163-169`).
- **The JSONB filter that exists cannot match.** `app/services/kb.py:315-318` filters by
  `KbChunk.source_meta["category"].astext.in_(scope)`, but no production path ever writes a
  `category`, so even the one wired scope is inert.
- **The UI shows nothing.** `web/src/components/pages/KbList.tsx` renders status, version, and cost —
  the admin has no way to see that what they upload can reach a customer.

**Risk direction (the important nuance):** the assistant is the *more* privileged consumer (cases,
agenda, KPIs, customers); the chatbot only has `kb.retrieve`. The danger is not the assistant
reading more — it is the **least** privileged consumer, the customer, reading everything.

**Why this is coupled to the threshold finding:** today the broken `min_sim=0.65` makes the bot
decline almost everything, which *masks* the exposure. The `odd/tasks/kb-workspace.md` record left
the threshold as a separate later unit, and the user sequenced audience first precisely because
fixing the threshold without fixing audience is the moment the exposure becomes real.

## Scope

**In:** a DB-enforced audience column and migration; the audience filter in `retrieve`; audience
defaults at ingest; an explicit reclassification action; the "restore never widens" rule; the
customer-chat call sites; the assistant's explicit opt-out; the panel API and serializer; the
`KbList` audience column, upload selector, reclassification control, and restore warning; the
canonical spec entry; tests and full verification.

**Out:** any change to the topic `scope` axis or to `agent/registry.yaml`'s `kb_scope` values
(they stay declared and unwired); per-version audience storage; `min_sim` calibration; the visual
redesign of `KbList`; any change to retrieval ranking, chunking, or the embedding model.

## Spec constraints (binding — do not violate)

- `openspec/specs/knowledge-base/spec.md:23-35` — **KB-2**: the bot MUST answer only from
  *authorized* KB content. This change is the first thing that makes "authorized" real.
- `openspec/specs/panel-design-system/spec.md:742` — **DS-GRAMMAR-1**: `KbList` MUST retain
  control-room `DataTable`, KPI, `Badge`, filter, and state primitives. **The `DataTable` stays.**
- `openspec/specs/panel-design-system/spec.md:749-751` — **DS-GRAMMAR-2**: styles live in
  `primitives.css` or another tokenized boundary; no hard-coded colour, no new dependency.
- `openspec/specs/panel-design-system/spec.md:763-765` — **DS-GRAMMAR-3**: reuse existing
  primitives instead of a duplicate equivalent.
- `openspec/specs/panel-app/spec.md:278-290` — **PNL-APP-17**: KB mutations MUST surface validation
  errors and refresh from the server after commit.
- `web/DESIGN_SYSTEM.md:305-311` — the KB page architecture; version creation and restoration are
  explicit and must never overwrite history silently.
- `web/DESIGN_SYSTEM.md:424` — neutral Chilean Spanish; no Argentine voseo.
- `openspec/specs/agent-orchestration/spec.md:97-105` — **AO-7**: the `source_meta.category` scope
  convention. The audience axis is **orthogonal** to it and must not be folded into that key.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-audience`
- Branch: `odd/kb-audience`
- Base: `4527fcc9` — the merge-base with `main`. The branch was cut after PR #246
  (`odd/tool-name-honesty`) had already landed, so `337fa3da` (the commit the previous session
  recorded) is NOT this branch's base. Verified with `git merge-base HEAD main`.
- Files:
  - `odd/tasks/kb-audience.md`
  - `db/migrations/027_kb_visibility.sql`
  - `app/models.py`, `app/services/kb.py`
  - `app/panel/api/routes/kb.py`, `app/panel/api/serializers.py`
  - `app/chat/nodes/respond.py`, `app/chat/subgraphs/research_triage.py`,
    `app/chat/assistant/tools/registry.py`
  - `agent/registry.yaml`
  - `tests/integration/test_kb.py`, `tests/functional/test_api_kb_settings.py`, and the existing
    customer-chat test file chosen in T4
  - `web/src/types.ts`, `web/src/api.ts`, `web/src/components/pages/KbList.tsx`,
    `web/src/components/primitives/primitives.css`, `web/src/stories/pages/KbList.stories.tsx`,
    `web/src/stories/pages/KbList.stories.test.tsx`,
    `web/src/stories/pages/_shared/mockData/kb.ts` (added during T5: the shared document
    fixtures needed the new `visibility` field)
  - `openspec/specs/knowledge-base/spec.md`, `openspec/specs/agent-orchestration/spec.md`

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml` (`testing.strict_tdd: true`); runner `uv run pytest`.
  Observe RED before each source change; never invent RED evidence.
- Test DB for this worktree: `infra/test-db.sh up` → host port **5609**, project
  `lumat-test-lumat-agent-odd-kb-audience`.
- Frontend: `cd web && npm run test` and `cd web && npm run build`.
- Artifacts in English; UI copy in neutral Chilean Spanish.
- No commit, push, or PR from a delegated phase unless the orchestrator authorizes it.
- The retrieval ranking, `DEFAULT_TOP_K`, `DEFAULT_MIN_SIM`, `CHUNK_SIZE`, and the embedding
  pipeline MUST NOT change.

## Decisions

- **D1 — Own column on `KbDocument`, not `source_meta.category`.** The column is
  `visibility kb_visibility NOT NULL DEFAULT 'internal'`, with the PG enum created in the migration
  and mapped through the existing `pg_enum()` helper (`app/models.py:40-52`) exactly like
  `DocumentFormat`. Reasons: (a) today's bug *is* a silently missing JSONB key — re-choosing JSONB
  re-commits the same class of failure; a `NOT NULL` column with a server default cannot be omitted;
  (b) `source_meta.category` is the **topic** axis that AO-7 scopes (`["valores","postventa"]`,
  `agent/registry.yaml:20`) — overloading one key with two axes makes a document unable to be both
  `postventa` and `internal`; (c) a column is directly indexable; (d) `retrieve` already joins
  `KbDocument` (`app/services/kb.py:310-314`), so the filter is one more predicate.
- **D2 — Fail-safe defaults on both ends.** Ingest defaults to `internal`; `retrieve`'s `audience`
  defaults to `customer`. A forgotten argument on either side fails **closed**, never open. The
  cost is that existing retrieval tests must state their audience explicitly — that churn is the
  honest price of not having a silent leak.
- **D3 — Audience is a consumer gate, orthogonal to the topic scope.** A new `audience` parameter,
  never a reuse of `scope`. The customer-facing consumers pass `customer`; the internal consumers
  pass `None` explicitly.
- **D4 — Restore never widens.** `restore_version` re-opens the document as `internal`
  unconditionally. The restored bytes were authored under an audience we do not store, so the only
  rule that cannot leak is the one that never widens. Re-publishing to customers is an explicit
  action. Accepted trade-off: restoring a customer-safe version costs one extra reclassification.
- **D5 — Reclassification is a dedicated action, not a field on edit.** `update_document` is left
  untouched, so a content edit can never change the audience by accident — which would be a *new*
  silent-reclassification path. A separate `set_visibility` keeps the two concerns apart and avoids
  a spurious version bump on a pure reclassification.
- **D6 — The internal surfaces opt out explicitly.** The Lumat assistant and the admin retrieval
  probe pass `audience=None` with a comment, so the intent is visible at the call site rather than
  inherited from a default.
- **D7 — No per-version audience storage.** Considered and rejected for this unit: it would need a
  per-version record, a migration, and writes in ingest/update/restore. D4 already removes the leak;
  D7 only removes the re-click.
- **D8 — Name.** DB type `kb_visibility`, Python enum `KbVisibility`, column `visibility`. The
  `memories` table already has `memory_visibility ('thread','project')`
  (`db/migrations/026_memory_provenance.sql:13`) — a different axis, a different type, a different
  table. In UI copy the KB axis is called **"Audiencia"**, never "Visibilidad", to keep the two
  apart for the human reader.

## Tasks

- [x] **T1** — `db/migrations/027_kb_visibility.sql` + `app/models.py`. RED observed:
      `ImportError: cannot import name 'KbVisibility' from 'app.models'` (collection error).
- [x] **T2** — `app/services/kb.py` (`ingest_document` audience parameter, `retrieve(audience=...)`
      with the `KbDocument.visibility` predicate, `set_visibility`, `restore_version` never-widens,
      visibility in the audit payloads) + `tests/integration/test_kb.py`. GREEN:
      `tests/integration/test_kb.py` → **20 passed**.
- [x] **T3** — Panel API (`POST /kb` audience field with a 400 on an invalid value,
      `POST /kb/{id}/visibility`, `to_doc_dict` serializes `visibility`, the search probe passes
      `audience=None`) + `tests/functional/test_api_kb_settings.py`. RED observed: **13 failed /
      24 passed** (three `test_kb_search_*` returning `[]`, the audit-shape assertion, and every new
      endpoint test at 404). GREEN: **37 passed**.
- [x] **T4** — Chat consumers: `respond.py` and `research_triage.py` pass
      `audience=KbVisibility.CUSTOMER`; the assistant tool passes `audience=None`. The six chat tests
      that broke were repaired by declaring their seeded documents `visibility=customer` (their
      subject IS the customer-facing grounding) — no assertion was weakened. Two new tests were
      added: the customer path cannot ground on an internal document, and the assistant still
      retrieves one. The delegated writer was cancelled before reporting, so the orchestrator
      produced the RED evidence itself: with the gate temporarily disabled
      (`audience=None` in both chat call sites), `test_customer_chat_cannot_ground_on_internal_kb_document`
      fails with `assert False` on the audience assertion; the source was restored byte-for-byte
      afterwards.
- [x] **T5** — Frontend: `types.ts`/`api.ts` (`uploadKbDocument` carries the audience, new
      `setKbVisibility`), `KbList.tsx` (Audiencia `Badge` column, upload `Select` defaulting to
      `internal`, reclassification control, restore confirmation stating the audience effect),
      `primitives.css`, the shared KB fixtures, and the story tests. RED observed: **6 failed /
      17 passed** in `KbList.stories.test.tsx`. GREEN: **78 files / 587 tests passed**;
      `npm run build` → `✓ built in 5.08s`.
- [x] **T6** — Specs: **KB-5 — Document Audience** added to
      `openspec/specs/knowledge-base/spec.md` (5 scenarios); the topic/audience orthogonality note in
      `openspec/specs/agent-orchestration/spec.md`; the `kb_scope` clarification comment in
      `agent/registry.yaml`. No value in the registry changed.
- [x] **T7** — Verification (all observed, exit code `0`):
  - `eval "$(bash infra/test-db.sh env)" && uv run pytest tests/ -q` → **full backend suite green**.
  - `cd web && npx vitest run` → **78 files / 587 tests passed**.
  - `cd web && npm run build` → **clean**.
  - `git diff --check` → no whitespace errors.
  - Fresh-volume schema proof: `bash infra/test-db.sh down` (removes the volume) → `up` → the suite
    applies `001_init` … `027_kb_visibility` in lexical order on an empty database and passes
    (`tests/integration/test_migrations.py` + `tests/integration/test_kb.py` → **37 passed**).

### Harness note worth keeping

`infra/test-db.sh env` must be `eval`'d before pytest. Without it `admin_database_url()` falls back
to the `DATABASE_URL` that the integration conftest sets first, so `db/migrate.sh` connects as the
unprivileged `app` role and every test errors with `password authentication failed for user "app"`.
With the export, `TEST_ADMIN_DB_URL` is explicit and migrations connect as `lumat`. This is a
pre-existing harness quirk, not something this change introduced.

## Acceptance criteria

1. A document ingested without an explicit audience is `internal`; the database rejects any value
   outside `customer | internal`, and rejects `NULL`.
2. `kb.retrieve(...)` without an explicit audience returns only `customer` documents; passing
   `audience=None` returns the whole active corpus.
3. The customer chatbot and `research_triage` cannot retrieve an `internal` document — proven by a
   test that fails against the pre-change code.
4. The Lumat assistant still retrieves `internal` documents.
5. Restoring a version of a `customer` document re-opens it as `internal`, and the UI says so
   before the action is confirmed.
6. An admin can reclassify a document without creating a new version, and the change is audited.
7. `KbList` shows every document's audience and lets the uploader choose it; the `DataTable`
   (DS-GRAMMAR-1) is retained and no hard-coded colour is introduced (DS-GRAMMAR-2).
8. The full backend and frontend suites are green, `npm run build` is clean, and only the
   authorized files changed.

## Checks

- `bash infra/test-db.sh up && uv run pytest tests/integration/test_kb.py tests/functional/test_api_kb_settings.py -q`
- `uv run pytest tests/ -q`
- `cd web && npm run test`
- `cd web && npm run build`
- `git status --short` / `git diff --check`

## Size

`git diff --shortstat 4527fcc9..HEAD` → **25 files, 883 insertions, 45 deletions**.

Breakdown: the ODD record is ~283 of those lines; tests are ~445; the rest is source
(`db/migrations/027_kb_visibility.sql` 11, `app/models.py` 13, `app/services/kb.py` 49,
`app/panel/api/routes/kb.py` 41, `app/panel/api/serializers.py` 1, the three chat call sites 15,
the web client + UI 34, specs + registry 43).

This is above the 400-line review heuristic. It is reported honestly rather than hidden: the
production-source surface is ~160 lines, and the remainder is the tests that prove the boundary,
the spec entry, and this record. It is consistent with the two most recent units in this repo
(PR #245: 9 files / +576; PR #244: 10 files / +994).

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create kb-audience`); `infra/.env` copied in; `.venv`
      synced; `web/node_modules` installed; test DB derivation confirmed (port `5609`, project
      `lumat-test-lumat-agent-odd-kb-audience`).
- [x] Graph Check (Step 1): `graphify-out/GRAPH_REPORT.md` read; `graphify query "kb retrieve ingest
      document visibility audience"` run over the KB area. Nodes consulted: `retrieve()`
      (`app/services/kb.py:287`), `ingest_document()` (`app/services/kb.py:177`), `KbDocument`
      (`app/models.py:403`), `DocumentFormat` (`app/models.py:114`), `respond()`
      (`app/chat/nodes/respond.py:115`), `_kb_check()` (`app/chat/subgraphs/research_triage.py:67`),
      `record_audit()` (`app/services/audit.py:18`), `visibility_target()`
      (`app/services/tukulpan.py:111`, the memory axis — a different subsystem, see D8). The graph
      also surfaced the prior `odd/tasks/kb-workspace.md` audience node, confirming this unit was
      already scoped as the immediate successor.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Review (native RDD)

- **Lineage** `review-308aef6320ef2aa9` · risk tier **medium** (`configuration_change` in
  `agent/registry.yaml`) · one lens: **`review-reliability`** · 25 files / 944 changed lines ·
  correction budget 200, unused.
- **Approved on the first capture, zero findings.** 0 correction rounds.
- **Consent**: the medium-risk envelope was relayed losslessly and the human chose
  *"Revisar este cambio"* (`granted`); the provider-owned grant invocation was executed once.
- **Acknowledgement consumed**: `gentle-ai.review-acknowledged/v1`, `authority: burned`,
  consumed revision `sha256:fc2a10e8f36c0f1de7f8b6eadf5f336d2ad48de8f5ce296821f5f859e8efabcf`.
- **Projection note (recurring trap, confirmed again):** the `workspace` projection reviews
  *uncommitted* changes. With the work already committed the candidate comes back empty
  (`base_tree == candidate_tree`). The fix is `--base-ref <merge-base> --committed-only` on the
  STATUS preflight — **not** un-committing.
- **Untracked scope:** `rapso worktree create` leaves an untracked
  `.opencode/tools/package-lock.json`. The preflight refuses to freeze a candidate while an
  eligible untracked path is undeclared; declaring `--untracked-scope=exclude` with the canonical
  `--expected-untracked-inventory` digest (both required together) resolves it without committing
  or deleting the generated file.

No advisory findings were raised for this candidate.

## Next step

All seven tasks are implemented and verified. Nothing has been pushed and no PR exists. Delivery
(branch push, PR, merge) is the next human decision, under ordinary repository policy.

Deliberately NOT folded into this change:

1. **`min_sim` calibration.** Still deferred, still the recorded next unit. This change makes the
   audience real, which is what the user sequenced first precisely because fixing the threshold is
   the moment the exposure would otherwise become real.
2. **Per-version audience storage (D7).** Not implemented: the "restore never widens" rule removes
   the leak, and the only cost left is one reclassification click.
3. **`R3-001`** — bound `top_k`/`min_sim` at the panel search API (advisory from the kb-workspace
   review, still open).
4. **`R3-002`** — frontend assertions for the KB search panel (advisory, still open).
5. **The visual direction of `KbList`.** Still formally open; this change keeps the `DataTable` as
   DS-GRAMMAR-1 requires.
6. **The `kb_scope` axis remains declared and unwired.** This change deliberately did not touch it:
   audience is a consumer gate, not a per-agent topic declaration. Wiring or retiring `kb_scope` is
   its own decision, and the false-confidence problem it creates is now documented in the registry.
