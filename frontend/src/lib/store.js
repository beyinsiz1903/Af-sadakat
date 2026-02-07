import { create } from 'zustand';

export const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  tenant: JSON.parse(localStorage.getItem('tenant') || 'null'),
  token: localStorage.getItem('token') || null,
  
  login: (token, user, tenant) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('tenant', JSON.stringify(tenant));
    set({ token, user, tenant });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('tenant');
    set({ token: null, user: null, tenant: null });
  },
  
  updateTenant: (tenant) => {
    localStorage.setItem('tenant', JSON.stringify(tenant));
    set({ tenant });
  },
  
  isAuthenticated: () => !!get().token,
}));

export const useUIStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
