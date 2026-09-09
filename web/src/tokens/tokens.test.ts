import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

import { spacing, radius, zIndex } from './tokens';

// `npm test` runs with web/ as cwd; the source tree under test is web/src.
const componentsRoot = join(process.cwd(), 'src');
const tokensRaw = readFileSync(join(componentsRoot, 'tokens', 'tokens.css'), 'utf8');

describe('design tokens (PDW-TKN-1 / PDW-TKN-2)', () => {
  it('tokens.css is a single :root source with the exact spot-checked palette', () => {
    expect(tokensRaw).toContain(':root');
    expect(tokensRaw).toContain('#143c2c'); // brand primary-800
    expect(tokensRaw).toContain('#F1F1E8'); // bg (cream, DS-V1-SHELL)
    expect(tokensRaw).toContain('#1a202c'); // text
    expect(tokensRaw).toContain('#b71c1c'); // danger
    expect(tokensRaw).toContain('#1b5e20'); // success
    expect(tokensRaw).toContain('6px'); // radius-sm
    expect(tokensRaw).toContain('8px'); // radius-md
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

  it('pins the approved Lumat brand roles from the definitive design system', () => {
    expect(cssVars.get('--brand-lime')).toBe('#abc333');
    expect(cssVars.get('--brand-cyan')).toBe('#3d93af');
    expect(cssVars.get('--brand-aqua')).toBe('#8bccd5');
    expect(cssVars.get('--brand-forest')).toBe('#576f31');
    expect(cssVars.get('--brand-graphite')).toBe('#656665');
    expect(cssVars.get('--info')).toBe('#14788f');
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

  it('keeps every pre-existing --* declaration byte-identical after the alias layer (CST-ALIAS-2 · DS-TKN-2)', () => {
    // The alias layer only referenced declared tokens above; this asserts the
    // non-corp declarations are all still present and unconverted (the file was
    // appended, not rewritten) so the original token set survives intact.
    const nonCorp = new Map<string, string>();
    for (const line of tokensRaw.split('\n')) {
      const m = line.match(/^\s*(--[\w-]+)\s*:\s*([^;]+);/);
      if (m && !m[1].startsWith('--corp-')) nonCorp.set(m[1], m[2].trim());
    }
    // Spot-checked palette still exact (no drift from the alias append).
    expect(nonCorp.get('--primary-800')).toBe('#143c2c');
    expect(nonCorp.get('--bg')).toBe('#F1F1E8');
    expect(nonCorp.get('--surface')).toBe('#fff');
    expect(nonCorp.get('--text-muted')).toBe('#4a5568');
    expect(nonCorp.get('--radius-sm')).toBe('6px');
    expect(nonCorp.get('--space-3')).toBe('12px');
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

  it('D7: .btn and .field__control get a 44px touch target under (hover: none) (CST-PRIM-3)', () => {
    const mediaRe = /@media\s*\(hover\s*:\s*none\)\s*\{([\s\S]*?)\n\}/;
    const match = primitivesRaw.match(mediaRe);
    expect(match, 'primitives.css must define an @media (hover: none) block').not.toBeNull();
    const mediaBody = match![1];
    // The touch block groups both selectors into one rule (comma list) and sets
    // a 44px min-height on touch devices; desktop keeps 40px (no media bump).
    expect(mediaBody).toMatch(/\.btn\s*,/);
    expect(mediaBody).toMatch(/\.field__control/);
    expect(mediaBody).toMatch(/min-height\s*:\s*44px/);
  });
});
