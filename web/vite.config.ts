/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Lumat Panel SPA — dev proxy + test hookup (PDW-SRV-1).
// The production bundle is bounded to /panel/app/; API URLs remain same-origin.
//
// VITE_API_TARGET retargets the dev proxy. It defaults to :8000, the primary
// dev stack. An isolated stack (infra/docker-compose.harness.yml) remaps its
// API to :8001; without an overridable target this SPA would silently proxy to
// the other stack's API and display its data.
const apiTarget = process.env.VITE_API_TARGET ?? 'http://localhost:8000';
const wsTarget = apiTarget.replace(/^http/, 'ws');

export default defineConfig({
  plugins: [react()],
  base: '/panel/app/',
  server: {
    port: 5173,
    proxy: {
      // Same-origin cookie round-trips in dev: the SPA origin is :5173, the
      // API stays on apiTarget but the proxy makes fetches LOOK same-origin.
      '/panel/api': apiTarget,
      '/panel/ws': { target: wsTarget, ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['src/test/setup.ts'],
    globals: true,
    exclude: ['**/node_modules/**', '**/.storybook/quarantine/**/*.test.tsx', 'playwright/**'],
  },
});
