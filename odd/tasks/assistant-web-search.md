# ODD: assistant-web-search

**Branch**: `odd/assistant-web-search`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-web-search`
**Base**: `05983dae` (= `main` at branch time)
**Status**: merged — PR #329 (`a94a98b4`).

## Objective

Replace the non-functional DuckDuckGo web-search adapter with a configured Brave Search provider behind
the existing provider seam, return bounded **textual** evidence (title + url + snippet) instead of a bare
list of links, and never mask a provider failure as an empty result.

## Problem — measured, not inferred

`web.search` does not work, and it fails **silently**.

Measured 2026-09-23 from the dev host:

```
GET https://html.duckduckgo.com/html/?q=precio+calefont+chile
  status: 202
  content-type: text/html; charset=UTF-8
  bytes: 14234
  has result__a: False
  keywords present: ['anomaly', 'challenge', 'bots']
```

That is an anti-bot challenge page, not a result page. And the tool:

```
s.search('precio calefont chile', limit=5) -> 0 results
```

### Why the block reads as a valid no-hit

- `httpx.raise_for_status()` does not raise on **202** (it is 2xx).
- `_ResultParser` sees `<html>`, `<body>` and `</html>`, so all three malformed-structure guards pass.
- `candidate_count == 0`, so `if parser.unsafe_count or (parser.candidate_count and not parser.results)`
  is False.
- The adapter returns `parser.results[:limit]` → `[]`.

The assistant then truthfully reports "no results found" while the real cause is a block. Silent, and
indistinguishable from a genuine empty search. This is the failure class the operator hit.

### Second, independent defect: the tool returns no content

- `app/chat/assistant/tools/search.py:51` appends only `{"title": title, "url": url}`.
- No tool fetches a page: `kb.retrieve` is the only text-returning tool and it reads the internal KB.
- Therefore, even with a working provider, the responder receives a list of links and cannot ground a
  factual answer. With the persona forbidding invention, it would correctly refuse to assert anything —
  leaving only "here are some links".

Content is not a nicety here; it is the difference between a tool and a search box.

## Spec conflict AT-3 — resolved by the original design's own trigger

`openspec/specs/assistant-tools/spec.md:150` (AT-3) currently reads:

> Web search MUST use one bounded adapter interface over `httpx` and return source evidence. **Tavily and
> other external integrations MUST NOT be required by this capability.**

The archived design that produced it recorded *why*, and named the trigger for revisiting it
(`openspec/changes/archive/2026-09-09-panel-asistente-lumat/explore.md:14,23`):

> Use a bounded DuckDuckGo adapter over existing `httpx` for a no-dependency v1, behind one interface;
> **defer Tavily unless result quality/operational support justifies a key and dependency.**
>
> **Websearch:** DuckDuckGo via existing `httpx` is the leanest v1; **isolate it so Tavily can replace
> it.**

So the "MUST NOT be required" clause encoded a **v1 deferral**, not a permanent prohibition, and the
design explicitly anticipated replacement once operational support justified a key and a dependency. That
trigger is now met and measured above: the DuckDuckGo path is blocked, in production, by an anti-bot
challenge.

**Amendment**: AT-3's first sentence is preserved and strengthened. The "MUST NOT be required" clause is
replaced by requirements that the provider be configurable, that it return content, and that it fail
loudly. The adapter seam is retained so a non-integration provider can be reinstated without rework.

This is an amendment with evidence, not a silent override. It is a deliverable of this unit (T6).

## Contract

### Provider

Brave Search API — `GET https://api.search.brave.com/res/v1/web/search`, header `X-Subscription-Token`,
query params `q`, `count`, `country`/`search_lang` as appropriate. Provider isolated behind the existing
`search()` seam in `app/chat/assistant/tools/search.py`.

### Result shape (provider-neutral)

```python
{"title": str, "url": str, "snippet": str}
```

Brave's `description` maps to `snippet` at the provider boundary, so the seam stays provider-neutral and a
future provider only has to produce this shape.

### Bounds — the adapter owns them, never downstream truncation

- `MAX_RESULTS = 5`
- Each `title` and each `snippet` bounded by an adapter constant.
- Total serialized output must fit the responder evidence budget `_TOOL_EVIDENCE_LIMIT = 4_000`
  (`app/chat/assistant/nodes.py:37`) **with margin**, so a full result set is never truncated mid-payload.

### Failure truthfulness — the core fix

`SearchFailure` MUST be raised for: missing/empty API key, HTTP 401/403/429, any 5xx, timeout, non-JSON
body, JSON missing the expected structure, and any unrecognized challenge/block body. `[]` is reserved
**strictly** for a successful request whose result list is genuinely empty.

### Config

- `brave_search_api_key: str | None = None` in `app/config.py` (optional at boot, required at use —
  fail fast, same shape as `llm.openai_client()`).
- Forwarded in `infra/docker-compose.yml` and `infra/docker-compose.prod.yml`.
- Documented in `infra/.env.example`.
- Real value lives in `infra/.env` only (gitignored) — **never** committed, never in a test fixture, never
  echoed in logs.

### Evidence contract

A **narrow, explicit** allowance in `agent/personas/assistant.md`, in the same shape as the existing
capabilities allowance: the assistant MAY state what the retrieved web results say and MUST cite the
source URL. It does not loosen the KB rule for business questions, and it does not permit inventing
anything beyond the returned snippets.

Plus a matching instruction in `agent/prompts/assistant_respond.md`, consistent with the existing
`tool_statement` at `nodes.py:769-775`.

### Tool name is unchanged

`web.search` keeps its name and stays in `assistant.tools_whitelist` (22 entries). The whitelist, the
tool count, and `assistant.capabilities` are **not** touched.

## Scope

### In scope

| File | Change |
|---|---|
| `app/chat/assistant/tools/search.py` | `BraveSearch` provider, provider-neutral result shape, failure classification, bounds |
| `app/config.py` | `brave_search_api_key` setting |
| `infra/docker-compose.yml`, `infra/docker-compose.prod.yml` | forward the key into the api container |
| `infra/.env.example` | document `BRAVE_SEARCH_API_KEY` |
| `agent/personas/assistant.md` | narrow web-evidence allowance + citation duty |
| `agent/prompts/assistant_respond.md` | matching instruction |
| `openspec/specs/assistant-tools/spec.md` | AT-3 amendment (T6) |
| `tests/unit/test_assistant_tools.py` | adapter tests: success, block, 401/429/5xx, timeout, bad JSON, bounds, missing key |
| `tests/integration/test_assistant_harness_guardrails.py` | a `web.search` turn grounds on snippets and cites |
| `odd/tasks/assistant-web-search.md` | this document |

### Out of scope

- **SearXNG.** The retained seam makes it cheap to add later; it is not this unit.
- **Fetching full page content** (HTML extraction / arbitrary URL retrieval). Reasons in the trade-off
  below. A future single-URL tool carries its own SSRF analysis.
- **Persisting search results.** Brave forbids storing results (in part or whole) without a plan that
  grants explicit storage rights. Evidence is turn-scoped only.
- **Deploying to production.**
- **Removing `DuckDuckGoSearch`.** It stays behind the seam, unwired, so the interface remains honest
  about having more than one implementation.

### Two-sided architecture trade-off (the cut this unit accepts)

Cut: no full-page fetching, snippets only.

- **What dies if this is cut**: questions that require the deep detail of one specific page — a long
  step-by-step procedure, a complete price table, a full article — cannot be answered from snippets alone.
- **What the cut buys**: no SSRF surface from an operator-influenced URL being fetched by the VPS, no
  scraping of third-party pages against their terms, no HTML-extraction code to maintain, no large latency,
  and results that fit the responder's 4,000-character evidence budget.

If depth is later needed, it arrives as a **separate** bounded single-URL tool with its own analysis — not
by loosening this one.

## Tasks (strict TDD — observed RED before each source change)

- [x] **T1 — RED, adapter.** Failing tests first, with `respx` (available, `pyproject.toml:33`): a
  successful `200` JSON response maps to `{"title","url","snippet"}` bounded at `MAX_RESULTS`; a 202/HTML
  challenge body raises `SearchFailure`; 401, 403, 429, 500 and timeout each raise `SearchFailure`; a
  non-JSON 200 raises `SearchFailure`; JSON missing the expected structure raises `SearchFailure`; an empty
  but genuine result list returns `[]`; a missing API key raises `SearchFailure`; total output fits the
  4,000-character evidence budget.
- [x] **T2 — GREEN, adapter.** `BraveSearch` + provider-neutral shape + bounds + key fail-fast.
- [x] **T3 — Config and compose.** `brave_search_api_key` in `app/config.py`; forwarded in both compose
  files; documented in `infra/.env.example`.
- [x] **T4 — Evidence contract.** Persona allowance + responder instruction. The pinned persona phrases
  that `tests/unit/test_assistant_config.py` asserts MUST survive (see Constraints).
- [x] **T5 — Harness.** A `web.search` turn grounded on snippets, with the source URL cited, and a turn
  where the provider fails surfacing an error state rather than an empty result.
- [x] **T6 — Spec.** AT-3 amended with the reasoning and the evidence above, in the file's existing shape.
- [x] **T7 — Regression.** Full suite green; `test_web_search_is_bounded_and_failures_are_empty` replaced
  by tests asserting the **new** contract.
- [x] **T8 — Live markup sanitization.** Real Brave responses include HTML highlight tags in `title` and
   `description`; sanitize both fields with the standard-library `HTMLParser` before applying the existing
   whitespace collapse and bounds. Decode common HTML entities without adding a dependency.

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml:38` (`testing.strict_tdd: true`), runner
  `uv run pytest tests/`. Observe RED before each source change, then GREEN.
- `tests/unit/test_assistant_tools.py:494` (`test_web_search_is_bounded_and_failures_are_empty`)
  codifies the exact behavior being removed. It MUST be **replaced** by tests asserting the new contract —
  never deleted to make the change fit, and no other assertion may be weakened.
- Keep the pinned persona phrases verified by `tests/unit/test_assistant_config.py` intact: a prior unit
  lost one of them to a persona rewrite and only the full suite caught it.
- One concern per commit, ≤5 files per commit, Conventional Commits.
- **No `Co-Authored-By` and no AI attribution in commits.**
- English artifacts.
- No secret value ever enters the repo, a fixture, a log line, or this document.
- Ponytail after the code exists: report findings, never remove authorized behavior.

## Checks

```bash
cp ../lumat-agent/infra/.env infra/.env     # worktree starts without it
bash infra/test-db.sh up
eval "$(bash infra/test-db.sh env)"

uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py -q
uv run pytest tests/integration/test_assistant_harness_guardrails.py -q
uv run pytest tests/ -q

git status --short
git diff --check
```

The repository has no linter, typechecker, pre-commit or hooks. **The tests are the verification.**

Live verification with the real provider requires `BRAVE_SEARCH_API_KEY` in `infra/.env` and is recorded
as a separate evidence row, honestly marked if it could not be run.

## Acceptance criteria

1. `web.search` returns `title`, `url` and a bounded `snippet` per result.
2. A provider failure — block, auth error, rate limit, server error, timeout, malformed payload, missing
   key — raises `SearchFailure` and reaches the turn as a visible error state. It is never rendered as an
   empty result.
3. `[]` means exactly one thing: a successful search with no hits.
4. The provider is configurable and fails fast when unconfigured.
5. The assistant can ground an answer on the returned snippets and cites the source URL.
6. AT-3 is amended with the evidence, and the bounded-adapter-over-`httpx` interface is preserved.
7. The pinned persona phrases survive, the tool name and whitelist are unchanged, and the full suite is
   green.

## Progress

- 2026-09-23 — Problem measured (DDG 202 challenge → silent empty result) and the missing-content defect
  found in code.
- 2026-09-23 — Provider route chosen by the human: **Brave Search API** (over SearXNG self-hosted).
- 2026-09-23 — Worktree created with explicit human consent:
  `/home/stefan/repos/lumat-agent-odd-assistant-web-search`, branch `odd/assistant-web-search`, base
  `05983dae`.
- 2026-09-23 — This record created before the first source change.
- 2026-09-23 — T1–T7 implemented: Brave adapter, explicit failure states, bounded snippets, configuration,
  evidence instructions, harness coverage, and AT-3 amendment.
- 2026-09-23 — Live Brave verification confirmed HTTP 200 `web.results` list responses, a 1,859-character
  five-result payload, and an end-to-end grounded graph turn with cited markdown URLs. It also exposed
  `<strong>` markup in snippets, so T8 added standard-library sanitization for titles and snippets.

## Verification evidence

### Adapter RED/GREEN

```text
$ uv run pytest tests/unit/test_assistant_tools.py -q
==================================== ERRORS ====================================
ImportError while importing test module 'tests/unit/test_assistant_tools.py'.
E   ImportError: cannot import name 'BraveSearch' from 'app.chat.assistant.tools.search'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!

$ uv run pytest tests/unit/test_assistant_tools.py -q
.....................................................................    [100%]
```

The RED was an import-level failure, so no behavioral RED is claimed. The GREEN covered successful
provider-neutral mapping, bounds, challenge/HTTP/timeout/malformed-payload failures, genuine empty
results, missing key, and the evidence budget.

### Verification commands

```text
$ uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py -q
........................................................................ [ 98%]
.                                                                        [100%]

$ uv run pytest tests/integration/test_assistant_harness_guardrails.py -q
..............................                                           [100%]

$ uv run pytest tests/ -q
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 32%]
........................................................................ [ 37%]
........................................................................ [ 43%]
........................................................................ [ 48%]
........................................................................ [ 53%]
........................................................................ [ 59%]
........................................................................ [ 64%]
........................................................................ [ 70%]
........................................................................ [ 75%]
........................................................................ [ 80%]
........................................................................ [ 86%]
........................................................................ [ 91%]
........................................................................ [ 97%]
......................................                                   [100%]
=============================== warnings summary ===============================
tests/integration/test_webhook_ingest.py::test_startup_sweep_reprocesses_received
  RuntimeWarning: coroutine '_publish_all' was never awaited
tests/spec/test_projects_spec.py::test_project_slug_is_normalized_and_unique
  UserWarning: The model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 now uses mean pooling instead of CLS embedding.

$ git status --short
 M agent/personas/assistant.md
 M agent/prompts/assistant_respond.md
 M app/chat/assistant/tools/search.py
 M app/config.py
 M infra/.env.example
 M infra/docker-compose.prod.yml
 M infra/docker-compose.yml
 M openspec/specs/assistant-tools/spec.md
 M tests/integration/test_assistant_harness_guardrails.py
 M tests/unit/test_assistant_tools.py
?? odd/tasks/assistant-web-search.md

$ git diff --check
(no output)
```

Initial implementation live verification: **NOT RUN** — the key was absent or remained a placeholder in
`infra/.env`; adapter behavior was verified with `respx` mocks. T8 live evidence is recorded below.

### T8 RED/GREEN

```text
$ uv run pytest tests/unit/test_assistant_tools.py -q
..................................F...................................   [100%]
__________ test_web_search_sanitizes_html_and_entities_in_text_fields __________
E       AssertionError: assert "<" not in result["title"]
E       AssertionError: assert '<' not in '<em>Calefon... &amp; Chile'

$ uv run pytest tests/unit/test_assistant_tools.py -q
......................................................................   [100%]
```

The implementation uses the standard-library `HTMLParser` already present in this module because
`convert_charrefs=True` removes tags through `handle_data` and decodes entities without a dependency.

### Live Brave provider evidence

| Observation | Result |
|---|---|
| Real provider response shape | HTTP 200; `web.results` was a list in every observed response. The missing-`web` risk was not confirmed. No zero-result response was forced; the observed shape is compatible with `web.results: []`, so the current empty-result path is correct. |
| Real result bounds | Five results; serialized payload was 1,859 characters, below the 4,000-character evidence budget. |
| Real graph turn | `run_assistant`, session-less, live provider: planner selected `kind=tool`, `tool=web.search`; guardrails executed it; tool status was `completed`; final response was grounded in snippets and cited source URLs as markdown links. |
| T8 defect | Brave `description` contained `<strong>entre $90.000 y $280.000</strong>` and HTML entities; raw markup could leak into tool evidence and markdown output. |

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "assistant tool registry handlers and planner pipeline"` — `TOOL_REGISTRY`,
  `ToolDefinition`, `execute_tool()`, `get_tool()`, `nodes.py`, `agent_chat.py`.
- Edge: `plan_llm` → `_planner_tool_catalog` → `TOOL_REGISTRY`; edge: `guardrails` → `execute_tool` →
  `respond_stream`.
- Direct reads: `app/chat/assistant/tools/search.py` (full), `registry.py:439,498-521`,
  `nodes.py:37,769-784`, `agent/personas/assistant.md`, `agent/prompts/assistant_respond.md`,
  `tests/unit/test_assistant_tools.py:494-506,905-931`, `openspec/specs/assistant-tools/spec.md:150-162`.
- 2026-09-23 session query: `graphify query "assistant web search adapter and tool registry"` —
  `search()`, `DuckDuckGoSearch`, `search.py`, `registry.py`, `execute_tool()`, `get_tool()`,
  `nodes.py`, and the assistant harness test.
- 2026-09-23 session paths: `graphify path "search.py" "registry.py" --undirected` — one
  `search.py <--imports_from-- registry.py` hop; `graphify path "search.py" "nodes.py" --undirected` —
  `search.py <--imports_from-- registry.py <--imports_from-- nodes.py`.

## Next step

T1–T8 are complete and merged as PR #329 (`a94a98b4`).
