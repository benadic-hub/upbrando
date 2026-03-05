import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { Button } from "@/components/ui/Button";
import { getErrorMessage } from "@/services/http";
import { Icon } from "@/components/ui/Icon";

export function Topbar() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const organization = useAuthStore((state) => state.organization);
  const roles = useAuthStore((state) => state.roles);
  const logout = useAuthStore((state) => state.logout);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);
  const pushToast = useUiStore((state) => state.pushToast);

  const onLogout = async () => {
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    }
  };

  return (
    <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-border bg-surface/90 px-6 backdrop-blur">
      <div className="flex min-w-0 items-center gap-3">
        <Button className="h-10 w-10 px-0" variant="secondary" onClick={toggleSidebar}>
          <Icon name="menu" />
        </Button>
        <label className="relative hidden min-w-[260px] lg:block">
          <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            className="h-10 w-full rounded-md border border-border bg-surface-2 pl-9 pr-3 text-body-lg text-text outline-none ring-primary/20 transition focus:ring-2"
            placeholder="Search modules, users, tasks..."
            type="search"
          />
        </label>
        <div className="min-w-0">
          <p className="truncate text-heading-6 text-text">{organization?.name ?? "Organization"}</p>
          <p className="truncate text-body-md text-muted">{user?.email}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border bg-surface-2 text-muted transition hover:text-text"
          title="Notifications"
          type="button"
        >
          <Icon name="notification" />
        </button>

        <div className="hidden text-right md:block">
          <p className="text-body-lg font-medium text-text">{user?.fullName ?? "User"}</p>
          <p className="text-body-sm text-muted">{roles[0]?.name ?? "Member"}</p>
        </div>

        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-soft text-body-lg font-semibold text-primary">
          {(user?.fullName ?? "U").charAt(0).toUpperCase()}
        </div>
        <Button variant="secondary" onClick={onLogout}>
          Logout
        </Button>
      </div>
    </header>
  );
}
