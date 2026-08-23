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
 *
 * Phase 5D (docs/architecture/administration-ui.md §13) fills in the
 * `system/departments`, `system/admins`, and `admin/users` slots that
 * were placeholders through Phase 5C — each as a nested route group
 * behind one `RoleGuard` layout instance, rather than repeating the
 * guard on every child route.
 *
 * Phase 5F (docs/architecture/dashboard.md §4) adds `dashboard` as a
 * plain, unguarded child route — available to every role, since the
 * page itself renders role-appropriate content rather than needing a
 * `RoleGuard`. The index redirect intentionally still goes to
 * `letters`, not `dashboard` — preserving the existing landing
 * behavior was an explicit implementation-brief instruction, not an
 * oversight.
 */
import { Navigate, createBrowserRouter } from 'react-router-dom'

import AppShell from '../layouts/AppShell'
import AdminAuthorizePage from '../pages/AdminAuthorizePage'
import AdminDetailPage from '../pages/AdminDetailPage'
import AdminListPage from '../pages/AdminListPage'
import DashboardPage from '../pages/DashboardPage'
import DepartmentCreatePage from '../pages/DepartmentCreatePage'
import DepartmentDetailPage from '../pages/DepartmentDetailPage'
import DepartmentListPage from '../pages/DepartmentListPage'
import LetterDetailPage from '../pages/LetterDetailPage'
import LetterFormPage from '../pages/LetterFormPage'
import LetterListPage from '../pages/LetterListPage'
import LoginPage from '../pages/LoginPage'
import NotificationsPage from '../pages/NotificationsPage'
import PlaceholderPage from '../pages/PlaceholderPage'
import RootRedirect from '../pages/RootRedirect'
import SignupPage from '../pages/SignupPage'
import UserAuthorizePage from '../pages/UserAuthorizePage'
import UserAuthorizationsPage from '../pages/UserAuthorizationsPage'
import UserDetailPage from '../pages/UserDetailPage'
import UserListPage from '../pages/UserListPage'
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
          { path: 'dashboard', element: <DashboardPage /> },
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
          { path: 'notifications', element: <NotificationsPage /> },
          {
            path: 'admin/users',
            element: <RoleGuard allowedRoles={['ADMIN']} />,
            children: [
              { index: true, element: <UserListPage /> },
              { path: 'authorize', element: <UserAuthorizePage /> },
              { path: 'authorizations', element: <UserAuthorizationsPage /> },
              { path: ':id', element: <UserDetailPage /> },
            ],
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
            element: <RoleGuard allowedRoles={['SYSTEM_ADMIN']} />,
            children: [
              { index: true, element: <DepartmentListPage /> },
              { path: 'new', element: <DepartmentCreatePage /> },
              { path: ':id', element: <DepartmentDetailPage /> },
            ],
          },
          {
            path: 'system/admins',
            element: <RoleGuard allowedRoles={['SYSTEM_ADMIN']} />,
            children: [
              { index: true, element: <AdminListPage /> },
              { path: 'authorize', element: <AdminAuthorizePage /> },
              { path: ':id', element: <AdminDetailPage /> },
            ],
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
