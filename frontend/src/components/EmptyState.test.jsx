import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import EmptyState from './EmptyState'

describe('EmptyState', () => {
  it('renders the given message as real, visible text', () => {
    render(<EmptyState message="No departments match the current filter." />)
    expect(screen.getByText('No departments match the current filter.')).toBeInTheDocument()
  })

  it('falls back to a default message when none is given', () => {
    render(<EmptyState />)
    expect(screen.getByText('Nothing to show yet.')).toBeInTheDocument()
  })

  it('marks its decorative glyph as aria-hidden, never the accessible content', () => {
    const { container } = render(<EmptyState message="No results." />)
    const icon = container.querySelector('[aria-hidden="true"]')
    expect(icon).toBeInTheDocument()
    expect(icon).toHaveTextContent('')
    expect(screen.getByText('No results.')).toBeInTheDocument()
  })
})
