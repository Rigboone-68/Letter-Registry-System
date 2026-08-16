/**
 * Application shell.
 *
 * PHASE 1: placeholder only. No routing, authentication, layouts, or
 * feature screens are implemented yet. The router is mounted here in a
 * later phase:
 *
 *   import { RouterProvider } from 'react-router-dom'
 *   import { router } from './routes'
 *   export default function App() { return <RouterProvider router={router} /> }
 */

import { APP_NAME, APP_SHORT_NAME } from './constants/app.js'

export default function App() {
  return (
    <main>
      <h1>{APP_NAME} ({APP_SHORT_NAME})</h1>
      <p>Phase 1 foundation. No functionality is implemented yet.</p>
    </main>
  )
}
