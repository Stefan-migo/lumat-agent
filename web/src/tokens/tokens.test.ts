import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

import { spacing, radius, zIndex } from './tokens';

// `npm test` runs with web/ as cwd; the source tree under test is web/src.
const componentsRoot = join(process.cwd(), 'src');
const tokensRaw = readFileSync(join(componentsRoot, 'tokens', 'tokens.css'), 'utf8');

const cssVars = new Map<string, string>();
for (const line of tokensRaw.split('\n')) {
  const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
  if (m) cssVars.set(m[1], m[2].trim());
}

type Rgb = [number, number, number];

const resolveColor = (name: string): Rgb => {
  const value = cssVars.get(name) ?? name;
  const alias = value.match(/^var\((--[\w-]+)\)$/);
  if (alias) return resolveColor(alias[1]);
  const mix = value.match(/^color-mix\(in srgb, var\((--[\w-]+)\) ([\d.]+)%, var\((--[\w-]+)\)\)$/);
  if (mix) {
    const first = resolveColor(mix[1]);
    const second = resolveColor(mix[3]);
    const weight = Number(mix[2]) / 100;
    return first.map((channel, index) => weight * channel + (1 - weight) * second[index]) as Rgb;
  }
  const hex = value.match(/^#([\da-f]{3}|[\da-f]{6}|[\da-f]{8})$/i);
  if (!hex) throw new Error(`Unsupported color token: ${name} = ${value}`);
  const raw = hex[1].length === 3
    ? hex[1].split('').map((channel) => channel + channel).join('')
    : hex[1];
  const rgb: Rgb = [parseInt(raw.slice(0, 2), 16), parseInt(raw.slice(2, 4), 16), parseInt(raw.slice(4, 6), 16)];
  if (raw.length === 8) {
    const alpha = parseInt(raw.slice(6), 16) / 255;
    const background = resolveColor('--bg');
    return rgb.map((channel, index) => alpha * channel + (1 - alpha) * background[index]) as Rgb;
  }
  return rgb;
};

const relativeLuminance = ([r, g, b]: Rgb): number => {
  const linear = (channel: number): number => {
    const normalized = channel / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
};

const contrast = (foreground: Rgb, background: Rgb): number => {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  return (Math.max(foregroundLuminance, backgroundLuminance) + 0.05) /
    (Math.min(foregroundLuminance, backgroundLuminance) + 0.05);
};

const requiredPalette = {
  '--chrome-950': '#012f1d', '--chrome-900': '#073d2b', '--chrome-active': '#012214',
  '--bg': '#dbe1d6', '--header-bg': '#dee4db', '--surface': '#e8ebe4', '--border': '#d5dad1',
  '--lime-500': '#c6d529', '--lime-600': '#d3e41d', '--lime-700': '#a2c312',
  '--teal-500': '#52babb', '--teal-400': '#6adbdf', '--text': '#111a2e',
  '--text-muted': '#5a6469', '--text-on-dark': '#e9f0e9', '--text-on-dark-2': '#88a599',
  '--warning': '#8f5406',
};

const surfaceRoles = [
  '--bg', '--header-bg', '--surface', '--table-head-bg', '--surface-subtle', '--brand-bg',
  '--brand-bg-elevated', '--danger-bg', '--success-bg', '--warning-bg', '--success-tint',
  '--danger-tint', '--warning-tint', '--info-tint', '--corp-bg', '--corp-surface', '--corp-surface-hover',
];

describe('design tokens (PDW-TKN-1 / PDW-TKN-2)', () => {
  it('keeps shell rail layout tokens in text-zoom-immune pixels', () => {
    expect(cssVars.get('--shell-rail-compact')).toBe('64px');
    expect(cssVars.get('--shell-rail-expanded')).toBe('240px');
  });

  it('defines one root with the exact approved canonical palette', () => {
    expect(tokensRaw.match(/:root\s*\{/g)).toHaveLength(1);
    for (const [role, value] of Object.entries(requiredPalette)) expect(cssVars.get(role)).toBe(value);
  });

  it('resolves every surface alias and supported mix and rejects pure white', () => {
    for (const role of surfaceRoles) {
      expect(cssVars.has(role), `missing surface role ${role}`).toBe(true);
      expect(resolveColor(role), `${role} must resolve to a non-white RGB color`).not.toEqual([255, 255, 255]);
    }
    expect(() => resolveColor('--unsupported-surface')).toThrow(/Unsupported color token/);
  });

  it('tokens.ts mirrors the JS-consumed subset without drift (PDW-TKN-2)', () => {
    const cssVars = new Map<string, string>();
    for (const line of tokensRaw.split('\n')) {
      const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
      if (m) cssVars.set(m[1], m[2].trim());
    }

    // space scale
    for (const [n, value] of Object.entries(spacing)) {
      expect(cssVars.get(`--space-${n}`)).toBe(value);
    }
    // radius
    for (const [name, value] of Object.entries(radius)) {
      expect(cssVars.get(`--radius-${name}`)).toBe(value);
    }
    // z-index
    expect(cssVars.get('--z-modal')).toBe(zIndex.modal);
  });

  it('no hard-coded hex color appears anywhere outside tokens.css (PDW-TKN-2)', () => {
    const hexRe = /#[0-9a-fA-F]{3,6}\b/g;
    const offenders: string[] = [];

    const walk = (dir: string): void => {
      for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) {
          walk(full);
          continue;
        }
        if (
          !/\.(ts|tsx|css)$/.test(entry) ||
          entry.endsWith('.test.ts') ||
          entry.endsWith('.test.tsx') ||
          entry.endsWith('.stories.tsx')
        ) {
          continue;
        }
        const rel = relative(componentsRoot, full);
        if (rel === 'tokens/tokens.css') continue;
        const body = readFileSync(full, 'utf8');
        if (hexRe.test(body)) offenders.push(rel);
      }
    };
    walk(componentsRoot);

    expect(offenders).toEqual([]);
  });
});

describe('design tokens — B9 foundation additions (DS-TKN-3..7)', () => {
  // Same line regex the Tokens page uses — one pattern, two consumers (D7/D11).
  const cssVars = new Map<string, string>();
  for (const line of tokensRaw.split('\n')) {
    const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
    if (m) cssVars.set(m[1], m[2].trim());
  }

  it('type scale, leading, and weight tokens match the design table (DS-TKN-3)', () => {
    expect(cssVars.get('--text-xs')).toBe('0.75rem');
    expect(cssVars.get('--text-base')).toBe('1rem');
    expect(cssVars.get('--text-xl')).toBe('1.5rem');
    expect(cssVars.get('--text-3xl')).toBe('2.25rem');
    expect(cssVars.get('--leading-tight')).toBe('1.2');
    expect(cssVars.get('--leading-snug')).toBe('1.375');
    expect(cssVars.get('--leading-normal')).toBe('1.5');
    expect(cssVars.get('--leading-relaxed')).toBe('1.625');
    expect(cssVars.get('--weight-regular')).toBe('400');
    expect(cssVars.get('--weight-medium')).toBe('500');
    expect(cssVars.get('--weight-semibold')).toBe('600');
    expect(cssVars.get('--weight-bold')).toBe('700');
  });

  it('focus-ring set matches the design table (DS-TKN-4)', () => {
    expect(cssVars.get('--focus-ring')).toBe('#256f51');
    expect(cssVars.get('--focus-ring-width')).toBe('2px');
    expect(cssVars.get('--focus-ring-offset')).toBe('2px');
  });

  it('motion scale matches the design table (DS-TKN-5)', () => {
    expect(cssVars.get('--duration-fast')).toBe('100ms');
    expect(cssVars.get('--duration-base')).toBe('150ms');
    expect(cssVars.get('--duration-slow')).toBe('250ms');
    expect(cssVars.get('--ease-out')).toBe('cubic-bezier(0.33, 1, 0.68, 1)');
    expect(cssVars.get('--ease-in-out')).toBe('cubic-bezier(0.65, 0, 0.35, 1)');
  });

  it('breakpoint reference tokens match the design table (DS-TKN-6)', () => {
    expect(cssVars.get('--bp-sm')).toBe('640px');
    expect(cssVars.get('--bp-md')).toBe('1024px');
    expect(cssVars.get('--bp-lg')).toBe('1280px');
  });

  it('shadow-3 extends the elevation scale (DS-TKN-7)', () => {
    expect(cssVars.get('--shadow-3')).toBe('0 8px 24px rgba(0, 0, 0, 0.16)');
  });

  it('provides the visual foundation vocabulary with real primitive consumers', () => {
    expect(cssVars.get('--radius-lg')).toBe('10px');
    expect(cssVars.get('--radius-xl')).toBe('14px');
    expect(cssVars.get('--radius-pill')).toBe('9999px');
    expect(cssVars.get('--surface-subtle')).toBe('var(--table-head-bg)');
    expect(cssVars.get('--elevation-raised')).toBe('none');
    expect(cssVars.get('--elevation-overlay')).toBe('var(--shadow-3)');
    expect(cssVars.get('--icon-sm')).toBe('16px');
    expect(cssVars.get('--icon-md')).toBe('20px');
    expect(cssVars.get('--icon-lg')).toBe('24px');
    expect(cssVars.get('--font-ui')).toBe('Inter, var(--font-sans)');

    const primitivesRaw = readFileSync(
      join(componentsRoot, 'components', 'primitives', 'primitives.css'),
      'utf8',
    );
    expect(primitivesRaw).toMatch(/\.card\s*\{[^}]*border-radius:\s*var\(--radius-lg\);/s);
    expect(primitivesRaw).toMatch(/\.btn\s*\{[^}]*border-radius:\s*var\(--radius-lg\);/s);
    expect(primitivesRaw).toMatch(/\.badge--neutral\s*\{[^}]*background:\s*var\(--surface-subtle\);/s);
    expect(primitivesRaw).not.toMatch(/\.card\s*\{[^}]*box-shadow:/s);
    expect(primitivesRaw).toMatch(/\.dialog\s*\{[^}]*border-radius:\s*var\(--radius-xl\);/s);
    expect(tokensRaw).toMatch(/--elevation-overlay:\s*var\(--shadow-3\)/);
    expect(primitivesRaw).toMatch(/\.btn\s*>\s*svg,[^\{]*\.dialog__close\s*>\s*svg\s*\{[^}]*width:\s*var\(--icon-md\);/s);
    expect(primitivesRaw).toMatch(/\.icon\.icon--sm\s*\{[^}]*width:\s*var\(--icon-sm\);/s);
    expect(primitivesRaw).toMatch(/\.icon\.icon--lg\s*\{[^}]*width:\s*var\(--icon-lg\);/s);
    expect(primitivesRaw).toMatch(/\.card__title\s*\{[^}]*font-family:\s*var\(--font-ui\);/s);
  });

  it('pins the approved Lumat brand roles from the definitive design system', () => {
    expect(cssVars.get('--brand-lime')).toBe('#abc333');
    expect(cssVars.get('--brand-cyan')).toBe('#3d93af');
    expect(cssVars.get('--brand-aqua')).toBe('#8bccd5');
    expect(cssVars.get('--brand-forest')).toBe('#576f31');
    expect(cssVars.get('--brand-graphite')).toBe('#656665');
    expect(cssVars.get('--info')).toBe('#14788f');
  });
});

describe('design tokens — WCAG 2.2 AA measured palette pairs', () => {
  it('meets text and boundary thresholds and records decorative-only dispositions', () => {
    const surface = resolveColor('--surface');
    const bg = resolveColor('--bg');
    const header = resolveColor('--header-bg');
    const strongBorder = resolveColor('--border-strong');
    const warning = resolveColor('--warning');
    const muted = resolveColor('--text-muted');
    const lightText = resolveColor('--text-on-dark-2');
    expect(contrast(resolveColor('--text'), bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(resolveColor('--text'), surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(resolveColor('--text'), header)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(muted, bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(muted, surface)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(muted, header)).toBeGreaterThanOrEqual(4.5);
    for (const role of ['--chrome-950', '--chrome-900', '--chrome-active']) {
      expect(contrast(resolveColor('--text-on-dark'), resolveColor(role)), role).toBeGreaterThanOrEqual(4.5);
      expect(contrast(lightText, resolveColor(role)), role).toBeGreaterThanOrEqual(4.5);
    }
    expect(contrast(strongBorder, surface), '--border-strong on --surface').toBeGreaterThanOrEqual(3);
    expect(contrast(warning, resolveColor('--warning-bg')), '--warning on --warning-bg').toBeGreaterThanOrEqual(4.5);
    expect(contrast(warning, surface), '--warning on --surface').toBeGreaterThanOrEqual(4.5);
    expect(contrast(warning, bg), '--warning on --bg').toBeGreaterThanOrEqual(4.5);
    expect(contrast(resolveColor('--teal-500'), resolveColor('--chrome-950'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(resolveColor('--teal-400'), resolveColor('--chrome-950'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(resolveColor('--lime-500'), resolveColor('--chrome-950'))).toBeGreaterThanOrEqual(3);
    expect(contrast(strongBorder, bg)).toBeLessThan(3);
    expect(tokensRaw).toMatch(/--border.*decorative/i);
    expect(tokensRaw).toMatch(/--lime-700.*decorative/i);
    expect(tokensRaw).toMatch(/status.*borders?.*decorative/i);
  });
});

describe('DESIGN_SYSTEM.md — final panel direction', () => {
  const guide = readFileSync(join(process.cwd(), 'DESIGN_SYSTEM.md'), 'utf8');

  it('documents every locked palette role and matches token values', () => {
    for (const [role, value] of Object.entries(requiredPalette)) {
      expect(guide, `${role} documentation`).toMatch(new RegExp(`${role}[^\\n]*${value}`, 'i'));
    }
  });

  it('documents resolved surfaces, measured contrast dispositions, shape, shell, and assets', () => {
    for (const text of [
      'never be pure white', '4.55:1', '5.04:1', '4.69:1', '4.61:1', '5.53:1', '6.36:1',
      '5.07:1', '5.48:1', 'decorative', '10px', '14px', '--shadow-3', 'overlay',
      '640', '1024', '1280', 'no dark mode', 'lumat-logo.png', 'lumat-mark.png',
    ]) expect(guide.toLowerCase()).toContain(text.toLowerCase());
    expect(guide).not.toMatch(/obtain or create an? (svg|production-ready logo)|low-resolution JPG/i);
  });
});

describe('design tokens — corp-* alias layer (CST-ALIAS-1..5 · DS-TKN-10..12)', () => {
  // Parse the FULL :root token declarations into { slot -> value } (file-scoped,
  // so the alias layer can assert its var() targets resolve against them).
  const allTokens = new Map<string, string>();
  const corpVars = new Map<string, string>();
  for (const line of tokensRaw.split('\n')) {
    const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
    if (!m) continue;
    const key = m[1];
    allTokens.set(key, m[2].trim());
    if (key.startsWith('--corp-')) corpVars.set(key, m[2].trim());
  }

  // The 17 catalog slots defined by the alias layer (proposal/design tables).
  const aliasedSlots = [
    '--corp-primary', '--corp-primary-fg', '--corp-accent', '--corp-border',
    '--corp-fg', '--corp-fg-muted', '--corp-text', '--corp-muted',
    '--corp-surface', '--corp-surface-hover', '--corp-bg', '--corp-radius',
    '--corp-gap', '--corp-value', '--corp-size', '--corp-w', '--corp-h',
  ];
  // Slots that intentionally do NOT resolve to a token (behavioral / fallback).
  const unresolvedSlots = new Set(['--corp-value', '--corp-size', '--corp-w', '--corp-h']);
  const declaredAliased = aliasedSlots.filter((s) => !unresolvedSlots.has(s));

  it('declares the 13 resolvable corp-* slots exactly once; size/w/h fall back unmatched (CST-ALIAS-3 · CST-ALIAS-4)', () => {
    for (const slot of declaredAliased) {
      expect(corpVars.has(slot), `missing slot ${slot}`).toBe(true);
    }
    expect(corpVars.size).toBe(14); // 13 mapped + --corp-value, no twins
    for (const slot of ['--corp-size', '--corp-w', '--corp-h']) {
      expect(corpVars.has(slot), `${slot} is unresolved → component default`).toBe(false);
    }
  });

  it('maps every resolved color/spacing slot to a var(--*) referencing an existing token (CST-ALIAS-1 · DS-TKN-10)', () => {
    const resolvedSlots = [...corpVars.entries()].filter(([, v]) => /^var\(--[\w-]+\)$/.test(v));
    expect(resolvedSlots.length).toBe(13); // 13 mapped var() targets
    for (const [slot, value] of resolvedSlots) {
      const target = value.slice(4, -1); // strip var( ... )
      expect(allTokens.has(target), `${slot} -> ${value} references a declared token`).toBe(true);
    }
  });

  it('declares zero hex literals anywhere in the corp-* alias layer (DS-TKN-10)', () => {
    const hexRe = /#[0-9a-fA-F]{3,6}\b/;
    const offenders: string[] = [];
    for (const [slot, value] of corpVars) {
      if (hexRe.test(value)) offenders.push(`${slot}: ${value}`);
    }
    expect(offenders).toEqual([]);
  });

  it('spot-checks the primary/bg/surface/value slot targets (DS-TKN-10 / CST-ALIAS-5)', () => {
    expect(corpVars.get('--corp-primary')).toBe('var(--primary-800)');
    expect(corpVars.get('--corp-primary-fg')).toBe('var(--surface)');
    expect(corpVars.get('--corp-bg')).toBe('var(--bg)');
    expect(corpVars.get('--corp-surface')).toBe('var(--surface)');
    expect(corpVars.get('--corp-value')).toBe('tabular-nums');
  });

  it('keeps --corp-size/-w/-h as documented fallbacks, never hardcoded or twinned (CST-ALIAS-4)', () => {
    for (const slot of ['--corp-size', '--corp-w', '--corp-h']) {
      expect(corpVars.get(slot)).toBeUndefined(); // absent → component default
    }
    // The fallback is documented with a build-warning comment in the alias block.
    expect(tokensRaw).toMatch(/--corp-size/);
    expect(tokensRaw).toMatch(/fall ?back|unresolved|default sizing/i);
  });

  it('keeps primary semantics and non-palette geometry tokens stable', () => {
    expect(cssVars.get('--primary-800')).toBe('#143c2c');
    expect(cssVars.get('--radius-sm')).toBe('6px');
    expect(cssVars.get('--space-3')).toBe('12px');
  });
});

describe('primitives.css — slice-1 catalog contract (CST-PRIM-1/3 · D7)', () => {
  const primitivesRaw = readFileSync(
    join(componentsRoot, 'components', 'primitives', 'primitives.css'),
    'utf8',
  );

  it('is hex-free — every value resolves through tokens (CST-PRIM-1)', () => {
    const hex = primitivesRaw.match(/#[0-9a-fA-F]{3,6}\b/);
    expect(hex).toBeNull();
  });

  it('D7: one (hover: none) block owns every 44px touch target (CST-PRIM-3)', () => {
    // The touch bump is cross-cutting: every interactive control takes its 44px
    // hit area from ONE block. A second, parallel @media (hover: none) block is
    // the regression this asserts against — it shipped twice already (combobox,
    // then menu), so the rule lives here now, not in a comment.
    const touchBlocks =
      primitivesRaw.match(/@media\s*\(hover\s*:\s*none\)\s*\{[\s\S]*?\n\}/g) ?? [];
    expect(
      touchBlocks.length,
      'touch sizing must live in exactly one @media (hover: none) block',
    ).toBe(1);

    const body = touchBlocks[0];
    expect(body).toMatch(/min-height\s*:\s*44px/);
    for (const selector of [
      '.btn',
      '.field__control',
      '.popover__trigger',
      '.tooltip__trigger',
      '.menu__trigger',
      '.menu__item',
      '.combobox__option',
    ]) {
      expect(
        body,
        `${selector} must take its 44px touch target from the single D7 block`,
      ).toContain(selector);
    }
  });
});
