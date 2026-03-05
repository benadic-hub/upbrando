import { useCallback, useEffect, useMemo, useState } from "react";
import type { AppUser } from "@shared/types/auth";
import type { ListMeta } from "@shared/types/api";
import { usersApi } from "@/services/users.api";
import { getErrorMessage } from "@/services/http";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { PageHeader } from "@/components/layout/PageHeader";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { Pagination } from "@/components/ui/Pagination";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";

const defaultMeta: ListMeta = {
  page: 1,
  pageSize: 10,
  total: 0,
  sortBy: "createdAt",
  sortDir: "desc"
};

type UserFormState = {
  email: string;
  fullName: string;
  password: string;
  status: "active" | "inactive" | "invited";
};

const emptyUserForm: UserFormState = {
  email: "",
  fullName: "",
  password: "",
  status: "active"
};

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
}

function statusTone(status: string): "success" | "warning" | "muted" {
  if (status === "active") {
    return "success";
  }
  if (status === "invited") {
    return "warning";
  }
  return "muted";
}

export function UsersPage() {
  const permissions = useAuthStore((state) => state.permissions);
  const pushToast = useUiStore((state) => state.pushToast);
  const canWrite = permissions.includes("users.write");

  const [rows, setRows] = useState<AppUser[]>([]);
  const [meta, setMeta] = useState<ListMeta>(defaultMeta);
  const [loading, setLoading] = useState(true);
  const [filtersVersion, setFiltersVersion] = useState(0);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<UserFormState>(emptyUserForm);
  const [savingCreate, setSavingCreate] = useState(false);

  const [editUser, setEditUser] = useState<AppUser | null>(null);
  const [editForm, setEditForm] = useState<Pick<UserFormState, "fullName" | "status">>({ fullName: "", status: "active" });
  const [savingEdit, setSavingEdit] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await usersApi.list({
        page: meta.page,
        pageSize: meta.pageSize,
        q: q || undefined,
        status: (status || undefined) as "active" | "inactive" | "invited" | undefined
      });
      setRows(response.data);
      setMeta(response.meta);
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  }, [filtersVersion, meta.page, meta.pageSize, pushToast, q, status]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const columns = useMemo(
    () => [
      {
        key: "fullName",
        header: "Name",
        render: (user: AppUser) => user.fullName
      },
      {
        key: "email",
        header: "Email",
        render: (user: AppUser) => user.email
      },
      {
        key: "status",
        header: "Status",
        render: (user: AppUser) => <Badge tone={statusTone(user.status)}>{user.status}</Badge>
      },
      {
        key: "lastLoginAt",
        header: "Last Login",
        render: (user: AppUser) => formatDate(user.lastLoginAt)
      },
      {
        key: "actions",
        header: "Actions",
        render: (user: AppUser) =>
          canWrite ? (
            <Button
              variant="secondary"
              onClick={() => {
                setEditUser(user);
                setEditForm({
                  fullName: user.fullName,
                  status: user.status as "active" | "inactive" | "invited"
                });
              }}
            >
              Edit
            </Button>
          ) : (
            <span className="text-muted">-</span>
          )
      }
    ],
    [canWrite]
  );

  const handleCreate = async () => {
    setSavingCreate(true);
    try {
      await usersApi.create({
        email: createForm.email,
        fullName: createForm.fullName,
        password: createForm.password || undefined,
        status: createForm.status
      });
      pushToast({ type: "success", message: "User created successfully." });
      setIsCreateOpen(false);
      setCreateForm(emptyUserForm);
      void loadUsers();
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setSavingCreate(false);
    }
  };

  const handleEdit = async () => {
    if (!editUser) {
      return;
    }
    setSavingEdit(true);
    try {
      await usersApi.update(editUser.id, {
        fullName: editForm.fullName,
        status: editForm.status
      });
      pushToast({ type: "success", message: "User updated successfully." });
      setEditUser(null);
      void loadUsers();
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setSavingEdit(false);
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Users"
        subtitle="Manage organization users."
        breadcrumbs={[
          { label: "Dashboard", to: "/dashboard" },
          { label: "Administration", to: "/administration" },
          { label: "Users" }
        ]}
        actions={
          canWrite ? (
            <Button
              onClick={() => {
                setCreateForm(emptyUserForm);
                setIsCreateOpen(true);
              }}
            >
              Create User
            </Button>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-3 rounded-md border border-border bg-surface p-4 shadow-sm md:grid-cols-3">
        <Input label="Search" value={q} placeholder="Search by name or email" onChange={(event) => setQ(event.target.value)} />
        <Select
          label="Status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          options={[
            { label: "All", value: "" },
            { label: "Active", value: "active" },
            { label: "Inactive", value: "inactive" },
            { label: "Invited", value: "invited" }
          ]}
        />
        <div className="flex items-end">
          <Button
            variant="secondary"
            onClick={() => {
              setMeta((prev) => ({ ...prev, page: 1 }));
              setFiltersVersion((prev) => prev + 1);
            }}
          >
            Apply Filters
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Spinner />
        </div>
      ) : (
        <Table columns={columns} rows={rows} rowKey={(user) => user.id} />
      )}

      <Pagination page={meta.page} pageSize={meta.pageSize} total={meta.total} onPageChange={(page) => setMeta((prev) => ({ ...prev, page }))} />

      <Modal
        title="Create User"
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} loading={savingCreate}>
              Create
            </Button>
          </>
        }
      >
        <Input label="Email" type="email" value={createForm.email} onChange={(event) => setCreateForm({ ...createForm, email: event.target.value })} />
        <Input label="Full Name" value={createForm.fullName} onChange={(event) => setCreateForm({ ...createForm, fullName: event.target.value })} />
        <Input
          label="Password (optional)"
          type="password"
          value={createForm.password}
          onChange={(event) => setCreateForm({ ...createForm, password: event.target.value })}
        />
        <Select
          label="Status"
          value={createForm.status}
          onChange={(event) => setCreateForm({ ...createForm, status: event.target.value as UserFormState["status"] })}
          options={[
            { label: "Active", value: "active" },
            { label: "Inactive", value: "inactive" },
            { label: "Invited", value: "invited" }
          ]}
        />
      </Modal>

      <Modal
        title="Edit User"
        isOpen={Boolean(editUser)}
        onClose={() => setEditUser(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditUser(null)}>
              Cancel
            </Button>
            <Button onClick={handleEdit} loading={savingEdit}>
              Save
            </Button>
          </>
        }
      >
        <Input label="Full Name" value={editForm.fullName} onChange={(event) => setEditForm({ ...editForm, fullName: event.target.value })} />
        <Select
          label="Status"
          value={editForm.status}
          onChange={(event) => setEditForm({ ...editForm, status: event.target.value as UserFormState["status"] })}
          options={[
            { label: "Active", value: "active" },
            { label: "Inactive", value: "inactive" },
            { label: "Invited", value: "invited" }
          ]}
        />
      </Modal>
    </div>
  );
}
