# Assistant Surface Contrast Verification

**Scope:** light-theme `AgentChat` only. Dark mode, D5, D6, token changes, and
accessibility dependencies are out of scope.

## Method and limitation

This is a manual token-pair calculation, not a rendered-pixel audit. It uses the
foreground/background pairs declared by `tokens.css` and consumed by the
assistant rules in `web/src/components/primitives/primitives.css`. It does not
prove contrast after browser anti-aliasing, font rendering, inherited styles,
platform placeholder styling, forced colors, or compositing over an unexpected
ancestor. Important flows still require keyboard, zoom/reflow, and
screen-reader verification, as required by `web/DESIGN_SYSTEM.md`.

WCAG 2.2 AA thresholds used here are **4.5:1 for normal text** and **3:1 for
large text and meaningful non-text UI**. Disabled controls are exempt from the
text-contrast requirement, but their calculated result is retained below.

The token `--brand-bg` is `#DDE2D6F5`, so its effective light-theme color is
calculated over `--bg` (`#F1F1E8`) as `#DEE3D7`. The `color-mix()` value of
`--brand-bg-elevated` is then calculated as 60% `#DEE3D7` plus 40% white:
`#EBEEE7`. This makes the translucent token pair reproducible rather than
pretending that its alpha channel is opaque.

## Calculation

For each sRGB channel `c` in the range 0–1:

```
c_linear = c / 12.92                         when c <= 0.04045
c_linear = ((c + 0.055) / 1.055) ^ 2.4       otherwise
L = 0.2126 R_linear + 0.7152 G_linear + 0.0722 B_linear
contrast = (max(Lforeground, Lbackground) + 0.05)
           / (min(Lforeground, Lbackground) + 0.05)
```

For example, `--text` (`#1A202C`) has `L=0.014345` and `--surface`
(`#FFFFFF`) has `L=1.000000`; `(1.000000 + .05) / (.014345 + .05) = 16.32:1`.

The following table shows the same reproducible luminance inputs for every
pair used by the assistant surface. Values are rounded to six decimal places
for luminance and two decimal places for the ratio.

| Rendered state / use | Foreground | Background | L foreground | L background | Ratio | Result |
|---|---|---|---:|---:|---:|---|
| Agent message text, card headings | `--text` `#1A202C` | `--surface` `#FFFFFF` | 0.014345 | 1.000000 | 16.32:1 | PASS |
| Administrator message text | `--surface` `#FFFFFF` | `--primary-800` `#143C2C` | 1.000000 | 0.035623 | 12.26:1 | PASS |
| Agent metadata and timestamps | `--text-muted` `#4A5568` | `--surface` `#FFFFFF` | 0.089523 | 1.000000 | 7.53:1 | PASS |
| Composer placeholder and status text | `--text-muted` `#4A5568` | effective `--brand-bg-elevated` `#EBEEE7` | 0.089523 | 0.845808 | 6.42:1 | PASS |
| Context drawer supporting text | `--text-muted` `#4A5568` | effective `--brand-bg-elevated` `#EBEEE7` | 0.089523 | 0.845808 | 6.42:1 | PASS |
| Neutral badge text | `--text-muted` `#4A5568` | `--table-head-bg` `#EEF1F4` | 0.089523 | 0.876194 | 6.64:1 | PASS |
| Success badge text | `--success` `#1B5E20` | `--success-bg` `#E8F5E9` | 0.083427 | 0.883438 | 7.00:1 | PASS |
| Warning badge text | `--warning` `#A16207` | `--warning-bg` `#FEF3C7` | 0.163278 | 0.892955 | 4.42:1 | **FAIL** |
| Danger badge and form-error text | `--danger` `#B71C1C` | `--danger-bg` `#FDECEA` | 0.109816 | 0.868141 | 5.74:1 | PASS |
| Disclosure summary | `--primary-700` `#256F51` | effective `--brand-bg-elevated` `#EBEEE7` | 0.123563 | 0.845808 | 5.16:1 | PASS |
| Context drawer main text | `--text` `#1A202C` | effective `--brand-bg-elevated` `#EBEEE7` | 0.014345 | 0.845808 | 13.92:1 | PASS |
| Focus ring on message/card surface | `--focus-ring` `#256F51` | `--surface` `#FFFFFF` | 0.123563 | 1.000000 | 6.05:1 | PASS |
| Focus ring on assistant canvas | `--focus-ring` `#256F51` | `--bg` `#F1F1E8` | 0.123563 | 0.874376 | 5.33:1 | PASS |
| Focus ring on composer/drawer | `--focus-ring` `#256F51` | effective `--brand-bg-elevated` `#EBEEE7` | 0.123563 | 0.845808 | 5.16:1 | PASS |
| Streaming cursor / processing indicator | `--info` `#14788F` | `--bg` `#F1F1E8` | 0.155648 | 0.874376 | 4.49:1 | PASS for meaningful non-text UI (>=3:1) |
| Processing message text | `--text` `#1A202C` | `--bg` `#F1F1E8` | 0.014345 | 0.874376 | 14.37:1 | PASS |
| Composer border / control boundary | `--border` `#D8DDE3` | `--surface` `#FFFFFF` | 0.718579 | 1.000000 | 1.37:1 | **FAIL** |
| Canvas separator / assistant boundary | `--border` `#D8DDE3` | `--bg` `#F1F1E8` | 0.718579 | 0.874376 | 1.20:1 | **FAIL** |
| Secondary-button boundary | `--border-strong` `#C3CBD4` | effective `--brand-bg-elevated` `#EBEEE7` | 0.590674 | 0.845808 | 1.40:1 | **FAIL** |

The disabled primary button is rendered with `opacity: 0.5`. Its underlying
white-on-forest pair is 12.26:1, while the resulting blended pixels are
approximately `#F5F6F3` over `#80958A`, or 2.95:1. This is **not a pass under
the normal-text threshold**, but disabled controls are exempt from WCAG 1.4.3;
the visible label and native disabled semantics remain required. Processing
status text is not disabled text and is covered by the explicit passing row.

## Failures and recommended remediation

1. **Warning badge:** `--warning` on `--warning-bg` is 4.42:1, below 4.5:1
   for normal-size badge text. The token or badge background pairing should
   change in a future approved design-system change. No token was changed here.
2. **Borders:** `--border` and `--border-strong` are below 3:1 against their
   assistant surfaces. If these lines are intended to communicate a meaningful
   control boundary, the border role or adjacent surface should change in a
   future approved design-system change. No production CSS or token was changed
   here.

## Agreement with the design-system measurements

The recomputation agrees with the documented values: `--primary-800` on white
is **12.26:1**, `--primary-700` on white is **6.05:1**, and `--info` on white is
**5.11:1**. The assistant does not use `--info` on white for its cursor; its
actual canvas pairing is `--info` on `--bg`, calculated above. The documented
`--primary-600` warning was not used by the assistant surface.
