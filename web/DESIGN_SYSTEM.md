# Lumat Panel Design System

Status: definitive product direction; implementation evolves through scoped SDD changes.

This document defines how Lumat should look, read, and behave across the current FastAPI/Jinja panel and the React/Storybook panel. It is grounded in the real product, the supplied Lumat logo, the shipped token system, and the admin/operator workflows already represented in code.

## Quick implementation path

1. Start from the relevant OpenSpec behavior and the current page/story contract.
2. Reuse `tokens.css` and existing primitives; add only approved semantic or brand tokens with a real consumer.
3. Design the complete operational state model, including permissions and recovery.
4. Implement user-facing copy in neutral Chilean Spanish.
5. Verify the rendered result in Storybook at representative widths, with keyboard input, zoom/reflow, and relevant failure states.

## Direction at a glance

| Topic | Decision |
|---|---|
| Design mode | Calm service control room; operational workspace plus dense dashboard patterns |
| Primary authority | Deep forest `--primary-800`; not logo lime |
| Brand expression | Cyan for information, lime for recognition/selection, graphite for grounding |
| Typography | Existing system-ui stack; no font dependency |
| Shape | Compact 6/8px radii and 4px spacing scale |
| Theme | Light theme required; dark mode is a separate future change |
| Language | Neutral Chilean Spanish in the UI; English in code and technical artifacts |
| Verification | WCAG 2.2 AA, complete states, Storybook, responsive and keyboard checks |

## Authority and ownership

Use this order when sources disagree:

1. OpenSpec requirements define product behavior and acceptance scenarios.
2. `web/src/tokens/tokens.css` is the executable source of token values.
3. This document defines visual direction, semantic roles, component behavior, and migration rules.
4. Storybook demonstrates approved components, pages, variants, and states.
5. The Jinja panel remains a production reference until each route is migrated.

Do not duplicate token values in component or story code. Proposed tokens in this document become executable only when added to `tokens.css` through an approved SDD change.

## Product context

Lumat is an AI-assisted service operation for a Chilean plumbing and heating company. The panel is not a generic AI dashboard and not a marketing surface. It helps a small operational team:

- monitor WhatsApp demand;
- identify emergencies and conversations requiring human attention;
- inspect customer history and service cases;
- take over and respond within Meta's 24-hour window;
- maintain the agent knowledge base;
- control scope, emergency rules, tone, and spend limits.

### Users

| Role | Primary jobs | Access character |
|---|---|---|
| `operador` | Monitor customers, conversations, and cases; acknowledge or update operational work | Task-focused, bounded |
| `admin` | All operator work plus knowledge-base and global-settings management | Broader, higher risk |

Role restrictions must be visible through available navigation and actions. Do not render a disabled admin control to operators when the action is categorically unavailable; omit it and preserve a predictable layout.

## Design direction

### Visual thesis

Lumat is a calm service control room: deep forest structure conveys operational authority, cyan carries information and traceability, lime marks recognition and selection, and graphite keeps dense business data grounded.

### Interaction thesis

Every core flow follows the same sequence:

1. Scan the current state.
2. Identify the exception or next action.
3. Drill into the relevant customer, conversation, case, document, or setting.
4. Act with explicit labels and visible constraints.
5. Confirm success or provide a recoverable failure path.

Motion and decoration never compete with this sequence.

### Platform-first interaction policy

Use native mechanics by default:

- Native Popover API for popovers and tooltips; CSS anchor positioning enhances placement when supported.
- Native `<dialog>` for modal behavior.
- Native input + listbox semantics for comboboxes.

The only approved Radix dependency is `@radix-ui/react-dropdown-menu`, used for menu semantics and keyboard behavior. Radix has no combobox primitive, so no combobox package is justified. This exception follows implementation rule 4 below: “Add no dependency unless the approved requirement cannot be met with the existing stack or platform.” The menu’s composite keyboard semantics are the approved requirement that warrants it; all other listed interactions use the platform.

The browser target is Safari 26+, Chrome 125+, and Firefox 147+ on current operating systems, including iPhone 12+ hardware running current iOS. An iPhone 12 on iOS 18 is below target and does not provide anchor positioning. The Popover API alone remains usable on Safari 17+.

Anchor positioning is progressive enhancement, guarded by `@supports (anchor-name: --popover-trigger)`. Without support, popover and tooltip content stays explicitly positioned with `position: absolute` inside the trigger’s containing block (`.popover` or `.tooltip`). This fallback retains native Popover API dismissal and focus behavior; it is not a silent polyfill.

### Product principles

1. **Operational clarity over spectacle.** Dense tables, status, and actions must remain easy to scan.
2. **Exceptions before decoration.** Emergencies, human handoffs, closed reply windows, and cost limits receive the strongest hierarchy.
3. **Brand through roles, not saturation.** Forest, cyan, lime, and graphite have defined jobs; they do not flood every surface.
4. **One vocabulary.** The interface is Spanish for the Chilean operation; implementation identifiers remain English.
5. **Complete states are part of the design.** Loading, empty, stale, disabled, error, success, and permission states are first-class.
6. **Existing system first.** Reuse shipped tokens and primitives before creating anything new.

## Brand translation

The supplied logo contains five stable visual primitives. Values were extracted from the raster and should be confirmed against a future vector master before brand production work.

| Primitive | Raster reference | Intended role |
|---|---:|---|
| Lime | `#ABC333` | Recognition, selected rails, controlled highlights, one chart series |
| Cyan | `#3D93AF` | Information, secondary data series, diagrams, non-text graphical accents |
| Aqua | `#8BCCD5` | Soft informational surfaces and supporting geometry |
| Forest | `#576F31` | Secondary brand expression and editorial brand moments |
| Graphite | `#656665` | Wordmark neutral and supporting brand material |

The vertical, faceted logo mark suggests infrastructure, water, heating equipment, built environments, and reliable upward movement. Translate that geometry through aligned columns, compact leading-edge rails, clear dividers, and restrained radii. Do not turn it into generic “AI growth” decoration.

### Logo use

- Use the full lockup on login and other explicit brand-entry surfaces.
- Use a compact mark or small lockup in the application shell.
- Keep clear space of at least one mark-facet width around the lockup.
- Never recolor individual facets with semantic status colors.
- Do not use the low-resolution JPG as the final production asset. Obtain or create an SVG or transparent high-resolution master before shipping the logo in the React panel.
- Avoid robots, glowing brains, circuit-board backgrounds, and stock “AI” imagery.

## Color system

### Shipped operational foundation

The current primary scale, neutrals, and semantic pairs in `tokens.css` remain the baseline. In particular:

| Role | Token | Current value | Rule |
|---|---|---:|---|
| Primary action / deep navigation | `--primary-800` | `#143C2C` | White text; measured 12.26:1 |
| Primary hover / accessible link | `--primary-700` | `#256F51` | Use for normal-size links on light surfaces; measured 6.05:1 |
| Canvas | `--bg` | `#F1F1E8` | Default page background |
| Surface | `--surface` | `#FFFFFF` | Cards, tables, controls, dialogs |
| Text | `--text` | `#1A202C` | Default readable text |
| Muted text | `--text-muted` | `#4A5568` | Metadata and supporting text, never disabled semantics alone |
| Success | `--success` | `#1B5E20` | Confirmed success or healthy completion |
| Warning | `--warning` | `#A16207` | Attention, handoff, approaching limits |
| Danger | `--danger` | `#B71C1C` | Emergency, destructive action, fatal failure |

Do not use `--primary-600` for normal-size links on white. Its current 3.38:1 contrast fails WCAG AA. Use `--primary-700` until an explicit semantic link token is introduced.

### Brand token additions

Add these primitives to `tokens.css` only when the first approved consumer lands:

```css
--brand-lime: #abc333;
--brand-cyan: #3d93af;
--brand-aqua: #8bccd5;
--brand-forest: #576f31;
--brand-graphite: #656665;
--info: #14788f;
```

Their semantic use is constrained:

- `--brand-lime` is not body text, a focus indicator, or a white-text button background. It measures 1.98:1 on white.
- Lime may use `--text` or `--primary-800` on top; those combinations measure 7.93:1 and 6.18:1 respectively.
- `--brand-cyan` is suitable for large text and non-text UI graphics on white, but not normal-size body text.
- `--info` is the accessible cyan-derived text role on white, measured at 5.11:1.
- `--brand-aqua` is a background or graphical color. `--text` on aqua measures 8.76:1.
- Brand colors never replace danger, warning, or success semantics.

### Color hierarchy

Use color in this order:

1. Neutral structure and readable text.
2. Deep forest for the primary action and persistent navigation authority.
3. Semantic colors for state and risk.
4. Cyan for information, links only when accessible, and data differentiation.
5. Lime for recognition, selection, or one high-value accent.

Never communicate status, selection, or urgency through color alone. Pair color with a label and, for critical states, an icon or explicit instruction.

### Themes

Light theme is the only required production theme. Dark mode is future scope and must not be implemented by partially inverting current colors. It requires a separate SDD change covering every primitive, page state, chart, focus treatment, and visual-regression surface.

## Typography

Use the shipped `--font-sans: system-ui, sans-serif` stack for all UI. Do not add Manrope, Inter, or another web-font dependency without a measured brand or readability requirement.

| Role | Token | Weight | Use |
|---|---|---:|---|
| Page title | `--text-xl` or `--text-2xl` | `--weight-bold` | One per page |
| Section title | `--text-lg` | `--weight-semibold` | Card and region headings |
| Body / table | `--text-md` | `--weight-regular` | Default operational content |
| Control label | `--text-sm` | `--weight-semibold` | Inputs, filters, local actions |
| Metadata | `--text-xs` or `--text-sm` | regular/medium | Dates, counts, freshness, IDs |
| KPI value | `--text-2xl` | `--weight-bold` | Verified metrics only |

Rules:

- Use sentence case in Spanish.
- Use tabular numerals for money, percentages, timestamps, IDs, and comparable metrics.
- Keep long operational text left-aligned.
- Do not use all caps except very short machine/status labels where spacing and readability have been tested.
- Preserve 200% text zoom without clipping or lost actions.

## Spacing, shape, and elevation

The shipped 4px spacing scale is canonical. Prefer `--space-2`, `--space-3`, and `--space-4` for control, row, and region rhythm.

- Controls and compact indicators use `--radius-sm` (6px).
- Cards, avatars, dialogs, and larger containers use `--radius-md` (8px).
- Do not introduce pill-shaped containers except badges, tags, or explicitly rounded tokens.
- Borders are the default separation mechanism.
- `--shadow-1` is for subtle raised cards only when hierarchy needs it.
- `--shadow-2` and `--shadow-3` are reserved for menus, dialogs, drawers, and overlays.
- Avoid nested card-on-card layouts. Use headings, dividers, spacing, or table regions first.

## Application shell and information architecture

### Navigation

Use the shipped order and vocabulary:

1. Panel
2. Clientes
3. Conversaciones
4. Casos
5. Base de conocimientos — admin only
6. Configuración — admin only

Customer ficha, conversation thread, and human inbox thread are drill-down views, not top-level destinations.

### Shell contract

- Preserve the current compact 192px desktop sidebar until content testing demonstrates a need to widen it.
- Place the Lumat mark/lockup, primary navigation, and signed-in user context in the sidebar.
- Use a leading lime rail plus a soft forest tint for the active item. Keep the label dark and readable.
- Set `aria-current="page"` on the active item.
- The main region owns page title, context/freshness, and local actions.
- Do not add a redundant top bar until a real cross-page job requires it.
- Avoid permanent chrome that reduces the working area without adding navigation or context.

### Responsive behavior

Use the existing reference breakpoints:

| Width | Target behavior |
|---|---|
| `< 640px` | Single-column content; navigation drawer; 16px page padding; tables use controlled horizontal scroll or a purpose-built compact row |
| `640–1023px` | Collapsible navigation; one or two content columns based on content; actions wrap without reordering the primary task |
| `1024–1279px` | Persistent compact sidebar; standard operational layout |
| `>= 1280px` | Persistent sidebar; expanded tables and multi-region detail, bounded by readable line lengths |

Breakpoints respond to content, not device names. Never hide emergency, handoff, send, acknowledge, save, or retry actions to produce a cleaner screenshot.

## Page architecture

### Panel

The dashboard answers four current questions:

- How many contacts entered the operation?
- How many required human derivation?
- How many requested a visit?
- What service motives are driving demand?

Required content:

- `Contactos`, `Derivados`, and `Solicitudes de visita` KPI cards;
- explicit time window and start date;
- `Motivos` table or equivalent ranked breakdown;
- clear empty, loading, stale, partial-error, and fatal-error states.

Do not add autonomous-resolution, response-time, satisfaction, or revenue metrics until the backend defines and verifies their formulas.

### Clientes

- Search, result count, export, and customer table are the primary list tools.
- Customer name is the drill-down link; phone, state, consent, and creation date are supporting columns.
- The ficha groups identity, consent, state control, notes, and history.
- Destructive or blocking customer-state changes require clear consequences and recovery guidance.

### Conversaciones and human inbox

- List rows show customer, explicit conversation state, assignee, summary, freshness, and created date.
- A human-assigned row may receive a warning-tinted leading treatment, never a color-only highlight.
- The automatic H1 thread stays clearly read-only.
- The human inbox thread shows message direction, active owner, conversation state, and the 24-hour reply-window status near the composer.
- Composer availability is explicit: enabled only for a human-owned conversation inside the reply window.
- Disabled composers explain the exact reason. Do not use “Bot pausado” when the state means the bot is active; copy must reflect the actual state transition.
- State actions use direct labels: `Tomar conversación`, `Cerrar conversación`, `Devolver al agente`, and `Enviar respuesta`.

### Casos

- Emergencies and unacknowledged items sort or surface before routine cases.
- Every emergency shows text plus an icon and acknowledgment state.
- Inline updates preserve the row context and prevent duplicate submission.
- `Reconocer emergencia` is distinct from resolving or closing the case.
- Responsible person, service, priority, status, summary, and customer remain scannable.

### Base de conocimientos

- This is an admin workspace, not a file gallery.
- Show document title, format, active version, status, provider/model when relevant, cost metadata, and available actions.
- Version creation and restoration are explicit; never overwrite history silently.
- Disabling a document requires confirmation and states how it affects agent answers.
- Upload validation covers supported format, size, processing, failure, and retry.

### Configuración

- Group settings by business consequence: agent scope, emergency detection, tone, spend limits, Meta pricing, and current spend.
- Explain effects in plain Spanish before the input, especially escalation and cost-stop behavior.
- Use one save action per independently persisted group.
- Show saved, saving, validation, server-error, and stale-value states.
- Keep advanced machine syntax (`category=mode`, keyword lists) visually separated from ordinary controls and validate it before saving.

### Login

- Use the full Lumat lockup and a single compact authentication card.
- Copy is Spanish: `Usuario`, `Contraseña`, `Iniciar sesión`.
- Authentication errors are inline, non-destructive, and do not clear the username.
- Do not reveal whether a username exists.

## Component contracts

### Button

- `primary`: one per local action group; create, save, send, acknowledge, or execute the main task.
- `secondary`: neutral bordered action.
- `tertiary`: low-emphasis navigation or disclosure, introduced only when a real consumer exists.
- `danger`: destructive or irreversible action, introduced with confirmation behavior.
- Minimum control height is 40px; prefer a 44×44px target for frequent, risky, or touch-primary actions.
- Loading retains width, exposes busy state, and blocks duplicate submission.
- Disabled controls include a semantic disabled state and, when needed, a nearby explanation.

### Fields

- Labels stay visible; placeholders are examples, not labels.
- Help, constraints, and errors are connected with `aria-describedby`.
- Preserve entered data after recoverable validation and server failures.
- Error text explains what happened and how to fix it.
- Units appear in labels or adjacent text, never only in placeholders.

### Status badge

Use a dot or icon only as reinforcement. The visible label is mandatory.

| Domain | Approved user-facing labels | Guidance |
|---|---|---|
| Conversation | `Agente atendiendo`, `Atención humana`, `Cerrada` | Do not expose raw `bot`/`human`/`closed` values |
| Customer | `Nuevo`, `Activo`, `Inactivo`, `Bloqueado` | Blocked is danger only when it requires intervention |
| Case | `Abierto`, `En evaluación`, `Escalado`, `Cerrado` | Escalated is attention/danger; closed is not automatically success |
| KB document | `Activo`, `Deshabilitado`, `Procesando`, `Error` | Pair processing/error with next action |
| Reply window | `Respuesta disponible`, `Fuera de ventana` | Keep adjacent to composer |

### Data table

- Use semantic table markup and a caption or page context.
- Keep headings visible when long tables scroll.
- Align comparable numbers right and use tabular numerals.
- Keep row actions in the final region without forcing every row to become a form.
- Cover loading, empty, filtered-empty, partial-error, stale, and permission states.
- On narrow widths, preserve scanning value; do not automatically convert every table into unrelated cards.

### Cards and KPI cards

- Use cards for meaningful containment, not as the default layout primitive.
- KPI order is label, value, then verified context or change.
- State whether a direction is positive or negative in the data model; never infer meaning from arrow direction alone.
- Prefer flat regions and dividers for long settings or history surfaces.

### Feedback

- Inline feedback belongs beside fixable form and field problems.
- Page/region alerts communicate handoff, emergencies, limits, stale data, or failed dependencies.
- Toasts are reserved for completed background/global actions and never replace persistent critical errors.
- Announce meaningful asynchronous changes without moving focus.

### Dialog and disclosure

- Prefer native disclosure (`details`) for optional inline editing when interruption is unnecessary.
- Use dialogs for destructive confirmation or tasks that must block background interaction.
- Dialogs set meaningful initial focus, trap it while open, support Escape where safe, and restore focus on close.
- Confirmation names the affected customer, conversation, case, or document.

## Domain-state hierarchy

The same visual tone must mean the same degree of attention across pages.

| Level | Meaning | Examples | Treatment |
|---|---|---|---|
| Neutral | Routine information | Agent-owned conversation, inactive metadata | Neutral text/badge |
| Informational | Context or freshness | Processing, source/model details, time window open | Cyan-derived info plus text |
| Positive | Confirmed successful outcome | Settings saved, document restored | Success pair plus explicit result |
| Warning | Human attention soon/now | Human handoff, approaching spend limit, reply-window risk | Warning pair, clear next action |
| Danger | Immediate risk or failed critical task | Unacknowledged emergency, fatal send failure, exhausted spend limit | Danger pair, icon, action, and announcement |

Do not use positive green merely because an entity is closed. A closed case may be routine, successful, cancelled, or unresolved; the business outcome decides the tone.

## Content and localization

The UI language is neutral Chilean Spanish. Avoid English labels and Argentine voseo in the product surface.

Preferred terms:

- `Panel`
- `Clientes`
- `Conversaciones`
- `Casos`
- `Base de conocimientos`
- `Configuración`
- `Agente`
- `Atención humana`
- `Derivación`
- `Responsable`
- `Respuesta disponible`
- `Fuera de la ventana de 24 horas`

Use direct action labels: `Guardar`, `Agregar nota`, `Exportar CSV`, `Tomar conversación`, `Reconocer emergencia`, `Reintentar`, `Restaurar versión`.

Avoid raw implementation labels such as `bot`, `human`, `closed`, `inbound`, `outbound`, `provider/model`, and `category=mode` unless the screen is explicitly an advanced technical view. Translate or explain them.

Dates, times, currencies, decimals, and percentages follow the active Chilean locale and timezone context. Relative time supplements, but never replaces, an exact timestamp where auditability matters.

## Iconography, imagery, and motion

- Use one outline icon family only after an existing dependency or approved asset source is available; do not add a package just for decorative icons.
- Critical icons always have visible text.
- Default icon sizes are 16px, 20px, and 24px with consistent optical weight.
- Use logo facets as a subtle source for rails, dividers, and selected-state geometry, not as repeated background wallpaper.
- Standard transitions use the existing 100/150/250ms tokens.
- Animate opacity and transform where appropriate; avoid layout shift.
- Honor `prefers-reduced-motion` with a designed alternative.
- No looping decorative animation in the operational panel.

## Accessibility baseline

WCAG 2.2 Level AA is the minimum.

- Normal text: at least 4.5:1 contrast.
- Large text and meaningful graphical/UI boundaries: at least 3:1.
- All workflows operate by keyboard with visible focus and no traps.
- Focus order matches reading and visual order.
- Sticky elements do not cover focused controls.
- Controls have accurate accessible names and connected descriptions/errors.
- Color is never the only state channel.
- Pointer targets meet at least 24×24px or a valid exception; prefer 44×44px for frequent and risky actions.
- Text resizes to 200%; narrow reflow preserves content and actions.
- Status, progress, errors, and completion are announced appropriately.
- Reduced motion, high contrast/forced colors, long content, and localization expansion are included in verification.
- Important tables remain semantically navigable and expose their context.

Automated accessibility checks do not prove conformance. Important flows also require keyboard, zoom/reflow, and screen-reader verification.

## Storybook contract

Storybook is the visual and state review surface for the React panel.

Every primitive or page pattern must provide:

- purpose and when-to-use guidance;
- accessible names and interaction notes;
- controls where they clarify a real contract;
- relevant visual variants;
- representative loading, empty, error, disabled, stale, permission, and success states;
- narrow, medium, and desktop viewport checks aligned with 640/1024/1280px references;
- honest mock data shaped like production serializers;
- tests for behavior and state semantics, not snapshot volume.

Page-first stories may use local helpers while the product architecture is still being proven. Promote a helper into `web/src/components/` only after multiple production consumers need the same stable contract.

## Migration contract: Jinja to React

The design system spans both surfaces during migration.

1. Preserve production behavior and route authority in Jinja until the replacement is wired and verified.
2. Use Storybook to establish the target visual, content, and state contract.
3. Migrate tokens and language consistently; do not maintain two palettes or two vocabularies.
4. Verify serializer fidelity before wiring a page.
5. Replace one bounded workflow at a time with a recoverable rollback path.
6. Do not declare parity from a screenshot; verify permissions, keyboard behavior, error recovery, and responsive states.

Known convergence work:

- move Jinja raw colors toward the shared token roles;
- translate remaining English UI labels to approved Spanish;
- replace inaccessible `--primary-600` text links with the `--primary-700` role;
- align focus styles with the existing `--focus-ring*` tokens;
- obtain a production-ready logo asset;
- wire React pages only when their backend contracts exist.

## Implementation rules for coding agents

1. Run the project Graph Check before inspecting or changing frontend modules.
2. Read this guide, the relevant OpenSpec requirements, `tokens.css`, and the existing Storybook story before designing.
3. Reuse existing primitives and semantic tokens.
4. Add no dependency unless the approved requirement cannot be met with the existing stack or platform.
5. Add a token only for a repeated semantic role or an approved brand primitive with a real consumer.
6. Keep raw hex values inside `tokens.css` only.
7. Keep code and identifiers in English; keep user-facing copy in approved Spanish.
8. Preserve data contracts and role permissions.
9. Implement the complete relevant state model.
10. Verify the rendered surface at representative widths and with keyboard input before approval.

## Acceptance checklist

### Direction and brand

- [ ] The surface reads as a service-operation workspace, not a generic AI dashboard.
- [ ] Forest, cyan, lime, and graphite follow their defined roles.
- [ ] Lime is not used as small text, focus-only indication, or a white-text button background.
- [ ] Logo usage is restrained and based on a production-quality asset.

### Product fit

- [ ] Navigation matches the shipped information architecture and role access.
- [ ] Dashboard metrics come from verified product data.
- [ ] Emergency, handoff, reply-window, spend-limit, and permission states are explicit.
- [ ] Raw backend state names are translated for users.

### Components and states

- [ ] Components consume semantic tokens and reuse existing primitives.
- [ ] Relevant loading, empty, filtered-empty, stale, disabled, error, success, and permission states exist.
- [ ] Destructive actions name the affected object and provide confirmation or recovery.
- [ ] Tables remain usable and meaningful at narrow widths.

### Accessibility and verification

- [ ] Normal text meets 4.5:1 contrast and meaningful non-text UI meets 3:1.
- [ ] Links on light surfaces use an accessible foreground such as `--primary-700`.
- [ ] Keyboard operation, visible focus, focus recovery, zoom/reflow, and reduced motion are verified.
- [ ] Color is never the only state channel.
- [ ] Storybook and tests cover the relevant state matrix.
- [ ] Verification evidence distinguishes measured, automated, manual, and unverified checks.

## Non-goals

- Figma or a Figma-to-code workflow.
- A new component library or CSS framework.
- A font dependency or visual rebrand.
- Dark mode in the current slice.
- Decorative 3D, glassmorphism, gradients, parallax, or animation systems.
- New backend behavior, permissions, analytics formulas, or API contracts inferred from visual design.
- Premature abstraction of story-local helpers without proven production reuse.
