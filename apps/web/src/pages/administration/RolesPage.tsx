import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AppRole } from "@shared/types/auth";
import type { ListMeta } from "@shared/types/api";
import { rolesApi } from "@/services/roles.api";
import { getErrorMessage } from "@/services/http";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Table } from "@/components/ui/Table";
import { Pagination } from "@/components/ui/Pagination";
import { Spinner } from "@/components/ui/Spinner";

const defaultMeta: ListMeta = {
  page: 1,
  pageSize: 10,
  total: 0,
  sortBy: "createdAt",
  sortDir: "desc"
};

export function RolesPage() {
  const navigate = useNavigate();
  const permissions = useAuthStore((state) => state.permissions);
  const pushToast = useUiStore((state) => state.pushToast);
  const canWrite = permissions.includes("roles.write");

  const [rows, setRows] = useState<AppRole[]>([]);
  const [meta, setMeta] = useState<ListMeta>(defaultMeta);
  const [loading, setLoading] = useState(true);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleDescription, setNewRoleDescription] = useState("");
  const [savingCreate, setSavingCreate] = useState(false);

  const loadRoles = useCallback(async () => {
    setLoading(true);
    try {
      const response = await rolesApi.list({
        page: meta.page,
        pageSize: meta.pageSize
      });
      setRows(response.data);
      setMeta(response.meta);
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  }, [meta.page, meta.pageSize, pushToast]);

  useEffect(() => {
    void loadRoles();
  }, [loadRoles]);

  const columns = useMemo(
    () => [
      {
        key: "name",
        header: "Role Name",
        render: (role: AppRole) => role.name
      },
      {
        key: "description",
        header: "Description",
        render: (role: AppRole) => role.description || "-"
      },
      {
        key: "actions",
        header: "Actions",
        render: (role: AppRole) => (
          <Button variant="secondary" onClick={() => navigate(`/administration/roles/${role.id}`)}>
            View
          </Button>
        )
      }
    ],
    [navigate]
  );

  const handleCreateRole = async () => {
    setSavingCreate(true);
    try {
      await rolesApi.create({
        name: newRoleName,
        description: newRoleDescription || undefined
      });
      pushToast({ type: "success", message: "Role created successfully." });
      setIsCreateOpen(false);
      setNewRoleName("");
      setNewRoleDescription("");
      void loadRoles();
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setSavingCreate(false);
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Roles"
        subtitle="Manage organization roles and permissions."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Administration", to: "/administration" },
          { label: "Roles" }
        ]}
        actions={
          canWrite ? (
            <Button onClick={() => setIsCreateOpen(true)} variant="primary">
              Create Role
            </Button>
          ) : undefined
        }
      />

      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Spinner />
        </div>
      ) : (
        <Table columns={columns} rows={rows} rowKey={(role) => role.id} />
      )}

      <Pagination page={meta.page} pageSize={meta.pageSize} total={meta.total} onPageChange={(page) => setMeta((prev) => ({ ...prev, page }))} />

      <Modal
        title="Create Role"
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button loading={savingCreate} onClick={handleCreateRole}>
              Create
            </Button>
          </>
        }
      >
        <Input label="Role name" value={newRoleName} onChange={(event) => setNewRoleName(event.target.value)} />
        <Input
          label="Description"
          value={newRoleDescription}
          onChange={(event) => setNewRoleDescription(event.target.value)}
        />
      </Modal>
    </div>
  );
}
