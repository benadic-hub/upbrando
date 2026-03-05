import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { AuthLayout } from "./layouts/AuthLayout";
import { GuestRoute } from "@/components/auth/GuestRoute";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { ProjectsPage } from "@/pages/projects/ProjectsPage";
import { CrmPage } from "@/pages/crm/CrmPage";
import { HrmPage } from "@/pages/hrm/HrmPage";
import { FinancePage } from "@/pages/finance/FinancePage";
import { RecruitmentPage } from "@/pages/recruitment/RecruitmentPage";
import { ReportsPage } from "@/pages/reports/ReportsPage";
import { AdministrationPage } from "@/pages/administration/AdministrationPage";
import { UsersPage } from "@/pages/administration/UsersPage";
import { RolesPage } from "@/pages/administration/RolesPage";
import { RoleDetailsPage } from "@/pages/administration/RoleDetailsPage";
import { SettingsPage } from "@/pages/administration/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <GuestRoute>
        <AuthLayout>
          <LoginPage />
        </AuthLayout>
      </GuestRoute>
    )
  },
  {
    path: "/forgot-password",
    element: (
      <GuestRoute>
        <AuthLayout>
          <ForgotPasswordPage />
        </AuthLayout>
      </GuestRoute>
    )
  },
  {
    path: "/reset-password",
    element: (
      <GuestRoute>
        <AuthLayout>
          <ResetPasswordPage />
        </AuthLayout>
      </GuestRoute>
    )
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />
      },
      {
        path: "dashboard",
        element: <DashboardPage />
      },
      {
        path: "projects",
        element: <ProjectsPage />
      },
      {
        path: "crm",
        element: <CrmPage />
      },
      {
        path: "hrm",
        element: <HrmPage />
      },
      {
        path: "finance",
        element: <FinancePage />
      },
      {
        path: "recruitment",
        element: <RecruitmentPage />
      },
      {
        path: "reports",
        element: <ReportsPage />
      },
      {
        path: "administration",
        element: <AdministrationPage />
      },
      {
        path: "administration/users",
        element: (
          <ProtectedRoute requiredPermission="users.read">
            <UsersPage />
          </ProtectedRoute>
        )
      },
      {
        path: "administration/roles",
        element: (
          <ProtectedRoute requiredPermission="roles.read">
            <RolesPage />
          </ProtectedRoute>
        )
      },
      {
        path: "administration/roles/:id",
        element: (
          <ProtectedRoute requiredPermission="roles.read">
            <RoleDetailsPage />
          </ProtectedRoute>
        )
      },
      {
        path: "administration/settings",
        element: <SettingsPage />
      }
    ]
  },
  {
    path: "*",
    element: <Navigate to="/dashboard" replace />
  }
]);
