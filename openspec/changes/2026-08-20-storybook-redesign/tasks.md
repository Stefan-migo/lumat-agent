# Tasks: Storybook Redesign — Full Design-System Adoption

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1700 total (per slice: S1 ~60, S2 ~350, S3 ~250, S4 ~280, S5 ~320, S6 ~340) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 → PR 6 |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| S1 | primitives.css focus/motion tokens | PR 1 | npx tsc --noEmit && cd web && npm test | N/A — token-equivalent swaps, no behavior change | revert primitives.css alone |
| S2 | maps + StateMessage/PageFrame/DataTable/StatCard + helper tests | PR 2 | cd web && npm test | N/A — validated by Storybook helper stories | revert _shared + primitives label edits |
| S3 | ClientesList + CasesList restyle | PR 3 | cd web && npm test | build-storybook render at 390-1280px | revert two page stories + their tests |
| S4 | Conversations/Inbox/Thread restyle | PR 4 | cd web && npm test | build-storybook render at 390-1280px | revert three page stories + tests |
| S5 | ClientFicha/ChatWithAgent/Login | PR 5 | cd web && npm test | build-storybook render at 390-1280px | revert three page stories + tests |
| S6 | KbList + Settings restyle | PR 6 | cd web && npm test | build-storybook render at 390-1280px | revert two page stories + tests |

## Phase 1: Foundation (`primitives.css` token swaps)

- [x] 1.1 RED/assert-nothing: confirm no test asserts focus/motion values (exploration §tests).
- [x] 1.2 `web/src/components/primitives/primitives.css`: `.btn` transition → `--duration-base`/`--ease-out`.
- [x] 1.3 Same file: `.btn:focus-visible`, `.field__control:focus`, `.search-input:focus-within` → `--focus-ring-width`/`--focus-ring`/`--focus-ring-offset`.
- [x] 1.4 Same file: `.spinner__indicator` top → `--info` + `--duration-slow`; add `prefers-reduced-motion` block. No new hex (tokens.test guard green).

## Phase 2: Shared frame + label maps (DS-UI-LABELS/FRAME/TABLES/PRIMS-drift)

- [x] 2.1 RED `toneMaps.test.ts` + `StatusBadge.test.tsx`: every `types.ts` state resolves to non-empty Spanish label.
- [x] 2.2 GREEN: `_shared/toneMaps.ts` add `conversationLabel/customerStateLabel/caseStatusLabel/kbStatusLabel/directionLabel` maps (approved §labels).
- [x] 2.3 GREEN: `primitives/StatusBadge.tsx` add `label` prop + default Spanish map; render label not raw state.
- [x] 2.4 GREEN: `SearchInput.tsx` default `aria-label="Buscar"`; update `SearchInput.test.tsx` L10.
- [x] 2.5 Promote `_shared/StateMessage.tsx` (tone/role/title/detail/spinner) + `_shared/PageFrame.tsx` (titlebar+banner slot+content); test for role pairing (DS-UI-FRAME). Dashboard consumes StateMessage, sentinel green.
- [x] 2.6 GREEN: `DataTable.tsx` ES defaults (`No hay registros`/`Acciones`), `loading`/`stale`, `tabularNum`; `StatCard.tsx` tabular core. Update `helpers.test`/`DataTable.test` EN assertions.
- [x] 2.7 Primitives stories copy: StatusBadge/SearchInput/Badge/Card EN → Spanish (DS-UI-COPY).

## Phase 3: List pages (DS-UI-LINK/STATES/STORY)

- [x] 3.1 ClientesList `--primary-600`→`--primary-700` links (DS-UI-LINK AA); Stattle Spanish badges; empty `No hay registros`; add stale/error banners (DS-UI-STATES).
- [x] 3.2 CasesList onto PageFrame; Spanish title "Cases…"; `caseStatusLabel`; loading banner; emergency note → StateMessage (DS-UI-FRAME/STATES).
- [x] 3.3 RED→GREEN: update `ClientesList.stories.test.tsx`/`CasesList.stories.test.tsx` to Spanish (DS-UI-COPY); viewports at 390/640/768/1024/1280 (DS-UI-STORY).

## Phase 4: Conversations/Inbox/Thread

- [x] 4.1 ConversationsList onto PageFrame; Spanish "Conversaciones"/empty `No hay registros`; directionLabel for direction (thread column); `Acciones` header (design default); approved state labels (filter select + badges); warning-tinted leading treatment for human rows (paired with `Atención humana` label, never color-only); loading/stale/partial-error/fatal-error banners (DS-UI-COPY/STATES).
- [x] 4.2 InboxThread: neutral voseo-free placeholder "Escribe tu respuesta al cliente..."; "Bot pausado" → "El agente está atendiendo esta conversación"; raw state → conversationLabel; stale banner; controls → direct labels (Tomar conversación / Cerrar conversación / Devolver al agente); composer availability explicit (DS-UI-COPY/STATES).
- [x] 4.3 ConversationThread: raw `conv.state` → conversationLabel; raw direction → directionLabel; ⚠️ note → StateMessage status region; add loading/empty states; preserve bubble row alignment (DS-UI-STATES/COPY).
- [x] 4.4 RED→GREEN: updated the three `*.stories.test.tsx` EN/raw assertions → Spanish approved labels; viewports 390/640/768/1024/1280 via build-storybook render (DS-UI-STORY).

## Phase 5: Ficha/Chat/Login (DS-UI-TONEFIX/LOGIN/STATES)

- [x] 5.1 RED `ClientFicha.stories.test.tsx`: case status uses `caseStatusTone` not `customerStateTone`.
- [x] 5.2 GREEN: ClientFicha case rows → `caseStatusTone` + labels; saving/validation/disabled states (DS-UI-TONEFIX/STATES).
- [x] 5.3 ChatWithAgent: translate `agentStatus`/voseo/EN aria → Spanish; role labels (DS-UI-COPY).
- [x] 5.4 Login: Lumat lockup + `Usuario`/`Contraseña`/`Iniciar sesión`; RED→GREEN inline error preserves username, no existence leak; loading (DS-UI-LOGIN/STATES).

## Phase 6: KB + Settings

- [x] 6.1 KbList full Spanish; `category=mode`/provider-model separated from ordinary controls; processing/error/disable-confirmation states (DS-UI-COPY/STATES/PRIMS-cat).
- [x] 6.2 Settings full Spanish; advanced `category=mode` separated/explained; `Spend` tabular-num via DataTable; saved/saving/validation/server-error/stale (DS-UI-STATES/TABLES).
- [x] 6.3 RED→GREEN: update `KbList`/`Settings` test EN assertions; viewports.

## Phase 7: Green gate + cleanup

- [ ] 7.1 Run `cd web && npm test`, `npx tsc --noEmit`, `npm run build-storybook` — all green.
- [ ] 7.2 Grep Storybook surfaces for `--primary-600`, raw EN/voseo status labels, hardcoded focus/motion; remove strays (DS-UI-COPY/PRIMS success criteria).
