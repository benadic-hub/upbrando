import type { ApiResponse, ListResponse } from "@shared/types/api";
import type { AppUser } from "@shared/types/auth";
import { http } from "./http";

export type UsersListQuery = {
  page?: number;
  pageSize?: number;
  q?: string;
  status?: "active" | "inactive" | "invited";
  sortBy?: "createdAt" | "fullName" | "email" | "status";
  sortDir?: "asc" | "desc";
};

export type CreateUserInput = {
  email: string;
  fullName: string;
  password?: string;
  status?: "active" | "inactive" | "invited";
};

export type UpdateUserInput = {
  fullName?: string;
  status?: "active" | "inactive" | "invited";
};

export const usersApi = {
  list(query: UsersListQuery) {
    return http.get<ListResponse<AppUser>>("/users", query);
  },
  create(input: CreateUserInput) {
    return http.post<ApiResponse<AppUser>, CreateUserInput>("/users", input);
  },
  update(id: string, input: UpdateUserInput) {
    return http.patch<ApiResponse<AppUser>, UpdateUserInput>(`/users/${id}`, input);
  }
};
