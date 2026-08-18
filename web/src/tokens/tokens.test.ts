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
