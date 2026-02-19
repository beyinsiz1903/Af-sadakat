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

// Guest Services V2
export const guestServicesAPI = {
  // Guest-facing (no auth)
  hotelInfo: (slug) => api.get(`/v2/guest-services/g/${slug}/hotel-info`),
  roomServiceMenu: (slug) => api.get(`/v2/guest-services/g/${slug}/room-service-menu`),
  createRoomServiceOrder: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/room-service-order`, data),
  createSpaBooking: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/spa-booking`, data),
  createTransportRequest: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/transport-request`, data),
  createWakeupCall: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/wakeup-call`, data),
  createLaundryRequest: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/laundry-request`, data),
  createMinibarOrder: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/minibar-order`, data),
  submitSurvey: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/survey`, data),
  getMyOrders: (slug, code) => api.get(`/v2/guest-services/g/${slug}/room/${code}/my-orders`),
  getMyBookings: (slug, code) => api.get(`/v2/guest-services/g/${slug}/room/${code}/my-bookings`),
  getAnnouncements: (slug) => api.get(`/v2/guest-services/g/${slug}/announcements`),
  getSpaServices: (slug) => api.get(`/v2/guest-services/g/${slug}/spa-services`),
  getActivities: (slug) => api.get(`/v2/guest-services/g/${slug}/activities`),
  getActiveServices: (slug) => api.get(`/v2/guest-services/g/${slug}/active-services`),
  getRestaurants: (slug) => api.get(`/v2/guest-services/g/${slug}/restaurants`),
  checkAvailability: (slug, restaurantId, params) => api.get(`/v2/guest-services/g/${slug}/restaurants/${restaurantId}/availability`, { params }),
  createRestaurantReservation: (slug, code, data) => api.post(`/v2/guest-services/g/${slug}/room/${code}/restaurant-reservation`, data),
  getMyReservations: (slug, code) => api.get(`/v2/guest-services/g/${slug}/room/${code}/my-reservations`),
  // Admin
  getHotelInfoAdmin: (slug) => api.get(`/v2/guest-services/tenants/${slug}/hotel-info`),
  updateHotelInfo: (slug, data) => api.put(`/v2/guest-services/tenants/${slug}/hotel-info`, data),
  listSpaServicesAdmin: (slug) => api.get(`/v2/guest-services/tenants/${slug}/spa-services`),
  createSpaService: (slug, data) => api.post(`/v2/guest-services/tenants/${slug}/spa-services`, data),
  deleteSpaService: (slug, id) => api.delete(`/v2/guest-services/tenants/${slug}/spa-services/${id}`),
  listAnnouncementsAdmin: (slug) => api.get(`/v2/guest-services/tenants/${slug}/announcements`),
  createAnnouncement: (slug, data) => api.post(`/v2/guest-services/tenants/${slug}/announcements`, data),
  deleteAnnouncement: (slug, id) => api.delete(`/v2/guest-services/tenants/${slug}/announcements/${id}`),
  listSpaBookings: (slug, params) => api.get(`/v2/guest-services/tenants/${slug}/spa-bookings`, { params }),
  updateSpaBooking: (slug, id, data) => api.patch(`/v2/guest-services/tenants/${slug}/spa-bookings/${id}`, data),
  listTransportRequests: (slug, params) => api.get(`/v2/guest-services/tenants/${slug}/transport-requests`, { params }),
  updateTransportRequest: (slug, id, data) => api.patch(`/v2/guest-services/tenants/${slug}/transport-requests/${id}`, data),
  listLaundryRequests: (slug, params) => api.get(`/v2/guest-services/tenants/${slug}/laundry-requests`, { params }),
  updateLaundryRequest: (slug, id, data) => api.patch(`/v2/guest-services/tenants/${slug}/laundry-requests/${id}`, data),
  listWakeupCalls: (slug) => api.get(`/v2/guest-services/tenants/${slug}/wakeup-calls`),
  updateWakeupCall: (slug, id, data) => api.patch(`/v2/guest-services/tenants/${slug}/wakeup-calls/${id}`, data),
  listSurveys: (slug) => api.get(`/v2/guest-services/tenants/${slug}/surveys`),
  getSurveyStats: (slug) => api.get(`/v2/guest-services/tenants/${slug}/surveys/stats`),
  getServicesConfig: (slug) => api.get(`/v2/guest-services/tenants/${slug}/services-config`),
  updateServicesConfig: (slug, data) => api.put(`/v2/guest-services/tenants/${slug}/services-config`, data),
  // Admin restaurants
  listRestaurantsAdmin: (slug) => api.get(`/v2/guest-services/tenants/${slug}/restaurants`),
  createRestaurant: (slug, data) => api.post(`/v2/guest-services/tenants/${slug}/restaurants`, data),
  updateRestaurant: (slug, id, data) => api.patch(`/v2/guest-services/tenants/${slug}/restaurants/${id}`, data),
  deleteRestaurant: (slug, id) => api.delete(`/v2/guest-services/tenants/${slug}/restaurants/${id}`),
  listRestaurantReservations: (slug, params) => api.get(`/v2/guest-services/tenants/${slug}/restaurant-reservations`, { params }),
  updateRestaurantReservation: (slug, id, data) => api.patch(`/v2/guest-services/tenants/${slug}/restaurant-reservations/${id}`, data),
};

// Notifications V2
export const notificationsAPI = {
  list: (slug, params) => api.get(`/v2/notifications/tenants/${slug}/notifications`, { params }),
  markRead: (slug, id) => api.post(`/v2/notifications/tenants/${slug}/notifications/${id}/read`),
  markAllRead: (slug) => api.post(`/v2/notifications/tenants/${slug}/notifications/mark-all-read`),
  getUnreadCount: (slug) => api.get(`/v2/notifications/tenants/${slug}/notifications/unread-count`),
  create: (slug, data) => api.post(`/v2/notifications/tenants/${slug}/notifications`, data),
  getPreferences: (slug) => api.get(`/v2/notifications/tenants/${slug}/notification-preferences`),
  updatePreferences: (slug, data) => api.put(`/v2/notifications/tenants/${slug}/notification-preferences`, data),
};

// SLA V2
export const slaAPI = {
  listRules: (slug) => api.get(`/v2/sla/tenants/${slug}/sla-rules`),
  createRule: (slug, data) => api.post(`/v2/sla/tenants/${slug}/sla-rules`, data),
  updateRule: (slug, id, data) => api.patch(`/v2/sla/tenants/${slug}/sla-rules/${id}`, data),
  deleteRule: (slug, id) => api.delete(`/v2/sla/tenants/${slug}/sla-rules/${id}`),
  listBreaches: (slug, params) => api.get(`/v2/sla/tenants/${slug}/sla-breaches`, { params }),
  getStats: (slug) => api.get(`/v2/sla/tenants/${slug}/sla-stats`),
  listAssignmentRules: (slug) => api.get(`/v2/sla/tenants/${slug}/assignment-rules`),
  createAssignmentRule: (slug, data) => api.post(`/v2/sla/tenants/${slug}/assignment-rules`, data),
  deleteAssignmentRule: (slug, id) => api.delete(`/v2/sla/tenants/${slug}/assignment-rules/${id}`),
  listResponseTemplates: (slug, params) => api.get(`/v2/sla/tenants/${slug}/response-templates`, { params }),
  createResponseTemplate: (slug, data) => api.post(`/v2/sla/tenants/${slug}/response-templates`, data),
  deleteResponseTemplate: (slug, id) => api.delete(`/v2/sla/tenants/${slug}/response-templates/${id}`),
};

// Housekeeping V2
export const housekeepingAPI = {
  getRoomStatus: (slug, params) => api.get(`/v2/housekeeping/tenants/${slug}/room-status`, { params }),
  updateRoomHKStatus: (slug, roomId, data) => api.patch(`/v2/housekeeping/tenants/${slug}/rooms/${roomId}/hk-status`, data),
  listChecklists: (slug) => api.get(`/v2/housekeeping/tenants/${slug}/checklists`),
  createChecklist: (slug, data) => api.post(`/v2/housekeeping/tenants/${slug}/checklists`, data),
  updateChecklist: (slug, id, data) => api.patch(`/v2/housekeeping/tenants/${slug}/checklists/${id}`, data),
  deleteChecklist: (slug, id) => api.delete(`/v2/housekeeping/tenants/${slug}/checklists/${id}`),
  listCleaningTasks: (slug, params) => api.get(`/v2/housekeeping/tenants/${slug}/cleaning-tasks`, { params }),
  createCleaningTask: (slug, data) => api.post(`/v2/housekeeping/tenants/${slug}/cleaning-tasks`, data),
  updateCleaningTask: (slug, id, data) => api.patch(`/v2/housekeeping/tenants/${slug}/cleaning-tasks/${id}`, data),
  getStats: (slug) => api.get(`/v2/housekeeping/tenants/${slug}/hk-stats`),
};

// Lost & Found V2
export const lostFoundAPI = {
  list: (slug, params) => api.get(`/v2/lost-found/tenants/${slug}/items`, { params }),
  create: (slug, data) => api.post(`/v2/lost-found/tenants/${slug}/items`, data),
  update: (slug, id, data) => api.patch(`/v2/lost-found/tenants/${slug}/items/${id}`, data),
  delete: (slug, id) => api.delete(`/v2/lost-found/tenants/${slug}/items/${id}`),
  getStats: (slug) => api.get(`/v2/lost-found/tenants/${slug}/stats`),
};

// Social Dashboard V2
export const socialDashboardAPI = {
  getDashboard: (slug) => api.get(`/v2/social/tenants/${slug}/dashboard`),
  getUnifiedInbox: (slug, params) => api.get(`/v2/social/tenants/${slug}/unified-inbox`, { params }),
  getAllReviews: (slug, params) => api.get(`/v2/social/tenants/${slug}/all-reviews`, { params }),
  listModerationRules: (slug) => api.get(`/v2/social/tenants/${slug}/moderation-rules`),
  createModerationRule: (slug, data) => api.post(`/v2/social/tenants/${slug}/moderation-rules`, data),
  getAnalytics: (slug, params) => api.get(`/v2/social/tenants/${slug}/analytics`, { params }),
};

// Reports V2
export const reportsAPI = {
  departmentPerformance: (slug, params) => api.get(`/v2/reports/tenants/${slug}/department-performance`, { params }),
  guestSatisfaction: (slug, params) => api.get(`/v2/reports/tenants/${slug}/guest-satisfaction`, { params }),
  peakDemand: (slug, params) => api.get(`/v2/reports/tenants/${slug}/peak-demand`, { params }),
  staffProductivity: (slug, params) => api.get(`/v2/reports/tenants/${slug}/staff-productivity`, { params }),
  aiPerformance: (slug) => api.get(`/v2/reports/tenants/${slug}/ai-performance`),
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


// File Upload V2
export const uploadAPI = {
  guestUpload: (slug, formData) => api.post(`/v2/uploads/g/${slug}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  adminUpload: (slug, formData) => api.post(`/v2/uploads/tenants/${slug}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  guestFiles: (slug, params) => api.get(`/v2/uploads/g/${slug}/files`, { params }),
  adminFiles: (slug, params) => api.get(`/v2/uploads/tenants/${slug}/files`, { params }),
};

// Platform Integrations V2
export const platformsAPI = {
  list: (slug) => api.get(`/v2/platforms/tenants/${slug}/platforms`),
  get: (slug, platformId) => api.get(`/v2/platforms/tenants/${slug}/platforms/${platformId}`),
  configure: (slug, platformId, data) => api.post(`/v2/platforms/tenants/${slug}/platforms/${platformId}/configure`, data),
  disconnect: (slug, platformId) => api.post(`/v2/platforms/tenants/${slug}/platforms/${platformId}/disconnect`),
  sync: (slug, platformId) => api.post(`/v2/platforms/tenants/${slug}/platforms/${platformId}/sync`),
  reviews: (slug, platformId, params) => api.get(`/v2/platforms/tenants/${slug}/platforms/${platformId}/reviews`, { params }),
  getNotificationSettings: (slug) => api.get(`/v2/platforms/tenants/${slug}/notification-settings`),
  updateNotificationSettings: (slug, data) => api.put(`/v2/platforms/tenants/${slug}/notification-settings`, data),
  getNotificationLogs: (slug, params) => api.get(`/v2/platforms/tenants/${slug}/notification-logs`, { params }),
  testEmail: (slug, data) => api.post(`/v2/platforms/tenants/${slug}/test-email`, data),
  testSms: (slug, data) => api.post(`/v2/platforms/tenants/${slug}/test-sms`, data),
};
