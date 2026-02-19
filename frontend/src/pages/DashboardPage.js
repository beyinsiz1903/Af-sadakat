import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../lib/store';
import api from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ClipboardList, UtensilsCrossed, Users, MessageSquare, BedDouble, TableProperties, Star, Zap, TrendingUp, Gift, CalendarDays, ThumbsUp, ThumbsDown, Heart, Car, Shirt, Bell, Package } from 'lucide-react';

export default function DashboardPage() {
  const tenant = useAuthStore((s) => s.tenant);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats', tenant?.slug],
    queryFn: () => api.get(`/tenants/${tenant?.slug}/stats/enhanced`).then(r => r.data),
    enabled: !!tenant?.slug,
    refetchInterval: 15000,
  });

  if (isLoading || !stats) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div><h1 className="text-2xl font-bold">Dashboard</h1></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] animate-pulse">
              <CardContent className="p-6"><div className="h-16 bg-[hsl(var(--secondary))] rounded" /></CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const kpis = [
    { label: 'Open Requests', value: stats.requests.open, icon: ClipboardList, color: 'text-[hsl(var(--info))]', bgColor: 'bg-[hsl(var(--info)/0.1)]' },
    { label: 'Active Orders', value: stats.orders.active, icon: UtensilsCrossed, color: 'text-[hsl(var(--warning))]', bgColor: 'bg-[hsl(var(--warning)/0.1)]' },
    { label: 'Contacts', value: stats.contacts, icon: Users, color: 'text-[hsl(var(--primary))]', bgColor: 'bg-[hsl(var(--primary)/0.1)]' },
    { label: 'Conversations', value: stats.conversations, icon: MessageSquare, color: 'text-[hsl(var(--success))]', bgColor: 'bg-[hsl(var(--success)/0.1)]' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-[hsl(var(--muted-foreground))] text-sm mt-1">Welcome back. Here's what's happening at {tenant?.name}.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className="bg-[hsl(var(--card))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] transition-colors">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">{kpi.label}</p>
                    <p className="text-3xl font-bold mt-1" data-testid={`kpi-${kpi.label.toLowerCase().replace(/\s/g, '-')}`}>{kpi.value}</p>
                  </div>
                  <div className={`w-11 h-11 rounded-xl ${kpi.bgColor} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${kpi.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Request Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Total Requests</span>
              <Badge variant="secondary">{stats.requests.total}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">In Progress</span>
              <Badge className="bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.25)]">{stats.requests.in_progress}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Completed</span>
              <Badge className="bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.25)]">{stats.requests.done}</Badge>
            </div>
            {stats.avg_rating > 0 && (
              <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))]">
                <span className="text-sm flex items-center gap-1.5"><Star className="w-4 h-4 text-amber-400" /> Avg Rating</span>
                <span className="font-semibold">{stats.avg_rating}/5 <span className="text-xs text-[hsl(var(--muted-foreground))]">({stats.rating_count})</span></span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">Resources</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><BedDouble className="w-4 h-4" /> Rooms</span>
              <span className="text-sm font-medium">{stats.rooms} / {stats.limits?.max_rooms}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><TableProperties className="w-4 h-4" /> Tables</span>
              <span className="text-sm font-medium">{stats.tables} / {stats.limits?.max_tables}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><Users className="w-4 h-4" /> Users</span>
              <span className="text-sm font-medium">{stats.usage?.users} / {stats.limits?.max_users}</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-[hsl(var(--muted-foreground))]">AI Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm flex items-center gap-2"><Zap className="w-4 h-4 text-amber-400" /> AI Replies This Month</span>
              <span className="text-sm font-medium">{stats.usage?.ai_replies_this_month} / {stats.limits?.monthly_ai_replies}</span>
            </div>
            <div className="w-full bg-[hsl(var(--secondary))] rounded-full h-2 mt-2">
              <div
                className="bg-[hsl(var(--primary))] h-2 rounded-full transition-all"
                style={{ width: `${Math.min((stats.usage?.ai_replies_this_month / stats.limits?.monthly_ai_replies) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">Provider: Mock Template v1</p>
          </CardContent>
        </Card>
      </div>

      {/* Phase 3+4 Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Revenue</p>
                <p className="text-2xl font-bold mt-1">{new Intl.NumberFormat('tr-TR', {style:'currency', currency:'TRY'}).format(stats.revenue?.total || 0)}</p>
              </div>
              <div className="w-11 h-11 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Reviews</p>
                <p className="text-2xl font-bold mt-1">{stats.reviews?.total || 0}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-emerald-400 flex items-center gap-0.5"><ThumbsUp className="w-3 h-3" /> {stats.reviews?.sentiment?.positive || 0}</span>
                  <span className="text-xs text-rose-400 flex items-center gap-0.5"><ThumbsDown className="w-3 h-3" /> {stats.reviews?.sentiment?.negative || 0}</span>
                </div>
              </div>
              <div className="w-11 h-11 rounded-xl bg-amber-500/10 flex items-center justify-center">
                <Star className="w-5 h-5 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Loyalty Members</p>
                <p className="text-2xl font-bold mt-1">{stats.loyalty?.members || 0}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{stats.loyalty?.total_points_issued || 0} pts issued</p>
              </div>
              <div className="w-11 h-11 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <Gift className="w-5 h-5 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium">Reservations</p>
                <p className="text-2xl font-bold mt-1">{stats.reservations || 0}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{stats.offers || 0} offers sent</p>
              </div>
              <div className="w-11 h-11 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <CalendarDays className="w-5 h-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Service Operations Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: 'Spa Bookings', value: stats.spa_bookings?.pending || 0, sub: `${stats.spa_bookings?.total || 0} total`, icon: Heart, color: 'text-pink-400', bg: 'bg-pink-500/10' },
          { label: 'Restaurant Rez.', value: stats.restaurant_reservations?.pending || 0, sub: `${stats.restaurant_reservations?.confirmed || 0} confirmed`, icon: CalendarDays, color: 'text-violet-400', bg: 'bg-violet-500/10' },
          { label: 'Transport', value: stats.transport_requests?.pending || 0, sub: `${stats.transport_requests?.total || 0} total`, icon: Car, color: 'text-orange-400', bg: 'bg-orange-500/10' },
          { label: 'Laundry', value: stats.laundry_requests?.pending || 0, sub: `${stats.laundry_requests?.total || 0} total`, icon: Shirt, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
          { label: 'Notifications', value: stats.notifications_unread || 0, sub: 'unread', icon: Bell, color: 'text-amber-400', bg: 'bg-amber-500/10' },
          { label: 'Lost & Found', value: stats.lost_found?.stored || 0, sub: 'stored items', icon: Package, color: 'text-gray-400', bg: 'bg-gray-500/10' },
        ].map((item, i) => {
          const Icon = item.icon;
          return (
            <Card key={i} className="bg-[hsl(var(--card))] border-[hsl(var(--border))]">
              <CardContent className="p-3 text-center">
                <div className={`w-8 h-8 rounded-lg ${item.bg} flex items-center justify-center mx-auto mb-1`}>
                  <Icon className={`w-4 h-4 ${item.color}`} />
                </div>
                <p className="text-lg font-bold">{item.value}</p>
                <p className="text-[10px] text-[hsl(var(--muted-foreground))] font-medium">{item.label}</p>
                <p className="text-[9px] text-[hsl(var(--muted-foreground))]">{item.sub}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
