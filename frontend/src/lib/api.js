import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' }
});

// Add auth token and X-Property-Id to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Inject X-Property-Id for property-scoped endpoints
  const propertyId = localStorage.getItem('activePropertyId');
  if (propertyId) {
    config.headers['X-Property-Id'] = propertyId;
  }
  return config;
});

// Handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('tenant');
      if (!window.location.pathname.startsWith('/g/') && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

// Tenant
export const tenantAPI = {
  get: (slug) => api.get(`/tenants/${slug}`),
  update: (slug, data) => api.patch(`/tenants/${slug}`, data),
  updateLoyaltyRules: (slug, data) => api.patch(`/tenants/${slug}/loyalty-rules`, data),
  stats: (slug) => api.get(`/tenants/${slug}/stats`),
  seed: () => api.post('/seed'),
};

// Users
export const usersAPI = {
  list: (slug) => api.get(`/tenants/${slug}/users`),
  create: (slug, data) => api.post(`/tenants/${slug}/users`, data),
};

// Departments
export const departmentsAPI = {
  list: (slug) => api.get(`/tenants/${slug}/departments`),
  create: (slug, data) => api.post(`/tenants/${slug}/departments`, data),
  delete: (slug, id) => api.delete(`/tenants/${slug}/departments/${id}`),
};

// Service Categories
export const serviceCategoriesAPI = {
  list: (slug) => api.get(`/tenants/${slug}/service-categories`),
  create: (slug, data) => api.post(`/tenants/${slug}/service-categories`, data),
};

// Rooms
export const roomsAPI = {
  list: (slug) => api.get(`/tenants/${slug}/rooms`),
  create: (slug, data) => api.post(`/tenants/${slug}/rooms`, data),
  delete: (slug, id) => api.delete(`/tenants/${slug}/rooms/${id}`),
};

// Requests
export const requestsAPI = {
  list: (slug, params) => api.get(`/tenants/${slug}/requests`, { params }),
  update: (slug, id, data) => api.patch(`/tenants/${slug}/requests/${id}`, data),
  rate: (slug, id, data) => api.post(`/tenants/${slug}/requests/${id}/rate`, data),
};

// Tables
export const tablesAPI = {
  list: (slug) => api.get(`/tenants/${slug}/tables`),
  create: (slug, data) => api.post(`/tenants/${slug}/tables`, data),
  delete: (slug, id) => api.delete(`/tenants/${slug}/tables/${id}`),
};

// Menu
export const menuAPI = {
  listCategories: (slug) => api.get(`/tenants/${slug}/menu-categories`),
  createCategory: (slug, data) => api.post(`/tenants/${slug}/menu-categories`, data),
  deleteCategory: (slug, id) => api.delete(`/tenants/${slug}/menu-categories/${id}`),
  listItems: (slug, params) => api.get(`/tenants/${slug}/menu-items`, { params }),
  createItem: (slug, data) => api.post(`/tenants/${slug}/menu-items`, data),
  updateItem: (slug, id, data) => api.patch(`/tenants/${slug}/menu-items/${id}`, data),
  deleteItem: (slug, id) => api.delete(`/tenants/${slug}/menu-items/${id}`),
};

// Orders
export const ordersAPI = {
  list: (slug, params) => api.get(`/tenants/${slug}/orders`, { params }),
  updateStatus: (slug, id, data) => api.patch(`/tenants/${slug}/orders/${id}`, data),
};

// Contacts
export const contactsAPI = {
  list: (slug, params) => api.get(`/tenants/${slug}/contacts`, { params }),
  get: (slug, id) => api.get(`/tenants/${slug}/contacts/${id}`),
  update: (slug, id, data) => api.patch(`/tenants/${slug}/contacts/${id}`, data),
  timeline: (slug, id) => api.get(`/tenants/${slug}/contacts/${id}/timeline`),
};

// Conversations
export const conversationsAPI = {
  list: (slug, params) => api.get(`/tenants/${slug}/conversations`, { params }),
  update: (slug, id, data) => api.patch(`/tenants/${slug}/conversations/${id}`, data),
};

// AI
export const aiAPI = {
  suggestReply: (slug, data) => api.post(`/tenants/${slug}/ai/suggest-reply`, data),
};

// Loyalty
export const loyaltyAPI = {
  accounts: (slug) => api.get(`/tenants/${slug}/loyalty/accounts`),
  ledger: (slug, accountId) => api.get(`/tenants/${slug}/loyalty/${accountId}/ledger`),
};

// Guest APIs (no auth required)
export const guestAPI = {
  roomInfo: (slug, code) => api.get(`/g/${slug}/room/${code}/info`),
  roomRequests: (slug, code) => api.get(`/g/${slug}/room/${code}/requests`),
  createRequest: (slug, code, data) => api.post(`/g/${slug}/room/${code}/requests`, data),
  tableInfo: (slug, code) => api.get(`/g/${slug}/table/${code}/info`),
  tableOrders: (slug, code) => api.get(`/g/${slug}/table/${code}/orders`),
  createOrder: (slug, code, data) => api.post(`/g/${slug}/table/${code}/orders`, data),
  startChat: (slug) => api.post(`/g/${slug}/chat/start`),
  chatMessages: (slug, convId) => api.get(`/g/${slug}/chat/${convId}/messages`),
  sendMessage: (slug, convId, data) => api.post(`/g/${slug}/chat/${convId}/messages`, data),
  joinLoyalty: (slug, data) => api.post(`/g/${slug}/loyalty/join`, data),
};

// ============ V2 APIs ============

// Properties V2
export const propertiesAPI = {
  list: (slug) => api.get(`/v2/properties/tenants/${slug}/properties`),
  create: (slug, data) => api.post(`/v2/properties/tenants/${slug}/properties`, data),
  get: (slug, id) => api.get(`/v2/properties/tenants/${slug}/properties/${id}`),
  update: (slug, id, data) => api.patch(`/v2/properties/tenants/${slug}/properties/${id}`, data),
  deactivate: (slug, id) => api.post(`/v2/properties/tenants/${slug}/properties/${id}/deactivate`),
  activate: (slug, id) => api.post(`/v2/properties/tenants/${slug}/properties/${id}/activate`),
};

// Offers V2
export const offersAPI = {
  list: (slug, params) => api.get(`/v2/offers/tenants/${slug}/offers`, { params }),
  create: (slug, data) => api.post(`/v2/offers/tenants/${slug}/offers`, data),
  get: (slug, id) => api.get(`/v2/offers/tenants/${slug}/offers/${id}`),
  update: (slug, id, data) => api.patch(`/v2/offers/tenants/${slug}/offers/${id}`, data),
  send: (slug, id) => api.post(`/v2/offers/tenants/${slug}/offers/${id}/send`),
  cancel: (slug, id) => api.post(`/v2/offers/tenants/${slug}/offers/${id}/cancel`),
  createPaymentLink: (slug, id) => api.post(`/v2/offers/tenants/${slug}/offers/${id}/create-payment-link`),
};

// Payments V2 (public - no auth)
export const paymentsAPI = {
  getPaymentData: (linkId) => api.get(`/v2/payments/pay/${linkId}`),
  checkout: (linkId) => api.post(`/v2/payments/pay/${linkId}/checkout`),
  mockSucceed: (data) => api.post(`/v2/payments/webhook/mock/succeed`, data),
  mockFail: (data) => api.post(`/v2/payments/webhook/mock/fail`, data),
};

// Reservations V2
export const reservationsAPI = {
  list: (slug, params) => api.get(`/v2/reservations/tenants/${slug}/reservations`, { params }),
  get: (slug, id) => api.get(`/v2/reservations/tenants/${slug}/reservations/${id}`),
  cancel: (slug, id) => api.post(`/v2/reservations/tenants/${slug}/reservations/${id}/cancel`),
  exportCSV: (slug, params) => api.get(`/v2/reservations/tenants/${slug}/reservations/export/csv`, {
    params, responseType: 'blob'
  }),
};

// Inbox V2 - create offer from conversation
export const inboxOffersAPI = {
  createFromConversation: (slug, convId, data) =>
    api.post(`/v2/inbox/tenants/${slug}/conversations/${convId}/create-offer`, data),
};

// AI Sales V2
export const aiSalesAPI = {
  // Settings
  getSettings: (slug) => api.get(`/v2/ai-sales/tenants/${slug}/settings`),
  updateSettings: (slug, propertyId, data) =>
    api.put(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/settings`, data),

  // Room Rates
  listRoomRates: (slug, propertyId) =>
    api.get(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/room-rates`),
  createRoomRate: (slug, propertyId, data) =>
    api.post(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/room-rates`, data),
  updateRoomRate: (slug, propertyId, rateId, data) =>
    api.patch(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/room-rates/${rateId}`, data),
  deleteRoomRate: (slug, propertyId, rateId) =>
    api.delete(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/room-rates/${rateId}`),

  // Discount Rules
  getDiscountRules: (slug, propertyId) =>
    api.get(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/discount-rules`),
  updateDiscountRules: (slug, propertyId, data) =>
    api.put(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/discount-rules`, data),

  // Policies
  getPolicies: (slug, propertyId) =>
    api.get(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/policies`),
  updatePolicies: (slug, propertyId, data) =>
    api.put(`/v2/ai-sales/tenants/${slug}/properties/${propertyId}/policies`, data),

  // Stats
  getStats: (slug) => api.get(`/v2/ai-sales/tenants/${slug}/stats`),

  // Manual AI trigger
  triggerAI: (slug, convId) =>
    api.post(`/v2/ai-sales/tenants/${slug}/conversations/${convId}/ai-respond`),

  // Session info
  getSession: (slug, convId) =>
    api.get(`/v2/ai-sales/tenants/${slug}/conversations/${convId}/session`),
};
