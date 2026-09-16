# Panel assistant: real operational context and live markdown

Branch: `feat/panel-assistant-context-stream` (base `main` @ `01e503f4`)
Feature id: `panel-assistant-context-and-stream`

## Objective

Two fixes on the assistant surface (`web/src/components/pages/AgentChat.tsx`), both
closing gaps left by the panel UX backlog after PR #210:

- **T1 (backlog D)** — the "Contexto operativo" sidebar must show real data instead
  of a value sourced from the wrong channel.
- **T2 (backlog E9)** — the assistant's live stream must render as markdown while it
  arrives, not only after it is persisted.

## Problem

**T1.** The sidebar renders `Conexión: {stateLabels[connection]}`. That `connection`
comes from `realtimeClient.subscribeStatus`, which subscribes to `/panel/ws` — the
**client-conversations** realtime queue. The assistant does not use that channel at
all: its progress travels over SSE (`streamChatEvents` → `app/panel/api/routes/chat.py:310`)
and its live state is written to the DB by `publish_live`
(`app/services/agent_chat.py:581`, "best-effort short transaction for progress visible
to SSE clients"). `app/panel/api/routes/realtime.py` contains no reference to the
internal assistant, which is the same conclusion from the other direction.

Consequence: the line reads "Desconectada" always, regardless of the assistant's real
state. It is not a stale value — it is the wrong channel, so it can never become right.
A user asks a reasonable question ("what is this panel actually for?") and the UI answers
with a lie.

**T2.** While a run streams, the reply is rendered as plain text
(`AgentChat.tsx:967`, `<p>{stream}▌</p>`). It is formatted as markdown only once the
message is persisted (`:881-885`). Two costs: the user watches raw markup (`**bold**`,
`| tables |`) and then sees the entire block re-layout when the final message lands.

## Scope

### T1 — real operational context

- Fetch the real capability payload with the existing client helper
  `getAssistantCapabilities()` (`web/src/api.ts:162`), typed as `AssistantCapabilities`
  (`web/src/types.ts:144-145`).
- Render real facts in the sidebar: tool count, knowledge-base availability, memory
  availability, resolved persona. Use the endpoint's actual keys
  (`tools[]`, `kb_available`, `memory_available`, `personas[]`).
- Remove the misleading `Conexión: …` line **from the sidebar** (`:807`).
- Keep the existing "Solo lectura. La aprobación se realiza en el flujo de conversación."
  note and the `Ejecución: {lifecycle}` line — that one is real (it comes from the run
  lifecycle, not the WS).
- Handle the fetch's loading and error states honestly. `DESIGN_SYSTEM.md` L371/L372
  require an inline or region-level alert rather than a silent failure.
- Use neutral Chilean Spanish copy, consistent with the rest of the panel.

### T2 — markdown while streaming

- Render the live buffer through the existing `Markdown` wrapper
  (`web/src/components/shared/Markdown.tsx`) instead of a plain `<p>`.
- Mitigate partial markdown: while tokens are still arriving, keep the plain-text
  rendering; once the buffer settles, render markdown. A short trailing debounce
  (roughly 150–250 ms) is the intended mechanism.
  This is earned on two grounds, not just aesthetics:
  1. **Correctness** — an unbalanced fence or half-written table renders as a jump and
     then re-lays-out when it completes.
  2. **Cost** — `react-markdown` re-parses the *entire accumulated string* on every
     render. Without a debounce that is a full remark parse per token over a growing
     string. The debounce caps re-parses to one per idle window.
- The decorative cursor (`▌`) must stay outside the rendered markdown tree and remain
  `aria-hidden`.
- Preserve the existing semantics: `role="status"`, the `aria-label` that distinguishes
  "working" from "streaming", and the thinking-dots fallback when the buffer is empty.
- Reuse `Markdown`; do **not** add dependencies. `react-markdown@10` and `remark-gfm@4`
  are already installed, and the markdown CSS already exists (`primitives.css:1530-1539`).

## Out of scope (do not expand)

- The duplicate `Conexión` indicator in the compact status strip at `:1023`. It shares
  the same `connection` state but is a separate surface; removing it is a separate
  decision. Leave it untouched and report it.
- The dead WS `token`/`message` branches at `:382-396`. Same reasoning: real dead code,
  separate concern.
- Any change to the SSE contract, the backend, or the capabilities endpoint.
- Backlog items E10 (rerun scope), F11 (assistant memory), the `reopen()` error surface,
  and the `DESIGN_SYSTEM.md` page-architecture gap.

## Constraints

- `web/DESIGN_SYSTEM.md` is the authority on taste. Read it before writing UI.
  Relevant lines: L276 (drill-down is the name), L327 (a variant needs a real consumer),
  L329 (40 px minimum control height), L371/L372 (visible error surface),
  L385 (same tone = same attention across pages), L395 (no positive green just because
  something is closed), L418 (technical identifiers only in explicitly technical views),
  L424 (no icon package), L425 (critical icons carry visible text).
- Ponytail: YAGNI → stdlib → native → already-installed dependency → one line → minimum.
  No new abstractions, no new dependency, no boilerplate. Deletion over addition.
- Technical artifacts in English. UI copy in neutral Chilean Spanish.
- Do not commit. The human owns commits.

## Tasks

- [x] **T1** — Sidebar shows real assistant capabilities; misleading `Conexión` line gone.
- [x] **T2** — Live stream renders markdown once it settles, plain text while streaming.
- [x] **T3** — Tests updated/added for both, and the full suite green.

## Progress

| Task | State | Evidence |
| --- | --- | --- |
| T1 | done | `AgentChat.tsx` — capabilities fetch on first sidebar open (`capabilitiesRequested` ref caches it), loading + error states, sidebar renders tools/kb/memory/persona; the `Conexión` line is gone from the sidebar. `connection` state is left in place because the footer strip (`:1023`) still uses it. |
| T2 | done | `AgentChat.tsx` — 200 ms trailing debounce into `settledStream`; literal text while tokens arrive, `Markdown` once settled, cursor kept inside the literal branch. |
| T3 | done | `AgentChat.test.tsx` — the old connection-state test became a capabilities test; added a capabilities error-state test and a stream literal→markdown transition test. Net +2 tests (561 → 563). |

### Parent correction applied during readback

The writer's first version hoisted the decorative cursor `▌` out of the literal-text
paragraph and made it a *sibling* of the rendered block. Two regressions came with that:

1. The cursor stopped matching `.assistant-chat__stream span`, so it lost its
   `--info` colour and its blink animation.
2. Because the preceding element is block-level in both branches, the cursor fell onto
   its own line instead of trailing the text.

Corrected to: the literal-text branch stays byte-identical to the previous behaviour
(cursor inside the paragraph, styling intact), and the settled branch renders
`Markdown` with no trailing cursor — the same shape a persisted reply already uses.
No CSS change was needed. Tradeoff accepted and worth stating: the blinking cursor now
belongs to the pre-format phase only.

### Verification (observed)

Baseline before: 77 files / 561 tests.

- `npm run build` → exit 0 (`tsc -b` + `vite build`, built in 2.68 s). Pre-existing
  warning only: the JS chunk exceeds 500 kB.
- `npm test` → **77 files / 563 tests passed** (50.6 s).

Re-run after the parent correction: same result, 77 files / 563 tests.

### Open risks carried forward

- A failed capabilities fetch is not retried within the session (`capabilitiesRequested`
  is set before the request, so the error state is terminal until reload). Accepted as
  YAGNI; a retry affordance is a separate decision.
- The duplicate `Conexión` in the compact status strip (`:1023`) still reports the
  client-conversations channel. Deliberately out of scope — reported, not fixed.
- The dead WS `token`/`message` branches (`:382-396`) remain.

## Acceptance criteria

1. The sidebar renders facts from `GET /panel/api/assistant/capabilities`, not from
   the realtime conversations channel.
2. No "Desconectada"/"Conexión" value in the sidebar can be produced by a channel that
   never carries assistant data.
3. With the endpoint failing, the sidebar shows an honest error state, not a stuck
   "Cargando…" and not a fabricated value.
4. A streaming reply switches from plain text to formatted markdown without the block
   re-laying-out on every token.
5. No new dependency in `web/package.json`.
6. `web/package.json` scripts pass: typecheck/build and the test suite.

## Checks / verification commands

Run from `web/`:

- `npm run build` — `tsc -b && vite build` (typecheck + production build)
- `npm test` — `vitest run` (full suite)

Baseline before this change: build clean, 77 files / 561 tests passing.

## Graph nodes consulted

Graph: `graphify-out/graph.json` (refreshed 2026-09-16 17:00; `graphify-out/GRAPH_REPORT.md`).
Query: "AgentChat panel assistant: operational context sidebar, capabilities endpoint,
streaming message render, markdown rendering" → 985 nodes traversed.

Key nodes: `AgentChat()` `web/src/components/pages/AgentChat.tsx:304` (community `types.ts`),
`Markdown()` `web/src/components/shared/Markdown.tsx:31`, `types.ts` (god community for
the web surface), `PanelShell.tsx`, `panelRoutes.ts`, `tukulpan.py`,
`test_memory_observations.py`. `graphify path "AgentChat" "Markdown"` returned no directed
path (ambiguous source match) — recorded as a negative result, not evidence of no coupling.

## Design decisions (parent-owned)

- **Dropping the sidebar `Conexión` line rather than repointing it.** There is no truthful
  "connection" value to show: the assistant has no persistent socket whose state would be
  meaningful here. Repointing it at `capabilities` and keeping the label "Conexión" would
  keep the lie and change the payload. The label goes; the facts arrive.
- **The debounce is in scope** because it pays for itself twice (correctness and parse cost);
  see T2.
- **Footer indicator left alone on purpose** — see Out of scope. It is reported, not fixed.

## Recovery

Interrupted? Read this file plus the Engram mirror `odd/panel-assistant-context-and-stream/tasks`,
reconcile against the actual worktree, and resume the first unfinished task.
