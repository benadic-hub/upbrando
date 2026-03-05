import { create } from "zustand";

export type ToastItem = {
  id: string;
  type: "success" | "error" | "info";
  message: string;
};

type UiState = {
  sidebarCollapsed: boolean;
  toasts: ToastItem[];
  toggleSidebar: () => void;
  pushToast: (toast: Omit<ToastItem, "id">) => void;
  removeToast: (id: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  sidebarCollapsed: false,
  toasts: [],

  toggleSidebar() {
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
  },

  pushToast(toast) {
    const id = crypto.randomUUID();
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
  },

  removeToast(id) {
    set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }));
  }
}));
