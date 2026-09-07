import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const read = (path: string) => readFileSync(resolve(root, path), 'utf8');

describe('realtime deployment wiring', () => {
  it('keeps the Vite WebSocket proxy enabled', () => {
    expect(read('vite.config.ts')).toMatch(/['"]\/panel\/ws['"]\s*:\s*\{[^}]*ws\s*:\s*true/);
  });

  for (const host of ['panel.lumat.cl.conf', 'agente.lumat.cl.conf']) {
    it(`preserves the WebSocket upgrade contract on ${host}`, () => {
      const config = read(`../infra/nginx/${host}`);
      expect(config).toMatch(/location\s*=\s*\/panel\/ws\s*\{/);
      expect(config).toMatch(/proxy_http_version\s+1\.1/);
      expect(config).toMatch(/proxy_set_header\s+Upgrade\s+\$http_upgrade/);
      expect(config).toMatch(/proxy_set_header\s+Connection\s+"Upgrade"/);
      expect(config).toMatch(/proxy_(?:read|send)_timeout\s+1h/);
    });
  }
});
