import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import BootScreen from './BootScreen'

describe('BootScreen', () => {
  it('renders a truthful, accessible loading status', () => {
    render(<BootScreen />)

    const status = screen.getByRole('status')
    expect(status).toHaveTextContent('Loading Letter Registry System')
  })

  it('accepts a custom truthful label without changing the accessible role', () => {
    render(<BootScreen label="Restoring your session..." />)

    expect(screen.getByRole('status')).toHaveTextContent('Restoring your session...')
  })

  it('never claims unverified security/monitoring states', () => {
    render(<BootScreen />)

    const text = document.body.textContent.toLowerCase()
    expect(text).not.toMatch(/securing|encrypt|authenticating infrastructure|secure channel|all systems|system operational/)
  })

  it('renders the LRS application identity', () => {
    render(<BootScreen />)

    expect(screen.getByText('Letter Registry System')).toBeInTheDocument()
    expect(screen.getByText('LRS')).toBeInTheDocument()
  })

  it('renders the registry glyph as purely decorative', () => {
    const { container } = render(<BootScreen />)

    const glyph = container.querySelector('[aria-hidden="true"]')
    expect(glyph).toBeInTheDocument()
    // The decorative glyph must contribute no text of its own — the
    // accessible status text is the one real loading indication.
    expect(glyph).toHaveTextContent('')
  })

  it('is not the only indication of loading — the status text exists independently of the glyph', () => {
    const { container } = render(<BootScreen />)

    const glyph = container.querySelector('[aria-hidden="true"]')
    const status = screen.getByRole('status')
    expect(glyph.contains(status)).toBe(false)
  })
})
