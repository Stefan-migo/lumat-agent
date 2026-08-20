# Proposal: Storybook Redesign — Full design-system adoption across all Storybook surfaces

## Intent

Eliminate every trace of the old basic design from all Storybook surfaces and redesign them on the Lumat panel design system engram/design-system authority (`web/DESIGN_SYSTEM.md` + `web/src/tokens/tokens.css`). Today only PanelShell/AppShell, Dashboard, and PanelEntry carry the NEW "calm service control room" look; the 9 page stories, 5 `_shared/` helpers, 9 primitives + `primitives.css`, and story texts still ship English/voseo copy, raw status labels, `--primary-600` links, incomplete state matrices, and hardcoded focus/motion.

## Scope

### In Scope
- All 9 OLD page stories → design-system look, neutral Chilean Spanish, complete domain-state matrix.
- `_shared/` helpers + primitives.css focus/motion token correctness + StatusBadge/SearchInput Spanish label maps.
- Primitives/domain/tokens stories copy + tests encoding English/raw-state.

### Out of Scope
- **AppShell real-page wiring** (production still renders placeholders) — explicit deferral to a separate later change.
- **Helper promotion to `web/src/components/`** — needs multiple production consumers; separate change.
- Dark mode, new dependencies, backend/API changes, Jinja template migration.

## Capabilities

> Contract for sdd-spec. Research done against `openspec/specs/panel-design-system/spec.md`.

### New Capabilities
- None (no new spec files; redesign consumes the design system).

### Modified Capabilities
- `panel-design-system`: extend the existing spec requirements with Storybook page-surface adoption: approved Chilean Spanish labels via `StatusBadge`/toneMaps root maps; page shell/titlebar + `StateMessage` banner language; complete per-page domain-state matrix (loading/empty/stale/error/permission per §Domain-state hierarchy); primitives.css focus-ring (`--focus-ring*`) + motion (`--duration-*`/`--ease-*`) correctness; Login lockup + Spanish; KB processing/disable-confirmation and Settings save/stale states.

## Approach & Key Decisions

- **Approach C (hybrid)**: promote shared layer once, then restyle each page to consume it in per-page slices. Dashboard is the proving ground — keep its proven look; adopt shared PageFrame/StateMessage carefully or keep local styles until the frame proves out (explicit choice, low-risk).
- **Spanish label maps at root**: `StatusBadge` + `toneMaps` map raw `state`/`status`/`direction`/`provider/model` → approved labels (§Status badge): `Agente atendiendo`/`Atención humana`/`Cerrada`; `Nuevo`/`Activo`/`Inactivo`/`Bloqueado`; `Abierto`/`En evaluación`/`Escalado`/`Cerrado`; `Activo`/`Deshabilitado`/`Procesando`/`Error`. One fix covers all consumers.
- Links → `--primary-700`; focus rings → `--focus-ring*`; motion → `--duration-*`/`--ease-*`; `--info` spinner.
- Login: full Lumat lockup + `Usuario`/`Contraseña`/`Iniciar sesión`, inline error preserving username.
- Fix `ClientFicha` misuse `customerStateTone`→`caseStatusTone`.
- Ponytail/Scope: no new deps, no premature abstractions, no states beyond the design-system contract.

### Slice plan (chained PRs, ≤400 changed lines each, `npm test`+`tsc`+`build-storybook` green)

| # | Slice | Scope |
|---|-------|-------|
| S1 | Foundation/tokens | `primitives.css` focus/motion/spinner token swaps |
| S2 | Shared frame + label maps | Spanish maps, promote `StateMessage`, extend DataTable/StatCard/toneMaps; helper/test updates |
| S3 | List pages | ClientesList + CasesList onto shared frame (links, Spanish empty, banners) |
| S4 | Conversations/Inbox/Thread | ConversationsList, InboxThread (fix voseo/"Bot pausado"), ConversationThread |
| S5 | Ficha/Chat/Login | ClientFicha (tone-map fix, saving/validation), ChatWithAgent (translate agentStatus/aria), Login lockup |
| S6 | KB + Settings | full Spanish, `category=mode`/provider separation, KB processing/disable-confirm, Settings save/stale, tabular spend |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `web/src/stories/pages/*.stories.tsx` | Modified | 9 old pages restyle to control-room frame |
| `web/src/stories/pages/_shared/*` | Modified | PageHeader/DataTable/StatCard/StateMessage/toneMaps consolidation |
| `web/src/components/primitives/primitives.css` | Modified | focus-ring + motion token correctness (real production impact) |
| `web/src/components/primitives/StatusBadge.tsx`, `SearchInput.tsx` | Modified | Spanish label map + aria-label |
| `web/src/stories/primitives/*.stories.tsx` | Modified | Copy + matrix state fixes |
| `web/**/*.test.tsx` (~15) | Modified | English/raw-state assertions → Spanish |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Test churn (10+ tests assert EN/raw) | High | Budget test edits per slice; never leave a slice red |
| Copy consistency | Med | Approved glossary (§Content/§Status badge/Preferred terms) + shared maps; no voseo |
| primitives.css production impact | Low | Token-equivalent swaps; no test asserts values; verify suite |
| Dashboard regression sentinel | Med | Keep Dashboard tests green; frame proven on Dashboard before broad adoption |
| No-browser visual verification | Med | Reuse proven Dashboard pattern + review-driven verification |

## Rollback Plan

Per-slice revert via chained-PR branch. Foundation slices (S1 focus/motion, S2 maps) are token-equivalent and safe; any page regression reverts that page's single PR without touching helpers. `primitives.css` changes are isolated to one file and revert independently.

## Dependencies

- Green baseline (`tsc`, `npm test` 209 pass, `build-storybook`) confirmed in exploration.
- No new dependencies.

## Success Criteria

- [ ] No `--primary-600`, raw English/voseo status labels, or hardcoded focus/motion values in any Storybook surface.
- [ ] All 9 old pages + helpers + primitives show the control-room frame; state matrices complete per design-system hierarchy.
- [ ] `npm test` (all updated), `tsc`, and `build-storybook` green after each slice.
- [ ] Dashboard keeps proven look (regression sentinel green).
