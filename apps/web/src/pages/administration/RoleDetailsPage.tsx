import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { AppRole } from "@shared/types/auth";
import { rolesApi } from "@/services/roles.api";
import { getErrorMessage } from "@/services/http";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
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

  const [isPermissionsModalOpen, setIsPermissionsModalOpen] = useState(false);
  const [permissionsText, setPermissionsText] = useState("");
  const [savingPermissions, setSavingPermissions] = useState(false);

  const [userIdInput, setUserIdInput] = useState("");
  const [assignLoading, setAssignLoading] = useState(false);
  const [unassignLoading, setUnassignLoading] = useState(false);

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
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  }, [id, navigate, pushToast]);

  useEffect(() => {
    void loadRole();
  }, [loadRole]);

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
    if (!id || !userIdInput) {
      return;
    }
    setAssignLoading(true);
    try {
      await rolesApi.assign(id, userIdInput);
      pushToast({ type: "success", message: "Role assigned successfully." });
      setUserIdInput("");
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setAssignLoading(false);
    }
  };

  const handleUnassign = async () => {
    if (!id || !userIdInput) {
      return;
    }
    setUnassignLoading(true);
    try {
      await rolesApi.unassign(id, userIdInput);
      pushToast({ type: "success", message: "Role unassigned successfully." });
      setUserIdInput("");
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setUnassignLoading(false);
    }
  };

  const canSubmitUserAction = useMemo(() => Boolean(id && userIdInput.trim()), [id, userIdInput]);

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
          {permissionCodes.length === 0 ? (
            <span className="text-sm text-muted">No permission codes assigned.</span>
          ) : (
            permissionCodes.map((code) => (
              <span key={code} className="rounded-md border border-border bg-bg px-2 py-1 text-xs text-text">
                {code}
              </span>
            ))
          )}
        </div>
      </section>

      {canWrite ? (
        <section className="rounded-md border border-border bg-surface p-4 shadow-sm">
          <h3 className="mb-3 text-lg font-semibold text-text">Assign / Unassign User</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Input label="User ID" value={userIdInput} onChange={(event) => setUserIdInput(event.target.value)} />
            <div className="flex items-end gap-2 md:col-span-2">
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
