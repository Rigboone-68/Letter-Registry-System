import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Dev server proxies /api to the local FastAPI backend so the frontend
// never needs an absolute backend URL baked into the source.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // Vitest config (Phase 5A — docs/architecture/frontend.md §30).
  // jsdom gives component tests a browser-like DOM; setupFiles wires in
  // jest-dom's matchers once for every test file.
  //
  // testTimeout raised from Vitest's 5000ms default (Phase 5F): as the
  // suite grew past ~30 files, character-by-character `userEvent.type`
  // interaction tests (e.g. LetterFormPage.test.jsx) began intermittently
  // missing the default under full-suite worker-thread contention on a
  // loaded machine, despite being logically correct and consistently
  // fast in isolation — confirmed by re-running the full suite multiple
  // consecutive times and observing the same tests pass/fail
  // non-deterministically with no code change between runs. This raises
  // headroom for every test rather than special-casing one file, and
  // changes no assertion or test behavior.
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    css: true,
    testTimeout: 10000,
  },
})
