/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Lumat Panel SPA — dev proxy + test hookup (PDW-SRV-1).
// The production bundle is bounded to /panel/app/; API URLs remain same-origin.
export default defineConfig({
  plugins: [react()],
  base: '/panel/app/',
  server: {
    port: 5173,
    proxy: {
      // Same-origin cookie round-trips in dev: the SPA origin is :5173, the
      // API stays on :8000 but the proxy makes fetches LOOK same-origin.
      '/panel/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['src/test/setup.ts'],
    globals: true,
  },
});
