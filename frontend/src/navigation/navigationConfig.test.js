import { describe, expect, it } from 'vitest'

import { getNavigationForRole } from './navigationConfig'

describe('getNavigationForRole', () => {
  it('returns the full System Admin nav set', () => {
    const labels = getNavigationForRole('SYSTEM_ADMIN').map((item) => item.label)

    expect(labels).toEqual([
      'Letters',
      'Documents',
      'Notifications',
      'Departments',
      'Administrators',
      'Categories',
      'Classifications',
    ])
  })

  it('returns the Admin nav set, excluding System-Admin-only items', () => {
    const labels = getNavigationForRole('ADMIN').map((item) => item.label)

    expect(labels).toEqual(['Letters', 'Documents', 'Notifications', 'Users'])
    expect(labels).not.toContain('Departments')
    expect(labels).not.toContain('Administrators')
  })

  it('returns the User nav set, excluding every administrative item', () => {
    const labels = getNavigationForRole('USER').map((item) => item.label)

    expect(labels).toEqual(['Letters', 'Documents', 'Notifications'])
  })

  it('returns an empty array for an unknown or missing role rather than throwing', () => {
    expect(getNavigationForRole('NOT_A_REAL_ROLE')).toEqual([])
    expect(getNavigationForRole(undefined)).toEqual([])
  })

  it('never includes a department id in any path', () => {
    const allPaths = [
      ...getNavigationForRole('SYSTEM_ADMIN'),
      ...getNavigationForRole('ADMIN'),
      ...getNavigationForRole('USER'),
    ].map((item) => item.path)

    for (const path of allPaths) {
      expect(path).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-/i) // no UUID-shaped segment
    }
  })
})
