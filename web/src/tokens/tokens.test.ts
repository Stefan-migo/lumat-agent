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
    expect(tokensRaw).toContain('#f4f5f7'); // bg
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
});
