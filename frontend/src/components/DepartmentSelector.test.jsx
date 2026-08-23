import { useState } from 'react'

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DepartmentSelector from './DepartmentSelector'

const DEPARTMENTS = [{ id: 'd1', name: 'Finance', code: 'FIN', status: 'ACTIVE' }]

// A minimal controlled wrapper — a bare `vi.fn()` onChange never feeds
// back into `value`, so a controlled `<select>` would immediately
// revert to its unchanged prop on the next render, fighting the
// interaction rather than reflecting real usage (every actual call
// site — AdminAuthorizePage, AdminTransferDialog — owns real `value`
// state exactly like this).
function ControlledHarness({ onSelect }) {
  const [value, setValue] = useState('')
  return (
    <DepartmentSelector
      id="dept"
      name="department_id"
      departments={DEPARTMENTS}
      value={value}
      onChange={(event) => {
        setValue(event.target.value)
        onSelect?.(event)
      }}
      activeOnly
      required
    />
  )
}

describe('DepartmentSelector', () => {
  it('never lets the DOM silently diverge from an empty controlled value, even when required', () => {
    // The real-world bug (manual E2E finding): when `required` is true
    // and no `<option value="">` exists, a controlled `<select value="">`
    // has nothing to match, and the browser (and jsdom, which faithfully
    // implements this DOM-level select/option semantic) falls back to
    // visually selecting the first real option — here, Finance — while
    // React's own tracked value, and therefore the parent's form state,
    // never moves off `''`. This assertion checks the actual DOM value,
    // not a fired event, so it cannot be masked by any user-event
    // interaction-simulation nuance.
    render(
      <DepartmentSelector
        id="dept"
        name="department_id"
        departments={DEPARTMENTS}
        value=""
        onChange={vi.fn()}
        activeOnly
        required
      />
    )
    expect(document.getElementById('dept')).toHaveValue('')
  })

  it('renders a placeholder option even when required, so the empty controlled value always has a match', () => {
    render(
      <DepartmentSelector
        id="dept"
        name="department_id"
        departments={DEPARTMENTS}
        value=""
        onChange={vi.fn()}
        activeOnly
        required
      />
    )
    expect(screen.getByRole('option', { name: /select a department/i })).toBeInTheDocument()
  })

  it('fires onChange with the real department id when the user explicitly selects one, even when it is the only department', async () => {
    const handleSelect = vi.fn()
    render(<ControlledHarness onSelect={handleSelect} />)

    await userEvent.selectOptions(document.getElementById('dept'), 'd1')

    expect(handleSelect).toHaveBeenCalled()
    const event = handleSelect.mock.calls[0][0]
    expect(event.target.value).toBe('d1')
    expect(event.target.name).toBe('department_id')
    expect(document.getElementById('dept')).toHaveValue('d1')
  })

  it('does not render a placeholder when includeAllOption is used instead', () => {
    render(
      <DepartmentSelector
        id="dept"
        departments={DEPARTMENTS}
        value=""
        onChange={vi.fn()}
        activeOnly={false}
        includeAllOption
      />
    )
    expect(screen.getByRole('option', { name: /all departments/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /select a department/i })).not.toBeInTheDocument()
  })

  it('filters to ACTIVE departments only when activeOnly is set', () => {
    render(
      <DepartmentSelector
        id="dept"
        departments={[...DEPARTMENTS, { id: 'd2', name: 'Legacy', code: null, status: 'INACTIVE' }]}
        value=""
        onChange={vi.fn()}
        activeOnly
        required
      />
    )
    expect(screen.getByRole('option', { name: 'Finance' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /legacy/i })).not.toBeInTheDocument()
  })
})
