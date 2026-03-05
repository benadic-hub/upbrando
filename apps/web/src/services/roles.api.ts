import type { ApiResponse, ListResponse } from "@shared/types/api";
import type { AppRole, AppUser } from "@shared/types/auth";
import { http } from "./http";

export type RolesListQuery = {
  page?: number;
  pageSize?: number;
  sortBy?: "createdAt" | "name";
  sortDir?: "asc" | "desc";
};

export type CreateRoleInput = {
  name: string;
  description?: string;
};

export type UpdateRoleInput = {
  name?: string;
  description?: string | null;
};

export const rolesApi = {
  list(query: RolesListQuery) {
    return http.get<ListResponse<AppRole>>("/roles", query);
  },
  create(input: CreateRoleInput) {
    return http.post<ApiResponse<AppRole>, CreateRoleInput>("/roles", input);
  },
  update(id: string, input: UpdateRoleInput) {
    return http.patch<ApiResponse<AppRole>, UpdateRoleInput>(`/roles/${id}`, input);
  },
  permissions(id: string) {
    return http.get<ApiResponse<{ permissionCodes: string[] }>>(`/roles/${id}/permissions`);
  },
  users(id: string, query?: { page?: number; pageSize?: number; q?: string }) {
    return http.get<ListResponse<AppUser>>(`/roles/${id}/users`, query);
  },
  replacePermissions(id: string, permissionCodes: string[]) {
    return http.post<ApiResponse<{ ok: true }>, { permissionCodes: string[] }>(`/roles/${id}/permissions`, {
      permissionCodes
    });
  },
  assign(id: string, userId: string) {
    return http.post<ApiResponse<{ ok: true }>, { userId: string }>(`/roles/${id}/assign`, { userId });
  },
  unassign(id: string, userId: string) {
    return http.post<ApiResponse<{ ok: true }>, { userId: string }>(`/roles/${id}/unassign`, { userId });
  }
};
