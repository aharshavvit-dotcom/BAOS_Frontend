/**
 * UI store — modals, toasts, theme.
 */
import { create } from 'zustand';
import type { Toast } from '@/types';

interface UIState {
  toasts: Toast[];
  sidebarOpen: boolean;
  profileDropdownOpen: boolean;

  showToast: (message: string, type?: Toast['type']) => void;
  removeToast: (id: string) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setProfileDropdownOpen: (open: boolean) => void;
}

let toastId = 0;

export const useUIStore = create<UIState>((set) => ({
  toasts: [],
  sidebarOpen: true,
  profileDropdownOpen: false,

  showToast: (message, type = 'info') => {
    const id = `toast-${++toastId}`;
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }));
    // Auto-remove after 4 seconds
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 4000);
  },

  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setProfileDropdownOpen: (open) => set({ profileDropdownOpen: open }),
}));
