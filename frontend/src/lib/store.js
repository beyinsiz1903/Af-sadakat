import { create } from 'zustand';

export const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  tenant: JSON.parse(localStorage.getItem('tenant') || 'null'),
  token: localStorage.getItem('token') || null,
  activePropertyId: localStorage.getItem('activePropertyId') || null,
  
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
    localStorage.removeItem('activePropertyId');
    set({ token: null, user: null, tenant: null, activePropertyId: null });
  },
  
  updateTenant: (tenant) => {
    localStorage.setItem('tenant', JSON.stringify(tenant));
    set({ tenant });
  },
  
  setActiveProperty: (propertyId) => {
    const prev = get().activePropertyId;
    if (propertyId) {
      localStorage.setItem('activePropertyId', propertyId);
    } else {
      localStorage.removeItem('activePropertyId');
    }
    set({ activePropertyId: propertyId });
    // Trigger refetch when property changes (components listen via queryKey)
    if (prev && prev !== propertyId) {
      window.dispatchEvent(new CustomEvent('property-changed', { detail: { propertyId } }));
    }
  },
  
  isAuthenticated: () => !!get().token,
}));

export const useUIStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
