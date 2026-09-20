# Panel Design System Contrast Verification

**Scope:** the inherited `--border-strong` boundary on effective `--brand-bg`.
No token value is changed by this record.

## Method and limitation

This is a manual token-pair calculation, not a rendered-pixel audit. It uses the
token values and the WCAG relative-luminance formula below. It does not prove
contrast after browser anti-aliasing, font rendering, inherited styles, forced
colors, or compositing over an unexpected ancestor. Rendered surfaces still
require browser verification.

The token `--brand-bg` is `#DDE2D6F5`, so its effective color is composited over
`--bg` (`#F1F1E8`) as `#DEE3D7`. The alpha channel is therefore handled
explicitly rather than treated as opaque.

## Calculation

For each sRGB channel `c` in the range 0–1:

```
c_linear = c / 12.92                         when c <= 0.04045
c_linear = ((c + 0.055) / 1.055) ^ 2.4       otherwise
L = 0.2126 R_linear + 0.7152 G_linear + 0.0722 B_linear
contrast = (max(Lforeground, Lbackground) + 0.05)
           / (min(Lforeground, Lbackground) + 0.05)
```

`web/DESIGN_SYSTEM.md:463` requires at least 3:1 for meaningful graphical/UI
boundaries. The reproducible inputs for this token pair are:

| Boundary use | Foreground | Background | L foreground | L background | Ratio | Result |
|---|---|---|---:|---:|---:|---|
| `--border-strong` directly on `--brand-bg` | `--border-strong` `#7E858F` | effective `--brand-bg` `#DEE3D7` | 0.23204 | 0.75376 | 2.85:1 | **FAIL** |
| Context: `--border-strong` on `--surface` | `--border-strong` `#7E858F` | `--surface` `#FFFFFF` | 0.23204 | 1.00000 | 3.72:1 | PASS |
| Context: `--border-strong` on `--brand-bg-elevated` | `--border-strong` `#7E858F` | effective `--brand-bg-elevated` `#EBEEE7` | 0.23204 | 0.84581 | 3.18:1 | PASS |

For the failing pair, the calculation is:

```
(0.75376 + 0.05) / (0.23204 + 0.05) = 2.85:1
```

The passing `--surface` and `--brand-bg-elevated` pairs are already asserted
in `web/src/tokens/tokens.test.ts:185-198`. That coverage is why this specific
gap is not asserted there.

## Design-system follow-up

This gap means any future surface that needs a ≥3:1 stroke directly on
`--brand-bg` will hit the pair's failure. The value must be addressed by a
future approved design-system change; this record does not change any token.

The record is written after the change that surfaced the pair,
`odd/tasks/technician-surface.md`, which is merged. Per DS-CC-5 and its
scenario **Inherited contrast debt is recorded, not hidden**, the gap is
attributed to a future design-system change rather than to that completed
surface change or to this stylesheet-boundary unit.
