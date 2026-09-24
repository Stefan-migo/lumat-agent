# ODD: assistant-web-fetch

**Branch**: `odd/assistant-web-fetch`
**Worktree**: `/home/stefan/repos/lumat-agent-odd-assistant-web-fetch`
**Base**: `4b31796c` (= `main` at branch time)
**Status**: slices 1 and 2 shipped as PR #348 and PR #349, **both merged**. Slice 3 is **complete and
open as PR #352** on `odd/assistant-web-fetch-slice3` — T4–T8 done, full suite 1,440 green, native review
**`approved`** with zero findings and authority burned — awaiting its merge
**Origin**: `.rapsodia-code/sessions/archived/2026-09-24-panel-agency-and-web-grounding/session.md`
(decisions 4 and 6, risk row *local extractor reintroduces an SSRF surface*); Engram #4890, #4894, #4897.

This is **U2 of three**: U1 (bounded tool chaining) is merged; **U3** (panel sub-agent delegation) is
**not** started by this unit. Deep research is not a unit.

> Base note: the handoff named `main = af0231b6`. At branch time `main` had advanced to `4b31796c`
> (PR #346, `odd/inline-style-boundary`). `git diff --name-only af0231b6..4b31796c` touches only
> `web/` and `odd/tasks/` — **zero** files under `app/`, `agent/`, `tests/` or `openspec/`. The target
> area is byte-identical; the base drifted harmlessly forward.

## Objective

Give the panel assistant a **bounded single-URL reader**: `web.fetch`. `web.search` discovers sources
and returns 200-character snippets; nothing in the house can read a page. U1 made the loop chainable
precisely so `web.search → web.fetch → answer` becomes possible. This unit adds the second half of
that chain and hardens it against the SSRF surface it necessarily reintroduces.

## Problem — measured, not inferred

**The reader does not exist, and neither does any URL or address validation.**

Verified on the merged tree (`4b31796c`), not from memory:

| Claim | Evidence |
|---|---|
| No page reader of any kind | No fetcher in `app/` other than the two search providers; `web.fetch` absent from `TOOL_REGISTRY` and the whitelist. |
| No SSRF defence anywhere | Zero `ipaddress` usage in `app/`; no private/loopback/link-local check; no scheme allowlist for arbitrary URLs; no redirect policy. The only URL check is a string prefix test on **search results**: `url.startswith(("http://", "https://"))` (`app/chat/assistant/tools/search.py:88-89`). |
| `urlparse` exists but not for this | `scripts/kb_calibration.py:60,514-525`, for database URLs. |
| Redirects already unchecked where they exist | `DuckDuckGoSearch` uses `follow_redirects=True` (`search.py:160`) with no policy. |
| The reusable sanitizer has a real hole | `_TextSanitizer` (`search.py:26-33`) keeps only `handle_data`, so tags are stripped — but `handle_data` also fires for the **body of `<script>` and `<style>`**, so raw JS/CSS would leak into page text. It is reusable, not sufficient. |
| Snippets cannot ground a deep answer | `web.search` returns `{"title","url","snippet"}` only (`search.py:90-95`). A procedure, a price table or a full article cannot be answered from 200 characters. |
| Failure translation already exists | `registry.py:618-625` turns a provider failure into `status="error"` + `evidence`; `nodes.py:811-828` surfaces it to the turn instead of an empty result. The reader inherits this path. |

## Decisions (owner-confirmed, 2026-09-24)

**D1 — Provenance: any public http(s) URL, with mandatory hardening (option A).**

- Rejected **B** (only URLs returned by `web.search` this turn): it does not remove the risk — URLs from
  a third-party index are attacker-influenceable content on arbitrary hosts, so every defence is still
  mandatory — while it costs "read this link" entirely.
- *Consequence*: the hardening below is the unit's core, not a garnish. If it is done well, A is as safe
  as B and does twice the work.

**D2 — A new tool, not a change to `web.search`.** `web.fetch`, the **23rd** entry, `read_only=True`.

- `read_only=True` is forced, not chosen: a non-read-only plan at step 2 would be refused by the U1
  write policy, and the `search → fetch` chain is the point of the unit.
- Adding a tool grows the planner catalog by ~112 tokens/turn. **Catalog cost hygiene is out of scope** —
  it is its own lane and needs a live A/B (already ruled out by the `assistant-web-search` record).

**D3 — The reader owns its bound.** The serialized result MUST fit `_TOOL_EVIDENCE_LIMIT = 4_000`
(`nodes.py:37`) with margin. No bound is raised; `_TOOL_EVIDENCE_LIMIT` was sized for snippets and stays.

**D4 — No new dependency.** `httpx` and the standard-library `html.parser` already live in `search.py`.
The extractor is local, per decision 4 of the source session.

**D5 — The mandatory hardening set.**

1. Scheme allowlist: `http`, `https` only. Nothing else, case-insensitive.
2. No credentials in the URL (`user:pass@host`).
3. Default ports only — `80` for `http`, `443` for `https`. Cheap, and it removes probing of internal
   services on arbitrary ports.
4. Resolve the host and validate **every** returned address: reject loopback, private, link-local,
   multicast, reserved, unspecified, for IPv4 and IPv6. Resolving before checking is what collapses
   alternate numeric encodings (decimal/octal/hex) and bracketed IPv6 into a form we can test.
5. Redirects handled **manually** with a cap; every hop re-runs rules 1–4. `follow_redirects=False`.
6. Byte cap on the body, enforced while reading (not only from `Content-Length`).
7. Explicit timeouts (connect and total).
8. Response content-type allowlist (`text/html`, `application/xhtml+xml`, `text/plain`).
9. Failure is explicit: every rejection raises the reader's failure type and reaches the turn as
   `status="error"`. An empty result is never faked.

**D6 — The DNS-rebinding window stays open, deliberately and on the record.**

Between our resolution and the HTTP client's own, the name can answer differently (classic rebinding).
Closing it means connecting to the validated address instead of the name. httpx exposes no resolver or
peer-validation hook, so that requires building on `httpcore` internals — an httpx implementation
detail — for a narrow window.

**Evaluated in T2 and accepted.** What the policy does bound: only `http`/`https`, only default ports,
no credentials, **every redirect hop revalidated**, body byte-capped, timeouts, text-only. What it does
**not** stop: a name that answers public first and private second, reaching a private service on port
80/443. Follow-up candidate: pin the connection (a validating network backend) if the surface widens.

## Contract

1. `web.fetch(url)` returns bounded textual evidence: the final URL (after redirects), the page title
   when present, and extracted text — with the source URL citable by the responder.
2. The serialized result fits `_TOOL_EVIDENCE_LIMIT` with margin, proven by a test at the boundary.
3. Every D5 rule is individually tested and individually refutable.
4. `[]`-style silence does not exist here: a rejected or failed fetch is an explicit error state.
5. `web.search` is untouched — name, shape, provider seam and tests all unchanged.
6. The whitelist reports **23** tools and `assistant.capabilities` stays derived, not hand-maintained.
7. The extractor never emits `<script>`/`<style>` bodies, and collapses whitespace.
8. No bound is raised; no approval path, `resume_thread` or SDB behaviour changes.

## Scope

### In scope

| File | Change |
|---|---|
| `app/chat/assistant/tools/fetch.py` (new) | SSRF policy, bounded fetch, local extraction |
| `app/chat/assistant/tools/registry.py` | args model + `ToolDefinition(..., read_only=True, ...)` |
| `agent/registry.yaml` | `web.fetch` in the assistant whitelist (22 → 23) |
| `agent/personas/assistant.md` | extend the narrow web-evidence allowance to fetched page text + citation duty |
| `agent/prompts/assistant_respond.md` | matching instruction |
| `openspec/specs/assistant-tools/spec.md` | new requirement for the reader (AT-13) |
| `tests/unit/test_assistant_web_fetch.py` (new) | reader tests: D5 rules, extraction, bounds, failure. A dedicated file, not an addition to the already-large `test_assistant_tools.py` |
| `tests/integration/test_assistant_harness_guardrails.py` | a chained `web.search → web.fetch` turn grounded on page text and citing the URL; a blocked-URL turn surfacing an explicit error |
| `odd/tasks/assistant-web-fetch.md` | this document |

### Out of scope

- **U3** — panel sub-agent delegation. **Do not start.**
- Tool-catalog cost hygiene; lazy tool loading (already rejected 2026-09-17, still at 23 tools).
- Retry/backoff for Brave's 1 rps Free limit — a separate recorded follow-up.
- Persisting fetched content; storing pages; an extraction-quality arms race (readability heuristics,
  boilerplate removal beyond script/style suppression).
- Deploying to production.
- Changing `web.search`, the approval mechanism, `resume_thread` or SDB.

## Tasks (strict TDD — observed RED before each source change)

- [x] **T1 — SSRF policy, RED + GREEN.** Pure, no network. Scheme allowlist; credentials rejected;
  default ports only; every address validated for both families across loopback, private, link-local,
  multicast, reserved and unspecified; alternate numeric forms and bracketed IPv6 collapse to a checked
  address; a public address passes. **Done.** RED was import-level (`ImportError: cannot import name
  'fetch'`) — it proves the module was missing, not the behaviour, and no behavioural RED is claimed
  for this task. GREEN: 47 passed.
  - **Measured during T1, and it changed the predicate**: `is_global` alone is not sufficient.
    `224.0.0.1` (multicast) reports `is_global=True`, and `64:ff9b::7f00:1` (NAT64-encoded
    `127.0.0.1`) reports it too. The policy is therefore `not is_global or is_multicast`, with NAT64
    addresses unwrapped first. Both bypasses are pinned by tests.
- [x] **T2 — Bounded fetch, RED + GREEN.** Happy path via `respx`; manual redirects capped and
  revalidated per hop; byte cap enforced while reading; timeouts; content-type allowlist; every failure
  explicit. D6 evaluated and recorded above. **Done.**
  - RED was import-level for the new symbols, then **genuine behavioural RED**: 13 tests failed on a
    real defect — `httpx.Client.send(..., stream=True)` returns a response that is not a context
    manager in this version. Switched to `Client.stream(...)`, which also lets `follow_redirects=False`
    be forced **per request** rather than trusted from an injected client.
  - **Mutation check (the tests must bite).** Relaxing per-hop revalidation made
    `test_fetch_refuses_a_redirect_to_a_private_address_without_requesting_it` and
    `..._to_a_non_http_scheme` fail; disabling the byte cap made `..._stops_reading_at_the_byte_cap`
    fail. Exactly 3 failures, exactly the right 3. Source restored byte-identical (diff-verified).
- [x] **T3 — Extraction and the evidence bound, RED + GREEN.** `<script>`/`<style>`/`<noscript>`/
  `<template>` bodies suppressed; title captured; whitespace collapsed; serialized output bounded to fit
  `_TOOL_EVIDENCE_LIMIT`. **Done.**
  - **Behavioural RED found a real quality defect**: adjacent `<p>` elements glued their words together
    (`$90.000segunda linea`) once whitespace was collapsed. Fixed with block-level separators, and
    pinned in **both** directions — block tags separate, inline tags must not (`foo<b>bar</b>baz` stays
    one word).
  - Worst case measured, not asserted by hand: a 5,000-character title and a 50,000-character body
    produce a serialized result under `_TOOL_EVIDENCE_LIMIT`.
- [x] **T4 — Registry and whitelist, RED + GREEN.** Args model and `ToolDefinition`; whitelist 22 → 23.
  **Done.**
  - RED was a **wiring RED**, not behavioural: the new registry-contract test failed with
    `AssertionError: assert 'web.fetch' in {...}` because the tool was not registered yet. It proves
    the registration was missing, not the reader's behaviour — that behaviour is T1–T3's.
  - **A premise in this record was wrong, and the reality is better.** No test hardcodes a tool count.
    `tests/unit/test_agent_registry.py` asserts `set(reg.assistant.tools_whitelist) == set(TOOL_REGISTRY)`,
    and the capabilities and responder-inventory tests derive from `load_assistant_config()`. So the
    recorded plan to "update the tool-count, capabilities and known-tool assertions" had nothing to
    update: adding the tool to the registry is itself what turns the existing whitelist assertion into
    the RED. Nothing was rewritten and nothing was weakened.
  - `execute_tool` needed **no** change. `FetchFailure` subclasses `RuntimeError`, so it lands in the
    existing generic error branch and produces the same `status="error"` + `evidence` envelope the
    `SearchFailure` branch does. A dedicated `except FetchFailure` would be duplicate code.
  - URL cap set to 2,000 characters as input validation at a trust boundary; the citable output stays
    bounded by `URL_LIMIT`.
  - Verified: 23 registry entries == 23 whitelist entries; assistant/config/registry/planner 124 passed;
    harness + chat 84 passed; full suite 1437 collected, exit 0.
- [x] **T5 — Evidence contract.** Persona allowance + responder instruction, as narrow as the existing
  web-search one. **Done** (`b42c604f`). RED was a config-contract test over both artifacts; the six
  phrases `tests/unit/test_assistant_config.py` pins all still pass. The reader adds one duty search
  does not have: the citation is the URL the evidence reports **after redirects**, not the requested one.
- [x] **T6 — Spec.** AT-13 with five individually refutable scenarios. **Done** (`41ad1384`).
- [x] **T7 — Harness.** The chained turn and the blocked-URL turn. **Done** (`0764cb26`).
  - The chain test asserts `tool_loop_head` takes the back-edge after the search and finishes after the
    fetch, and that the responder receives both results carrying the page text and its URL.
  - The refusal test runs the **real** `execute_tool` and the real policy: a loopback address is refused
    while resolving, before any client is built, so the turn reaches a degraded state holding the
    reader's reason instead of an empty result. No mock of the thing under test, and no network.
  - **Mutation check**: disabling the back-edge in `tool_loop_head` failed the chain assertion, and
    renaming the policy's reason string failed the refusal assertion. Exactly those two failed, and
    both sources were restored byte-identical (`git diff` empty).
- [x] **T8 — Regression and measurement.** Full suite **1,440 collected, exit 0**. **Done**, with a real
  defect found and fixed — see *Measurement* below.

## Measurement — T8 (the serialized payload against the 4,000 budget)

Measured through `_bounded_evidence`, the function `read_page` returns from, with every cap saturated
(`url` 500, `title` 200, raw `text` 3,000) and serialized with `ensure_ascii=False`, exactly as
`_render_tool_evidence` does:

| Text | Before | After (`a2c68ade`) | Text kept |
|---|---|---|---|
| Plain | 3,736 | **3,600** | 2,864 / 3,000 |
| Quote-heavy (15%) | **4,186 — over** | **3,600** | 2,414 / 3,000 |
| All quotes | **6,736 — over** | **3,600** | 1,432 / 3,000 |
| All backslashes | **6,736 — over** | **3,600** | 1,432 / 3,000 |
| All control characters | **18,060 — over** | **3,598** | 477 / 3,000 |

**The defect this exposed.** `MAX_TEXT` bounded the raw string, but the evidence travels as JSON, so
the cap that mattered was on the *serialized* payload. Three of these cases did not fit: the renderer's
truncation was the real limit, which is not what D3 means by the reader owning its bound. The existing
boundary test (`test_reader_result_fits_the_tool_evidence_budget_at_its_worst_case`) fed a 50,000-char
body of the letter `a`, which never escapes, so it passed while the guarantee was false.

Reachability was checked rather than assumed. Quotes survive extraction and are ordinary page content.
The control-character case arrives through a `text/plain` body, which is decoded and collapsed with no
parser to normalise it; the same characters written as HTML entities (`&#0;`) reach the text as U+FFFD
instead, so they are not the extreme. The fitting prefix is **bisected** rather than cut
proportionally, because a cut derived from the overshoot empties the text on an all-control page.

**Owner decision.** Shown the measurement, the owner chose to fix it inside slice 3 rather than record
it as an accepted limitation.

**Live fetch.** `read_page("https://example.com/")` was run once against the real network: url
`https://example.com/`, title `Example Domain`, 127 characters of text, serialized **197 / 4,000**. It
is recorded as a separate evidence row and is **not** part of the suite — no test reaches the network,
as the Constraints require.

## Acceptance criteria

1. `web.fetch` reads a public page and returns citable, bounded text.
2. Every D5 rule is individually tested, and a rejected URL produces an explicit error state — never an
   empty result.
3. The serialized result fits the existing evidence budget with margin, measured.
4. `web.search`, the whitelist entries and the tool count move only as specified (22 → 23), and
   `assistant.capabilities` stays derived.
5. The pinned persona phrases survive.
6. U2 changes nothing about U3, the approval mechanism, `resume_thread` or SDB; full suite green.

## Checks

```bash
cp ../lumat-agent/infra/.env infra/.env     # a fresh worktree starts without it
uv sync                                     # test-db.sh needs .venv/bin/python
bash infra/test-db.sh up                    # port 5541 for this worktree
eval "$(bash infra/test-db.sh env)"

uv run pytest tests/unit/test_assistant_tools.py tests/unit/test_assistant_config.py
uv run pytest tests/unit/test_agent_registry.py tests/unit/test_assistant_planner.py
uv run pytest tests/integration/test_assistant_harness_guardrails.py tests/integration/test_assistant_chat.py
uv run pytest tests/

git status --short
git diff --check
```

No linter, typechecker, pre-commit or hooks exist. **The tests are the verification.** A live fetch of a
real public page is recorded as a separate evidence row, honestly marked if it could not be run.

## Constraints

- **Strict TDD: ON** — `openspec/config.yaml:38`, runner `uv run pytest tests/`.
- One concern per commit, ≤5 files per commit, Conventional Commits.
- **No `Co-Authored-By` and no AI attribution in commits.**
- English artifacts.
- No test may reach the network. `respx` (already a dependency, `pyproject.toml:33`) mocks HTTP.
- Bounds are bounds: `_TOOL_EVIDENCE_LIMIT` and the other limits are not raised to make this fit.
- Ponytail after the code exists: report findings, never remove authorized behaviour.

## Delivery forecast

Estimated **~450–550 authored lines** (reader module, unit tests, registry, whitelist, persona, prompt,
spec, harness), excluding this record. That exceeds the ~400-line review budget, so this unit ships as
**chained PRs** — three slices, each independently reviewable and each well under budget:

| Slice | Content | Rationale |
|---|---|---|
| 1 | T1 + the pure SSRF policy module and its tests | Pure, network-free, refutable alone |
| 2 | T2 + T3 + tests: bounded fetch, redirects, caps, extraction, evidence bound | The fetching behaviour, still unwired |
| 3 | T4–T8: registry, whitelist, persona, prompt, spec, harness, regression | The wiring that makes it reachable |

**Chain strategy**: `stacked-to-main` (owner-confirmed 2026-09-24). Each slice merges to `main` in
order; the next slice's PR opens after the previous one merges. The slices are layers of one new
module, so the strict order costs nothing. Recorded here before the first commit, as the budget rule
requires.

## Review outcome — slice 1 (native RDD)

- **`approved`**, authority burned (`review-696c33c4ce8b4c9e`). 3 changed paths, risk **medium**, one
  lens (`review-reliability`). PR at `https://github.com/Stefan-migo/lumat-agent/pull/348`.
- **One advisory, non-blocking — `R3-malformed-url`** (`fetch.py:45`, WARNING, informational):
  `urlsplit` raises `ValueError` on a malformed bracketed host, and that escaped `resolve_target`
  instead of becoming a `FetchFailure`, so "every refusal is a FetchFailure" was not literally total.
  Verified independently before fixing: **five** malformed shapes reproduce it (`[::1/`, `[::1]x/`,
  `]foo/`, `[not]/`, `[v6.]/`).
- **Closed in slice 2** rather than by editing the reviewed candidate — a RED test over the five
  shapes, then the parser call wrapped (`a9aa36c9`). Same pattern U1 used: ship the reviewed slice,
  carry its advisory forward as tracked work.

## Review outcome — slice 2 (native RDD)

- **`approved`**, authority burned (`review-f4f9c777ac79d4d8`). 3 changed paths, risk **medium**, one
  lens. PR at `https://github.com/Stefan-migo/lumat-agent/pull/349`.
- **`R3-dns-rebinding`** (`fetch.py:153`, WARNING, informational): the rebinding window D6 already
  records and accepts. The reviewer cited that record; it stays an accepted limitation, not new work.
- **`R3-non-success-status`** (`fetch.py:161`, WARNING, informational, deterministic, introduced):
  only `>= 400` was rejected, so a 3xx outside the manual redirect set **and** an empty success such as
  `204` both travelled on as usable pages. Verified by reproduction before fixing — four statuses
  returned a "page" instead of failing.
- **Closed in slice 3** rather than by editing the reviewed candidate. Two rules replaced one: only a
  2xx is a page, and a 2xx with no body is not one either.

## Review outcome — slice 3 (native RDD)

- **`approved`, with zero findings** — not one advisory, blocking or otherwise. Authority burned
  (`review-ec4cb1d85112e471`, acknowledgement `dbec8d39…`). 11 changed paths, risk **medium**, one lens
  (`review-reliability`). PR at `https://github.com/Stefan-migo/lumat-agent/pull/352`.
- The reviewer's evidence: *"Reviewed all changed paths, including fetch failure handling, redirect/status
  boundaries, serialized evidence sizing, registry wiring, configuration, specification, and regression
  tests."* The `R3-non-success-status` fix from slice 2 and the `_bounded_evidence` bisection were both
  inside the reviewed candidate and neither was questioned.
- **The reviewed tree is not this branch's HEAD.** The review froze the candidate at the T8 commit
  (`a2c68ade`); this section and the *Status* line above were written **after** the acknowledgement, in a
  documentation-only commit. Recording an outcome cannot precede the outcome, so the order is the honest
  one — but it means the receipt covers the tree without this text, exactly as it does for slices 1 and 2.

## Graph nodes consulted (Graph Check, Step 1)

- `graphify query "assistant web fetch URL retrieval and tool registry"` → `assistant/tools/registry.py`,
  `execute_tool()`, `get_tool()`, `SearchFailure`, `ToolValidationError`, `agent_registry.py`,
  `tests/unit/test_assistant_tools.py`, `tests/integration/test_assistant_harness_guardrails.py`.
- `graphify-out/GRAPH_REPORT.md` at the branch base; hubs: `assistant/tools/registry.py`, `nodes.py`,
  `BraveSearch`, `execute_tool`, `Planner Tool Catalog`.
- Direct reads during exploration: `search.py` (full), `registry.py:600-650`, `agent/registry.yaml:55-85`,
  `openspec/specs/assistant-tools/spec.md:237-260`, `tests/unit/test_assistant_config.py`.
- **T4 Graph Check**: `graphify query "assistant tool registry whitelist and planner tool catalog"` →
  `assistant/tools/registry.py`, `execute_tool()`, `get_tool()`, `ToolValidationError`,
  `is_tool_whitelisted()`, `agent_registry.py`, `unit/test_assistant_tools.py`,
  `Planner Tool Catalog`, plus the `TOOL_REGISTRY` consumers in `test_agent_registry.py` and
  `test_assistant_harness_guardrails.py`. The query returned 257 nodes and was truncated at its token
  budget; the 65 shown already carried the two consumers that mattered.
- **Correction worth keeping**: a delegated map reported that `tests/unit/test_assistant_config.py` does
  not exist. It does, and it pins the persona phrases. Verified directly — delegation output is a lead,
  not a fact.

## Progress

- 2026-09-24 — U2 definition recovered from the source session (`session.md`, decisions 4/6 and the SSRF
  risk row) and Engram #4890/#4894.
- 2026-09-24 — Code surface mapped by a delegated read-only mapper; base drift checked and dismissed
  with evidence; environment provisioned (test-db port 5541); Graph Check run.
- 2026-09-24 — D1 (option A) confirmed with the owner. **This record written before the first source
  change.**
- 2026-09-24 — Chain strategy `stacked-to-main` confirmed with the owner before the first commit.
- 2026-09-24 — **T1 done**, slice 1: `fetch.py` SSRF policy + `tests/unit/test_assistant_web_fetch.py`.
  47 passed. Found and closed two real bypasses in the predicate (`is_global` on multicast and on
  NAT64-encoded loopback) — see the T1 entry.
- 2026-09-24 — **T2 + T3 done**, slice 2: bounded fetch, revalidated redirects, byte/timeout/content
  bounds, local extraction and the evidence bound. 69 passed in the new file; 153 passed across the
  assistant, config, registry, planner and harness files. Committed as **one** work unit — neither half
  is reachable alone (the fetch has no caller until `read_page`), so the commit's concern   is "the reader
  returns bounded citable evidence", not two separate changes. Recorded because it deviates from the
  task-by-task commit granularity used so far.
- 2026-09-24 — **Slice 1 reviewed and shipped.** Native review `approved`, authority burned; one
  advisory (`R3-malformed-url`). Full suite on the stack head: **1427 passed, 2 warnings, 183.93s**
  (1358 base + 69 new). Branch pushed at the slice-1 commit and PR #348 opened.
- 2026-09-24 — **`R3-malformed-url` closed** (`a9aa36c9`): RED over the five malformed shapes, then the
  parser wrapped. 74 passed. The fix rides in slice 2 so the reviewed slice-1 candidate stays frozen.
- 2026-09-24 — **Slice 1 merged** (PR #348 → `3d0b80f7`); its merged remote branch deleted; `main`
  synced. Slice 2 moved to its own branch `odd/assistant-web-fetch-slice2` and pushed.
- 2026-09-24 — **Slice 2 reviewed and shipped as PR #349.** Native review `approved`, authority burned;
  two advisories. Slice 3 started on its own branch `odd/assistant-web-fetch-slice3`.
- 2026-09-24 — **`R3-non-success-status` closed** (`8db50c1b`): RED over 204/300/304/305 first — all
  four returned a "page" — then two rules, only a 2xx is a page and a 2xx with no body is not one.
  78 passed.
- 2026-09-24 — **Slice 2 merged.** PR #349 merged to `main` as **`5320dbb8`**; its merged remote branch
  deleted; `main` fast-forwarded locally. Slice 3 rebased onto the new `main` (unpushed, so no rewrite
  of published history): the two slice-3 commits were replayed as `e23c1e11` and `0835ac5a`, and the
  SHA this record cited for the slice-2 fix is now `e23c1e11`, not `8db50c1b`. Slice 3's diff against
  `main` is 3 files / 56 insertions before T4.
- 2026-09-24 — **T4 done** (`45c0d88d`): `WebFetchArgs`, `_web_fetch`, the `web.fetch` registry entry
  and the whitelist line. The record's premise about hardcoded assertions was wrong — none exist — so
  nothing was rewritten and nothing was weakened. RDD assessment over the commit: risk **medium**,
  `review_due: false` (`under_budget`, 6 paths / 82 lines since `5320dbb8`), so the reviewed boundary
  stays at `main` until a later commit reaches the budget.
- 2026-09-24 — **T5, T6 and T7 done**: the evidence allowance in both artifacts (`b42c604f`), AT-13 in
  the spec (`41ad1384`), and the two harness tests with their mutation check (`0764cb26`).
- 2026-09-24 — **T8 done, and it found a real defect.** The full suite is green (1,440 collected, exit
  0), but measuring the payload against the budget showed the reader bounded raw text while the
  evidence ships as JSON: quote-heavy pages serialized to 4,186 and a `text/plain` control-character
  body to 18,060, both over the 4,000 budget, so the renderer's truncation was the real limit. The
  owner chose to fix it inside slice 3. Fixed in `a2c68ade` — the payload is measured serialized and
  the text bisected to the longest prefix that fits — with two boundary tests that fail on the old
  code. Full numbers in *Measurement — T8*.
- 2026-09-24 — **Slice 3 shipped and reviewed.** Branch pushed, **PR #352** opened against `main`
  (11 files, +391/−22; the record excluded, **274 authored lines** of the 400 budget). The owner granted
  the native review, one lens ran, and it returned **`approved` with zero findings**; authority burned
  at `review-ec4cb1d85112e471`. Delivery is the owner's decision from here.

## Next step

Slice 3 is **complete, reviewed and open as PR #352** (`approved`, zero findings, authority burned).
Delivery is the owner's: merging the PR is ordinary repository policy and no review decision depends on
it. Nothing else is outstanding on this unit.

**After the merge**: refresh Graphify once (`graphify <root> --update`) per the delivery/cleanup rule,
and U3 (panel sub-agent delegation) remains unstarted and out of this unit's scope.
