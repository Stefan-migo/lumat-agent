# ODD: kb-workspace

## Objective

Make the KB an actually usable admin workspace: remove the bootstrap deadlock that blocks the first
upload, give the editor the content it is missing so it stops destroying documents, add a retrieval
probe so the KB's behaviour can be evaluated from the panel, and move the page's layout onto the
tokenized stylesheet boundary its spec requires — all without violating the canonical spec that
scopes `KbList` as a dense control-room page.

## Problem

The KB screen cannot be used at all. Verified against the running panel and against the source:

- **Bootstrap deadlock.** `web/src/components/pages/KbList.tsx:87` renders the `EmptyState` and the
  upload `Card` from the *same* ternary branch. When `docs.length === 0` only the `EmptyState`
  renders, so the control that would create the first document never appears. The empty state tells
  the user to upload the first document while withholding the means to do it. `kb_documents` is 0 and
  nothing in the UI could change that.
- **Silent content destruction.** `KbList.tsx:35` seeds the edit `Textarea` with
  `defaultValue={`Contenido de ${doc.title}…`}` — an invented placeholder, not the stored content.
  Line 36 submits exactly that value. `GET /panel/api/kb` omits `content`
  (`app/panel/api/serializers.py:398-411`) and no get-one endpoint exists, so the frontend has no way
  to load the real text. Opening `Editar` and saving without retyping overwrites the document with
  the literal placeholder string and creates a new version. `web/DESIGN_SYSTEM.md:309` forbids
  precisely this: *"never overwrite history silently"*.
- **No retrieval surface.** `kb.retrieve()` has exactly one consumer, the conversation brain
  (`app/chat/nodes/respond.py:130-145`). There is no endpoint and no screen to run a query and see
  what comes back, so the KB's real behaviour — chunking, similarity, threshold — cannot be
  evaluated.
- **Copy violates the localization contract.** `KbList.tsx:87` reads *"Subí el primer documento para
  empezar."* `web/DESIGN_SYSTEM.md:424` requires neutral Chilean Spanish and explicitly forbids
  Argentine voseo in the product surface.
- **Layout lives in inline styles.** Nearly the whole page is inline `style` objects, including the
  single-line ternary at `:87`.

## Why the frontend is first

Filling the KB is the prerequisite for exercising the conversation brain: with `kb_documents = 0`
every retrieval intent misses and hands off. The KB is the surface that unblocks the chatbot test, so
fixing it first is the shortest path to a testable agent.

## Spec constraints (binding — do not violate)

- `openspec/specs/panel-design-system/spec.md:742` — **DS-GRAMMAR-1**: `KbList` MUST retain
  control-room `DataTable`, KPI, `Badge`, filter, and state primitives. The agent-app grammar applies
  to conversation routes only. **This change keeps the `DataTable`.**
- `openspec/specs/panel-design-system/spec.md:749-751` — **DS-GRAMMAR-2**: grammar styles live in
  `web/src/components/primitives/primitives.css` or another existing tokenized stylesheet boundary;
  reuse `tokens.css` / `--corp-*` roles before adding any token; add no dependency; contain no
  hard-coded colour values.
- `openspec/specs/panel-design-system/spec.md:763-765` — **DS-GRAMMAR-3**: reuse the existing
  primitives instead of a duplicate equivalent.
- `web/DESIGN_SYSTEM.md:305-311` — the KB page architecture (admin workspace, not a file gallery).
- `web/DESIGN_SYSTEM.md:375` — approved KB status labels.
- `web/DESIGN_SYSTEM.md:424` — neutral Chilean Spanish; no Argentine voseo.

Redesigning `KbList` into the Assistant Lumat conversational line is **out of scope**: it would
require a formal amendment to DS-GRAMMAR-1 / PNL-APP-12. It was evaluated and deferred.

## Scope

**In:** the two new panel KB endpoints and their tests; the frontend API client and types; the KB page
fixes, copy, layout extraction to the tokenized stylesheet; the KB search surface; updated Storybook
stories and tests.

**Out:** any change to `app/services/kb.py` (retrieval logic is reused unmodified); hard delete (no
endpoint exists, it is not needed to evaluate retrieval, and `Deshabilitar` already covers
withdrawal); the conversation brain; the agent-app grammar rollout to other dense pages; any spec
amendment.

## Authorized scope

- Worktree: `/home/stefan/repos/lumat-agent-odd-kb-workspace`
- Branch: `odd/kb-workspace`
- Base: `b38e33bd`
- Files: `odd/tasks/kb-workspace.md`, `app/panel/api/routes/kb.py`,
  `app/panel/api/serializers.py`, `tests/functional/test_api_kb_settings.py`,
  `web/src/api.ts`, `web/src/types.ts`, `web/src/components/pages/KbList.tsx`,
  `web/src/components/primitives/primitives.css`, `web/src/stories/pages/KbList.stories.tsx`,
  `web/src/stories/pages/KbList.stories.test.tsx`

## Constraints

- **Strict TDD: ON** — source `openspec/config.yaml` (`testing.strict_tdd: true`); runner pytest via
  `uv run pytest`. Observe RED before each source change; never invent RED evidence.
- Python test command (isolated test DB for this worktree, host port `6156`, project
  `lumat-test-lumat-agent-odd-kb-workspace`): `infra/test-db.sh up`, then `uv run pytest <paths> -q`.
- Frontend checks: `cd web && npm run test` and `cd web && npm run build`.
- Artifacts in English; UI copy in neutral Chilean Spanish.
- No commits, no push, no PR from a delegated phase unless the orchestrator authorizes it.

## Decisions

- **D1 — Keep the `DataTable`.** DS-GRAMMAR-1 names `KbList` as a dense control-room page. The
  page's problems are a deadlock, an inline-style soup, and dishonest copy — none of them require
  abandoning the table. Rebuilding it as a conversational surface is a spec change, not a redesign.
- **D2 — The retrieval probe is a read endpoint over the existing service.** `kb.retrieve()` already
  returns `document_id`, `version`, `chunk_index`, `content`, `source_meta`, and `similarity`
  (`app/services/kb.py:326-336`). The endpoint adds the document `title` via a join and nothing else.
  No retrieval logic is reimplemented or changed.
- **D3 — `top_k` and `min_sim` are caller-controlled on the probe.** Evaluating the KB means moving
  the threshold and observing the effect; hard-coding the production defaults would make the probe
  useless for that.
- **D4 — Content exposure is opt-in on the serializer.** Adding `content` to the list payload would
  inflate every list response. The get-one endpoint asks for it explicitly.
- **D5 — Static layout moves to `primitives.css` under a KB-scoped section.** DS-GRAMMAR-2 requires a
  tokenized stylesheet boundary and forbids hard-coded colours. Runtime-only values (none are needed
  here) would stay inline.

## Tasks

- [x] **T1** — RED/GREEN: `GET /panel/api/kb/{doc_id}` returning the document **including
  `content`**, admin-only, 404 JSON when absent. Tests in
  `tests/functional/test_api_kb_settings.py` following its existing `_login`/`_seed_doc` patterns.
- [x] **T2** — RED/GREEN: `GET /panel/api/kb/search?q=&top_k=&min_sim=` returning
  `document_id`, `title`, `version`, `chunk_index`, `content`, `similarity`, ordered best-first.
  Tests: relevant hit, below-threshold → empty, disabled document excluded, `top_k` and `min_sim`
  honoured, admin-only 401/403.
- [x] **T3** — `web/src/api.ts` + `web/src/types.ts`: `getKbDocument`, `searchKb` and their types.
- [x] **T4** — RED/GREEN: the upload control is reachable in the empty state. **Fix the test that
  blessed the bug**: the empty story must assert the available action, not only the message.
- [x] **T5** — The edit form loads the stored content from T1 instead of a placeholder.
- [x] **T6** — KB search surface: query field, results with similarity, empty/error states, using the
  existing control-room primitives.
- [x] **T7** — Copy: neutral Chilean Spanish (remove voseo) and status labels per `DESIGN_SYSTEM.md:375`.
- [x] **T8** — Layout extracted from inline styles into `primitives.css` with existing tokens;
  DS-GRAMMAR-2 satisfied (no hard-coded colours, no new dependency).
- [x] **T9** — Storybook stories and tests updated; full suite green. **Partial:** the story *file*
  itself was not modified — the component's props did not change, so the existing stories still
  render and every story test passes. No story can yet drive the search-result state, because
  `SearchPanel` owns its own fetch instead of taking injectable props like `KbList` does. Recorded
  as a limitation, not silently claimed as done.

## Acceptance criteria

1. With zero documents, the panel renders the upload control and a document can be created from the
   UI. A regression test fails against the pre-change code.
2. Opening `Editar` on an existing document shows its **stored content**; saving without edits does
   not alter the document's text.
3. `GET /panel/api/kb/search` returns ranked chunks with similarity; lowering `min_sim` returns more
   results and raising it returns fewer; a disabled document never appears.
4. UI copy contains no Argentine voseo and uses the approved status labels.
5. `KbList` still renders a `DataTable` with control-room primitives (DS-GRAMMAR-1 holds).
6. No hard-coded colour value is introduced in the KB styles.
7. Only the authorized files change.

## Checks

- `infra/test-db.sh up && uv run pytest tests/functional/test_api_kb_settings.py tests/integration/test_kb.py -q`
- `uv run pytest tests/ -q`
- `cd web && npm run test`
- `cd web && npm run build`
- `git status --short` / `git diff --check`

## Progress

- [x] Created this ODD record before the first source change.
- [x] Worktree created (`rapso worktree create kb-workspace`); `infra/.env` copied in; test DB up on
      port `6156`; `.venv` synced.
- [x] Graph Check (Step 1): `graphify query` over the KB area; `graphify-out/` present and fresh.
      It surfaced `PNL-APP-12` and the canonical `DS-GRAMMAR-1`, which is what stopped an
      out-of-scope redesign.
- [x] T1 + T2 — commit `27b6dfd0`. RED observed (`assert 404 == 200`, `KeyError: 'results'`,
      `{'detail': 'Not Found'} != {'detail': 'kb document not found'`, `assert 404 == 400`).
- [x] Verification of T1 + T2 — `uv run pytest tests/functional/test_api_kb_settings.py -q` →
      `29 passed`; `tests/integration/test_kb.py` → `14 passed`; **full suite `tests/` → 100%,
      `EXIT=0`**. The delegated writer reported `partial` only because the full suite exceeded its
      20-minute budget; re-run by the orchestrator proved the timeout was CPU contention from a
      sibling worktree (`odd/tool-name-honesty`) running the suite concurrently, not a failure.
- [x] T3..T9 — commit `9f153656`.
- [x] RED proven empirically for T4/T5: with the **pre-change** `KbList.tsx` restored and the new
      tests in place, `renders the empty state with an operable upload action` fails with
      `Unable to find an accessible element with the role "heading" and name "Agregar documento"`
      — i.e. the upload control genuinely did not exist in the empty state — and
      `loads the stored document content when editing` fails with
      `Unable to find an element with the display value: Contenido almacenado desde la base de conocimientos..`
- [x] GREEN: `npx vitest run` → **567 passed / 77 files**; `npm run build` (`tsc -b && vite build`) →
      `✓ 332 modules transformed`, `built in 4.21s`.
- [x] Spec check: `KbList` still renders `DataTable` for both the document list and the search
      results (DS-GRAMMAR-1); no hard-coded colour in the CSS additions, no new dependency
      (DS-GRAMMAR-2); only the nine authorized files changed.
- [x] End-to-end against the isolated stack (`-p lumat-kb`, host `:8001`, freshly seeded admin):
      login `200`; upload of a real `.md` → `200` with `provider=local`,
      `model=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (real embeddings, no fake);
      `GET /panel/api/kb/1` returns `content`; `GET /panel/api/kb` does **not**; `/kb/search` honours
      `min_sim` and `top_k`; blank `q` → `400`, missing `q` → `422`.

### Finding worth escalating: the production similarity threshold looks too strict

Measured against one small seeded document with the real embedding model:

| Query | Similarity | vs production `min_sim = 0.65` |
| --- | --- | --- |
| `cuanto cuesta la mantencion del calefont` | **0.6237** | **below — miss** |
| `instalacion cocina a gas` | 0.5491 | below — miss |
| `mantencion anual calefont` | 0.5070 | below — miss |
| `receta de empanadas` (unrelated control) | 0.1935 | below — correctly a miss |

A clearly relevant, naturally phrased question about a document that **is** in the KB scores below
the threshold, so the brain takes the "cannot answer reliably" path and hands off. The probe is
exactly what surfaced this.

**Honest limits:** one three-line document, four queries, no chunk-boundary study, and the model is a
small multilingual MiniLM. This is a signal, not a benchmark. It does not, on its own, prove the
threshold is wrong — but it does mean the threshold must be evaluated against a realistic document
corpus before go-live, and `min_sim` is now tunable from the panel for exactly that.

## Recovery

Resume with `mem_context`, then the project-scoped `mem_search` for this feature, then
`mem_get_observation` for the full document, then read this file.

## Review (native RDD)

- **Lineage** `review-cbd1881f7f51f9b2` · risk tier **medium** (`executable_change` in
  `app/panel/api/routes/kb.py`) · one lens: **`review-reliability`** · 9 files / 559 lines ·
  correction budget 200, unused.
- **Approved on the first capture, zero blocking findings.** 0 correction rounds.
- **Projection note (recurring trap):** the `workspace` projection reviews *uncommitted* changes; with
  the work already committed the candidate came back empty (`base_tree == candidate_tree`,
  `paths: []`). The fix is `--base-ref <base> --committed-only` on the STATUS preflight — **not**
  un-committing. See the recorded recipe in Engram.
- **Advisory findings (non-blocking, no correction offered for this candidate):**
  - `R3-001` — **WARNING** — `app/panel/api/routes/kb.py:72-74`: the search endpoint accepts
    unrestricted `top_k` and `min_sim`, including non-positive or out-of-range values, with no API
    validation. *The orchestrator had already flagged this risk; it is confirmed and deferred.*
  - `R3-002` — **SUGGESTION** — `web/src/components/pages/KbList.tsx:98-119`: the search panel's
    request wiring and its loading/empty/error/denied states lack frontend assertions; the backend
    tests do not prove the UI sends the intended parameters or renders what comes back.
- Acknowledgement consumed: `gentle-ai.review-acknowledged/v1`, `authority: burned`.

Both advisories are recorded as **separate later work**, never as a reason to re-run review on this
candidate.

## Next step

Reviewed and approved. **Nothing has been pushed and no PR exists.** Delivery (branch push, PR,
merge) is the next human decision, under ordinary repository policy.

Deferred, recorded, and deliberately NOT folded into this change:

1. **`min_sim` calibration.** The probe measured 0.39–0.62 for clearly relevant queries against a
   production threshold of 0.65. Suspects, in cheap-to-expensive order: chunking (500/50), the
   quantized ONNX variant, the model choice, and the absolute-threshold rule itself. Needs a labelled
   set before any number changes.
2. **KB audience scoping (decided: option B).** The KB has no visibility field; `kb_scope` is
   declared in `agent/registry.yaml` but deliberately not enforced; both the chatbot and the Lumat
   assistant read the whole active corpus. **This is the business-risk item** and it goes first.
   It gets its own worktree.
3. **`R3-001`** — bound `top_k`/`min_sim` at the API.
4. **`R3-002`** — frontend assertions for the search panel.
5. **Visual direction of `KbList`.** Still formally open: this change respects DS-GRAMMAR-1 and keeps
   the `DataTable`. A redesign into the Assistant Lumat line would need a DS-GRAMMAR-1 / PNL-APP-12
   amendment.
