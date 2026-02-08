import React, { useEffect, useRef } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../lib/store';
import { useQuery } from '@tanstack/react-query';
import { propertiesAPI } from '../../lib/api';
import { WebSocketManager } from '../../lib/websocket';
import {
  LayoutDashboard, Inbox, MessageSquare, ClipboardList, UtensilsCrossed,
  BedDouble, TableProperties, BookOpen, Users, Settings, LogOut, Hotel, ChevronLeft, Menu,
  Star, Gift, Plug, Building2
} from 'lucide-react';
import { BarChart3, CreditCard, Shield, Share2, Server } from 'lucide-react';
import { FileText as AuditIcon } from 'lucide-react';
import { Bot } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { useState } from 'react';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/requests', label: 'Requests', icon: ClipboardList },
  { path: '/orders', label: 'Orders', icon: UtensilsCrossed },
  { path: '/reviews', label: 'Reviews', icon: Star },
  { type: 'separator', label: 'Management' },
  { path: '/properties', label: 'Properties', icon: Building2 },
  { path: '/rooms', label: 'Rooms', icon: BedDouble },
  { path: '/tables', label: 'Tables', icon: TableProperties },
  { path: '/menu', label: 'Menu', icon: BookOpen },
  { path: '/contacts', label: 'Contacts', icon: Users },
  { path: '/offers', label: 'Offers', icon: Gift },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { type: 'separator', label: 'System' },
  { path: '/billing', label: 'Billing', icon: CreditCard },
  { path: '/connectors', label: 'Integrations', icon: Plug },
  { path: '/compliance', label: 'Compliance', icon: Shield },
  { path: '/growth', label: 'Growth', icon: Share2 },
  { path: '/system', label: 'System', icon: Server },
  { path: '/audit', label: 'Audit Log', icon: AuditIcon },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export default function AdminLayout() {
  const { user, tenant, logout, activePropertyId, setActiveProperty } = useAuthStore();
  const navigate = useNavigate();
  const wsRef = useRef(null);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [propertyDropdownOpen, setPropertyDropdownOpen] = useState(false);

  const { data: properties = [] } = useQuery({
    queryKey: ['properties', tenant?.slug],
    queryFn: () => propertiesAPI.list(tenant?.slug).then(r => r.data),
    enabled: !!tenant?.slug,
  });

  // Set default property if not set
  useEffect(() => {
    if (properties.length > 0 && !activePropertyId) {
      setActiveProperty(properties[0].id);
    }
  }, [properties, activePropertyId, setActiveProperty]);

  const activeProperty = properties.find(p => p.id === activePropertyId) || properties[0];

  useEffect(() => {
    if (tenant?.id) {
      wsRef.current = new WebSocketManager(tenant.id);
      wsRef.current.connect();
      window.__ws = wsRef.current;
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [tenant?.id]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const filteredNav = navItems.filter(item => {
    if (!tenant) return true;
    if (item.path === '/rooms' && !tenant.hotel_enabled) return false;
    if (item.path === '/tables' && !tenant.restaurant_enabled) return false;
    if (item.path === '/menu' && !tenant.restaurant_enabled) return false;
    if (item.path === '/orders' && !tenant.restaurant_enabled) return false;
    return true;
  });

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))]">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:relative z-50 h-full flex flex-col
        bg-[hsl(var(--card))] border-r border-[hsl(var(--border))]
        transition-all duration-200 ease-out
        ${collapsed ? 'w-[72px]' : 'w-[260px]'}
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b border-[hsl(var(--border))]">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center flex-shrink-0">
              <Hotel className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <h1 className="text-sm font-semibold truncate">{tenant?.name || 'OmniHub'}</h1>
                <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">{tenant?.plan || 'Pro'} Plan</p>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto hidden lg:flex h-8 w-8"
            onClick={() => setCollapsed(!collapsed)}
            data-testid="sidebar-collapse-btn"
          >
            <ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
          </Button>
        </div>

        {/* Nav */}
        <ScrollArea className="flex-1 py-3">
          <nav className="space-y-1 px-3">
            {filteredNav.map((item, i) => {
              if (item.type === 'separator') {
                return !collapsed ? (
                  <div key={i} className="pt-4 pb-2">
                    <p className="text-[10px] uppercase tracking-wider text-[hsl(var(--muted-foreground))] px-3 font-medium">{item.label}</p>
                  </div>
                ) : <Separator key={i} className="my-3" />;
              }
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) => `
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                    transition-colors duration-150
                    ${isActive
                      ? 'bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]'
                      : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--foreground))]'
                    }
                    ${collapsed ? 'justify-center' : ''}
                  `}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              );
            })}
          </nav>
        </ScrollArea>

        {/* User */}
        <div className="border-t border-[hsl(var(--border))] p-3">
          <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'}`}>
            <div className="w-9 h-9 rounded-full bg-[hsl(var(--primary)/0.2)] flex items-center justify-center flex-shrink-0">
              <span className="text-sm font-semibold text-[hsl(var(--primary))]">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </span>
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.name}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] truncate capitalize">{user?.role}</p>
              </div>
            )}
            {!collapsed && (
              <Button variant="ghost" size="icon" className="h-8 w-8 flex-shrink-0" onClick={handleLogout} data-testid="logout-btn">
                <LogOut className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-16 border-b border-[hsl(var(--border))] flex items-center px-4 lg:px-6 bg-[hsl(var(--card))] flex-shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden mr-3"
            onClick={() => setMobileOpen(true)}
            data-testid="mobile-menu-btn"
          >
            <Menu className="w-5 h-5" />
          </Button>
          
          {/* Property Switcher */}
          {properties.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setPropertyDropdownOpen(!propertyDropdownOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--accent))] transition-colors text-sm"
                data-testid="property-switcher"
              >
                <Building2 className="w-4 h-4 text-[hsl(var(--primary))]" />
                <span className="font-medium max-w-[200px] truncate">{activeProperty?.name || 'Select Property'}</span>
                <svg className={`w-3 h-3 transition-transform ${propertyDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
              </button>
              {propertyDropdownOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setPropertyDropdownOpen(false)} />
                  <div className="absolute top-full left-0 mt-1 w-64 bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg shadow-xl z-20 py-1">
                    {properties.filter(p => p.is_active).map(prop => (
                      <button
                        key={prop.id}
                        onClick={() => { setActiveProperty(prop.id); setPropertyDropdownOpen(false); }}
                        className={`w-full text-left px-3 py-2 text-sm hover:bg-[hsl(var(--accent))] transition-colors flex items-center gap-2 ${prop.id === activePropertyId ? 'text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]' : ''}`}
                        data-testid={`property-option-${prop.slug}`}
                      >
                        <Building2 className="w-3 h-3" />
                        <span className="truncate">{prop.name}</span>
                        {prop.id === activePropertyId && <span className="ml-auto text-xs">&#10003;</span>}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          <div className="flex-1" />
          <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
            <div className="w-2 h-2 rounded-full bg-[hsl(var(--success))] pulse-dot" />
            <span>Connected</span>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
