import { useEffect } from "react";
import type { PropsWithChildren } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/auth.store";
import { Spinner } from "@/components/ui/Spinner";

export function GuestRoute({ children }: PropsWithChildren) {
  const isAuthed = useAuthStore((state) => state.isAuthed);
  const isLoading = useAuthStore((state) => state.isLoading);
  const hasBootstrapped = useAuthStore((state) => state.hasBootstrapped);
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

  if (isAuthed) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children ?? <Outlet />}</>;
}
