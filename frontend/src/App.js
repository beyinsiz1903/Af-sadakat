import React, { useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from './components/ui/sonner';
import { useAuthStore } from './lib/store';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import RequestsBoard from './pages/RequestsBoard';
import OrdersBoard from './pages/OrdersBoard';
import RoomsPage from './pages/RoomsPage';
import TablesPage from './pages/TablesPage';
import MenuPage from './pages/MenuPage';
import ContactsPage from './pages/ContactsPage';
import SettingsPage from './pages/SettingsPage';
import InboxPage from './pages/InboxPage';
import ReviewsPage from './pages/ReviewsPage';
import OffersPage from './pages/OffersPage';
import ConnectorsPage from './pages/ConnectorsPage';

// Guest Pages
import GuestRoomPanel from './pages/guest/GuestRoomPanel';
import GuestTablePanel from './pages/guest/GuestTablePanel';
import GuestChat from './pages/guest/GuestChat';

// Layout
import AdminLayout from './components/layout/AdminLayout';

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

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="App dark">
        <BrowserRouter>
          <Routes>
            {/* Auth */}
            <Route path="/login" element={<LoginPage />} />
            
            {/* Admin/Staff Routes */}
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
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            
            {/* Guest Routes (no auth) */}
            <Route path="/g/:tenantSlug/room/:roomCode" element={<GuestRoomPanel />} />
            <Route path="/g/:tenantSlug/table/:tableCode" element={<GuestTablePanel />} />
            <Route path="/g/:tenantSlug/chat" element={<GuestChat />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" theme="dark" />
      </div>
    </QueryClientProvider>
  );
}

export default App;
