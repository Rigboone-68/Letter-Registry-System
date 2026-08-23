import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import ConfirmDialog from './ConfirmDialog'

function renderDialog(props = {}) {
  return render(
    <ConfirmDialog
      title="Deactivate Finance?"
      message="This cannot be undone lightly."
      confirmLabel="Deactivate"
      onConfirm={vi.fn()}
      onCancel={vi.fn()}
      confirming={false}
      {...props}
    />
  )
}

describe('ConfirmDialog', () => {
  it('renders as an accessible dialog with the given title and message', () => {
    renderDialog()
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByRole('heading', { name: 'Deactivate Finance?' })).toBeInTheDocument()
    expect(screen.getByText('This cannot be undone lightly.')).toBeInTheDocument()
  })

  it('focuses Cancel (the safe default) on open', () => {
    renderDialog()
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('calls onCancel when Escape is pressed', async () => {
    const onCancel = vi.fn()
    renderDialog({ onCancel })
    await userEvent.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalled()
  })

  it('calls onCancel when the backdrop is clicked', async () => {
    const onCancel = vi.fn()
    const { container } = renderDialog({ onCancel })
    await userEvent.click(container.firstChild)
    expect(onCancel).toHaveBeenCalled()
  })

  it('calls onConfirm when the confirm button is clicked', async () => {
    const onConfirm = vi.fn()
    renderDialog({ onConfirm })
    await userEvent.click(screen.getByRole('button', { name: 'Deactivate' }))
    expect(onConfirm).toHaveBeenCalled()
  })

  it('disables the confirm button and shows the confirming label while in flight', () => {
    renderDialog({ confirming: true, confirmingLabel: 'Deactivating…' })
    const button = screen.getByRole('button', { name: 'Deactivating…' })
    expect(button).toBeDisabled()
  })

  it('traps Tab between Cancel and Confirm', async () => {
    renderDialog()
    const cancel = screen.getByRole('button', { name: 'Cancel' })
    const confirm = screen.getByRole('button', { name: 'Deactivate' })

    confirm.focus()
    await userEvent.tab()
    expect(cancel).toHaveFocus()

    await userEvent.tab({ shift: true })
    expect(confirm).toHaveFocus()
  })
})
