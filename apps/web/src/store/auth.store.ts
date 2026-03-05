import { create } from "zustand";
import type { AppOrganization, AppRole, AppUser } from "@shared/types/auth";
import { authApi } from "@/services/auth.api";
import { HttpError } from "@/services/http";

type AuthState = {
  user: AppUser | null;
  organization: AppOrganization | null;
  roles: AppRole[];
  permissions: string[];
  isLoading: boolean;
  isAuthed: boolean;
  hasBootstrapped: boolean;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
  clearSession: () => void;
};

function clearState(state: AuthState): Pick<AuthState, "user" | "organization" | "roles" | "permissions" | "isAuthed"> {
  return {
    user: null,
    organization: null,
    roles: [],
    permissions: [],
    isAuthed: false
  };
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  organization: null,
  roles: [],
  permissions: [],
  isLoading: false,
  isAuthed: false,
  hasBootstrapped: false,

  async bootstrap() {
    if (get().isLoading) {
      return;
    }
    set({ isLoading: true });
    try {
      const response = await authApi.me();
      set({
        user: response.data.user,
        organization: response.data.organization,
        roles: response.data.roles,
        permissions: response.data.permissions,
        isAuthed: true,
        isLoading: false,
        hasBootstrapped: true
      });
    } catch (error) {
      if (!(error instanceof HttpError) || error.status !== 401) {
        // swallow non-auth bootstrap errors while leaving user unauthenticated
      }
      set({
        ...clearState(get()),
        isLoading: false,
        hasBootstrapped: true
      });
    }
  },

  async login(email: string, password: string) {
    set({ isLoading: true });
    const response = await authApi.login({ email, password });
    set({
      user: response.data.user,
      organization: response.data.organization,
      roles: response.data.roles,
      permissions: response.data.permissions,
      isAuthed: true,
      isLoading: false,
      hasBootstrapped: true
    });
  },

  async logout() {
    set({ isLoading: true });
    try {
      await authApi.logout();
    } finally {
      set({
        ...clearState(get()),
        isLoading: false,
        hasBootstrapped: true
      });
    }
  },

  async forgotPassword(email: string) {
    await authApi.forgotPassword({ email });
  },

  async resetPassword(token: string, newPassword: string) {
    await authApi.resetPassword({ token, newPassword });
  },

  clearSession() {
    set({
      ...clearState(get()),
      hasBootstrapped: true
    });
  }
}));
