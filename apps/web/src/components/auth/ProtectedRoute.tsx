import { useEffect } from "react";
import type { PropsWithChildren } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth.store";
import { Spinner } from "@/components/ui/Spinner";

type ProtectedRouteProps = PropsWithChildren<{
  requiredPermission?: string;
}>;

export function ProtectedRoute({ children, requiredPermission }: ProtectedRouteProps) {
  const isAuthed = useAuthStore((state) => state.isAuthed);
  const isLoading = useAuthStore((state) => state.isLoading);
  const hasBootstrapped = useAuthStore((state) => state.hasBootstrapped);
  const permissions = useAuthStore((state) => state.permissions);
  const bootstrap = useAuthStore((state) => state.bootstrap);

  useEffect(() => {
    if (!hasBootstrapped && !isLoading) {
      void bootstrap();
    }
  }, [bootstrap, hasBootstrapped, isLoading]);

  if (!hasBootstrapped || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!isAuthed) {
    return <Navigate to="/login" replace />;
  }

  if (requiredPermission && !permissions.includes(requiredPermission)) {
    return (
      <div className="p-8">
        <h2 className="text-xl font-semibold text-text">Access denied</h2>
        <p className="mt-2 text-sm text-muted">You do not have permission to view this page.</p>
      </div>
    );
  }

  return <>{children ?? <Outlet />}</>;
}
