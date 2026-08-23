/**
 * Route architecture (docs/architecture/frontend.md §19), built exactly
 * as this document's own final report describes it — derived from the
 * confirmed backend/role model, not blindly copied from any
 * illustrative example. Documents have no standalone route (always
 * reached from within a Letter's detail page in the eventual feature
 * build) — the `/app/documents` stub exists only because the
 * navigation config (§13 of the implementation brief) lists "Documents"
 * as a nav entry for every role; its placeholder page says so rather
 * than silently dropping the entry or building a page the architecture
 * review didn't recommend.
 */
import { Navigate, createBrowserRouter } from 'react-router-dom'

import AppShell from '../layouts/AppShell'
import LetterDetailPage from '../pages/LetterDetailPage'
import LetterFormPage from '../pages/LetterFormPage'
import LetterListPage from '../pages/LetterListPage'
import LoginPage from '../pages/LoginPage'
import PlaceholderPage from '../pages/PlaceholderPage'
import RootRedirect from '../pages/RootRedirect'
import SignupPage from '../pages/SignupPage'
import ProtectedRoute from './ProtectedRoute'
import RoleGuard from './RoleGuard'

export const router = createBrowserRouter([
  { path: '/', element: <RootRedirect /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },
  {
    path: '/app',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="letters" replace /> },
          { path: 'letters', element: <LetterListPage /> },
          { path: 'letters/new', element: <LetterFormPage /> },
          { path: 'letters/:id', element: <LetterDetailPage /> },
          { path: 'letters/:id/edit', element: <LetterFormPage /> },
          {
            path: 'documents',
            element: (
              <PlaceholderPage
                title="Documents"
                description="Documents are managed from within a Letter's own detail page, not as a standalone list — there is no separate document endpoint to browse independently."
              />
            ),
          },
          { path: 'notifications', element: <PlaceholderPage title="Notifications" /> },
          {
            path: 'admin/users',
            element: (
              <RoleGuard allowedRoles={['ADMIN']}>
                <PlaceholderPage title="Users" />
              </RoleGuard>
            ),
          },
          {
            path: 'system/letters',
            element: (
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <LetterListPage />
              </RoleGuard>
            ),
          },
          {
            path: 'system/departments',
            element: (
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <PlaceholderPage title="Departments" />
              </RoleGuard>
            ),
          },
          {
            path: 'system/admins',
            element: (
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <PlaceholderPage title="Administrators" />
              </RoleGuard>
            ),
          },
          {
            path: 'system/categories',
            element: (
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <PlaceholderPage title="Categories" />
              </RoleGuard>
            ),
          },
          {
            path: 'system/classifications',
            element: (
              <RoleGuard allowedRoles={['SYSTEM_ADMIN']}>
                <PlaceholderPage title="Classifications" />
              </RoleGuard>
            ),
          },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])
