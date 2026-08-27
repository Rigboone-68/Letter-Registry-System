import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import StatusBadge from './StatusBadge'

describe('StatusBadge', () => {
  it.each([
    ['ACTIVE', 'Active'],
    ['INACTIVE', 'Inactive'],
    ['ARCHIVED', 'Archived'],
    ['PENDING_APPROVAL', 'Pending Approval'],
    ['DEACTIVATED', 'Deactivated'],
    ['USED', 'Used'],
    ['REVOKED', 'Revoked'],
  ])('renders %s with its label as real, visible text', (value, label) => {
    render(<StatusBadge value={value} label={label} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('falls back to the raw value as text when no label is given', () => {
    render(<StatusBadge value="ACTIVE" />)
    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
  })

  it('renders an unknown value with a neutral tone instead of throwing', () => {
    render(<StatusBadge value="SOMETHING_NEW" label="Something New" />)
    expect(screen.getByText('Something New')).toBeInTheDocument()
  })

  it('marks its shape indicator as decorative, never the accessible content', () => {
    const { container } = render(<StatusBadge value="ACTIVE" label="Active" />)
    const indicator = container.querySelector('[aria-hidden="true"]')
    expect(indicator).toBeInTheDocument()
    expect(indicator).toHaveTextContent('')
    // The visible text is still present as real, separately-readable content.
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('prefixes the accessible name with domain, without changing the visible text', () => {
    render(<StatusBadge value="ACTIVE" label="Active" domain="User" />)
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('User status:')).toBeInTheDocument()
  })
})
