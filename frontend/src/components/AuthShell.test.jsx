import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { APP_NAME, APP_SHORT_NAME, PRODUCTION_CREDIT } from '../constants/app'
import AuthShell from './AuthShell'

describe('AuthShell', () => {
  it('renders the supplied institutional background image as decorative', () => {
    const { container } = render(<AuthShell>content</AuthShell>)
    const images = container.querySelectorAll('img')
    // Background image + government logo — both present, both decorative.
    expect(images.length).toBe(2)
    for (const img of images) {
      expect(img).toHaveAttribute('alt', '')
    }
  })

  it('renders the government logo alongside the application identity, never a duplicate announcement', () => {
    render(<AuthShell>content</AuthShell>)
    // The visible brand text already names the identity — the logo
    // itself carries no separate accessible name.
    expect(screen.getByText(APP_NAME)).toBeInTheDocument()
    expect(screen.getByText(`${APP_SHORT_NAME} Operational Registry`)).toBeInTheDocument()
  })

  it('renders the credit line exactly once', () => {
    render(<AuthShell>content</AuthShell>)
    expect(screen.getAllByText(PRODUCTION_CREDIT)).toHaveLength(1)
  })

  it('renders its children', () => {
    render(
      <AuthShell>
        <div>the actual form</div>
      </AuthShell>
    )
    expect(screen.getByText('the actual form')).toBeInTheDocument()
  })
})
