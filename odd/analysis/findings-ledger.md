# Panel section analysis — findings ledger

One ledger for every section. Read-only analysis feeds it; implementation consumes it.
Contract: `.opencode/skills/panel-section-analysis/SKILL.md`.

## Legend

- **Class** — `local` (only this section's files) · `shared-primitive` (a primitive or shell file
  other sections render through → one upstream unit) · `token-palette` (`tokens.css` → escalate to
  the owner, do not reopen).
- **Severity** — `blocker` · `major` · `minor` · `nit`.
- **Evidence** — every row carries reference evidence, a code anchor, and the owner note (or the
  literal `owner did not flag`).

## Findings

`dashboard` analyzed against `main` = `1c6e9595`, refs `refs/Diseño Lumat/Dashboard.png`,
`mobileTablet/dashboardMobile.png`, `mobileTablet/dashboardTablet.png`. Validated rows only.

| ID | Section | Class | Severity | Finding | Reference evidence | Code anchor | Owner note | Fix scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dashboard-001 | dashboard | local | major | The page heading renders "Panel"; the owner rules both the reference ("Panel unificado") and the current title out and requires "Dashboard". | `refs/Diseño Lumat/Dashboard.png` — page header | `web/src/components/pages/Dashboard.tsx:148` | titulo ni referencia ni original estan correctos. el titulo debe ser simplemente Dashboard. | `web/src/components/pages/Dashboard.tsx` |
| dashboard-002 | dashboard | local | minor | The "Hoy" date chip renders a lowercase weekday (`Intl.DateTimeFormat("es-CL", { weekday: "long" })`); the references show a capitalized weekday. | `refs/Diseño Lumat/Dashboard.png` — date chip | `web/src/components/pages/Dashboard.tsx:70` | seccion HOY referencia tiene la razon | `web/src/components/pages/Dashboard.tsx` |
| dashboard-003 | dashboard | local | minor | The agenda ops card is titled "Agenda"; the references show "Agenda de hoy". | `refs/Diseño Lumat/Dashboard.png` — first "Hoy" ops card | `web/src/components/pages/Dashboard.tsx:157` | seccion HOY referencia tiene la razon | `web/src/components/pages/Dashboard.tsx` |
| dashboard-004 | dashboard | shared-primitive | major | The three "Hoy" ops cards lack the footer links the reference shows ("Ver agenda →", "Ver conversaciones →", "Ver casos →"); each card body renders only its list/empty state. | `refs/Diseño Lumat/Dashboard.png` — "Hoy" cards; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — "Hoy" cards | `web/src/components/pages/Dashboard.tsx:137` | seccion HOY referencia tiene la razon | `web/src/components/pages/Dashboard.tsx`; `.dashboard__card-ops` rules in `web/src/components/primitives/primitives.css` |
| dashboard-005 | dashboard | shared-primitive | major | The assistant surface is rendered as a tall 2×2 grid tile; the references show it as a horizontal banner across the shortcut area. | `refs/Diseño Lumat/Dashboard.png` — assistant banner; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — assistant card; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — assistant banner | `web/src/components/pages/Dashboard.tsx:185` | seccion atajos referencia tiene la razon (igual como dice la referencia atajos no tiene titulo.) | `web/src/components/pages/Dashboard.tsx`; `.dashboard__grid`, `.dashboard__card--agent`, `.dashboard__card--wide` in `web/src/components/primitives/primitives.css` |
| dashboard-006 | dashboard | local | minor | The agent surface is labelled "Agente Lumat"; the references label it "Asistente Lumat". | `refs/Diseño Lumat/Dashboard.png` — assistant banner; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — assistant card | `web/src/components/pages/Dashboard.tsx:185-188` | seccion atajos referencia tiene la razon (igual como dice la referencia atajos no tiene titulo.) | `web/src/components/pages/Dashboard.tsx` |
| dashboard-007 | dashboard | shared-primitive | minor | Desktop renders an "Atajos" heading above the shortcut row, which the desktop reference omits; the mobile and tablet references do show an "Accesos rápidos" heading, so the treatment differs by breakpoint. | `refs/Diseño Lumat/Dashboard.png` — shortcut row; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — "Accesos rápidos" heading; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — "Accesos rápidos" heading | `web/src/components/pages/Dashboard.tsx:183` | seccion atajos referencia tiene la razon (igual como dice la referencia atajos no tiene titulo.) | `web/src/components/pages/Dashboard.tsx`; `.dashboard__section-head` rules in `web/src/components/primitives/primitives.css` |
| dashboard-008 | dashboard | shared-primitive | major | The shortcut set must carry a settings entry in place of the reference's "Casos" on every breakpoint; the current set has no settings entry. Label per owner decision: "Configuración" on desktop/tablet, "Config" on mobile. Concerns the shortcut cards only — the "Hoy" urgent-case rows stay on `navigate("cases")` per AD-HOY-1. | `refs/Diseño Lumat/Dashboard.png` — shortcut row; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — "Accesos rápidos"; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — "Accesos rápidos" | `web/src/components/pages/Dashboard.tsx:129-131` | en todas las versiones mobile, tablet, desktop, el acceso directo a casos debe ser cambiado por configuracion. o config. | `web/src/components/pages/Dashboard.tsx`; shortcut layout rules in `web/src/components/primitives/primitives.css` |
| dashboard-009 | dashboard | local | major | The activity section heading reads "Período"; all references read "Actividad del período". | `refs/Diseño Lumat/Dashboard.png` — activity section heading; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — activity heading; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — activity heading | `web/src/components/pages/Dashboard.tsx:206` | actividad del periodo referencia tiene la razon. | `web/src/components/pages/Dashboard.tsx` |
| dashboard-010 | dashboard | shared-primitive | major | The activity section has no period-selector control nor the adjacent "Desde el …" caption the references show; the window is surfaced only in the page-header meta. **Owner decision (2026-10-01): the selector must be FUNCTIONAL** — changing it changes the window and refetches, not a static affordance. Today `getDashboardTrend(timezone)` takes no window. | `refs/Diseño Lumat/Dashboard.png` — period selector and caption; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — activity selector and caption; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — activity selector and caption | `web/src/components/pages/Dashboard.tsx:148` | actividad del periodo referencia tiene la razon. (+ deberia ser funcional.) | `web/src/components/pages/Dashboard.tsx`; `web/src/api.ts` (`getDashboardTrend`); activity-section rules in `web/src/components/primitives/primitives.css`; backend trend endpoint if the window is not already parameterised |
| dashboard-011 | dashboard | local | minor | The chart empty state omits the reference's supporting sentence and uses different primary copy ("Sin actividad registrada en el período" vs "Sin contactos en este período" + "La actividad aparecerá aquí cuando se registren contactos."). | `refs/Diseño Lumat/Dashboard.png` — "Contactos por día" empty state; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — chart empty state; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — chart empty state | `web/src/components/pages/Dashboard.tsx:228` | actividad del periodo referencia tiene la razon. | `web/src/components/pages/Dashboard.tsx` |
| dashboard-012 | dashboard | shared-primitive | minor | Motivos render as inline chips ("label · count"); the references show one row per reason with a trailing count badge. | `refs/Diseño Lumat/Dashboard.png` — Motivos card; `refs/Diseño Lumat/mobileTablet/dashboardMobile.png` — Motivos card; `refs/Diseño Lumat/mobileTablet/dashboardTablet.png` — Motivos card | `web/src/components/pages/Dashboard.tsx:232-235` | actividad del periodo referencia tiene la razon. | `web/src/components/pages/Dashboard.tsx`; `.dashboard__chips` and `.dashboard__chip` rules in `web/src/components/primitives/primitives.css` |

### Owner adjudications — no change required

- **dashboard-013 — tablet "Chats" is a design error in the reference. Owner decision (2026-10-01): "Chats" belongs only in the mobile bottom nav; the dashboard shortcut stays "Conversaciones" on every breakpoint.** Row withdrawn from Findings. No change.
- **Subtitle.** The reference shows "Resumen de atención y actividad."; the app renders the activity-window meta (`Dashboard.tsx:148`). The owner prefers "la version original" (the app); the string "Resumen de atención" never existed in `web/src` history (`git log -S'Resumen de atención'` → empty). Ruled in favour of the app; no change.
- **"Hoy" urgent-case rows** stay on `navigate("cases")` per AD-HOY-1 (`openspec/specs/advanced-dashboards/spec.md`); dashboard-008 concerns shortcut cards only.
- **"Sin respuesta" and "Urgentes"** card titles match the references; no change.
- **White background:** no dashboard element uses a white background; all card/surface rules use `var(--surface)` (`#e8ebe4`). Owner rule recorded as a forward constraint for implementation, not a finding.
- **Mobile 2-column shortcut grid** already exists in the responsive CSS; no change.

## Shared-primitive roll-up

Findings that belong to one upstream unit. Populated as sections are analyzed; **implemented
before** per-section work.

| ID | Section | Finding | Shared file |
| --- | --- | --- | --- |
| dashboard-004 | dashboard | "Hoy" ops cards lack the reference footer links | `web/src/components/primitives/primitives.css` |
| dashboard-005 | dashboard | Assistant is a 2×2 tile, not a full-width banner | `web/src/components/primitives/primitives.css` |
| dashboard-007 | dashboard | Desktop renders an "Atajos" heading the reference omits | `web/src/components/primitives/primitives.css` |
| dashboard-008 | dashboard | Shortcut set needs "Configuración" in place of "Casos" | `web/src/components/primitives/primitives.css` |
| dashboard-010 | dashboard | No period selector nor "Desde el …" caption | `web/src/components/primitives/primitives.css` |
| dashboard-012 | dashboard | Motivos render as chips, not rows with a count badge | `web/src/components/primitives/primitives.css` |

## Token/palette escalations

Findings that touch `tokens.css`. Owner decision required; not reopened per section.

| ID | Section | Finding | Owner decision |
| --- | --- | --- | --- |
| _(none yet)_ | | | |
