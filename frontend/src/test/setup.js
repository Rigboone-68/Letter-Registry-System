// Runs once before every test file (see vite.config.js `test.setupFiles`).
// Adds jest-dom's DOM-specific matchers (toBeInTheDocument, etc.) to
// Vitest's `expect`.
import '@testing-library/jest-dom/vitest'

// Testing Library's auto-cleanup-after-each-test only self-registers
// when `afterEach` is a *global* (Jest's default). This project doesn't
// enable Vitest's `test.globals` (each test file imports `afterEach`
// explicitly instead, for the same "no hidden magic" reason every other
// test file in this project imports what it uses) — so cleanup is wired
// up explicitly here, once, rather than in every component test file.
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
})
