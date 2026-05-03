import React, { useEffect, lazy, Suspense } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from './components/ui/sonner';
import { useAuthStore } from './lib/store';
import { Loader2 } from 'lucide-react';

import LoginPage from './pages/LoginPage';

const AdminLayout = lazy(() => import('./components/layout/AdminLayout'));

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const RequestsBoard = lazy(() => import('./pages/RequestsBoard'));
const OrdersBoard = lazy(() => import('./pages/OrdersBoard'));
const RoomsPage = lazy(() => import('./pages/RoomsPage'));
const TablesPage = lazy(() => import('./pages/TablesPage'));
const MenuPage = lazy(() => import('./pages/MenuPage'));
const ContactsPage = lazy(() => import('./pages/ContactsPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const InboxPage = lazy(() => import('./pages/InboxPage'));
const ReviewsPage = lazy(() => import('./pages/ReviewsPage'));
const OffersPage = lazy(() => import('./pages/OffersPage'));
const PropertiesPage = lazy(() => import('./pages/PropertiesPage'));
const PaymentPage = lazy(() => import('./pages/PaymentPage'));
const ConnectorsPage = lazy(() => import('./pages/ConnectorsPage'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
const BillingPage = lazy(() => import('./pages/BillingPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));
const CompliancePage = lazy(() => import('./pages/CompliancePage'));
const GrowthPage = lazy(() => import('./pages/GrowthPage'));
const SystemMetricsPage = lazy(() => import('./pages/SystemMetricsPage'));
const AuditLogPage = lazy(() => import('./pages/AuditLogPage'));
const AISalesPage = lazy(() => import('./pages/AISalesPage'));
const HousekeepingPage = lazy(() => import('./pages/HousekeepingPage'));
const LostFoundPage = lazy(() => import('./pages/LostFoundPage'));
const SLAManagementPage = lazy(() => import('./pages/SLAManagementPage'));
const SocialDashboardPage = lazy(() => import('./pages/SocialDashboardPage'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));
const NotificationCenterPage = lazy(() => import('./pages/NotificationCenterPage'));
const RestaurantReservationsPage = lazy(() => import('./pages/RestaurantReservationsPage'));
const GamificationPage = lazy(() => import('./pages/GamificationPage'));
const PushNotificationsPage = lazy(() => import('./pages/PushNotificationsPage'));
const ABTestingPage = lazy(() => import('./pages/ABTestingPage'));
const LoyaltyEnginePage = lazy(() => import('./pages/LoyaltyEnginePage'));
const ReferralLandingPage = lazy(() => import('./pages/ReferralLandingPage'));
const ReservationCalendar = lazy(() => import('./pages/admin/ReservationCalendar'));

const GuestRoomPanel = lazy(() => import('./pages/guest/GuestRoomPanel'));
const GuestTablePanel = lazy(() => import('./pages/guest/GuestTablePanel'));
const GuestChat = lazy(() => import('./pages/guest/GuestChat'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
});

function ProtectedRoute({ children }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function PageFallback() {
  return (
    <div className="flex items-center justify-center w-full h-[60vh]">
      <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
    </div>
  );
}

function App() {
  useEffect(() => {
    const removeBadge = () => {
      const badge = document.getElementById('emergent-badge');
      if (badge) badge.remove();
      document.querySelectorAll('a[href*="emergent.sh"]').forEach(el => el.remove());
    };
    const interval = setInterval(removeBadge, 500);
    removeBadge();
    return () => clearInterval(interval);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <div className="App dark">
        <BrowserRouter>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />

              <Route path="/" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
                <Route index element={<DashboardPage />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="requests" element={<RequestsBoard />} />
                <Route path="orders" element={<OrdersBoard />} />
                <Route path="rooms" element={<RoomsPage />} />
                <Route path="tables" element={<TablesPage />} />
                <Route path="menu" element={<MenuPage />} />
                <Route path="contacts" element={<ContactsPage />} />
                <Route path="inbox" element={<InboxPage />} />
                <Route path="reviews" element={<ReviewsPage />} />
                <Route path="offers" element={<OffersPage />} />
                <Route path="properties" element={<PropertiesPage />} />
                <Route path="connectors" element={<ConnectorsPage />} />
                <Route path="billing" element={<BillingPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="compliance" element={<CompliancePage />} />
                <Route path="growth" element={<GrowthPage />} />
                <Route path="system" element={<SystemMetricsPage />} />
                <Route path="audit" element={<AuditLogPage />} />
                <Route path="ai-sales" element={<AISalesPage />} />
                <Route path="housekeeping" element={<HousekeepingPage />} />
                <Route path="lost-found" element={<LostFoundPage />} />
                <Route path="sla" element={<SLAManagementPage />} />
                <Route path="social" element={<SocialDashboardPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="notifications" element={<NotificationCenterPage />} />
                <Route path="restaurant-reservations" element={<RestaurantReservationsPage />} />
                <Route path="calendar" element={<ReservationCalendar />} />
                <Route path="gamification" element={<GamificationPage />} />
                <Route path="push-notifications" element={<PushNotificationsPage />} />
                <Route path="ab-testing" element={<ABTestingPage />} />
                <Route path="loyalty-engine" element={<LoyaltyEnginePage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>

              <Route path="/g/:tenantSlug/room/:roomCode" element={<GuestRoomPanel />} />
              <Route path="/g/:tenantSlug/table/:tableCode" element={<GuestTablePanel />} />
              <Route path="/g/:tenantSlug/chat" element={<GuestChat />} />

              <Route path="/pay/:paymentLinkId" element={<PaymentPage />} />
              <Route path="/r/:referralCode" element={<ReferralLandingPage />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster position="top-right" theme="dark" />
      </div>
    </QueryClientProvider>
  );
}

export default App;
