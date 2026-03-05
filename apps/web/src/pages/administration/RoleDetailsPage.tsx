import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { AppRole, AppUser } from "@shared/types/auth";
import { ALL_PERMISSIONS, PERMISSION_GROUPS, groupPermission } from "@shared/constants/permissions";
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

function prettyGroupName(group: string): string {
  if (!group) {
    return "Misc";
  }
  return `${group.charAt(0).toUpperCase()}${group.slice(1)}`;
}

function parsePermissionText(rawText: string) {
  const codes = Array.from(
    new Set(
      rawText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
    )
  );
  const unknownCodes = codes.filter((code) => !ALL_PERMISSIONS.includes(code));
  return { codes, unknownCodes };
}

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
  const [permissionSearch, setPermissionSearch] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() =>
    PERMISSION_GROUPS.reduce<Record<string, boolean>>((accumulator, item) => {
      accumulator[item.group] = true;
      return accumulator;
    }, {})
  );
  const [draftPermissionCodes, setDraftPermissionCodes] = useState<Set<string>>(new Set());
  const [permissionsText, setPermissionsText] = useState("");
  const [advancedMode, setAdvancedMode] = useState(false);
  const [confirmEmptySelection, setConfirmEmptySelection] = useState(false);
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

  const currentPermissionSet = useMemo(() => new Set(permissionCodes), [permissionCodes]);

  const selectedPermissionCodes = useMemo(() => Array.from(draftPermissionCodes).sort(), [draftPermissionCodes]);

  const { addedPermissions, removedPermissions } = useMemo(() => {
    const added = selectedPermissionCodes.filter((code) => !currentPermissionSet.has(code));
    const removed = Array.from(currentPermissionSet).filter((code) => !draftPermissionCodes.has(code)).sort();
    return { addedPermissions: added, removedPermissions: removed };
  }, [currentPermissionSet, draftPermissionCodes, selectedPermissionCodes]);

  const hasPermissionChanges = addedPermissions.length > 0 || removedPermissions.length > 0;
  const isDangerousEmptySave = selectedPermissionCodes.length === 0 && currentPermissionSet.size > 0;

  const visiblePermissionGroups = useMemo(() => {
    const needle = permissionSearch.trim().toLowerCase();
    if (!needle) {
      return PERMISSION_GROUPS;
    }
    return PERMISSION_GROUPS.map((group) => {
      if (group.group.toLowerCase().includes(needle)) {
        return group;
      }
      return {
        ...group,
        codes: group.codes.filter((code) => code.toLowerCase().includes(needle))
      };
    }).filter((group) => group.codes.length > 0);
  }, [permissionSearch]);

  const openPermissionsModal = () => {
    const sortedCurrent = [...permissionCodes].sort();
    setDraftPermissionCodes(new Set(sortedCurrent));
    setPermissionsText(sortedCurrent.join("\n"));
    setPermissionSearch("");
    setAdvancedMode(false);
    setConfirmEmptySelection(false);
    setIsPermissionsModalOpen(true);
  };

  const applyPermissionTextToSelection = useCallback(
    (showUnknownToast: boolean) => {
      const parsed = parsePermissionText(permissionsText);
      setDraftPermissionCodes(new Set(parsed.codes));
      if (showUnknownToast && parsed.unknownCodes.length > 0) {
        pushToast({
          type: "info",
          message: `Included ${parsed.unknownCodes.length} custom permission code(s) not in catalog.`
        });
      }
      return parsed.codes;
    },
    [permissionsText, pushToast]
  );

  const togglePermissionCode = (code: string) => {
    setDraftPermissionCodes((previous) => {
      const next = new Set(previous);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const selectAllInGroup = (codes: string[]) => {
    setDraftPermissionCodes((previous) => {
      const next = new Set(previous);
      codes.forEach((code) => next.add(code));
      return next;
    });
  };

  const clearGroup = (codes: string[]) => {
    setDraftPermissionCodes((previous) => {
      const next = new Set(previous);
      codes.forEach((code) => next.delete(code));
      return next;
    });
  };

  const selectAllPermissions = () => setDraftPermissionCodes(new Set(ALL_PERMISSIONS));
  const clearAllPermissions = () => setDraftPermissionCodes(new Set());
  const resetToCurrentPermissions = () => setDraftPermissionCodes(new Set(permissionCodes));

  const toggleGroupExpanded = (group: string) => {
    setExpandedGroups((previous) => ({
      ...previous,
      [group]: !(previous[group] ?? true)
    }));
  };

  const handleToggleAdvancedMode = () => {
    if (advancedMode) {
      applyPermissionTextToSelection(true);
      setAdvancedMode(false);
      return;
    }
    setPermissionsText(selectedPermissionCodes.join("\n"));
    setAdvancedMode(true);
  };

  const handlePermissionTextChange = (value: string) => {
    setPermissionsText(value);
    if (advancedMode) {
      const parsed = parsePermissionText(value);
      setDraftPermissionCodes(new Set(parsed.codes));
    }
  };

  const handleReplacePermissions = async () => {
    if (!id) {
      return;
    }

    let finalCodes = selectedPermissionCodes;
    if (advancedMode) {
      finalCodes = Array.from(new Set(applyPermissionTextToSelection(true))).sort();
    }

    const added = finalCodes.filter((code) => !currentPermissionSet.has(code));
    const removed = Array.from(currentPermissionSet).filter((code) => !finalCodes.includes(code));
    const hasChanges = added.length > 0 || removed.length > 0;
    if (!hasChanges) {
      pushToast({ type: "info", message: "No permission changes to save." });
      return;
    }

    if (finalCodes.length === 0 && currentPermissionSet.size > 0 && !confirmEmptySelection) {
      pushToast({
        type: "error",
        message: "Confirm removal of all permissions before saving."
      });
      return;
    }

    setSavingPermissions(true);
    try {
      await rolesApi.replacePermissions(id, finalCodes.sort());
      pushToast({ type: "success", message: "Permissions updated successfully." });
      setIsPermissionsModalOpen(false);
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
      const group = groupPermission(code);
      const list = grouped.get(group) ?? [];
      list.push(code);
      grouped.set(group, list);
    });
    return Array.from(grouped.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([group, codes]) => [group, codes.sort()] as const);
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
          {canWrite ? <Button onClick={openPermissionsModal}>Replace Permissions</Button> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {groupedPermissions.length === 0 ? (
            <span className="text-sm text-muted">No permission codes assigned.</span>
          ) : (
            groupedPermissions.map(([group, codes]) => (
              <div key={group} className="w-full rounded-md border border-border bg-bg p-2">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{prettyGroupName(group)}</p>
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
            <Button variant="secondary" onClick={() => setIsPermissionsModalOpen(false)} disabled={savingPermissions}>
              Cancel
            </Button>
            <Button
              onClick={handleReplacePermissions}
              loading={savingPermissions}
              disabled={!hasPermissionChanges || (isDangerousEmptySave && !confirmEmptySelection)}
            >
              Save
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={selectAllPermissions} disabled={advancedMode}>
              Select all
            </Button>
            <Button variant="secondary" onClick={clearAllPermissions} disabled={advancedMode}>
              Clear all
            </Button>
            <Button variant="secondary" onClick={resetToCurrentPermissions} disabled={advancedMode}>
              Reset to current
            </Button>
            <Button variant="secondary" onClick={handleToggleAdvancedMode}>
              {advancedMode ? "Use checklist mode" : "Edit as text"}
            </Button>
          </div>

          {advancedMode ? (
            <Textarea
              label="Permission Codes (one per line)"
              className="min-h-48"
              value={permissionsText}
              onChange={(event) => handlePermissionTextChange(event.target.value)}
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <section className="rounded-md border border-border bg-bg p-3">
                <Input
                  label="Search permissions"
                  placeholder="Search group or code"
                  value={permissionSearch}
                  onChange={(event) => setPermissionSearch(event.target.value)}
                />
                <div className="mt-3 max-h-80 space-y-3 overflow-auto pr-1">
                  {visiblePermissionGroups.length === 0 ? (
                    <p className="text-sm text-muted">No permissions match your search.</p>
                  ) : (
                    visiblePermissionGroups.map((group) => {
                      const expanded = expandedGroups[group.group] ?? true;
                      return (
                        <div key={group.group} className="rounded-md border border-border bg-surface p-2">
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <button
                              type="button"
                              className="text-sm font-semibold text-text"
                              onClick={() => toggleGroupExpanded(group.group)}
                            >
                              {expanded ? "▾" : "▸"} {prettyGroupName(group.group)}
                            </button>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="secondary"
                                className="h-7 px-2 text-xs"
                                onClick={() => selectAllInGroup(group.codes)}
                              >
                                Select group
                              </Button>
                              <Button
                                variant="secondary"
                                className="h-7 px-2 text-xs"
                                onClick={() => clearGroup(group.codes)}
                              >
                                Clear group
                              </Button>
                            </div>
                          </div>
                          {expanded ? (
                            <div className="space-y-1">
                              {group.codes.map((code) => (
                                <label key={code} className="flex items-center gap-2 text-sm text-text">
                                  <input
                                    type="checkbox"
                                    checked={draftPermissionCodes.has(code)}
                                    onChange={() => togglePermissionCode(code)}
                                  />
                                  <span>{code}</span>
                                </label>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      );
                    })
                  )}
                </div>
              </section>

              <section className="rounded-md border border-border bg-bg p-3">
                <h4 className="text-sm font-semibold text-text">Selected permissions ({selectedPermissionCodes.length})</h4>
                <div className="mt-2 max-h-28 overflow-auto rounded-md border border-border bg-surface p-2 text-xs text-text">
                  {selectedPermissionCodes.length ? selectedPermissionCodes.join(", ") : "None selected"}
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md border border-border bg-surface p-2">
                    Current: <span className="font-semibold">{currentPermissionSet.size}</span>
                  </div>
                  <div className="rounded-md border border-border bg-surface p-2">
                    Selected: <span className="font-semibold">{selectedPermissionCodes.length}</span>
                  </div>
                  <div className="rounded-md border border-border bg-surface p-2">
                    Added: <span className="font-semibold text-green-600">{addedPermissions.length}</span>
                  </div>
                  <div className="rounded-md border border-border bg-surface p-2">
                    Removed: <span className="font-semibold text-red-600">{removedPermissions.length}</span>
                  </div>
                </div>

                <div className="mt-3 space-y-2 text-xs">
                  <div>
                    <p className="mb-1 font-semibold text-green-700">Added</p>
                    <div className="max-h-16 overflow-auto rounded-md border border-green-200 bg-green-50 p-2 text-green-800">
                      {addedPermissions.length ? addedPermissions.join(", ") : "None"}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 font-semibold text-red-700">Removed</p>
                    <div className="max-h-16 overflow-auto rounded-md border border-red-200 bg-red-50 p-2 text-red-800">
                      {removedPermissions.length ? removedPermissions.join(", ") : "None"}
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}

          {isDangerousEmptySave ? (
            <label className="flex items-start gap-2 rounded-md border border-red-300 bg-red-50 p-2 text-sm text-red-800">
              <input
                type="checkbox"
                checked={confirmEmptySelection}
                onChange={(event) => setConfirmEmptySelection(event.target.checked)}
              />
              <span>I understand this will remove all permissions from this role.</span>
            </label>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
