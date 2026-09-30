/** JS-consumed subset of `tokens.css`, mirrored for type-safety (B6/T6.1).
 *
 * Only the values React/TS code needs to reference directly (spacing, radius,
 * z-index) live here. Everything visual is a CSS custom property on `:root` —
 * this module is drift-guarded against `tokens.css` by `tokens.test.ts`
 * (PDW-TKN-2): it parses `tokens.css?raw` and asserts equality.
 */

export const spacing: Record<number, string> = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
};

export const radius: Record<'sm' | 'md' | 'lg' | 'xl' | 'pill', string> = {
  sm: '6px',
  md: '8px',
  lg: '10px',
  xl: '14px',
  pill: '9999px',
};

export const zIndex: Record<'modal', string> = {
  modal: '100',
};
