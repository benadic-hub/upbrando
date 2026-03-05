import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { AppRole, AppUser } from "@shared/types/auth";
import { rolesApi } from "@/services/roles.api";
import { usersApi } from "@/services/users.api";
import { getErrorMessage } from "@/services/http";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { Textarea } from "@/components/ui/Textarea";

export function RoleDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const permissions = useAuthStore((state) => state.permissions);
  const pushToast = useUiStore((state) => state.pushToast);
  const canWrite = permissions.includes("roles.write");

  const [role, setRole] = useState<AppRole | null>(null);
  const [loading, setLoading] = useState(true);
  const [permissionCodes, setPermissionCodes] = useState<string[]>([]);
  const [assignedUsers, setAssignedUsers] = useState<AppUser[]>([]);

  const [isPermissionsModalOpen, setIsPermissionsModalOpen] = useState(false);
  const [permissionsText, setPermissionsText] = useState("");
  const [savingPermissions, setSavingPermissions] = useState(false);

  const [userSearch, setUserSearch] = useState("");
  const [userOptions, setUserOptions] = useState<AppUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [loadingUserOptions, setLoadingUserOptions] = useState(false);
  const [assignLoading, setAssignLoading] = useState(false);
  const [unassignLoading, setUnassignLoading] = useState(false);

  const loadRoleUsers = useCallback(
    async (roleId: string) => {
      const response = await rolesApi.users(roleId, { page: 1, pageSize: 100 });
      setAssignedUsers(response.data);
    },
    [setAssignedUsers]
  );

  const loadUserOptions = useCallback(
    async (query: string) => {
      setLoadingUserOptions(true);
      try {
        const response = await usersApi.list({ page: 1, pageSize: 25, q: query.trim() || undefined });
        setUserOptions(response.data);
      } catch (error) {
        pushToast({ type: "error", message: getErrorMessage(error) });
      } finally {
        setLoadingUserOptions(false);
      }
    },
    [pushToast]
  );

  const loadRole = useCallback(async () => {
    setLoading(true);
    try {
      if (!id) {
        pushToast({ type: "error", message: "Missing role ID." });
        navigate("/administration/roles", { replace: true });
        return;
      }

      const [rolesResponse, permissionsResponse] = await Promise.all([
        rolesApi.list({ page: 1, pageSize: 100 }),
        rolesApi.permissions(id)
      ]);

      const fallbackRole: AppRole = {
        id,
        organizationId: "",
        name: `Role ${id}`,
        description: null,
        createdAt: "",
        updatedAt: ""
      };
      const found = rolesResponse.data.find((item) => item.id === id) ?? fallbackRole;
      setRole(found);
      setPermissionCodes(permissionsResponse.data.permissionCodes);
      await loadRoleUsers(id);
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  }, [id, loadRoleUsers, navigate, pushToast]);

  useEffect(() => {
    void loadRole();
  }, [loadRole]);

  useEffect(() => {
    void loadUserOptions(userSearch);
  }, [loadUserOptions, userSearch]);

  const handleReplacePermissions = async () => {
    if (!id) {
      return;
    }
    const codes = permissionsText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    setSavingPermissions(true);
    try {
      await rolesApi.replacePermissions(id, codes);
      pushToast({ type: "success", message: "Permissions updated successfully." });
      setIsPermissionsModalOpen(false);
      setPermissionsText("");
      void loadRole();
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setSavingPermissions(false);
    }
  };

  const handleAssign = async () => {
    if (!id || !selectedUserId) {
      return;
    }
    setAssignLoading(true);
    try {
      await rolesApi.assign(id, selectedUserId);
      pushToast({ type: "success", message: "Role assigned successfully." });
      await loadRoleUsers(id);
      setSelectedUserId("");
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setAssignLoading(false);
    }
  };

  const handleUnassign = async () => {
    if (!id || !selectedUserId) {
      return;
    }
    setUnassignLoading(true);
    try {
      await rolesApi.unassign(id, selectedUserId);
      pushToast({ type: "success", message: "Role unassigned successfully." });
      await loadRoleUsers(id);
      setSelectedUserId("");
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setUnassignLoading(false);
    }
  };

  const canSubmitUserAction = useMemo(() => Boolean(id && selectedUserId.trim()), [id, selectedUserId]);

  const groupedPermissions = useMemo(() => {
    const grouped = new Map<string, string[]>();
    permissionCodes.forEach((code) => {
      const prefix = code.includes(".") ? code.split(".")[0] : "other";
      const list = grouped.get(prefix) ?? [];
      list.push(code);
      grouped.set(prefix, list);
    });
    return Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [permissionCodes]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Spinner />
      </div>
    );
  }

  if (!role) {
    return (
      <div className="space-y-4">
        <PageHeader title="Role not found" subtitle="The selected role could not be loaded." />
        <Button variant="secondary" onClick={() => navigate("/administration/roles")}>
          Back to Roles
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title={role.name}
        subtitle={role.description || "No description"}
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Administration", to: "/administration" },
          { label: "Roles", to: "/administration/roles" },
          { label: role.name }
        ]}
        actions={
          <Button variant="secondary" onClick={() => navigate("/administration/roles")}>
            Back
          </Button>
        }
      />

      <section className="rounded-md border border-border bg-surface p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text">Permissions</h3>
          {canWrite ? (
            <Button
              onClick={() => {
                setPermissionsText(permissionCodes.join("\n"));
                setIsPermissionsModalOpen(true);
              }}
            >
              Replace Permissions
            </Button>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {groupedPermissions.length === 0 ? (
            <span className="text-sm text-muted">No permission codes assigned.</span>
          ) : (
            groupedPermissions.map(([group, codes]) => (
              <div key={group} className="w-full rounded-md border border-border bg-bg p-2">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{group}</p>
                <div className="flex flex-wrap gap-2">
                  {codes.map((code) => (
                    <span key={code} className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text">
                      {code}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {canWrite ? (
        <section className="rounded-md border border-border bg-surface p-4 shadow-sm">
          <h3 className="mb-3 text-lg font-semibold text-text">Assign / Unassign User</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Input
              label="Search user"
              placeholder="Type name or email"
              value={userSearch}
              onChange={(event) => setUserSearch(event.target.value)}
            />
            <Select
              label="Select user"
              value={selectedUserId}
              onChange={(event) => setSelectedUserId(event.target.value)}
              options={[
                { label: loadingUserOptions ? "Loading..." : "Choose a user", value: "" },
                ...userOptions.map((user) => ({
                  value: user.id,
                  label: `${user.fullName} (${user.email})`
                }))
              ]}
            />
            <div className="flex items-end gap-2">
              <Button onClick={handleAssign} loading={assignLoading} disabled={!canSubmitUserAction || unassignLoading}>
                Assign
              </Button>
              <Button
                variant="secondary"
                onClick={handleUnassign}
                loading={unassignLoading}
                disabled={!canSubmitUserAction || assignLoading}
              >
                Unassign
              </Button>
            </div>
          </div>
          <div className="mt-4">
            <h4 className="mb-2 text-sm font-semibold text-text">Assigned users</h4>
            {assignedUsers.length === 0 ? (
              <p className="text-sm text-muted">No users are currently assigned to this role.</p>
            ) : (
              <ul className="space-y-2">
                {assignedUsers.map((user) => (
                  <li key={user.id} className="rounded-md border border-border bg-bg px-3 py-2 text-sm text-text">
                    <span className="font-medium">{user.fullName}</span>
                    <span className="ml-2 text-muted">{user.email}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}

      <Modal
        title="Replace Permissions"
        isOpen={isPermissionsModalOpen}
        onClose={() => setIsPermissionsModalOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsPermissionsModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleReplacePermissions} loading={savingPermissions}>
              Save
            </Button>
          </>
        }
      >
        <Textarea
          label="Permission Codes (one per line)"
          className="min-h-48"
          value={permissionsText}
          onChange={(event) => setPermissionsText(event.target.value)}
        />
      </Modal>
    </div>
  );
}
