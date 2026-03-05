import { useMemo, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import clsx from "clsx";
import { useUiStore } from "@/store/ui.store";
import { useAuthStore } from "@/store/auth.store";
import { Icon, type IconName } from "@/components/ui/Icon";

type NavItem = {
  label: string;
  to: string;
  icon: IconName;
  requiredPermission?: string;
};

type NavGroup = {
  label: string;
  icon: IconName;
  to?: string;
  requiredPermission?: string;
  children?: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    label: "Dashboard",
    icon: "dashboard",
    to: "/dashboard"
  },
  {
    label: "Projects",
    icon: "projects",
    to: "/projects"
  },
  {
    label: "CRM",
    icon: "crm",
    to: "/crm"
  },
  {
    label: "HRM",
    icon: "hrm",
    to: "/hrm"
  },
  {
    label: "Finance & Accounts",
    icon: "finance",
    to: "/finance"
  },
  {
    label: "Recruitment",
    icon: "recruitment",
    to: "/recruitment"
  },
  {
    label: "Administration",
    icon: "administration",
    to: "/administration",
    children: [
      { label: "Users", to: "/administration/users", icon: "users", requiredPermission: "users.read" },
      { label: "Roles", to: "/administration/roles", icon: "roles", requiredPermission: "roles.read" },
      { label: "Settings", to: "/administration/settings", icon: "settings" }
    ]
  },
  {
    label: "Reports",
    icon: "reports",
    to: "/reports"
  }
];

export function Sidebar() {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const permissions = useAuthStore((state) => state.permissions);
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    Administration: true
  });

  const visibleGroups = useMemo(
    () =>
      navGroups
        .map((group) => ({
          ...group,
          children: group.children?.filter((item) => !item.requiredPermission || permissions.includes(item.requiredPermission))
        }))
        .filter((group) => !group.requiredPermission || permissions.includes(group.requiredPermission)),
    [permissions]
  );

  const toggleGroup = (groupLabel: string) => {
    setOpenGroups((prev) => ({ ...prev, [groupLabel]: !prev[groupLabel] }));
  };

  const isActive = (to?: string) => {
    if (!to) {
      return false;
    }
    return location.pathname === to || location.pathname.startsWith(`${to}/`);
  };

  return (
    <aside
      className={clsx(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200",
        collapsed ? "w-[84px]" : "w-[272px]"
      )}
    >
      <div className="border-b border-border px-4 py-5">
        <h1 className={clsx("truncate text-heading-4 font-semibold text-text", collapsed ? "text-center" : "")}>
          {collapsed ? "UP" : "UPBRANDO"}
        </h1>
        {!collapsed ? <p className="mt-1 text-body-sm uppercase tracking-wide text-muted">EMS Dashboard</p> : null}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {visibleGroups.map((group) => (
          <div key={group.label} className="space-y-1">
            {group.to ? (
              <NavLink
                to={group.to}
                className={clsx(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-body-lg font-medium transition",
                  isActive(group.to) ? "bg-primary-soft text-primary" : "text-text hover:bg-surface-2"
                )}
                title={collapsed ? group.label : undefined}
              >
                <Icon name={group.icon} className="h-4 w-4 shrink-0" />
                {!collapsed ? <span className="truncate">{group.label}</span> : null}
              </NavLink>
            ) : null}
            {group.children && group.children.length > 0 && !collapsed ? (
              <div className="ml-2 space-y-1 border-l border-border pl-3">
                {group.children.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={clsx(
                      "flex items-center gap-2 rounded-md px-3 py-2 text-body-lg transition",
                      isActive(item.to) ? "bg-primary-soft text-primary" : "text-muted hover:bg-surface-2 hover:text-text"
                    )}
                  >
                    <Icon name={item.icon} className="h-3.5 w-3.5" />
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            ) : null}
            {group.children && group.children.length > 0 && collapsed ? (
              <button
                className={clsx(
                  "flex w-full items-center justify-center rounded-md py-2 text-muted transition hover:bg-surface-2",
                  isActive(group.to) ? "bg-primary-soft text-primary" : ""
                )}
                onClick={() => toggleGroup(group.label)}
                title={openGroups[group.label] ? `Collapse ${group.label}` : `Expand ${group.label}`}
                type="button"
              >
                <Icon name={openGroups[group.label] ? "chevron-down" : "chevron-right"} />
              </button>
            ) : null}
          </div>
        ))}
      </nav>
      <div className="border-t border-border px-4 py-4 text-body-sm text-muted">{collapsed ? "v1" : "Pilot v1.0"}</div>
    </aside>
  );
}
